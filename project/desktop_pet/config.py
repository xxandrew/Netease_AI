"""台词库、表情配置、时段配置"""
from enum import Enum

# ── 角色基础尺寸 ─────────────────────────────
PET_SIZE   = 160          # 窗口宽 = 高（正方形）
PET_WIDTH  = PET_SIZE
PET_HEIGHT = PET_SIZE
PET_SCALE  = 1.0          # 可在右键菜单调整
# ── 状态枚举 ─────────────────────────────────
class PetState(Enum):
    IDLE       = "idle"
    CLICKED    = "clicked"
    HAPPY      = "happy"
    SURPRISED  = "surprised"
    SAD        = "sad"
    SLEEPY     = "sleepy"
    WAKE       = "wake"
    BLINK      = "blink"
    NIGHT      = "night"
    DRAG       = "drag"

# 向后兼容旧名称
State = PetState

# ── 时段问候语 ─────────────────────────────────
TIME_GREETINGS = {
    "morning":    (6,  11,  "早安！今天也要元气满满哦～ 🌅"),
    "noon":       (11, 14,  "中午了！记得吃饭哦，别忘了休息 🍱"),
    "afternoon":  (14, 18,  "下午好！来一杯咖啡提提神？ ☕"),
    "evening":    (18, 22,  "晚上好～今天辛苦了！ 🌙"),
    "night":      (22, 24,  "都这么晚了…注意休息哦 💤"),
    "midnight":   (0,  6,   "深夜了，身体是本钱，早点睡吧 🌛"),
}

# ── 台词库（按状态） ───────────────────────────
DIALOGUES: dict[PetState, list[str]] = {

    # ── 点击/互动（职场灰色幽默主线）────────────
    PetState.CLICKED: [
        # 摸鱼系
        "又来摸我？你的 KPI 同意了吗？",
        "点我一下，需求不会自己消失的。",
        "我在假装工作，你呢？",
        "别戳了，会议还没开完呢……",
        "你刚才盯着我看了三分钟，汇报怎么写？",
        "领导走了？那我们都放松一下。",
        "周五下午还不摸鱼，对得起这一周吗？",
        # 加班系
        "几点了……还没下班？正常。",
        "今天第几次被拉进临时群了？",
        "又加班？身体是革命的本钱，钱不是。",
        "你已经连续工作了很久，但绩效不会知道这些。",
        "「这个需求很简单」—— 说这话的人已经下班了。",
        "还好我没有 OKR，不然早卷死了。",
        # 会议系
        "这个会议本可以是一封邮件。",
        "拉齐一下，对齐一下，再同步一下……我睡了。",
        "「赋能」「抓手」「闭环」—— 宾果！",
        # 鸡汤反转系
        "加油！虽然加油也没用，但加油！",
        "你很棒，只是绩效不知道。",
        "每个困难都是成长机会—— HR 语录第47条。",
        "坚持住，年终奖还有……也许有……可能有。",
        "努力不一定有回报，但不努力一定很爽。",
        # 通勤系
        "地铁挤吗？我不用坐地铁，好羡慕你。",
        "上班路上想到辞职，下班路上想到房贷。",
    ],

    # ── 困意/打盹 ────────────────────────────────
    PetState.SLEEPY: [
        "PPT 还没做完……但眼皮先交工了……",
        "下午三点综合症，全公司同款……z z z",
        "哈欠—— 对不起，我在认真听会议。",
        "困是因为昨晚又开会到十一点……",
        "我只是在闭目养神……顺便摸鱼……",
    ],

    # ── 积极提示（右键菜单触发）──────────────────
    PetState.HAPPY: [
        "💡 划水要划出境界，摸鱼要摸出艺术。",
        "今天没被拉进临时群？好兆头！🎉",
        "需求冻结了！香槟先备着。",
        "下班准时打卡，人生赢家！",
        "Bug 不是你的，锅也不是你的，棒！",
        "喝杯水，你值得。（虽然工资不一定值。）",
    ],

    # ── 惊讶 ──────────────────────────────────────
    PetState.SURPRISED: [
        "！！需求又改了？！",
        "等等，这个我做过……怎么又回来了？",
        "今天居然准时开完了？我不信。",
        "发年终奖了？！先别激动，看完税后再说。",
    ],

    # ── 难过/emo ───────────────────────────────────
    PetState.SAD: [
        "review 被打回来了……没关系，再改第九版。",
        "感觉今天被 PUA 了……",
        "又是「方向没问题，细节再打磨一下」的一天。",
        "我只是想按时下班，怎么就这么难。",
    ],

    # ── 发呆 idle ─────────────────────────────────
    PetState.IDLE: [
        "（正在模拟思考状态……）",
        "（假装在看文档）",
        "（发呆中，请勿打扰）",
        "（在想要不要改简历）",
        "（发现屏幕右下角有个宠物）（那就是我）",
    ],
}

# 向后兼容旧名称
CLICK_LINES = DIALOGUES[PetState.CLICKED]

# ── 表情对应颜色（代码绘图模式）──────────────
EXPRESSION_COLORS = {
    PetState.IDLE:       "#7EC8E3",
    PetState.CLICKED:    "#FFB347",
    PetState.HAPPY:      "#98FB98",
    PetState.SURPRISED:  "#FFD700",
    PetState.SAD:        "#B0C4DE",
    PetState.SLEEPY:     "#DDA0DD",
    PetState.WAKE:       "#FFA07A",
    PetState.BLINK:      "#7EC8E3",
    PetState.NIGHT:      "#6A5ACD",
    PetState.DRAG:       "#87CEEB",
}

# ── 表情文字（emoji 方式） ─────────────────────
EXPRESSION_EMOJI = {
    PetState.IDLE:       "( ◕‿◕ )",
    PetState.CLICKED:    "( ≧▽≦ )",
    PetState.HAPPY:      "( ＾▽＾ )",
    PetState.SURPRISED:  "( °o° )",
    PetState.SAD:        "( ；_；)",
    PetState.SLEEPY:     "( -_- )zzZ",
    PetState.WAKE:       "( ＞＜ )",
    PetState.NIGHT:      "( ˘ω˘ )",
    PetState.DRAG:       "(  ˘³˘ )",
}

# ── 待机超时（秒）─────────────────────────────
IDLE_TIMEOUT_SEC = 60

# ── 动画帧间隔（毫秒/帧）────────────────────────
FRAME_INTERVAL = {
    PetState.IDLE:       800,
    PetState.CLICKED:    120,
    PetState.HAPPY:      150,
    PetState.SURPRISED:  100,
    PetState.SAD:        600,
    PetState.SLEEPY:     900,
    PetState.WAKE:       120,
    PetState.BLINK:      100,
    PetState.NIGHT:      700,
    PetState.DRAG:       200,
}

# ── 音效文件名（放在 assets/sounds/ 下）───────
SOUNDS = {
    "click":    "click.wav",
    "happy":    "happy.wav",
    "wake":     "wake.wav",
}