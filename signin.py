#!/usr/bin/env python3
"""
MT论坛 (bbs.binmt.cc) 每日自动签到
基于 dsu_pa498 签到插件，通过 cookie 登录 + POST 请求完成签到。
"""
import os
import sys
import re
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = "https://bbs.binmt.cc"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": BASE_URL + "/",
}


def get_formhash(session):
    """从首页获取 formhash"""
    resp = session.get(f"{BASE_URL}/forum.php", headers=HEADERS, timeout=15)
    resp.encoding = "utf-8"
    match = re.search(r'formhash=([a-f0-9]+)', resp.text)
    if match:
        return match.group(1)
    match = re.search(r'name="formhash"\s+value="([a-f0-9]+)"', resp.text)
    if match:
        return match.group(1)
    return None


def check_logged_in(session):
    """检查是否已登录（通过 cookie）"""
    resp = session.get(f"{BASE_URL}/forum.php", headers=HEADERS, timeout=15)
    resp.encoding = "utf-8"
    # 登录后页面会有"退出"或"注销"链接，以及个人中心入口
    if "logging&action=logout" in resp.text or "member.php?mod=logging&action=logout" in resp.text:
        return True
    # 也检查是否有 auth cookie
    for cookie in session.cookies:
        if "auth" in cookie.name.lower():
            return True
    return False


def parse_cookies(cookie_string):
    """解析 cookie 字符串为字典并加载到 session"""
    cookies = {}
    for item in cookie_string.split(";"):
        item = item.strip()
        if "=" in item:
            key, _, value = item.partition("=")
            cookies[key.strip()] = value.strip()
    return cookies


def check_already_signed(session):
    """检查是否已签到"""
    resp = session.get(
        f"{BASE_URL}/plugin.php?id=dsu_pa498:sign&operation=qiandao&infloat=1&inajax=1",
        headers={**HEADERS, "X-Requested-With": "XMLHttpRequest"},
        timeout=15,
    )
    resp.encoding = "utf-8"
    return "已经签到" in resp.text or "已签到" in resp.text


def sign_dsu_pa498(session, formhash):
    """使用 dsu_pa498 插件签到（POST）"""
    print("📝 正在签到 (dsu_pa498)...")

    try:
        resp = session.post(
            f"{BASE_URL}/plugin.php?id=dsu_pa498:sign&operation=qiandao&infloat=1&inajax=1",
            data={
                "formhash": formhash,
                "qdxq": "kx",
                "qdmode": "3",
                "todaysay": "",
                "faession": "1",
            },
            headers={
                **HEADERS,
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=15,
        )
        resp.encoding = "utf-8"
        text = resp.text

        if "已经签到" in text or "已签到" in text:
            print("✅ 今天已经签到过了")
            return True, "已签到"
        elif "成功" in text or "恭喜" in text:
            reward = re.search(r'(\d+)\s*(?:金钱|积分|金币)', text)
            detail = f"，获得 {reward.group(1)} 积分" if reward else ""
            print(f"✅ 签到成功{detail}")
            return True, f"签到成功{detail}"
        else:
            print(f"⚠️ 签到状态不明确: {text[:200]}")
            return False, "状态不明"
    except Exception as e:
        print(f"❌ 签到异常: {e}")
        return False, str(e)


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

    session = requests.Session()

    # 加载 cookie
    cookies = parse_cookies(cookie_string)
    for k, v in cookies.items():
        session.cookies.set(k, v, domain="bbs.binmt.cc")

    # 检查登录状态
    if not check_logged_in(session):
        print("❌ Cookie 无效或已过期，请重新获取")
        sys.exit(1)

    print("✅ Cookie 有效，已登录")
    print()

    # 获取 formhash
    formhash = get_formhash(session)
    if not formhash:
        print("❌ 无法获取 formhash")
        sys.exit(1)

    # 检查是否已签到
    if check_already_signed(session):
        print("🎉 今天已经签到过了！")
        return

    # 执行签到
    ok, msg = sign_dsu_pa498(session, formhash)

    print()
    print("=" * 50)
    if ok:
        print(f"🎉 {msg}")
    else:
        print(f"⚠️ {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
