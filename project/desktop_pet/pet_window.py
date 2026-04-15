"""
桌面宠物主窗口
- 透明无边框，常驻顶层
- 左键拖动，右键菜单，左键单击触发互动
- 嵌入 PetRenderer 实现帧动画
"""
import random
from PyQt6.QtWidgets import QWidget, QApplication, QMenu
from PyQt6.QtCore    import Qt, QTimer, QPoint
from PyQt6.QtGui     import QPainter

from config   import PetState, DIALOGUES, PET_SIZE
from renderer import PetRenderer
from bubble   import BubbleWindow


class PetWindow(QWidget):

    def __init__(self):
        super().__init__()
        self._renderer = PetRenderer(PET_SIZE, PET_SIZE)

        # ── 窗口属性 ──────────────────────────────────────────
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint     |
            Qt.WindowType.WindowStaysOnTopHint    |
            Qt.WindowType.Tool                    # 不在任务栏显示
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(PET_SIZE, PET_SIZE)

        # 初始位置：屏幕右下角
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - PET_SIZE - 40,
                  screen.height() - PET_SIZE - 60)

        # ── 状态 ──────────────────────────────────────────────
        self._state  = PetState.IDLE
        self._bubble = None           # 当前气泡实例
        self._drag_pos: QPoint | None = None

        # ── 动画主循环 ────────────────────────────────────────
        # 平时 80ms(≈12fps)，点击时切到 30ms(≈33fps)
        self._frame_timer = QTimer(self)
        self._frame_timer.timeout.connect(self._on_frame)
        self._frame_timer.start(80)    # 默认慢速

        # ── 闲置行为定时器（随机出现随机状态） ──────────────
        self._idle_timer = QTimer(self)
        self._idle_timer.timeout.connect(self._random_idle)
        self._idle_timer.start(12000)  # 每 12 秒触发一次

        # ── 状态复位定时器（单次） ────────────────────────────
        self._reset_timer = QTimer(self)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.timeout.connect(self._reset_to_idle)

        self.show()

    # ─────────────────────────── 绘制 ────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._renderer.draw(p, 0, 0, self._state)
        p.end()

    def _on_frame(self):
        self._renderer.advance()
        self.update()

    # ─────────────────────────── 交互 ────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._on_click()

        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            self.move(new_pos)
            # 同步移动气泡
            if self._bubble and self._bubble.isVisible():
                self._bubble._reposition()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def _on_click(self):
        """左键单击 → 切换状态 + 弹出气泡"""
        # 切换到点击状态
        self._set_state(PetState.CLICKED)
        self._reset_timer.start(1500)

        # 弹出气泡（关掉旧的）
        if self._bubble and self._bubble.isVisible():
            self._bubble.close()
        text = random.choice(DIALOGUES[PetState.CLICKED])
        self._bubble = BubbleWindow(text, self, duration_ms=3000)

    def _random_idle(self):
        """随机触发眨眼/睡意等闲置行为"""
        if self._state != PetState.IDLE:
            return
        roll = random.random()
        if roll < 0.35:
            self._set_state(PetState.BLINK)
            self._reset_timer.start(600)
        elif roll < 0.55:
            self._set_state(PetState.SLEEPY)
            self._reset_timer.start(4000)
            text = random.choice(DIALOGUES[PetState.SLEEPY])
            if self._bubble is None or not self._bubble.isVisible():
                self._bubble = BubbleWindow(text, self, duration_ms=3500)

    # ── 动画速度配置（毫秒/帧）──────────────────
    _ANIM_SPEED = {
        PetState.IDLE:      80,    # 慢悠悠晃动
        PetState.BLINK:     80,
        PetState.SLEEPY:    100,   # 昏昏欲睡，更慢
        PetState.NIGHT:     100,
        PetState.SAD:       90,
        PetState.CLICKED:   28,    # 点击：活泼快速
        PetState.HAPPY:     32,
        PetState.SURPRISED: 25,
        PetState.WAKE:      30,
        PetState.DRAG:      40,
    }

    def _set_state(self, state: PetState):
        self._state = state
        self._renderer.reset_phase()
        # 切换帧率
        interval = self._ANIM_SPEED.get(state, 80)
        self._frame_timer.setInterval(interval)

    def _reset_to_idle(self):
        self._set_state(PetState.IDLE)

    # ─────────────────────────── 右键菜单 ────────────────────
    def _show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #2a2a3a;
                border: 1px solid #5050a0;
                border-radius: 6px;
                color: #eee;
                font-size: 12px;
            }
            QMenu::item:selected { background: #5050a0; border-radius: 4px; }
            QMenu::item { padding: 5px 18px; }
        """)

        hello_action  = menu.addAction("👋 打个招呼")
        tip_action    = menu.addAction("💡 给个提示")
        menu.addSeparator()
        quit_action   = menu.addAction("❌ 关闭宠物")

        action = menu.exec(pos)

        if action == hello_action:
            self._set_state(PetState.CLICKED)
            self._reset_timer.start(1500)
            text = random.choice(DIALOGUES[PetState.CLICKED])
            if self._bubble and self._bubble.isVisible():
                self._bubble.close()
            self._bubble = BubbleWindow(text, self, duration_ms=3000)

        elif action == tip_action:
            self._set_state(PetState.HAPPY)
            self._reset_timer.start(2000)
            text = random.choice(DIALOGUES.get(PetState.HAPPY, ["💡 今天也要加油哦！"]))
            if self._bubble and self._bubble.isVisible():
                self._bubble.close()
            self._bubble = BubbleWindow(text, self, duration_ms=4000)

        elif action == quit_action:
            QApplication.quit()
