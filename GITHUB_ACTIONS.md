# GitHub Actions 云端运行

这个模式不改变桌面软件。桌面版继续使用 `BushQCryptoAI.exe`；云端和后台版使用独立入口 `cloud_runner.py`。

## 需要配置的 GitHub Secrets

在 GitHub 仓库进入：

`Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`

添加：

- `DEEPSEEK_API_KEY`
- `TAVILY_API_KEY`
- `WECHAT_WORK_WEBHOOK_URL`

可选：

- `DEEPSEEK_MODEL`

## 自动运行时间

`.github/workflows/crypto-analysis.yml` 会自动运行：

- 每 8 小时一次
- 北京时间 14:00，欧洲市场开盘前提醒
- 北京时间 20:30，美股夏令时开盘前提醒

亚洲开盘前提醒建议继续用本地软件或后续单独加一条 GitHub cron，因为 GitHub Actions 使用 UTC，跨日期表达需要单独处理。

## 手动运行

进入 GitHub 仓库：

`Actions` -> `BushQ Crypto AI` -> `Run workflow`

可以选择：

- `full`：发送总结和完整报告
- `summary`：只发送总结
- `config`：按配置文件决定

## 本地后台 exe

新 exe 位于：

`dist_cloud/BushQCryptoAICloud/BushQCryptoAICloud.exe`

运行示例：

```powershell
dist_cloud\BushQCryptoAICloud\BushQCryptoAICloud.exe --create-config --send-mode full
```

后台 exe 不依赖桌面界面，适合任务计划程序、服务器、GitHub Actions 同一套逻辑。
