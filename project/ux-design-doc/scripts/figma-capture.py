#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
figma-capture.py — 从 Figma 链接批量导出顶层 Frame，存入 case/design/
用法（在 case 目录下运行，必须加 -X utf8）：
    python -X utf8 ../scripts/figma-capture.py <figma_url>

依赖：FIGMA_TOKEN 环境变量
输出：
    design/<序号>-<frame名>.png
    structure.json（frame名 → 文件名映射，重导时复用文件名避免断图）
"""

import os
import sys
import re
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

FIGMA_TOKEN = os.environ.get("FIGMA_TOKEN")
if not FIGMA_TOKEN:
    print("❌ 未找到 FIGMA_TOKEN 环境变量，请先执行：set FIGMA_TOKEN=<你的token>")
    sys.exit(1)
API_BASE = "https://api.figma.com/v1"


# ── API ──────────────────────────────────────────────────────────────────────

def api_get(endpoint, params=None, timeout=30):
    url = f"{API_BASE}/{endpoint}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"X-Figma-Token": FIGMA_TOKEN})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ── URL 解析 ──────────────────────────────────────────────────────────────────

def parse_figma_url(url):
    file_match = re.search(r'figma\.com/(?:file|design)/([a-zA-Z0-9]+)', url)
    file_key = file_match.group(1) if file_match else None
    node_match = re.search(r'node-id=([a-zA-Z0-9%:+-]+)', url)
    node_id = None
    if node_match:
        node_id = node_match.group(1).replace('%3A', ':').replace('%2D', '-')
        # URL 格式 2960-9281 → API 格式 2960:9281（纯数字+短横线的情况）
        if re.match(r'^\d+-\d+$', node_id):
            node_id = node_id.replace('-', ':')
    return file_key, node_id


# ── Frame 结构 ────────────────────────────────────────────────────────────────

def find_node(node, target_id):
    if node.get("id") == target_id:
        return node
    for child in node.get("children", []):
        found = find_node(child, target_id)
        if found:
            return found
    return None


def get_top_frames(file_key, node_id=None):
    """返回目标节点下的直接子 Frame 列表。COMPONENT_SET 自动展开为各 variant。
    同时返回文件级 components 字典（nodeId → {key, name, ...}），供导出 component-keys.json 使用。"""
    print("正在读取 Figma 文件结构…")
    data = api_get(f"files/{file_key}")
    doc = data["document"]
    # 顶层 components 字典：nodeId → {key, name, ...}
    get_top_frames._components = data.get("components", {})

    if node_id:
        parent = find_node(doc, node_id)
        if not parent:
            print(f"❌ 未找到节点 {node_id}")
            sys.exit(1)
        print(f"节点：{parent.get('name', node_id)}（类型：{parent.get('type')}）")
    else:
        pages = doc.get("children", [])
        if not pages:
            print("❌ 文件无页面")
            sys.exit(1)
        parent = pages[0]
        print(f"页面：{parent['name']}（未指定节点，使用首页）")

    raw = [
        c for c in parent.get("children", [])
        if c.get("type") in ("FRAME", "COMPONENT", "COMPONENT_SET", "GROUP", "SECTION")
    ]

    frames = []
    for c in raw:
        _collect_frames(c, "", frames)

    return frames

# 用函数属性存储最近一次调用的 components 字典（避免修改返回值破坏调用方）
get_top_frames._components = {}


def _collect_frames(node, prefix, result):
    """递归收集可导出的 Frame/Component，展开 GROUP/SECTION，拆分 COMPONENT_SET variant。"""
    t = node.get("type")
    display = f"{prefix}{node['name']}" if prefix else node["name"]

    if t in ("GROUP", "SECTION"):
        # 透明容器：递归展开，前缀追加组名
        for child in node.get("children", []):
            _collect_frames(child, f"{display} / ", result)

    elif t == "COMPONENT_SET":
        variants = [v for v in node.get("children", []) if v.get("type") == "COMPONENT"]
        if variants:
            for v in variants:
                v["_display_name"] = f"{display} / {v['name']}"
                result.append(v)
        else:
            node["_display_name"] = display
            result.append(node)

    elif t in ("FRAME", "COMPONENT"):
        node["_display_name"] = display
        result.append(node)
    # 其他类型（TEXT、VECTOR 等）跳过


# ── 文字提取 ─────────────────────────────────────────────────────────────────

def _collect_texts(node, results, parent_name=""):
    """递归收集 TEXT 节点的文字内容，附带直接父层名称。"""
    t = node.get("type")
    name = node.get("name", "")
    if t == "TEXT":
        content = node.get("characters", "").strip()
        if content:
            results.append({"parent": parent_name, "content": content})
    else:
        for child in node.get("children", []):
            _collect_texts(child, results, parent_name=name)


def print_frame_texts(frame):
    """打印一个 Frame 内所有文字内容（按直接父层分组，去重）。"""
    raw = []
    _collect_texts(frame, raw)

    # 按 parent 分组，同组内去重
    groups = {}
    seen_content = set()
    for item in raw:
        content = item["content"]
        if content in seen_content:
            continue
        seen_content.add(content)
        p = item["parent"] or "—"
        groups.setdefault(p, []).append(content)

    print(f"\n  📝 文字内容（共 {len(seen_content)} 条）：")
    for parent, texts in groups.items():
        joined = "　".join(f"「{t}」" for t in texts)
        print(f"    [{parent}]  {joined}")


# ── 导出 ──────────────────────────────────────────────────────────────────────

BATCH_SIZE = 5       # 每批最多请求数量
MAX_RETRY  = 3       # 失败重试次数
RETRY_WAIT = 3       # 初始等待秒数（指数退避）

def fetch_image_urls(file_key, frame_ids, scale=1):
    """分批（每批 BATCH_SIZE 个）获取图片 URL，失败自动 retry（指数退避）。"""
    result = {}
    batches = [frame_ids[i:i + BATCH_SIZE] for i in range(0, len(frame_ids), BATCH_SIZE)]
    for b_idx, batch in enumerate(batches, 1):
        print(f"  📡 请求第 {b_idx}/{len(batches)} 批（{len(batch)} 个节点）…")
        for attempt in range(1, MAX_RETRY + 1):
            try:
                ids_str = ",".join(batch)
                data = api_get(f"images/{file_key}",
                               {"ids": ids_str, "format": "png", "scale": scale},
                               timeout=60)
                if data.get("err"):
                    raise RuntimeError(f"Figma API 错误：{data['err']}")
                result.update(data.get("images", {}))
                break
            except Exception as e:
                if attempt < MAX_RETRY:
                    wait = RETRY_WAIT * (2 ** (attempt - 1))
                    print(f"  ⚠️  第 {b_idx} 批第 {attempt} 次失败（{e}），{wait}s 后重试…")
                    time.sleep(wait)
                else:
                    print(f"  ❌ 第 {b_idx} 批重试 {MAX_RETRY} 次均失败，跳过该批：{e}")
    return result


def download_image(url):
    with urllib.request.urlopen(url) as resp:
        return resp.read()


# ── 文件名 ────────────────────────────────────────────────────────────────────

def safe_filename(name, index, existing_filenames=None):
    """序号-名称.png，去掉 Windows 非法字符；文件名冲突时自动追加 _2、_3…"""
    safe = re.sub(r'[\\/:*?"<>|]', '', name).strip()
    safe = re.sub(r'\s+', '-', safe)
    base = f"{index:02d}-{safe}"
    candidate = f"{base}.png"
    if existing_filenames is not None:
        counter = 2
        while candidate in existing_filenames:
            candidate = f"{base}_{counter}.png"
            counter += 1
        existing_filenames.add(candidate)
    return candidate


# ── 主流程 ────────────────────────────────────────────────────────────────────

def parse_selection(choice_str, total):
    """解析用户输入，返回 1-based 编号列表"""
    indices = []
    for part in choice_str.split():
        if '-' in part:
            a, b = part.split('-', 1)
            indices.extend(range(int(a), int(b) + 1))
        else:
            indices.append(int(part))
    return sorted(set(i for i in indices if 1 <= i <= total))


def main():
    if not FIGMA_TOKEN:
        print("❌ 未设置 FIGMA_TOKEN 环境变量")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("用法：")
        print("  列清单： python -X utf8 ../scripts/figma-capture.py <figma_url>")
        print("  导出：   python -X utf8 ../scripts/figma-capture.py <figma_url> 1 3 5")
        print("  导出范围：python -X utf8 ../scripts/figma-capture.py <figma_url> 1-5")
        print("  全部导出：python -X utf8 ../scripts/figma-capture.py <figma_url> all")
        sys.exit(1)

    # 解析 --text 参数（文字提取模式，不下载图片）
    raw_args = sys.argv[2:]
    text_mode = "--text" in raw_args
    if text_mode:
        raw_args = [a for a in raw_args if a != "--text"]

    # 解析 --scale 参数
    scale = 1
    if "--scale" in raw_args:
        idx = raw_args.index("--scale")
        try:
            scale = float(raw_args[idx + 1])
            raw_args = [a for i, a in enumerate(raw_args) if i != idx and i != idx + 1]
        except (IndexError, ValueError):
            print("❌ --scale 参数格式错误，用法：--scale 2")
            sys.exit(1)

    url = sys.argv[1]
    selection_args = raw_args  # 可选：编号参数

    file_key, node_id = parse_figma_url(url)

    if not file_key:
        print("❌ 无法从 URL 解析 file_key，请检查链接格式")
        sys.exit(1)

    print(f"📎 file_key：{file_key}" + (f"  node_id：{node_id}" if node_id else ""))

    # 获取 Frame 列表（同时填充 _get_top_frames._components）
    frames = get_top_frames(file_key, node_id)
    components_map = get_top_frames._components  # {nodeId: {key, name, ...}}

    if not frames:
        print("❌ 未找到任何 Frame（检查节点类型或页面是否为空）")
        sys.exit(1)

    # 展示清单（始终展示）
    print(f"\n共找到 {len(frames)} 个 Frame：")
    for i, f in enumerate(frames, 1):
        if selection_args:
            all_sel = selection_args == ["all"] or i in parse_selection(" ".join(selection_args), len(frames))
            mark = "☑" if all_sel else "☐"
        else:
            mark = "  "
        print(f"  {mark} {i:3d}.  {f['_display_name']}")

    # 无参数 → 仅列清单，退出
    if not selection_args:
        print("\n👆 仅列出清单。导出时请附编号，例如：")
        print(f"   python -X utf8 ../scripts/figma-capture.py \"<url>\" 1 2 3")
        print(f"   python -X utf8 ../scripts/figma-capture.py \"<url>\" 1-7")
        print(f"   python -X utf8 ../scripts/figma-capture.py \"<url>\" all")
        sys.exit(0)

    # 解析选择
    if selection_args == ["all"]:
        selected_indices = list(range(1, len(frames) + 1))
    else:
        selected_indices = parse_selection(" ".join(selection_args), len(frames))

    if not selected_indices:
        print("❌ 未匹配到有效编号，退出")
        sys.exit(0)

    selected = [frames[i - 1] for i in selected_indices]

    # --text 模式：输出文字内容，不下载图片
    if text_mode:
        for i, frame in zip(selected_indices, selected):
            print(f"\n[{i}] {frame['_display_name']}")
            print_frame_texts(frame)
        sys.exit(0)

    print(f"\n已选 {len(selected)} 个 Frame，开始导出…")

    # 创建 design 目录
    design_dir = Path("design")
    design_dir.mkdir(exist_ok=True)

    # 读取已有 structure.json
    structure_path = Path("structure.json")
    structure = {}
    if structure_path.exists():
        with open(structure_path, "r", encoding="utf-8") as fp:
            structure = json.load(fp)

    # 批量获取图片 URL（分批 + retry）
    frame_ids = [f["id"] for f in selected]
    print(f"导出分辨率：{scale}x")
    image_urls = fetch_image_urls(file_key, frame_ids, scale)

    # 下载并保存
    saved = 0
    errors = 0
    used_filenames = set(structure.values())   # D: 已占用文件名集合，用于去重
    for seq, (frame, fid) in enumerate(zip(selected, frame_ids), 1):
        img_url = image_urls.get(fid)
        if not img_url:
            print(f"  ⚠️  [{seq}] {frame['name']} — 无图片 URL，跳过")
            errors += 1
            continue

        # 复用已有文件名（避免断图），否则新建（D: 传入 used_filenames 去重）
        display_name = frame["_display_name"]
        filename = structure.get(display_name) or safe_filename(
            display_name, selected_indices[seq - 1], used_filenames
        )

        try:
            img_data = download_image(img_url)
            filepath = design_dir / filename
            with open(filepath, "wb") as fp:
                fp.write(img_data)
            structure[display_name] = filename
            print(f"  ✅  {display_name}  →  design/{filename}")
            saved += 1
        except Exception as e:
            print(f"  ❌  {frame['name']} 下载失败：{e}")
            errors += 1

    # 写回 structure.json
    with open(structure_path, "w", encoding="utf-8") as fp:
        json.dump(structure, fp, ensure_ascii=False, indent=2)

    # 写 frame-map.json（界面名 → nodeId + 文件名，供 md2docjson 生成 Figma 文档 JSON 使用）
    frame_map_path = Path("frame-map.json")
    frame_map = []
    if frame_map_path.exists():
        with open(frame_map_path, "r", encoding="utf-8") as fp:
            try:
                existing = json.load(fp)
                frame_map = existing.get("frames", [])
            except Exception:
                frame_map = []
    # 用 nodeId 做 key 去重更新（保留未本次导出的条目）
    existing_ids = {e["nodeId"]: e for e in frame_map}
    for seq, (frame, fid) in enumerate(zip(selected, frame_ids), 1):
        display_name = frame["_display_name"]
        filename = structure.get(display_name, "")
        existing_ids[fid] = {
            "index": selected_indices[seq - 1],
            "name": display_name,
            "nodeId": fid,
            "file": f"design/{filename}" if filename else ""
        }
    merged = sorted(existing_ids.values(), key=lambda x: x["index"])
    frame_map_data = {
        "figma_url": url,
        "file_key": file_key,
        "frames": merged
    }
    with open(frame_map_path, "w", encoding="utf-8") as fp:
        json.dump(frame_map_data, fp, ensure_ascii=False, indent=2)

    # 写 flat-map.json（平坦格式 {uiName: figmaFrameName}，供 md2docjson.mjs 直接使用）
    # key = Figma frame 名称，value = 同名（用户可手动改 key 来对齐 MD 里的 uiName）
    flat_map_path = Path("flat-map.json")
    flat_map = {}
    if flat_map_path.exists():
        try:
            with open(flat_map_path, "r", encoding="utf-8") as fp:
                flat_map = json.load(fp)
        except Exception:
            flat_map = {}
    # 追加/更新本次导出的条目（不覆盖用户手动改过的 key）
    for frame in merged:
        name = frame["name"]
        if name not in flat_map:
            flat_map[name] = name     # 默认 key = value = Figma frame 名称
    with open(flat_map_path, "w", encoding="utf-8") as fp:
        json.dump(flat_map, fp, ensure_ascii=False, indent=2)

    # 写 component-keys.json（{display_name: componentKey}，供插件用 importComponentByKeyAsync）
    comp_keys = {}
    for frame in merged:
        fid   = frame["nodeId"]
        dname = frame["name"]
        cinfo = components_map.get(fid)
        if cinfo and cinfo.get("key"):
            comp_keys[dname] = cinfo["key"]
    if comp_keys:
        ck_path = Path("component-keys.json")
        # 读取已有数据，合并更新（保留未本次导出的条目）
        existing_ck = {}
        if ck_path.exists():
            try:
                with open(ck_path, "r", encoding="utf-8") as fp:
                    existing_ck = json.load(fp)
            except Exception:
                existing_ck = {}
        existing_ck.update(comp_keys)
        with open(ck_path, "w", encoding="utf-8") as fp:
            json.dump(existing_ck, fp, ensure_ascii=False, indent=2)
        print(f"🔑 component-keys.json 已更新（{len(comp_keys)} 个 component key）。")
    else:
        print("⚠️  未找到 component key（确认界面已在 Figma 中转为 Component）。")

    print(f"\n完成！导出 {saved} 张" + (f"，{errors} 个失败" if errors else "") + "，structure.json 已更新。")
    print(f"📍 frame-map.json 已更新（{len(merged)} 个界面，含 nodeId）。")
    print(f"📍 flat-map.json 已更新（{len(flat_map)} 条，key=Figma名称，可手动改 key 对齐 MD 的 uiName）。")


if __name__ == "__main__":
    main()
