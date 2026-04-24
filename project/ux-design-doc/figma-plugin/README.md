# G79 交互文档生成 · Figma 插件

版本：v2.2.0

---

## 安装插件

1. 打开 Figma 桌面版
2. 菜单 → **Plugins** → **Development** → **Import plugin from manifest…**
3. 选择本目录下的 `manifest.json`
4. 插件出现在 **Plugins → Development → 文档助手**

> ⚠️ 插件需要加载你 Figma 文件中的**组件库**，请确保已在该文件中引用了 G79 文档模板库。

---

## 使用流程

```
interaction-spec.md
      ↓
node ../scripts/md2docjson.mjs    → figma-doc.json
      ↓
打开 Figma 插件「文档助手」
粘贴 figma-doc.json 内容 → 点击「生成文档」
      ↓
Figma 画布自动渲染完整交互文档 ✅
```

### 第一步：生成 JSON

在 case 目录下运行：

```bash
node ../scripts/md2docjson.mjs interaction-spec.md
```

生成 `figma-doc.json`，会自动在 VSCode 中打开预览。

### 第二步：准备 Figma 文件

- 打开你的 Figma 交互稿文件
- 确认文件中已引入 G79 文档模板组件库
- 将所有需要展示的界面已转为 **Component** 或 **Variant**

### 第三步：运行插件

1. 打开插件「文档助手」
2. 将 `figma-doc.json` 的全部内容粘贴到输入框
3. 点击「生成文档」
4. 文档自动渲染在当前页面 🎉

---

## 注意事项

| 项目 | 说明 |
|------|------|
| **必须用桌面版** | 浏览器版 Figma 不支持 Development 插件 |
| **组件必须在当前页** | 插件只扫描当前 Page，不跨页 |
| **界面需是 Component/Variant** | Frame 会被忽略，转成 Component 后 componentKey 才有效 |
| **每次修改插件后** | 需回到 `others/figma-plugin-doc/` 重新 `npm run build`，再覆盖 `dist/` 文件 |
