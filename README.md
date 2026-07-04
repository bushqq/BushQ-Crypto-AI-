# BushQ Crypto AI

加密市场情报与日报推送工具。项目会采集行情、新闻、情绪指数与市场结构数据，调用 DeepSeek 生成分析报告，并可通过企业微信机器人推送摘要或全文。

## 功能

- OKX 合约行情与 K 线采集
- 恐惧贪婪指数、新闻、币种基础信息采集
- DeepSeek AI 综合分析
- Markdown 日报生成
- 企业微信机器人推送
- SQLite 本地存储
- Windows 批处理启动、健康检查与打包脚本

## 快速开始

1. 安装依赖：

```powershell
pip install -r requirements.txt
```

2. 复制配置模板：

```powershell
copy config\config.example.yaml config\config.yaml
```

3. 创建 `.env` 并填入密钥：

```text
DEEPSEEK_API_KEY=your_deepseek_key
TAVILY_API_KEY=your_tavily_key
WECHAT_WORK_WEBHOOK_URL=your_wechat_work_webhook
```

4. 运行：

```powershell
python main.py
```

也可以直接双击 `启动CIC.bat`，按菜单选择运行方式。

## 常用命令

```powershell
.\立即运行一次.bat
.\自动推送运行.bat
.\健康检查.bat
```

## 配置与数据

- 配置模板：`config/config.example.yaml`
- 真实配置：`config/config.yaml`
- 密钥文件：`.env`
- 报告输出：`data/reports`
- 数据库：`data/crypto_intelligence.db`
- Prompt：`templates/prompts/daily_analysis.md`

真实配置、密钥、本地数据库、报告和打包产物默认不会提交到 Git。
