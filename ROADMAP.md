# Roadmap

## 待实现（优先级排序）

### 1. 新闻源接入 🟢 简单
- [ ] CryptoCompare 新闻 + 社交情绪
- [ ] CoinGecko 行情 + 新闻 + 趋势币种
- [ ] Fear & Greed Index 市场情绪

### 2. 分析 Skill 🟡 中等
- [ ] 技术分析：MA/RSI/MACD/布林带（OHLCV 自算）
- [ ] 接入 Fear & Greed Index
- [ ] 链上数据（Glassnode / Dune）

### 3. Web + 飞书界面 🔴 较大
- [ ] Web 端：Gradio 一行出 UI
- [ ] 飞书：自定义机器人 webhook

### 4. 风控增强
- [ ] 止损增强：开仓后补设/修改止损（futures_modify_stop）
- [ ] 日亏损上限：当日累计亏损超阈值禁止交易
- [ ] 交易日志回查：CLI 命令查最近订单

---

## 已完成
- [x] v0.1：现货+合约交易、护栏+人工确认、止盈自动算价、杠杆显示修复
