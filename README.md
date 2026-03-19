# MT论坛每日自动签到

~~自动完成 [bbs.binmt.cc](https://bbs.binmt.cc) 每日签到，基于 GitHub Actions 每天定时执行。~~

## ⚠️ 项目已归档

**本项目已停止维护。**

### 原因

bbs.binmt.cc 启用了滑块验证（反爬系统），会对**数据中心 IP**（如 GitHub Actions）直接拦截，无论用 requests 还是 Playwright 无头浏览器都无法通过验证。

### 尝试过的方案

| 方案 | 结果 |
|---|---|
| requests 直接请求 | 被滑块拦截，返回验证页面 |
| Playwright 无头浏览器 | 滑块检测到自动化，无法通过 |
| Playwright + 反检测 | 同上，GitHub Actions IP 被标记 |
| Discuz! 移动端 API | 同样被拦截 |
| Self-hosted Runner | 可行但需要保持电脑常开，不便 |

### 如果你想继续

最可行的方案是用 **self-hosted GitHub Actions runner** 跑在你自己的设备上（用家里的网络就不会被拦）。

代码已经写好了，只需要：
1. 在本机安装 [self-hosted runner](https://github.com/leeyoloo/mt-signin/settings/actions/runners/new)
2. 在仓库 Settings → Secrets 配置 `MT_COOKIE`
3. runner 保持运行即可

### 本地手动签到

如果你只是想手动签到，脚本还是可以用的：

```bash
pip install requests
MT_COOKIE='你的cookie' python signin.py
```
