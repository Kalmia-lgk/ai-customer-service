# ============================================================
# AI 智能客服系统 - Windows 图形化启动器（打包为 exe 使用）
# 功能: 控制面板窗口 → 检查环境 → 安装依赖 → 启动服务
#       → 用浏览器"应用模式"打开客户端 + 管理端两个独立 app 窗口
#       （无地址栏、无标签页，外观等同桌面应用）
# 打包: pyinstaller --onefile --windowed --name 启动AI客服系统 launcher.py
# ============================================================
from __future__ import annotations

import os
import queue
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

import tkinter as tk
from tkinter import ttk

PORT = 8000
HEALTH_URL = f"http://127.0.0.1:{PORT}/api/health"
CUSTOMER_URL = f"http://localhost:{PORT}/"
ADMIN_URL = f"http://localhost:{PORT}/admin/"

# Windows 下隐藏子进程的黑色控制台窗口
NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def project_root() -> Path:
    """exe 所在目录即项目根目录（开发时为脚本所在目录）"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def find_python(root: Path) -> str | None:
    """查找可用的 Python 解释器（优先项目虚拟环境）"""
    candidates = [
        root / ".venv" / "Scripts" / "python.exe",
        root / "venv" / "Scripts" / "python.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    for name in ("python", "python3", "py"):
        path = shutil.which(name)
        if path:
            try:
                out = subprocess.run(
                    [path, "--version"], capture_output=True, text=True,
                    timeout=10, creationflags=NO_WINDOW,
                )
                if out.returncode == 0 and "Python 3" in (out.stdout + out.stderr):
                    return path
            except Exception:
                continue
    return None


def find_app_browser() -> str | None:
    """
    查找支持 --app 应用模式的浏览器 (Edge / Chrome)
    找到后用它把网页打开成无地址栏的独立应用窗口
    """
    candidates: list[str] = []

    # 注册表 App Paths（最可靠）
    if sys.platform == "win32":
        import winreg
        for exe in ("msedge.exe", "chrome.exe"):
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(
                        hive,
                        rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe}",
                    ) as key:
                        path, _ = winreg.QueryValueEx(key, "")
                        if path:
                            candidates.append(path)
                except OSError:
                    continue

    # 常见安装路径兜底
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    local = os.environ.get("LocalAppData", "")
    candidates += [
        rf"{pf86}\Microsoft\Edge\Application\msedge.exe",
        rf"{pf}\Microsoft\Edge\Application\msedge.exe",
        rf"{pf}\Google\Chrome\Application\chrome.exe",
        rf"{pf86}\Google\Chrome\Application\chrome.exe",
        rf"{local}\Google\Chrome\Application\chrome.exe",
    ]

    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def kill_port(port: int, log) -> None:
    """结束占用端口的进程"""
    try:
        out = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True,
            timeout=15, creationflags=NO_WINDOW,
        ).stdout
        pids: set[str] = set()
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 5 and f":{port}" in parts[1] and "LISTENING" in line:
                pids.add(parts[-1])
        for pid in pids:
            if pid != "0":
                log(f"端口 {port} 被进程 {pid} 占用，正在结束...")
                subprocess.run(
                    ["taskkill", "/PID", pid, "/F"],
                    capture_output=True, timeout=15, creationflags=NO_WINDOW,
                )
        if pids:
            time.sleep(2)
    except Exception as e:
        log(f"释放端口失败: {e}")


class LauncherApp:
    """控制面板主窗口"""

    def __init__(self) -> None:
        self.server: subprocess.Popen | None = None
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.browser = find_app_browser()

        self.root = tk.Tk()
        self.root.title("AI 智能客服系统 - 控制面板")
        self.root.geometry("680x480")
        self.root.minsize(540, 380)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._build_ui()
        self._poll_log_queue()

        # 后台线程执行启动流程，避免卡死界面
        threading.Thread(target=self._startup_flow, daemon=True).start()

    # ==================== 打开应用窗口 ====================

    def open_app_window(self, url: str, size: str = "1280,860") -> None:
        """用浏览器应用模式打开独立窗口（无地址栏/标签页），失败则退回普通浏览器"""
        if self.browser:
            subprocess.Popen(
                [self.browser, f"--app={url}", f"--window-size={size}", "--new-window"],
                creationflags=NO_WINDOW,
            )
        else:
            webbrowser.open(url)

    def open_customer(self) -> None:
        self.open_app_window(CUSTOMER_URL)

    def open_admin(self) -> None:
        self.open_app_window(ADMIN_URL)

    # ==================== UI ====================

    def _build_ui(self) -> None:
        header = tk.Frame(self.root, bg="#1e293b")
        header.pack(fill="x")
        tk.Label(
            header, text="🤖 AI 智能客服系统", font=("Microsoft YaHei UI", 15, "bold"),
            fg="white", bg="#1e293b", pady=10,
        ).pack(side="left", padx=16)
        self.status_label = tk.Label(
            header, text="● 正在启动...", font=("Microsoft YaHei UI", 11),
            fg="#fbbf24", bg="#1e293b",
        )
        self.status_label.pack(side="right", padx=16)

        btn_bar = tk.Frame(self.root, pady=10)
        btn_bar.pack(fill="x", padx=16)

        self.btn_customer = ttk.Button(
            btn_bar, text="打开客户端窗口", command=self.open_customer, state="disabled",
        )
        self.btn_customer.pack(side="left", padx=(0, 8))

        self.btn_admin = ttk.Button(
            btn_bar, text="打开管理端窗口", command=self.open_admin, state="disabled",
        )
        self.btn_admin.pack(side="left", padx=(0, 8))

        self.btn_stop = ttk.Button(btn_bar, text="停止并退出", command=self.on_close)
        self.btn_stop.pack(side="right")

        mode = "应用窗口模式" if self.browser else "普通浏览器模式"
        info = tk.Label(
            self.root,
            text=f"打开方式: {mode}    管理端用邮箱账号登录    最小化不影响服务运行",
            font=("Microsoft YaHei UI", 9), fg="#64748b", anchor="w",
        )
        info.pack(fill="x", padx=16)

        log_frame = tk.Frame(self.root)
        log_frame.pack(fill="both", expand=True, padx=16, pady=(6, 16))
        self.log_text = tk.Text(
            log_frame, font=("Consolas", 9), bg="#0f172a", fg="#cbd5e1",
            state="disabled", wrap="word", relief="flat", padx=8, pady=8,
        )
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

    def log(self, message: str) -> None:
        """线程安全的日志输出（写入队列，由主线程消费）"""
        self.log_queue.put(message.rstrip())

    def _poll_log_queue(self) -> None:
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.configure(state="normal")
                self.log_text.insert("end", msg + "\n")
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_log_queue)

    def _set_status(self, text: str, color: str) -> None:
        self.root.after(0, lambda: self.status_label.config(text=text, fg=color))

    # ==================== 启动流程（后台线程） ====================

    def _startup_flow(self) -> None:
        root = project_root()
        backend = root / "backend"

        if not (backend / "app" / "main.py").exists():
            self.log(f"[错误] 未找到后端代码: {backend}")
            self.log("请将本程序放在项目根目录（与 backend 文件夹同级）后再运行。")
            self._set_status("● 启动失败", "#ef4444")
            return

        # 1. Python 环境
        python = find_python(root)
        if not python:
            self.log("[错误] 未检测到 Python 3，请先安装 Python 3.12+：")
            self.log("       https://www.python.org/downloads/")
            self._set_status("● 缺少 Python", "#ef4444")
            return
        self.log(f"[完成] Python: {python}")
        if self.browser:
            self.log(f"[完成] 应用窗口浏览器: {self.browser}")
        else:
            self.log("[提示] 未找到 Edge/Chrome，将使用默认浏览器打开页面。")

        # 2. 依赖
        check = subprocess.run(
            [python, "-c", "import fastapi, uvicorn, chromadb, openai, loguru, sqlmodel, langgraph, jwt"],
            capture_output=True, creationflags=NO_WINDOW,
        )
        if check.returncode != 0:
            self.log("[信息] 检测到依赖缺失，开始安装（首次运行需要几分钟，请耐心等待）...")
            self._set_status("● 安装依赖中...", "#fbbf24")
            result = subprocess.run(
                [python, "-m", "pip", "install", "-r", str(root / "requirements.txt"),
                 "--disable-pip-version-check"],
                cwd=str(root), capture_output=True, text=True, creationflags=NO_WINDOW,
            )
            if result.returncode != 0:
                self.log("[警告] 部分依赖安装失败，服务可能无法正常启动。")
                self.log((result.stderr or "")[-2000:])
            else:
                self.log("[完成] 依赖安装完毕。")
        else:
            self.log("[完成] 依赖已安装。")

        # 3. 端口
        if port_in_use(PORT):
            kill_port(PORT, self.log)
        self.log(f"[完成] 端口 {PORT} 可用。")

        # 4. 启动服务（隐藏控制台，日志转发到本窗口）
        self.log("[信息] 正在启动服务...")
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        self.server = subprocess.Popen(
            [python, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(PORT)],
            cwd=str(backend), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            creationflags=NO_WINDOW,
        )
        threading.Thread(target=self._pump_server_logs, daemon=True).start()

        # 5. 等待就绪
        deadline = time.time() + 90
        while time.time() < deadline:
            if self.server.poll() is not None:
                self.log("[错误] 服务进程意外退出，请查看上方日志。")
                self._set_status("● 启动失败", "#ef4444")
                return
            try:
                with urllib.request.urlopen(HEALTH_URL, timeout=3) as resp:
                    if resp.status == 200:
                        break
            except Exception:
                pass
            time.sleep(1.5)
        else:
            self.log("[错误] 服务在 90 秒内未就绪，请查看上方日志排查。")
            self._set_status("● 启动超时", "#ef4444")
            return

        # 6. 就绪：启用按钮 + 打开两个应用窗口 + 控制面板最小化
        self.log("[完成] 服务已就绪！正在打开客户端和管理端窗口...")
        self._set_status("● 运行中", "#4ade80")
        self.root.after(0, lambda: self.btn_customer.config(state="normal"))
        self.root.after(0, lambda: self.btn_admin.config(state="normal"))
        self.open_customer()
        time.sleep(1.5)  # 稍作间隔，确保两个窗口都能弹出
        self.open_admin()
        self.log("[提示] 本控制面板已最小化到任务栏，关闭它会停止服务。")
        self.root.after(800, self.root.iconify)

    def _pump_server_logs(self) -> None:
        """把服务日志实时转发到窗口"""
        if not self.server or not self.server.stdout:
            return
        for line in self.server.stdout:
            self.log(line)

    # ==================== 退出 ====================

    def on_close(self) -> None:
        if self.server and self.server.poll() is None:
            self.log("[信息] 正在停止服务...")
            self.server.terminate()
            try:
                self.server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server.kill()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    LauncherApp().run()
