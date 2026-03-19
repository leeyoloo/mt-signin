#!/usr/bin/env python3
"""
MT论坛 (bbs.binmt.cc) 每日自动签到
基于 dsu_pa498 签到插件，通过 cookie 登录 + POST 请求完成签到。
使用 Playwright stealth 无头浏览器绕过滑块验证。
"""
import os
import sys
import re
import time
from datetime import datetime, timezone, timedelta

BASE_URL = "https://bbs.binmt.cc"


def parse_cookies(cookie_string):
    """解析 cookie 字符串为 Playwright 格式"""
    cookies = []
    for item in cookie_string.split(";"):
        item = item.strip()
        if "=" in item:
            key, _, value = item.partition("=")
            cookies.append({
                "name": key.strip(),
                "value": value.strip(),
                "domain": "bbs.binmt.cc",
                "path": "/",
            })
    return cookies


def get_formhash(page):
    """从当前页面获取 formhash"""
    html = page.content()
    for pattern in [
        r'formhash=([a-f0-9]+)',
        r'name=["\']formhash["\'][^>]*value=["\']([a-f0-9]+)["\']',
        r'value=["\']([a-f0-9]+)["\'][^>]*name=["\']formhash["\']',
        r'formhash["\s:=]+["\']([a-f0-9]+)["\']',
    ]:
        m = re.search(pattern, html)
        if m:
            return m.group(1)
    return None


def main():
    cookie_string = os.environ.get("MT_COOKIE", "")
    if not cookie_string:
        print("❌ 请设置环境变量 MT_COOKIE")
        sys.exit(1)

    cst = timezone(timedelta(hours=8))
    now = datetime.now(cst)
    print(f"🕐 {now.strftime('%Y-%m-%d %H:%M:%S')} CST")
    print(f"🌐 {BASE_URL}")
    print("=" * 50)

    try:
        from playwright.sync_api import sync_playwright
        from playwright_stealth import stealth_sync
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 768},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )

        # 注入 cookie
        cookies = parse_cookies(cookie_string)
        context.add_cookies(cookies)

        page = context.new_page()
        stealth_sync(page)  # 反检测

        # 访问首页
        print("🌐 正在访问论坛首页...")
        page.goto(f"{BASE_URL}/forum.php", wait_until="domcontentloaded", timeout=30000)

        # 截图保存，方便调试
        page.screenshot(path="/tmp/mt_page.png", full_page=False)
        print(f"📸 页面截图已保存")

        # 等待页面稳定
        time.sleep(5)

        # 检查是否还在验证页面
        html = page.content()
        if "_guard" in html or "slider" in html:
            print("⚠️ 仍在滑块验证页面，尝试等待更长时间...")
            time.sleep(10)
            html = page.content()

        # 再截一张
        page.screenshot(path="/tmp/mt_page2.png", full_page=False)

        # 检查是否登录
        if "logging&action=logout" in html:
            print("✅ Cookie 有效，已登录")
        elif "_guard" in html:
            print("❌ 滑块验证未通过，无法访问论坛")
            print(f"   页面内容前300字: {html[:300]}")
            browser.close()
            sys.exit(1)
        else:
            print("❌ Cookie 无效或已过期")
            browser.close()
            sys.exit(1)

        print()

        # 获取 formhash
        formhash = get_formhash(page)
        if not formhash:
            # 尝试导航到其他页面
            page.goto(f"{BASE_URL}/home.php?mod=space", wait_until="domcontentloaded", timeout=15000)
            time.sleep(2)
            formhash = get_formhash(page)

        if not formhash:
            print("❌ 无法获取 formhash")
            browser.close()
            sys.exit(1)

        print(f"📋 formhash: {formhash}")

        # 检查是否已签到
        print("📝 检查签到状态...")
        page.goto(
            f"{BASE_URL}/plugin.php?id=dsu_pa498:sign&operation=qiandao&infloat=1&inajax=1",
            wait_until="domcontentloaded",
            timeout=15000,
        )
        time.sleep(2)
        sign_html = page.content()

        if "已经签到" in sign_html or "已签到" in sign_html:
            print("🎉 今天已经签到过了！")
            browser.close()
            return

        # 执行签到
        print("📝 正在签到 (dsu_pa498)...")

        response = page.evaluate(f"""
            async () => {{
                const resp = await fetch('{BASE_URL}/plugin.php?id=dsu_pa498:sign&operation=qiandao&infloat=1&inajax=1', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-Requested-With': 'XMLHttpRequest',
                    }},
                    body: 'formhash={formhash}&qdxq=kx&qdmode=3&todaysay=&faession=1',
                }});
                return await resp.text();
            }}
        """)

        result_text = response if response else ""
        if "已经签到" in result_text or "已签到" in result_text:
            print("✅ 今天已经签到过了")
        elif "成功" in result_text or "恭喜" in result_text:
            reward = re.search(r'(\d+)\s*(?:金钱|积分|金币)', result_text)
            detail = f"，获得 {reward.group(1)} 积分" if reward else ""
            print(f"✅ 签到成功{detail}")
        else:
            print(f"⚠️ 签到结果: {result_text[:300]}")

        browser.close()

    print()
    print("=" * 50)
    print("🎉 完成！")


if __name__ == "__main__":
    main()
