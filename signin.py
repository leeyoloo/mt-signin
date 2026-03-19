#!/usr/bin/env python3
"""
MT论坛 (bbs.binmt.cc) 每日自动签到
基于 dsu_pa498 签到插件，通过 cookie 登录 + POST 请求完成签到。
使用 Playwright 无头浏览器绕过滑块验证。
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


def wait_for_guard(page, timeout=30):
    """等待滑块验证自动完成或页面加载完成"""
    print("⏳ 等待页面加载（可能有滑块验证）...")
    # 先等一会，让滑块 JS 执行
    time.sleep(3)

    for _ in range(timeout):
        # 检查是否还在验证页面
        html = page.content()
        if "_guard" not in html and "slider" not in html:
            print("✅ 页面加载完成（已通过验证）")
            return True
        # 检查是否需要手动滑块（有 canvas 或 slider 元素）
        if page.query_selector('.slider') or page.query_selector('canvas'):
            print("⚠️ 检测到滑块，尝试自动处理...")
            # 尝试模拟滑动
            try:
                slider = page.query_selector('.slider') or page.query_selector('[class*="slider"]')
                if slider:
                    box = slider.bounding_box()
                    if box:
                        page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
                        page.mouse.down()
                        # 模拟人类滑动
                        steps = 20
                        for i in range(steps):
                            page.mouse.move(
                                box['x'] + box['width']/2 + (i * 10),
                                box['y'] + box['height']/2,
                                steps=5
                            )
                            time.sleep(0.02)
                        page.mouse.up()
                        time.sleep(2)
            except Exception as e:
                print(f"   滑块处理异常: {e}")
        time.sleep(1)

    print("⚠️ 验证等待超时，继续尝试...")
    return False


def main():
    cookie_string = os.environ.get("MT_COOKIE", "")
    if not cookie_string:
        print("❌ 请设置环境变量 MT_COOKIE")
        print("   获取方式：浏览器登录论坛 → F12 → Network → 复制 Cookie 头")
        sys.exit(1)

    cst = timezone(timedelta(hours=8))
    now = datetime.now(cst)
    print(f"🕐 {now.strftime('%Y-%m-%d %H:%M:%S')} CST")
    print(f"🌐 {BASE_URL}")
    print("=" * 50)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright 未安装")
        sys.exit(1)

    with sync_playwright() as p:
        # 启动无头浏览器
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
            ]
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 14; Pixel 8) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Mobile Safari/537.36",
            viewport={"width": 390, "height": 844},
            locale="zh-CN",
        )

        # 注入 cookie
        cookies = parse_cookies(cookie_string)
        context.add_cookies(cookies)

        page = context.new_page()

        # 注入反检测脚本
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => false});
            window.chrome = {runtime: {}};
        """)

        # 访问首页
        print("🌐 正在访问论坛首页...")
        page.goto(f"{BASE_URL}/forum.php", wait_until="domcontentloaded", timeout=30000)
        wait_for_guard(page)

        # 检查是否登录
        html = page.content()
        if "logging&action=logout" in html:
            print("✅ Cookie 有效，已登录")
        else:
            print("❌ Cookie 无效或已过期")
            browser.close()
            sys.exit(1)

        print()

        # 获取 formhash
        formhash = get_formhash(page)
        if not formhash:
            print("❌ 无法获取 formhash")
            print(f"   页面内容前500字: {html[:500]}")
            browser.close()
            sys.exit(1)

        print(f"📋 formhash: {formhash}")

        # 检查是否已签到
        page.goto(
            f"{BASE_URL}/plugin.php?id=dsu_pa498:sign&operation=qiandao&infloat=1&inajax=1",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        time.sleep(2)
        sign_html = page.content()

        if "已经签到" in sign_html or "已签到" in sign_html:
            print("🎉 今天已经签到过了！")
            browser.close()
            return

        # 执行签到
        print("📝 正在签到 (dsu_pa498)...")

        # 用 Playwright 发起 POST 请求
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
