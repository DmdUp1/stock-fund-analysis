"""桌面版入口 —— 原生窗口启动 FastAPI 服务（无需手动开浏览器/管理进程）"""

import sys
import os
import threading
import time
import socket
from pathlib import Path

# ── 确定 exe 所在目录（保证 data/.env 在 exe 同目录） ──
if getattr(sys, "frozen", False):
    _EXE_DIR = Path(sys.executable).parent
else:
    _EXE_DIR = Path(__file__).resolve().parent

# 把 backend 目录加入 path，使 app 包可被导入
_PKG_DIR = _EXE_DIR if not getattr(sys, "frozen", False) else Path(sys._MEIPASS)
if str(_PKG_DIR) not in sys.path:
    sys.path.insert(0, str(_PKG_DIR))

# ── 日志定向到 exe 同目录的 data/ 下 ──
_LOG_DIR = _EXE_DIR / "data"
_LOG_FILE = _LOG_DIR / "desktop.log"


def _setup_logging():
    # Windowed 模式下 sys.stdout 为 None，uvicorn 日志会崩溃
    # 重定向到 devnull 使其正常工作
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(str(_LOG_FILE), encoding="utf-8"),
        ],
    )


def _find_free_port() -> int:
    """找一个系统空闲端口"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _msgbox(title: str, message: str, error: bool = False):
    """Windows 原生消息框（在 GUI 启动前使用）"""
    import ctypes
    flags = 0x10 if error else 0x40  # MB_ICONERROR | MB_ICONINFORMATION
    ctypes.windll.user32.MessageBoxW(0, message, title, flags)


def _start_server(port: int):
    """在后台线程中运行 uvicorn"""
    try:
        import asyncio
        import uvicorn
        from app.main import app

        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
        server = uvicorn.Server(config)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.serve())
    except Exception as e:
        import traceback
        err = traceback.format_exc()
        try:
            with open(_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"后端启动失败:\n{err}\n")
        except Exception:
            pass


def _wait_for_server(url: str, timeout: int = 30) -> bool:
    """轮询等待后端就绪"""
    import httpx
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = httpx.get(f"{url}/api/health", timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _open_browser(url: str):
    """在浏览器中打开（pywebview 不可用时的降级方案）"""
    import webbrowser
    print(f"[desktop] 请在浏览器中打开: {url}")
    webbrowser.open(url)
    # 保持进程运行直到用户按 Enter
    print("[desktop] 按 Ctrl+C 或关闭此窗口以停止服务...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


def main() -> int:
    _setup_logging()

    # 解析命令行参数
    use_browser = "--browser" in sys.argv or os.environ.get("DESKTOP_MODE") == "browser"

    # 1) 找空闲端口
    port = _find_free_port()
    backend_url = f"http://127.0.0.1:{port}"
    print(f"[desktop] 后端服务端口: {port}")

    # 2) 启动后端线程
    t = threading.Thread(target=_start_server, args=(port,), daemon=True)
    t.start()

    # 3) 等待后端就绪
    print("[desktop] 等待后端启动...")
    if not _wait_for_server(backend_url):
        _msgbox("启动失败", "后端服务启动超时，请检查 data/desktop.log 查看详细错误", error=True)
        return 1

    print("[desktop] 后端已就绪")

    # 4) 打开窗口 —— 优先使用 pywebview，失败则降级到浏览器
    if use_browser:
        _open_browser(backend_url)
    else:
        try:
            import webview
            webview.create_window(
                "金融分析平台",
                backend_url,
                width=1280,
                height=800,
                min_size=(960, 600),
                resizable=True,
                text_select=False,
            )
            webview.start(private_mode=True, debug=False)
        except ImportError:
            print("[desktop] pywebview 不可用，降级到浏览器模式")
            _open_browser(backend_url)
        except Exception as e:
            print(f"[desktop] 桌面窗口打开失败 ({e})，降级到浏览器模式")
            _open_browser(backend_url)

    print("[desktop] 程序退出")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        import traceback
        traceback.print_exc()
        _msgbox("运行时错误", f"程序异常退出：{e}", error=True)
        sys.exit(1)
