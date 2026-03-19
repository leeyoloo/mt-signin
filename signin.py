#!/usr/bin/env python3
"""
MT论坛 (bbs.binmt.cc) 每日自动签到
基于 dsu_pa498 签到插件，通过 cookie 登录 + POST 请求完成签到。
通过 self-hosted runner 运行在本地，绕过数据中心 IP 限制。
"""
import os
import sys
import re
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = "https://bbs.binmt.cc"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": BASE_URL + "/",
}


def parse_cookies(cookie_string):
    """解析 cookie 字符串"""
    cookies = {}
    for item in cookie_string.split(";"):
        item = item.strip()
        if "=" in item:
            key, _, value = item.partition("=")
            cookies[key.strip()] = value.strip()
    return cookies


def get_formhash(session):
    """从页面获取 formhash"""
    for url in [f"{BASE_URL}/forum.php", f"{BASE_URL}/home.php?mod=space"]:
        try:
            resp = session.get(url, headers=HEADERS, timeout=15)
            resp.encoding = "utf-8"
            for pattern in [
                r'formhash=([a-f0-9]+)',
                r'name=["\']formhash["\'][^>]*value=["\']([a-f0-9]+)["\']',
                r'formhash["\s:=]+["\']([a-f0-9]+)["\']',
            ]:
                m = re.search(pattern, resp.text)
                if m:
                    return m.group(1)
        except:
            continue
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

    session = requests.Session()
    cookies = parse_cookies(cookie_string)
    for k, v in cookies.items():
        session.cookies.set(k, v, domain="bbs.binmt.cc")
        session.cookies.set(k, v, domain=".bbs.binmt.cc")

    print(f"📋 已加载 {len(cookies)} 个 cookie")

    # 检查登录状态
    try:
        resp = session.get(f"{BASE_URL}/forum.php", headers=HEADERS, timeout=15)
        resp.encoding = "utf-8"
        if "logging&action=logout" in resp.text:
            print("✅ Cookie 有效，已登录")
        else:
            print("❌ Cookie 无效或已过期")
            sys.exit(1)
    except Exception as e:
        print(f"❌ 网络异常: {e}")
        sys.exit(1)

    # 获取 formhash
    formhash = get_formhash(session)
    if not formhash:
        print("❌ 无法获取 formhash")
        sys.exit(1)

    print(f"📋 formhash: {formhash}")

    # 检查是否已签到
    try:
        resp = session.get(
            f"{BASE_URL}/plugin.php?id=dsu_pa498:sign&operation=qiandao&infloat=1&inajax=1",
            headers={**HEADERS, "X-Requested-With": "XMLHttpRequest"},
            timeout=15,
        )
        resp.encoding = "utf-8"
        if "已经签到" in resp.text or "已签到" in resp.text:
            print("🎉 今天已经签到过了！")
            return
    except:
        pass

    # 执行签到
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
        elif "成功" in text or "恭喜" in text:
            reward = re.search(r'(\d+)\s*(?:金钱|积分|金币)', text)
            detail = f"，获得 {reward.group(1)} 积分" if reward else ""
            print(f"✅ 签到成功{detail}")
        else:
            print(f"⚠️ 签到结果: {text[:300]}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ 签到异常: {e}")
        sys.exit(1)

    print()
    print("=" * 50)
    print("🎉 完成！")


if __name__ == "__main__":
    main()
