# MT论坛每日自动签到

自动完成 [bbs.binmt.cc](https://bbs.binmt.cc) 每日签到，基于 GitHub Actions 每天定时执行。

## 使用方法

### 1. 获取 Cookie

1. 用浏览器打开 [bbs.binmt.cc](https://bbs.binmt.cc) 并登录
2. 按 `F12` 打开开发者工具
3. 切到 **Network** 标签，刷新页面
4. 点击任意请求，在 **Request Headers** 中找到 `Cookie:` 那一行
5. 复制整行 Cookie 内容（`name1=value1; name2=value2; ...`）

### 2. Fork 本仓库

点击右上角 Fork，将仓库复制到你的 GitHub 账号下。

### 3. 配置 Secrets

进入你 Fork 后的仓库 → **Settings** → **Secrets and variables** → **Actions**，添加：

| Secret 名称 | 说明 |
|---|---|
| `MT_COOKIE` | 浏览器中复制的完整 Cookie 字符串 |

> ⚠️ Cookie 有效期约 30 天，过期后需要重新获取并更新 Secret。

### 4. 启用 Actions

进入 **Actions** 标签页，点击 **I understand my workflows, go ahead and enable them**。

### 5. 手动测试

**Actions** → **MT论坛每日签到** → **Run workflow**，手动触发一次确认正常。

## 签到时间

默认每天 **北京时间 8:00** 自动签到（UTC 0:00）。

修改 `.github/workflows/signin.yml` 中的 cron 表达式即可调整：

```yaml
schedule:
  - cron: '0 0 * * *'   # 北京时间 8:00
  # - cron: '0 12 * * *' # 北京时间 20:00
```

## 本地运行

```bash
pip install -r requirements.txt
MT_COOKIE='你的cookie字符串' python signin.py
```

## 注意事项

- GitHub Actions 定时任务可能有最多 **15 分钟** 的延迟
- Cookie 有效期约 30 天，过期需重新获取
- 签到使用 dsu_pa498 插件（论坛最常用的签到插件）
