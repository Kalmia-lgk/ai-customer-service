import time

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge")
    page = b.new_page()
    page.on("pageerror", lambda e: print("[pageerror]", e))
    page.on("console", lambda m: print("[console]", m.type, m.text) if m.type in ("error", "warning") else None)
    page.on("request", lambda r: print("[req]", r.method, r.url.replace(BASE, "")) if "/api/" in r.url or "/ws/" in r.url else None)
    page.goto(BASE, wait_until="networkidle")
    page.fill("#input", "AI解决不了我的问题，请帮我转接人工客服")
    page.press("#input", "Enter")
    for i in range(40):
        time.sleep(1)
        if page.locator("#ticket-banner").is_visible():
            print("BANNER VISIBLE at", i, "s:", page.locator("#ticket-status-text").inner_text())
            break
    else:
        print("BANNER NEVER VISIBLE")
        print("hidden attr:", page.locator("#ticket-banner").get_attribute("hidden"))
    b.close()
