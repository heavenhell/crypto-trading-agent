"""
全局配置 —— 风控护栏、白名单、LLM 选择都集中在这里。
★ 风控边界写在 LLM 之外，是硬编码的安全底线，LLM 无权修改。
"""
import os
from dotenv import load_dotenv

load_dotenv(override=True)

# ========== 运行模式 ==========
# testnet = 假钱（默认）；mainnet = 真钱（最后阶段、千万小心）
TRADING_MODE = os.getenv("TRADING_MODE", "testnet")

# ========== 风控护栏（硬限制，不可被 LLM 绕过）==========
class Guardrails:
    MAX_ORDER_USDT = 100          # 单笔最大名义价值（USDT）
    MAX_LEVERAGE = 20             # 合约最大杠杆
    ALLOWED_SYMBOLS = {"BTC", "ETH", "BNB"}   # 允许交易的币种（base）
    MARGIN_MODE = "isolated"      # 逐仓
    REQUIRE_CONFIRM_ALL_WRITES = True   # 所有写操作都需人工确认

# ========== LLM 配置 ==========
# 二选一："openai" 或 "deepseek"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

LLM_CONFIG = {
    "openai": {
        "model": "gpt-4o",
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": None,   # 用默认
    },
    "deepseek": {
        # DeepSeek 是 OpenAI 兼容接口
        "model": "deepseek-chat",
        "api_key": os.getenv("DEEPSEEK_API_KEY"),
        "base_url": "https://api.deepseek.com/v1",
    },
}

# ========== 交易所密钥 ==========
SPOT_KEYS = {
    "apiKey": os.getenv("BINANCE_SPOT_TESTNET_API_KEY"),
    "secret": os.getenv("BINANCE_SPOT_TESTNET_SECRET"),
}
FUTURES_KEYS = {
    "apiKey": os.getenv("BINANCE_FUTURES_TESTNET_API_KEY"),
    "secret": os.getenv("BINANCE_FUTURES_TESTNET_SECRET"),
}
