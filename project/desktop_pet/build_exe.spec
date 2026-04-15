# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for 桌面宠物 Alex

import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=[
        # 如果以后有 assets 目录（PNG帧/音效），取消下行注释
        # ('assets', 'assets'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'pandas', 'PIL',
        'scipy', 'tkinter', 'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='桌面宠物_Alex',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,           # 压缩体积（需要 upx 工具，没有也没关系）
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,      # 不显示黑色命令行窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets/icon.ico',   # 有图标文件时取消注释
)
