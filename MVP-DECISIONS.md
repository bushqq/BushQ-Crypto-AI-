# MVP Decisions

Project: Crypto Intelligence Center

## Confirmed Decisions

| 项目 | 决定 |
| --- | --- |
| LLM | DeepSeek v4 pro |
| 交易所 | OKX 主力 |
| 新闻源 | Tavily |
| 币种 | BTC + ETH + SOL + LTC + DOGE |
| K线周期 | 4h + 1d |
| 链上数据 | MVP 跳过，V2 增加付费源后再做 |
| 推送时间 | 美股、亚洲、欧洲开盘前1小时 |
| 推送方式 | 企业微信机器人 |
| 运行环境 | 本地 Windows |
| 配置格式 | YAML |
| 长消息处理 | 拆分多条发送 |
| AI Prompt | 先由系统提供模板，用户后续调整 |
| 项目目录 | Desktop\du |

## Latest Clarifications

- 企业微信机器人 Webhook 保存到本地 `.env`。
- Tavily API Key 保存到本地 `.env`。
- 行情只做 OKX 合约，不做现货。
- 报告包含 BTC、ETH、SOL、LTC、DOGE 五个币种。
- OKX 合约标的使用 BTC-USDT-SWAP、ETH-USDT-SWAP、SOL-USDT-SWAP、LTC-USDT-SWAP、DOGE-USDT-SWAP。
- 推送时段按影响加密货币波动的主要股市开盘前1小时：东京、伦敦、纽约。
- DeepSeek API Key 保存到本地 `.env`。
