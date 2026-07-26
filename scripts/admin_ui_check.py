"""管理端 UI 走查 + 双端实时联动验证（访客转人工 ↔ 客服接管回复）。"""
from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
SHOTS = PROJECT_ROOT / "scripts" / "shots"
SHOTS.mkdir(exist_ok=True)
BASE = "http://127.0.0.1:8000"

E2E_EMAIL = "e2e-admin@outlook.com"
E2E_PWD = "test123456"


def ensure_test_admin() -> None:
    from sqlmodel import Session, select

    from app.db import engine, init_db
    from app.models import User
    from app.security import hash_password

    init_db()
    with Session(engine) as db:
        if db.exec(select(User).where(User.email == E2E_EMAIL)).first():
            return
        db.add(User(email=E2E_EMAIL, name="E2E测试", password_hash=hash_password(E2E_PWD), role="super_admin"))
        db.commit()


def main() -> None:
    from playwright.sync_api import sync_playwright

    ensure_test_admin()
    ok: list[str] = []
    fail: list[str] = []

    def check(name: str, cond: bool, detail: str = ""):
        (ok if cond else fail).append(name)
        print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        admin = ctx.new_page()

        # ---------- 登录 ----------
        admin.goto(f"{BASE}/admin/", wait_until="networkidle")
        admin.evaluate("localStorage.removeItem('aicc_admin_token'); localStorage.removeItem('aicc_admin_user')")
        admin.reload(wait_until="networkidle")
        admin.screenshot(path=str(SHOTS / "admin_login.png"))
        admin.fill("#login-email", E2E_EMAIL)
        admin.fill("#login-password", E2E_PWD)
        admin.click("#login-submit")
        admin.wait_for_selector("#app-view:not([hidden])", timeout=10000)
        check("登录进入控制台", True)

        # ---------- 概览 ----------
        admin.wait_for_selector(".stat-card", timeout=10000)
        admin.wait_for_timeout(400)
        admin.screenshot(path=str(SHOTS / "admin_overview.png"))
        check("概览统计卡片", admin.locator(".stat-card").count() >= 6)
        check("近7日柱状图", admin.locator(".bar-col").count() == 7)

        # ---------- 访客端发起转人工（第二个页面） ----------
        cust = ctx.new_page()
        cust.goto(BASE, wait_until="networkidle")
        cust.fill("#input", "AI解决不了我的问题，请帮我转接人工客服")
        cust.press("#input", "Enter")
        # 等待 Agent 建单（banner 出现）
        cust.wait_for_selector("#ticket-banner:not([hidden])", timeout=60000)
        check("访客端 Agent 自动建单", True)
        cust.screenshot(path=str(SHOTS / "client_ticket_waiting.png"))

        # ---------- 管理端工单页：新工单实时出现 ----------
        admin.click('a[data-page="tickets"]')
        admin.wait_for_selector(".ticket-item", timeout=10000)
        admin.wait_for_timeout(500)
        admin.screenshot(path=str(SHOTS / "admin_tickets.png"))
        # 点最新（第一个）工单
        admin.locator(".ticket-item").first.click()
        admin.wait_for_selector("#btn-claim", timeout=8000)
        admin.click("#btn-claim")
        admin.wait_for_selector("#btn-resolve", timeout=8000)
        check("接管工单", True)

        # 客服回复
        admin.fill("#reply-input", "您好，我是人工客服小李，请问有什么可以帮您？")
        admin.click("#btn-reply")
        admin.wait_for_timeout(1200)
        check("客服消息出现在管理端", admin.locator(".tmsg-agent").count() >= 1)
        admin.screenshot(path=str(SHOTS / "admin_ticket_detail.png"))

        # ---------- 访客端：WS 实时收到人工消息 ----------
        cust.wait_for_selector(".msg-human", timeout=8000)
        check("访客端实时收到人工回复", True)
        # 访客回消息
        cust.fill("#input", "我想咨询发票问题")
        cust.press("#input", "Enter")
        cust.wait_for_timeout(1200)
        check("访客消息实时到达管理端", "发票" in admin.locator("#ticket-msgs").inner_text())
        cust.screenshot(path=str(SHOTS / "client_human_chat.png"))

        # 解决工单 → 访客端横幅变已解决
        admin.click("#btn-resolve")
        cust.wait_for_selector("#ticket-banner.resolved", timeout=8000)
        check("工单解决状态实时同步访客端", True)

        # ---------- 知识库 / 用户 / 设置页 ----------
        admin.click('a[data-page="knowledge"]')
        admin.wait_for_selector(".dropzone", timeout=8000)
        admin.wait_for_timeout(400)
        admin.screenshot(path=str(SHOTS / "admin_knowledge.png"))
        check("知识库页文档表格", admin.locator("#doc-rows tr").count() >= 1)

        admin.click('a[data-page="users"]')
        admin.wait_for_selector("#user-rows tr", timeout=8000)
        admin.screenshot(path=str(SHOTS / "admin_users.png"))
        check("用户页列表", admin.locator("#user-rows tr").count() >= 2)

        admin.click('a[data-page="settings"]')
        admin.wait_for_selector("#s-base", timeout=8000)
        check("设置页回填配置", bool(admin.input_value("#s-base")))
        admin.screenshot(path=str(SHOTS / "admin_settings.png"))

        browser.close()

    print(f"\n结果: {len(ok)} 通过, {len(fail)} 失败")
    if fail:
        print("失败项:", fail)
        sys.exit(1)


if __name__ == "__main__":
    main()
