"""
desktop_pet — 桌面宠物启动入口
运行: python main.py
打包: pyinstaller --noconsole --onefile main.py
"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui     import QIcon

from pet_window import PetWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("桌面宠物")
    app.setQuitOnLastWindowClosed(False)   # 关掉气泡窗口时不退出

    pet = PetWindow()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
