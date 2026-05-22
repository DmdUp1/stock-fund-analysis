import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import webbrowser
import os

# 固定你的项目根目录（自动适配，不用改路径）
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND_PATH = os.path.join(PROJECT_ROOT, "frontend")
BACKEND_PATH = os.path.join(PROJECT_ROOT, "backend")
VENV_PYTHON = os.path.join(BACKEND_PATH, ".venv", "Scripts", "python.exe")

FRONT_URL = "http://localhost:5176/"
BACK_URL = "http://127.0.0.1:8000"

process_list = []

# 强制杀死端口，解决10013报错
def kill_port(port):
    try:
        result = subprocess.run(
            f"netstat -ano | findstr \":{port}\"",
            shell=True, capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            if "LISTENING" in line:
                pid = line.strip().split()[-1]
                subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
    except:
        pass

# 校验端口是否真正启动成功
def check_port_running(port):
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0

class AppLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("股票基金分析项目 · 一键启动器")
        self.root.geometry("600x350")
        self.root.resizable(False, False)

        # 标题
        title_label = ttk.Label(root, text="项目一键启停面板", font=("微软雅黑", 24, "bold"))
        title_label.pack(pady=25)

        # 状态显示
        self.status_var = tk.StringVar(value="当前状态：未启动 ❌")
        ttk.Label(root, textvariable=self.status_var, font=("微软雅黑", 16)).pack(pady=8)

        # 地址展示
        ttk.Label(root, text=f"前端地址：{FRONT_URL}", font=("微软雅黑", 12)).pack(pady=3)
        ttk.Label(root, text=f"后端地址：{BACK_URL}", font=("微软雅黑", 12)).pack(pady=3)

        # 按钮区域
        btn_frame = ttk.Frame(root)
        btn_frame.pack(pady=35)

        self.start_btn = ttk.Button(btn_frame, text="启动项目", command=self.start_all, width=15)
        self.start_btn.grid(row=0, column=0, padx=12)

        self.stop_btn = ttk.Button(btn_frame, text="关闭项目", command=self.stop_all, width=15)
        self.stop_btn.grid(row=0, column=1, padx=12)

        ttk.Button(btn_frame, text="打开前端", command=self.open_front, width=15).grid(row=0, column=2, padx=12)
        ttk.Button(btn_frame, text="打开后端", command=self.open_back, width=15).grid(row=0, column=3, padx=12)

    def start_all(self):
        global process_list
        if process_list:
            messagebox.showinfo("提示", "项目已在运行中")
            return

        # 启动前先清空端口占用
        kill_port(5176)
        kill_port(8000)

        try:
            # 启动前端（pnpm dev）
            p_front = subprocess.Popen(
                "pnpm dev",
                cwd=FRONTEND_PATH,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )

            # 启动后端（用.venv里的python，强制激活虚拟环境）
            p_back = subprocess.Popen(
                f'"{VENV_PYTHON}" -m uvicorn app.main:app --reload',
                cwd=BACKEND_PATH,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )

            process_list = [p_front, p_back]

            # 等待3秒，校验端口是否真正启动
            import time
            time.sleep(3)
            front_ok = check_port_running(5176)
            back_ok = check_port_running(8000)

            if front_ok and back_ok:
                self.status_var.set("当前状态：前后端全部运行中 ✅")
                self.start_btn.config(state="disabled")
                messagebox.showinfo("启动成功", f"前端：{FRONT_URL}\n后端：{BACK_URL}\n服务已全部启动")
            else:
                messagebox.showwarning("启动异常", f"前端启动：{'成功' if front_ok else '失败'}\n后端启动：{'成功' if back_ok else '失败'}")

        except Exception as e:
            messagebox.showerror("启动失败", f"异常信息：{str(e)}")

    def stop_all(self):
        global process_list
        if not process_list:
            messagebox.showinfo("提示", "未运行任何服务")
            return

        try:
            for p in process_list:
                subprocess.run(f"taskkill /F /PID {p.pid}", shell=True, capture_output=True)
            process_list.clear()
            self.status_var.set("当前状态：已关闭 ❌")
            self.start_btn.config(state="normal")
            messagebox.showinfo("操作完成", "前后端服务已全部关闭")
        except:
            pass

    def open_front(self):
        webbrowser.open(FRONT_URL)

    def open_back(self):
        webbrowser.open(BACK_URL)

if __name__ == "__main__":
    root = tk.Tk()
    AppLauncher(root)
    root.mainloop()