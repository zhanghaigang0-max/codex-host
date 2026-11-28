# AI 金融决策中心

一个基于 GitHub Actions 的股票与加密货币每日市场观察 MVP。

## 当前功能
- 股票行情：NVDA、QQQ（Stooq 日线 CSV）
- 加密货币行情：BTCUSDT、ETHUSDT（Binance 公共日线 API）
- 指标：SMA20、SMA50、RSI14、近20日年化波动率估算
- 输出：`reports/latest.md`、`data/latest.json`、`data/history.jsonl`
- 自动运行：每天 00:20 UTC（北京时间 08:20），也可在 Actions 手动运行

## 运行
在 GitHub 仓库的 Actions 页面选择 “AI 金融决策中心 - 每日市场分析”，点击 Run workflow。

## 当前限制
这是行情与规则指标分析，不是自主 AI 投资顾问。暂未接入新闻、LLM、多模型辩论、回测或交易所账户；不会执行交易。所有信号仅供研究，不构成投资建议。

## 数据来源
- Stooq：NVDA、QQQ 历史日线
- Binance 公共 API：BTCUSDT、ETHUSDT 日线 K 线

请注意第三方数据源的可用性、延迟、交易日与时区差异。不要将 API 密钥或交易所密钥写入代码或提交到仓库。
