"""PyInstaller 入口 —— 启动 FastAPI 并自动打开浏览器"""

import sys
import threading
import time
import webbrowser


def _open_browser():
    """延迟打开浏览器，等待服务就绪"""
    time.sleep(2)
    try:
        webbrowser.open("http://127.0.0.1:8000")
    except Exception:
        pass


def main():
    # 在包内运行时自动打开浏览器
    if getattr(sys, "frozen", False):
        threading.Thread(target=_open_browser, daemon=True).start()

    import uvicorn
    from app.main import app

    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n错误: {e}")
        print("\n按 Enter 键退出...")
        input()
