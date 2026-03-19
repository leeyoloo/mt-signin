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

# 反检测注入脚本
STEALTH_JS = """
// 隐藏 webdriver
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

// 伪造 plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const makePlugin = (name, desc, filename) => {
            const p = Object.create(Plugin.prototype);
            Object.defineProperties(p, {
                name: {value: name, enumerable: true},
                description: {value: desc, enumerable: true},
                filename: {value: filename, enumerable: true},
                length: {value: 1, enumerable: true},
            });
            return p;
        };
        return [
            makePlugin('Chrome PDF Plugin', 'Portable Document Format', 'internal-pdf-viewer'),
            makePlugin('Chrome PDF Viewer', '', 'mhjfbmdgcfjbbpaeojofohoefgiehjai'),
            makePlugin('Native Client', '', 'internal-nacl-plugin'),
        ];
    }
});

// 伪造 languages
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});

// 伪造 platform
Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});

// 伪造 chrome 对象
window.chrome = {
    runtime: {
        connect: function(){},
        sendMessage: function(){},
    },
    loadTimes: function(){ return {}; },
    csi: function(){ return {}; },
};

// 伪造 permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) =>
    parameters.name === 'notifications'
        ? Promise.resolve({state: Notification.permission})
        : originalQuery(parameters);

// 隐藏 automation 标记
delete navigator.__proto__.webdriver;

// 伪造 iframe contentWindow
const origGetOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
Object.getOwnPropertyDescriptor = function(obj, prop) {
    if (prop === 'contentWindow' && obj instanceof HTMLIFrameElement) {
        return origGetOwnPropertyDescriptor(obj, prop);
    }
    return origGetOwnPropertyDescriptor(obj, prop);
};
"""


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
    except ImportError:
        print("❌ Playwright 未安装")
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

        # 注入反检测脚本（每次页面加载都执行）
        page.add_init_script(STEALTH_JS)

        # 访问首页
        print("🌐 正在访问论坛首页...")
        page.goto(f"{BASE_URL}/forum.php", wait_until="networkidle", timeout=30000)

        # 截图
        page.screenshot(path="/tmp/mt_page.png", full_page=False)
        print("📸 截图已保存")

        # 等待页面稳定
        time.sleep(5)

        html = page.content()

        # 检查是否还在验证页面
        if "_guard" in html or "slider" in html.lower():
            print("⚠️ 仍在滑块验证页，等待更多时间...")
            time.sleep(10)
            html = page.content()
            page.screenshot(path="/tmp/mt_page2.png", full_page=False)

        # 检查登录状态
        if "logging&action=logout" in html:
            print("✅ Cookie 有效，已登录")
        elif "_guard" in html:
            print("❌ 滑块验证未通过")
            print(f"   页面: {html[:400]}")
            browser.close()
            sys.exit(1)
        else:
            print("❌ Cookie 无效或已过期")
            browser.close()
            sys.exit(1)

        # 获取 formhash
        formhash = get_formhash(page)
        if not formhash:
            page.goto(f"{BASE_URL}/home.php?mod=space", wait_until="networkidle", timeout=15000)
            time.sleep(2)
            formhash = get_formhash(page)

        if not formhash:
            print("❌ 无法获取 formhash")
            browser.close()
            sys.exit(1)

        print(f"📋 formhash: {formhash}")

        # 检查已签到
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

        # 签到
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

        result = response or ""
        if "已经签到" in result or "已签到" in result:
            print("✅ 今天已经签到过了")
        elif "成功" in result or "恭喜" in result:
            reward = re.search(r'(\d+)\s*(?:金钱|积分|金币)', result)
            detail = f"，获得 {reward.group(1)} 积分" if reward else ""
            print(f"✅ 签到成功{detail}")
        else:
            print(f"⚠️ 签到结果: {result[:300]}")

        browser.close()

    print()
    print("=" * 50)
    print("🎉 完成！")


if __name__ == "__main__":
    main()
