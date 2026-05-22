# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller 打包配置 —— 桌面版
构建命令: pyinstaller build.spec
"""

from pathlib import Path

# 项目路径 —— 通过当前工作目录推导
SCRIPT_DIR = Path.cwd()
PROJECT_ROOT = SCRIPT_DIR.parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

if not FRONTEND_DIST.exists():
    # 备用：从 spec 文件所在目录推导
    FRONTEND_DIST = SCRIPT_DIR.parent / "frontend" / "dist"

BLOCK_CATALOG = None

a = Analysis(
    ["run_desktop.py"],
    pathex=[str(SCRIPT_DIR)],
    binaries=[],
    datas=[
        # 将前端构建产物打包进来
        (str(FRONTEND_DIST), "frontend_dist"),
    ],
    hiddenimports=[
        # SQLAlchemy
        "sqlalchemy.ext.asyncio",
        "sqlalchemy.sql.default_comparator",
        "sqlalchemy.pool",
        # APScheduler
        "apscheduler.triggers.cron",
        "apscheduler.triggers.interval",
        "apscheduler.triggers.date",
        # 数据库驱动
        "aiosqlite",
        # 数据源
        "akshare",
        "baostock",
        "pandas",
        "numpy",
        # HTTP
        "httpx",
        "h11",
        "httpcore",
        "sniffio",
        # AI / 缓存
        "openai",
        "cachetools",
        "dotenv",
        # 桌面 GUI
        "webview",
        "pythonnet",
        "clr_loader",
    ],
    hookspath=[],
    hooksconfig={},
    excludes=[
        # 排除不需要的 GUI 库以减少体积
        "PyQt5",
        "PySide2",
        "matplotlib",
        "PIL",
        "cv2",
        # Jupyter / IPython
        "IPython",
        "jupyter",
        "notebook",
        # 文档生成
        "sphinx",
        "docutils",
        # 测试框架
        "pytest",
        "unittest",
        # 调试
        "debugpy",
        "ptvsd",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="StockAnalyzer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # 不显示终端窗口（桌面应用模式）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="app.ico",          # 应用图标
)
