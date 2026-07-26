"""客户端 UI 自动化走查：截图 + 发消息验证流式/引用/Agent 步骤。"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
SHOTS = PROJECT_ROOT / "scripts" / "shots"
SHOTS.mkdir(exist_ok=True)
BASE = "http://127.0.0.1:8000"


def make_token() -> str:
    from sqlmodel import Session, select

    from app.db import engine
    from app.models import User
    from app.security import create_token

    with Session(engine) as db:
        user = db.exec(select(User).where(User.role == "super_admin")).first()
        return create_token(user)


def ensure_doc(token: str) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    docs = requests.get(f"{BASE}/api/documents", headers=headers, timeout=30).json()
    if docs:
        return
    text = (
        "产品退款政策：本产品支持 7 天无理由退款，购买后 7 天内联系客服提供订单号即可申请，"
        "退款 3 个工作日内原路退回。超过 7 天但在 30 天内，质量问题凭检测报告可全额退款。"
    )
    requests.post(
        f"{BASE}/api/documents/upload", headers=headers,
        files={"file": ("产品手册.txt", text.encode("utf-8"), "text/plain")}, timeout=120,
    ).raise_for_status()


def main() -> None:
    ensure_doc(make_token())
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")  # 用系统 Edge，免下载内核
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(BASE, wait_until="networkidle")

        # 1. 空状态（浅色）
        page.screenshot(path=str(SHOTS / "client_empty_light.png"))

        # 2. 深色模式
        page.click("#btn-theme")
        page.wait_for_timeout(300)
        page.screenshot(path=str(SHOTS / "client_empty_dark.png"))
        page.click("#btn-theme")

        # 3. 发送知识问题，等待流式完成
        page.fill("#input", "你们支持退款吗？")
        page.press("#input", "Enter")
        # 等待流式结束（呼吸光标消失）
        page.wait_for_selector(".msg-assistant .md", timeout=15000)
        for _ in range(60):
            if page.locator(".streaming-cursor").count() == 0:
                break
            time.sleep(0.5)
        page.wait_for_timeout(500)
        page.screenshot(path=str(SHOTS / "client_chat.png"))

        # 4. 展开引用
        if page.locator(".sources summary").count():
            page.click(".sources summary")
            page.wait_for_timeout(300)
            page.screenshot(path=str(SHOTS / "client_sources.png"))

        # 5. 断言关键元素
        assert page.locator(".msg-user .bubble").count() >= 1, "用户气泡缺失"
        assert page.locator(".agent-steps .step").count() >= 2, "Agent 步骤条缺失"
        answer = page.locator(".msg-assistant .md").last.inner_text()
        assert "退款" in answer, f"回答异常: {answer[:80]}"
        print("UI 走查通过；截图在 scripts/shots/")
        browser.close()


if __name__ == "__main__":
    main()
