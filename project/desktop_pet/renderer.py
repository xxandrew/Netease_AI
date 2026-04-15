"""
像素风 2D 大脸渲染器
用 16×16 固定点阵（调色板索引）定义每帧表情，无渐变无阴影，硬核像素风
"""
import math
from PyQt6.QtGui  import QPainter, QColor, QPixmap
from PyQt6.QtCore import Qt, QRectF

from config import PetState, PET_SIZE

# ── 调色板（索引 → QColor）───────────────────────────────────
# 0 = 透明, 1 = 肤色, 2 = 肤色暗, 3 = 头发, 4 = 头发暗
# 5 = 眼白, 6 = 虹膜蓝, 7 = 瞳孔, 8 = 嘴/描边, 9 = 牙白
# 10= 腮红, 11= 舌头红, 12= 泪蓝, 13= 汗蓝, 14= 星黄, 15= 星粉
PAL = [
    QColor(  0,   0,   0,   0),   # 0 透明
    QColor(255, 210, 160, 255),   # 1 肤色
    QColor(220, 170, 120, 255),   # 2 肤暗
    QColor(200, 105,  30, 255),   # 3 头发橙
    QColor(140,  60,   5, 255),   # 4 头发暗
    QColor(255, 255, 255, 255),   # 5 眼白
    QColor( 70, 120, 200, 255),   # 6 虹膜
    QColor( 15,  12,  40, 255),   # 7 瞳孔/轮廓
    QColor( 35,  22,   8, 255),   # 8 嘴/描边
    QColor(255, 255, 255, 255),   # 9 牙白
    QColor(240, 150, 135, 200),   # 10 腮红
    QColor(220,  70,  80, 255),   # 11 舌红
    QColor( 80, 140, 255, 200),   # 12 泪蓝
    QColor(120, 190, 255, 220),   # 13 汗蓝
    QColor(255, 220,  40, 255),   # 14 星黄
    QColor(255, 110, 190, 255),   # 15 星粉
]

# ── 16×16 像素帧定义 ──────────────────────────────────────────
# 每行 16 个索引，共 16 行
# 布局：头发上 + 脸 + 头发侧 + 五官

def _F(s: str):
    """把多行字符串转成 16×16 整数列表，便于视觉编辑"""
    rows = [r for r in s.strip().split('\n') if r.strip()]
    result = []
    for r in rows:
        vals = r.strip().split()
        result.extend(int(v) for v in vals)
    return result

# ─── IDLE（微笑，平静）─────────────────────────────────────
FRAME_IDLE = _F("""
 0  3  3  3  3  3  3  3  3  3  3  3  3  3  0  0
 0  3  3  4  3  3  4  3  3  4  3  3  4  3  0  0
 3  3  1  1  1  1  1  1  1  1  1  1  1  3  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  1  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  2  3  0
 3  1  5  5  7  1  1  1  1  7  5  5  1  2  3  0
 3  1  5  6  7  1  1  1  1  7  6  5  1  2  3  0
 3  1  5  5  5  1  1  1  1  5  5  5  1  2  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  2  3  0
 3  1 10  1  1  1  1  1  1  1  1  1 10  2  3  0
 3  1  1  8  1  1  1  1  1  1  8  1  1  2  3  0
 3  1  1  1  8  8  8  8  8  8  1  1  1  2  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  2  3  0
 3  3  2  2  2  2  2  2  2  2  2  2  2  3  3  0
 0  3  3  3  3  3  3  3  3  3  3  3  3  3  0  0
 0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
""")

# ─── CLICKED / HAPPY（大笑，W嘴）────────────────────────────
FRAME_HAPPY = _F("""
 0  3  3  3  3  3  3  3  3  3  3  3  3  3  0  0
 0  3  3  4  3  3  4  3  3  4  3  3  4  3  0  0
 3  3  1  1  1  1  1  1  1  1  1  1  1  3  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  1  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  2  3  0
 3  1  5  5  7  1  1  1  1  7  5  5  1  2  3  0
 3  1  5  6  1  1  1  1  1  1  6  5  1  2  3  0
 3  1  5  5  5  1  1  1  1  5  5  5  1  2  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  2  3  0
 3  1 10  1  1  1  1  1  1  1  1  1 10  2  3  0
 3  1  1  8  1  8  1  8  1  8  1  8  1  2  3  0
 3  1  1  1  9  1  9  1  9  1  9  1  1  2  3  0
 3  1  1  1  8  8  8  8  8  8  8  1  1  2  3  0
 3  3  2  2  2  2  2  2  2  2  2  2  2  3  3  0
 0  3  3  3  3  3  3  3  3  3  3  3  3  3  0  0
 0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
""")

# ─── SLEEPY（困，闭眼线）────────────────────────────────────
FRAME_SLEEPY = _F("""
 0  3  3  3  3  3  3  3  3  3  3  3  3  3  0  0
 0  3  3  4  3  3  4  3  3  4  3  3  4  3  0  0
 3  3  1  1  1  1  1  1  1  1  1  1  1  3  3  0
 3  4  1  1  1  1  1  1  1  1  1  1  1  4  3  0
 3  4  1  1  1  1  1  1  1  1  1  1  1  2  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  2  3  0
 3  1  7  7  7  1  1  1  1  7  7  7  1  2  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  2  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  2  3  0
 3  1 10  1  1  1  1  1  1  1  1  1 10  2  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  2  3  0
 3  1  1  1  1  8  8  8  1  1  1  1  1  2  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  2  3  0
 3  3  2  2  2  2  2  2  2  2  2  2  2  3  3  0
 0  3  3  3  3  3  3  3  3  3  3  3  3  3  0  0
 0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
""")

# ─── SURPRISED（瞪眼，O嘴）──────────────────────────────────
FRAME_SURPRISED = _F("""
 0  3  3  3  3  3  3  3  3  3  3  3  3  3  0 13
 0  3  3  4  3  3  4  3  3  4  3  3  4  3  0 13
 3  3  1  1  1  1  1  1  1  1  1  1  1  3  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  1  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  2  3  0
 3  1  5  5  5  7  1  1  7  5  5  5  1  2  3  0
 3  1  5  6  6  7  1  1  7  6  6  5  1  2  3  0
 3  1  5  5  6  7  1  1  7  6  5  5  1  2  3  0
 3  1  5  5  5  7  1  1  7  5  5  5  1  2  3  0
 3  1 10  1  1  1  1  1  1  1  1  1 10  2  3  0
 3  1  1  1  8  8  8  8  8  8  1  1  1  2  3  0
 3  1  1  1  8 11 11 11 11  8  1  1  1  2  3  0
 3  1  1  1  8  8  8  8  8  8  1  1  1  2  3  0
 3  3  2  2  2  2  2  2  2  2  2  2  2  3  3  0
 0  3  3  3  3  3  3  3  3  3  3  3  3  3  0  0
 0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
""")

# ─── SAD（苦脸，sbitmap，倒嘴）────────────────────────────────
FRAME_SAD = _F("""
 0  3  3  3  3  3  3  3  3  3  3  3  3  3  0  0
 0  3  3  4  3  3  4  3  3  4  3  3  4  3  0  0
 3  3  1  1  1  1  1  1  1  1  1  1  1  3  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  1  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  2  3  0
 3  1  5  5  7  1  1  1  1  7  5  5  1  2  3  0
 3  1  5  6  7  1  1  1  1  7  6  5  1  2  3  0
 3  1  5  5  5  1  1  1  1  5  5  5  1  2  3  0
 3  1  1 12  1  1  1  1  1  1 12  1  1  2  3  0
 3  1 10 12  1  1  1  1  1  1 12  1 10  2  3  0
 3  1  1  1  8  8  8  8  8  8  1  1  1  2  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  2  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  2  3  0
 3  3  2  2  2  2  2  2  2  2  2  2  2  3  3  0
 0  3  3  3  3  3  3  3  3  3  3  3  3  3  0  0
 0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
""")

# ─── BLINK（眨眼，一帧）────────────────────────────────────
FRAME_BLINK = _F("""
 0  3  3  3  3  3  3  3  3  3  3  3  3  3  0  0
 0  3  3  4  3  3  4  3  3  4  3  3  4  3  0  0
 3  3  1  1  1  1  1  1  1  1  1  1  1  3  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  1  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  2  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  2  3  0
 3  1  7  7  7  1  1  1  1  7  7  7  1  2  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  2  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  2  3  0
 3  1 10  1  1  1  1  1  1  1  1  1 10  2  3  0
 3  1  1  8  1  1  1  1  1  1  8  1  1  2  3  0
 3  1  1  1  8  8  8  8  8  8  1  1  1  2  3  0
 3  1  1  1  1  1  1  1  1  1  1  1  1  2  3  0
 3  3  2  2  2  2  2  2  2  2  2  2  2  3  3  0
 0  3  3  3  3  3  3  3  3  3  3  3  3  3  0  0
 0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0
""")

# 状态 → 帧数据映射
STATE_FRAMES = {
    PetState.IDLE:       FRAME_IDLE,
    PetState.BLINK:      FRAME_BLINK,
    PetState.CLICKED:    FRAME_HAPPY,
    PetState.HAPPY:      FRAME_HAPPY,
    PetState.WAKE:       FRAME_HAPPY,
    PetState.SLEEPY:     FRAME_SLEEPY,
    PetState.NIGHT:      FRAME_SLEEPY,
    PetState.SURPRISED:  FRAME_SURPRISED,
    PetState.SAD:        FRAME_SAD,
    PetState.DRAG:       FRAME_IDLE,
}

GRID = 16   # 点阵大小


class PetRenderer:
    """像素风 2D 大脸渲染器（16×16 点阵查表绘制）"""

    def __init__(self, width: int = PET_SIZE, height: int = PET_SIZE):
        self._w = width
        self._h = height
        self._frame = 0

    def advance(self):
        self._frame += 1

    def reset_phase(self):
        self._frame = 0

    def draw(self, painter: QPainter, x: int, y: int, state: PetState):
        pix = self._render(state, self._frame)
        painter.drawPixmap(x, y, pix)

    def render(self, state: PetState, frame: int | None = None,
               scale: float = 1.0) -> QPixmap:
        if frame is not None:
            self._frame = frame
        return self._render(state, self._frame, scale)

    # ─────────────────────────────────────────────────────────
    def _render(self, state: PetState, frame: int,
                scale: float = 1.0) -> QPixmap:
        # 眨眼：每 18 帧换一次 blink 帧（持续 1 帧）
        blink_states = (PetState.IDLE, PetState.HAPPY,
                        PetState.CLICKED, PetState.DRAG)
        if state in blink_states and (frame % 18 == 0):
            grid_data = FRAME_BLINK
        else:
            grid_data = STATE_FRAMES.get(state, FRAME_IDLE)

        # 速度系数（用于浮动动画）
        spd = {
            PetState.CLICKED: 2.0, PetState.SURPRISED: 2.2,
            PetState.HAPPY: 1.5,   PetState.WAKE: 1.6,
            PetState.SLEEPY: 0.3,  PetState.NIGHT: 0.3,
            PetState.SAD: 0.4,
        }.get(state, 0.55)
        f = frame * spd

        # 上下浮动偏移（像素）
        bob = math.sin(f * 0.14) * 2.5
        if state == PetState.CLICKED:
            bob += math.sin(f * 1.0) * 1.5   # 点击时额外抖动
        if state in (PetState.SLEEPY, PetState.NIGHT):
            bob += 2.0

        w = int(self._w * scale)
        h = int(self._h * scale)
        cell_w = w / GRID
        cell_h = h / GRID

        pixmap = QPixmap(w, h)
        pixmap.fill(Qt.GlobalColor.transparent)
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        p.setPen(Qt.PenStyle.NoPen)

        # 绘制每个像素格
        for row in range(GRID):
            for col in range(GRID):
                idx = grid_data[row * GRID + col]
                if idx == 0:
                    continue   # 透明跳过
                color = PAL[idx]
                x_px = col * cell_w
                y_px = row * cell_h + bob   # 应用浮动
                p.setBrush(color)
                p.drawRect(QRectF(x_px, y_px, cell_w, cell_h))

        # ZZZ 特效（困意状态）
        if state in (PetState.SLEEPY, PetState.NIGHT):
            self._draw_zzz(p, frame, w, h, cell_w)

        # 星星特效（开心/点击）
        if state in (PetState.HAPPY, PetState.CLICKED,
                     PetState.WAKE, PetState.SURPRISED):
            self._draw_stars(p, frame, w, h, cell_w)

        p.end()
        return pixmap

    def _draw_zzz(self, p, frame, w, h, cell):
        """简单像素 z 字母"""
        import random
        font_size = max(8, int(cell * 1.4))
        from PyQt6.QtGui import QFont
        from PyQt6.QtCore import QPointF
        p.setFont(QFont("Consolas", font_size, QFont.Weight.Bold))
        for i, ch in enumerate("zzZ"):
            alpha = 80 + i * 70
            rise  = (frame // 6 + i) % 6
            c = QColor(140, 85, 210, alpha)
            p.setPen(c)
            p.drawText(QPointF(
                w * 0.68 + i * cell * 1.6,
                h * 0.20 - rise * cell * 0.7 - i * cell * 1.1
            ), ch)
        p.setPen(Qt.PenStyle.NoPen)

    def _draw_stars(self, p, frame, w, h, cell):
        """像素十字星"""
        import random
        random.seed(frame % 8)
        star_pal = [QColor(255,220,40), QColor(255,110,190), QColor(90,225,110)]
        sz = max(2, int(cell * 0.7))
        for i in range(3):
            sx = random.randint(int(cell * 0.5), w - int(cell * 2.5))
            sy = random.randint(int(cell * 0.2), int(h * 0.28))
            alpha = max(30, 200 - (frame % 8) * 20)
            c = QColor(star_pal[i % 3])
            c.setAlpha(alpha)
            p.setBrush(c)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRect(sx,      sy,      sz, sz)
            p.drawRect(sx - sz, sy + sz, sz, sz)
            p.drawRect(sx + sz, sy + sz, sz, sz)
            p.drawRect(sx,      sy+sz*2, sz, sz)
            p.drawRect(sx,      sy + sz, sz, sz)