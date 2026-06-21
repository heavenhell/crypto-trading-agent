# 数字货币自然语言交易 Agent（LangGraph + ccxt）完整版

用自然语言操作 Binance 现货 / 合约（USDⓈ-M）。**默认 testnet 假钱。**

## ⚠️ 安全须知（务必先读）

1. **全程 testnet 假钱**。真钱（mainnet）只在你充分验证、且明确知道风险后，
   把 `.env` 的 `TRADING_MODE` 改成 `mainnet` 才生效。**强烈建议先在 testnet 跑几百次。**
2. **LLM 永远碰不到真实下单动作**。它只能：调只读工具、或调 `propose_order`
   把订单意图结构化。真正下单在 `execute` 节点，且必经 **护栏 + 人工确认**。
3. **护栏是硬限制**（`config/settings.py`）：单笔≤100 USDT、杠杆≤20、
   白名单 BTC/ETH/BNB、合约逐仓。LLM 无法绕过；越界订单直接拒。
4. **每笔操作都记进 SQLite**（`tools/orders.db`），含意图/护栏结果/人工决定/执行结果，可审计。

## 安全链路（下单时）

```
你说"5倍开多0.01个ETH止损2000"
   ↓ LLM 解析
propose_order(market=futures, action=open_long, symbol=ETH, amount=0.01, leverage=5, stop_loss=2000)
   ↓
护栏硬校验（金额/杠杆/白名单）── 越界 → 拒绝，告知你
   ↓ 通过
interrupt 暂停 → 屏幕显示完整订单 → 你输入 approve/reject
   ↓ approve
真正调 ccxt 下单 → 记录进 SQLite
```

## 五阶段（全部交付）

| 阶段 | 内容 | 状态 |
|---|---|---|
| 0 | 环境 + testnet 连通 | ✅ |
| 1 | ccxt 只读工具 | ✅ |
| 2 | LangGraph 只读 agent + CLI | ✅ |
| 3 | 护栏 + 人工确认(HITL) | ✅ |
| 4 | 下单（现货+合约，testnet） | ✅ |
| 5 | SQLite 记录 + 上线说明 | ✅ |

## 部署（Windows PowerShell）

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # 编辑 .env 填 testnet key
python check_connection.py  # 先确认 testnet 连通（只读）
python main.py              # 启动
```

## testnet key（两套，别混用）

- 现货：https://testnet.binance.vision → 填 `.env` 的 `BINANCE_SPOT_TESTNET_*`
- 合约：https://testnet.binancefuture.com → 填 `.env` 的 `BINANCE_FUTURES_TESTNET_*`

## 试试这些话

查询（直接执行）：
```
BTC 现货多少钱？      我的合约余额？      我有哪些持仓？      ETH 资金费率？
```
下单（先护栏，再确认）：
```
买 50 USDT 的 BTC 现货
5倍杠杆开多 0.01 个 ETH，止损 2000
平掉所有 ETH 多单
```
测试护栏（会被拒）：
```
买 500 USDT 的 BTC          → 超单笔上限
50倍杠杆开多 BTC            → 超杠杆上限
买 100 USDT 的 DOGE        → 不在白名单
```

## 切换 DeepSeek

`.env` 设 `LLM_PROVIDER=deepseek` 并填 `DEEPSEEK_API_KEY`。

## ⚠️ 上线（切 mainnet）前必做

1. testnet 充分验证：各类下单、护栏拦截、确认/否决都跑通几十上百次。
2. 复查 `config/settings.py` 护栏值是否符合你的真实风险承受。
3. mainnet key 权限最小化：**只开"现货+合约交易"，绝不开提现权限**；绑定 IP 白名单。
4. 加一个紧急停止机制（kill 进程 / 一键平仓脚本）。
5. 从最小金额开始，人工盯几轮再说。
6. 合约带杠杆，亏损可超本金。务必清楚自己在做什么。

## 目录结构

```
crypto_agent/
├── .env.example
├── requirements.txt
├── config/settings.py          # 护栏 + LLM 配置
├── exchange.py                 # ccxt 连接
├── tools/
│   ├── query_tools.py          # 只读查询
│   ├── guardrails.py           # 护栏硬校验
│   ├── trade_tools.py          # 下单执行（现货/合约）
│   └── order_store.py          # SQLite 记录
├── agent/
│   ├── read_agent.py           # 只读 agent（阶段2，保留）
│   └── trade_agent.py          # 完整 agent（核心）
├── check_connection.py
└── main.py                     # CLI 入口
```
