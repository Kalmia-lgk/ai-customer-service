#!/usr/bin/env python3
"""
============================================================
AI 智能客服系统 - 一键启动脚本
============================================================
用法:
    python run.py              # 启动服务 (默认端口 8000)
    python run.py --port 3000  # 指定端口
    python run.py --demo       # Demo 模式 (无需 API Key)
    python run.py --install    # 仅安装依赖
============================================================
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# 项目根目录
ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"


def print_banner() -> None:
    """打印启动横幅"""
    print(r"""
╔══════════════════════════════════════════════════════╗
║                                                      ║
║      🤖  AI 智能客服系统  v1.0.0                     ║
║      RAG + Agent | FastAPI + ChromaDB                 ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
    """)


def check_python() -> bool:
    """检查 Python 版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 12):
        print(f"❌ 需要 Python 3.12+，当前版本: {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_env() -> bool:
    """检查 .env 配置"""
    env_file = ROOT / ".env"
    if not env_file.exists():
        env_example = ROOT / ".env.example"
        if env_example.exists():
            print("📋 .env 文件不存在，正在从 .env.example 创建...")
            content = env_example.read_text(encoding="utf-8")
            env_file.write_text(content, encoding="utf-8")
            print("⚠️  请编辑 .env 文件，填入你的 API Key")
            print(f"   文件位置: {env_file}")
        return False
    return True


def install_deps() -> bool:
    """安装依赖"""
    req_file = ROOT / "requirements.txt"
    if not req_file.exists():
        print("❌ requirements.txt 不存在")
        return False

    print("📦 正在安装依赖...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
            check=True,
            cwd=str(ROOT),
        )
        print("✅ 依赖安装完成")
        return True
    except subprocess.CalledProcessError:
        print("❌ 依赖安装失败，请手动执行: pip install -r requirements.txt")
        return False


def start_server(port: int, demo: bool = False) -> None:
    """启动 FastAPI 服务"""
    os.chdir(str(BACKEND))

    # 设置 Demo 模式环境变量
    env = os.environ.copy()
    if demo:
        env["DEMO_MODE"] = "true"
        print("🎮 Demo 模式已启用 - 无需 API Key，使用模拟回复")

    print(f"\n🚀 正在启动服务...")
    print(f"   📡 前端界面: http://localhost:{port}")
    print(f"   📖 API 文档: http://localhost:{port}/api/docs")
    print(f"   ❤️  健康检查: http://localhost:{port}/api/health")
    print(f"\n   按 Ctrl+C 停止服务\n")
    print("=" * 60)

    try:
        subprocess.run(
            [
                sys.executable, "-m", "uvicorn",
                "app.main:app",
                "--host", "0.0.0.0",
                "--port", str(port),
                "--reload",
            ],
            env=env,
            cwd=str(BACKEND),
        )
    except KeyboardInterrupt:
        print("\n\n👋 服务已停止")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI 智能客服系统 - 一键启动",
    )
    parser.add_argument("--port", "-p", type=int, default=8000, help="服务端口 (默认: 8000)")
    parser.add_argument("--demo", "-d", action="store_true", help="Demo 模式 (无需 API Key)")
    parser.add_argument("--install", "-i", action="store_true", help="仅安装依赖")
    args = parser.parse_args()

    print_banner()

    # 1. 检查 Python 版本
    if not check_python():
        sys.exit(1)

    # 2. 安装依赖
    if args.install:
        if not install_deps():
            sys.exit(1)
        print("\n✅ 依赖安装完成！现在可以运行: python run.py")
        return

    # 快速检查依赖
    try:
        import fastapi  # noqa: F401
    except ImportError:
        print("⚠️  依赖未安装，正在自动安装...")
        if not install_deps():
            sys.exit(1)

    # 3. 启动服务
    start_server(args.port, args.demo)


if __name__ == "__main__":
    main()
