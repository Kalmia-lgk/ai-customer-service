"""交付前全功能验收：用真实管理员账号在浏览器里把所有功能跑一遍。

覆盖：
- 管理端：真实账号登录 / 概览 / 知识库上传+删除 / 用户创建+删除 / 设置保存+测试连接 / 退出登录
- 客户端：空状态 / 主题切换 / 知识问答(流式+引用+步骤条) / 新会话 / 会话切换 / 会话删除 / 转人工
- 双端实时：工单接管 / 双向消息 / 解决工单 / 返回 AI
- API：修改密码
"""
from __future__ import annotations

import sys
import time
import uuid
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
SHOTS = PROJECT_ROOT / "scripts" / "shots"
SHOTS.mkdir(exist_ok=True)
BASE = "http://127.0.0.1:8000"

ADMIN_EMAIL = "1191852328@qq.com"
ADMIN_PWD = "admin123456"

ok: list[str] = []
fail: list[str] = []


def check(name: str, cond: bool, detail: str = ""):
    (ok if cond else fail).append(name)
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}".rstrip())


def wait_stream_done(page, timeout_s: int = 90):
    """等待流式回答结束（呼吸光标消失）。"""
    for _ in range(timeout_s * 2):
        if page.locator(".streaming-cursor").count() == 0:
            return
        time.sleep(0.5)


def api_password_check():
    """修改密码走 API 验证（避免动真实账号）。"""
    email = f"pwd-{uuid.uuid4().hex[:8]}@outlook.com"
    admin_token = requests.post(f"{BASE}/api/auth/login",
                                json={"email": ADMIN_EMAIL, "password": ADMIN_PWD}, timeout=30).json()["token"]
    h = {"Authorization": f"Bearer {admin_token}"}
    u = requests.post(f"{BASE}/api/admin/users", headers=h,
                      json={"email": email, "name": "pwd测试", "password": "old123456", "role": "agent"},
                      timeout=30).json()
    t = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": "old123456"}, timeout=30).json()["token"]
    r = requests.post(f"{BASE}/api/auth/change-password",
                      headers={"Authorization": f"Bearer {t}"},
                      json={"old_password": "old123456", "new_password": "new123456"}, timeout=30)
    check("修改密码接口", r.status_code == 200, str(r.status_code))
    r2 = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": "new123456"}, timeout=30)
    check("新密码可登录", r2.status_code == 200)
    requests.delete(f"{BASE}/api/admin/users/{u['id']}", headers=h, timeout=30)


def main() -> None:
    from playwright.sync_api import sync_playwright

    alerts: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})

        # ==================== 管理端：登录 ====================
        admin = ctx.new_page()
        admin.on("dialog", lambda d: (alerts.append(d.message), d.accept()))
        admin.goto(f"{BASE}/admin/", wait_until="networkidle")
        admin.evaluate("localStorage.clear()")
        admin.reload(wait_until="networkidle")
        admin.fill("#login-email", ADMIN_EMAIL)
        admin.fill("#login-password", ADMIN_PWD)
        admin.click("#login-submit")
        admin.wait_for_selector("#app-view:not([hidden])", timeout=10000)
        check("真实账号登录管理端", True)

        # ==================== 概览 ====================
        admin.wait_for_selector(".stat-card", timeout=10000)
        check("概览统计卡片", admin.locator(".stat-card").count() >= 6)
        check("近7日柱状图", admin.locator(".bar-col").count() == 7)
        admin.screenshot(path=str(SHOTS / "final_overview.png"))

        # ==================== 知识库：上传 ====================
        admin.click('a[data-page="knowledge"]')
        admin.wait_for_selector("#file-input", state="attached", timeout=8000)
        before_rows = admin.locator("#doc-rows tr").count()
        tmp = SHOTS / "临时测试文档.txt"
        tmp.write_text("这是一份验收专用的临时测试文档。配送政策：全国包邮，48 小时内发货。", encoding="utf-8")
        admin.set_input_files("#file-input", str(tmp))
        admin.wait_for_selector('#doc-rows button[data-name="临时测试文档.txt"]', timeout=120000)
        check("知识库上传（UI）", "已就绪" in admin.locator("#doc-rows").inner_text())
        admin.screenshot(path=str(SHOTS / "final_knowledge.png"))

        # ==================== 用户：创建 ====================
        admin.click('a[data-page="users"]')
        admin.wait_for_selector("#btn-add-user", timeout=8000)
        admin.click("#btn-add-user")
        admin.wait_for_selector(".modal", timeout=5000)
        admin.fill('.modal [data-key="name"]', "验收临时客服")
        admin.fill('.modal [data-key="email"]', "final-check@outlook.com")
        admin.fill('.modal [data-key="password"]', "check123456")
        admin.click('.modal [data-act="ok"]')
        admin.wait_for_selector('#user-rows button[data-name="验收临时客服"]', timeout=8000)
        check("用户创建（UI）", True)

        # ==================== 客户端：全流程 ====================
        cust = ctx.new_page()
        cust.on("dialog", lambda d: (alerts.append(d.message), d.accept()))
        cust.goto(BASE, wait_until="networkidle")
        cust.evaluate("localStorage.removeItem('aicc_visitor_id')")
        cust.reload(wait_until="networkidle")
        check("客户端空状态", cust.locator("#empty-state").is_visible())

        theme0 = cust.get_attribute("html", "data-theme")
        cust.click("#btn-theme")
        cust.wait_for_timeout(300)
        check("主题切换", cust.get_attribute("html", "data-theme") != theme0)
        cust.click("#btn-theme")

        # 知识问答（命中刚上传的临时文档）
        cust.fill("#input", "你们的配送政策是什么？多久发货？")
        cust.press("#input", "Enter")
        cust.wait_for_selector(".msg-assistant .md", timeout=90000)
        wait_stream_done(cust)
        answer = cust.locator(".msg-assistant .md").last.inner_text()
        check("知识问答回答", "48" in answer or "包邮" in answer, answer[:60])
        check("Agent 步骤条", cust.locator(".agent-steps .step").count() >= 2)
        if cust.locator(".sources summary").count():
            cust.click(".sources summary")
            cust.wait_for_timeout(300)
            check("引用展开", cust.locator(".sources").last.get_attribute("open") is not None)
        else:
            check("引用展开", False, "无引用块")
        cust.screenshot(path=str(SHOTS / "final_client_chat.png"))

        # 新会话 + 闲聊
        cust.click("#btn-new-session")
        cust.wait_for_timeout(300)
        cust.fill("#input", "你好")
        cust.press("#input", "Enter")
        cust.wait_for_selector(".msg-assistant .md", timeout=90000)
        wait_stream_done(cust)
        cust.wait_for_timeout(500)
        check("新会话（侧栏两条）", cust.locator(".session-item").count() == 2,
              f"实际 {cust.locator('.session-item').count()}")

        # 切回第一个会话（列表按更新时间倒序，第二项是旧会话）
        cust.locator(".session-item").nth(1).click()
        cust.wait_for_selector(".msg-user", timeout=8000)
        check("切换会话恢复历史", "配送" in cust.locator("#messages").inner_text())

        # 删除当前会话（重点回归项）
        n_before = cust.locator(".session-item").count()
        item = cust.locator(".session-item.active")
        item.hover()
        item.locator(".del").click()
        cust.wait_for_timeout(1000)
        n_after = cust.locator(".session-item").count()
        check("删除会话（UI）", n_after == n_before - 1 and not alerts,
              f"{n_before}->{n_after} alerts={alerts}")

        # 剩下的会话里转人工
        cust.locator(".session-item").first.click()
        cust.wait_for_timeout(500)
        cust.click("#btn-escalate")
        cust.wait_for_selector("#ticket-banner:not([hidden])", timeout=15000)
        check("手动转人工建单", True)

        # ==================== 双端实时联动 ====================
        admin.click('a[data-page="tickets"]')
        admin.wait_for_selector(".ticket-item", timeout=10000)
        admin.locator(".ticket-item").first.click()
        admin.wait_for_selector("#btn-claim", timeout=8000)
        admin.click("#btn-claim")
        admin.wait_for_selector("#btn-resolve", timeout=8000)
        check("接管工单", True)

        admin.fill("#reply-input", "您好，我是人工客服，请问有什么可以帮您？")
        admin.click("#btn-reply")
        cust.wait_for_selector(".msg-human", timeout=10000)
        check("访客实时收到人工消息", True)

        cust.fill("#input", "我想咨询发票的开具流程")
        cust.press("#input", "Enter")
        cust.wait_for_timeout(1500)
        check("访客消息实时到管理端", "发票" in admin.locator("#ticket-msgs").inner_text())
        admin.screenshot(path=str(SHOTS / "final_ticket.png"))

        admin.click("#btn-resolve")
        cust.wait_for_selector("#ticket-banner.resolved", timeout=8000)
        check("解决工单实时同步", True)
        cust.click("#btn-back-ai")
        cust.wait_for_timeout(500)
        check("返回 AI 对话", cust.locator("#ticket-banner").is_hidden())

        # ==================== 知识库：删除 ====================
        admin.click('a[data-page="knowledge"]')
        admin.wait_for_selector('#doc-rows button[data-name="临时测试文档.txt"]', timeout=8000)
        admin.locator('#doc-rows button[data-name="临时测试文档.txt"]').click()
        admin.wait_for_selector('.modal [data-act="ok"]', timeout=5000)
        admin.click('.modal [data-act="ok"]')
        admin.wait_for_selector('#doc-rows button[data-name="临时测试文档.txt"]', state="detached", timeout=30000)
        check("知识库删除（UI）", True)

        # ==================== 用户：删除 ====================
        admin.click('a[data-page="users"]')
        admin.wait_for_selector('#user-rows button[data-name="验收临时客服"]', timeout=8000)
        admin.locator('#user-rows button[data-name="验收临时客服"]').click()
        admin.wait_for_selector('.modal [data-act="ok"]', timeout=5000)
        admin.click('.modal [data-act="ok"]')
        admin.wait_for_selector('#user-rows button[data-name="验收临时客服"]', state="detached", timeout=10000)
        check("用户删除（UI）", True)

        # ==================== 设置：保存 + 测试连接 ====================
        admin.click('a[data-page="settings"]')
        admin.wait_for_selector("#s-base", timeout=8000)
        check("设置回填", bool(admin.input_value("#s-base")) and bool(admin.input_value("#s-key")))
        admin.click("#btn-save-llm")
        admin.wait_for_selector(".toast", timeout=8000)
        check("保存设置", "已保存" in admin.locator(".toast").last.inner_text())
        admin.click("#btn-test-llm")
        admin.wait_for_selector('#btn-test-llm:not([disabled])', timeout=60000)
        toasts = admin.locator(".toast").all_inner_texts()
        check("测试连接", any("连接成功" in t for t in toasts), str(toasts))
        admin.screenshot(path=str(SHOTS / "final_settings.png"))

        # ==================== 退出登录 ====================
        admin.click("#btn-logout")
        admin.wait_for_selector("#login-view:not([hidden])", timeout=8000)
        check("退出登录", True)

        browser.close()

    api_password_check()

    print(f"\n结果: {len(ok)} 通过, {len(fail)} 失败")
    if fail:
        print("失败项:", fail)
        sys.exit(1)


if __name__ == "__main__":
    main()
