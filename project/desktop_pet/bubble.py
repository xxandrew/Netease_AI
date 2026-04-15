"""气泡文字弹出窗口"""
from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath


class BubbleWindow(QWidget):
    """在宠物头顶显示的气泡文字"""

    def __init__(self, text: str, pet_widget, duration_ms: int = 3000):
        super().__init__()
        self.text = text
        self.pet  = pet_widget

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 文字测量
        font = QFont("Microsoft YaHei UI", 10)
        from PyQt6.QtGui import QFontMetrics
        fm = QFontMetrics(font)
        tw = fm.horizontalAdvance(text)
        th = fm.height()

        pad_x, pad_y = 14, 10
        bw = min(tw + pad_x * 2, 260)
        bh = th + pad_y * 2 + 14  # +14 for tail

        self.resize(bw, bh)
        self._bw = bw
        self._bh = bh
        self._font = font
        self._text = text
        self._tail_h = 12

        self._reposition()
        self.show()

        # 淡出定时器
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)
        self._timer.start(duration_ms)

        # 淡入
        self.setWindowOpacity(0)
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setDuration(250)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def _reposition(self):
        """定位到宠物头顶"""
        pet_geo = self.pet.geometry()
        x = pet_geo.x() + pet_geo.width() // 2 - self._bw // 2
        y = pet_geo.y() - self._bh - 6
        # 不超出屏幕
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        x = max(0, min(x, screen.width()  - self._bw))
        y = max(0, min(y, screen.height() - self._bh))
        self.move(x, y)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        bw, bh = self._bw, self._bh - self._tail_h

        # 气泡矩形
        path = QPainterPath()
        path.addRoundedRect(0, 0, bw, bh, 12, 12)

        # 小三角尾巴（底部居中）
        tail_x = bw // 2
        path.moveTo(tail_x - 7, bh)
        path.lineTo(tail_x,     bh + self._tail_h)
        path.lineTo(tail_x + 7, bh)
        path.closeSubpath()

        # 填充
        p.setBrush(QBrush(QColor(255, 255, 255, 230)))
        p.setPen(QPen(QColor(180, 180, 220, 180), 1.5))
        p.drawPath(path)

        # 文字
        p.setFont(self._font)
        p.setPen(QPen(QColor(60, 60, 80)))
        p.drawText(
            QRect(10, 8, bw - 20, bh - 16),
            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
            self._text
        )
        p.end()

    def _fade_out(self):
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(400)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InQuad)
        anim.finished.connect(self.close)
        anim.start()
        self._fade_anim = anim
