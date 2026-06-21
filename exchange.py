"""
交易所连接层 —— 创建 ccxt 实例。

★ 重要变化（2025 年底 Binance 迁移）：
  ccxt 的 set_sandbox_mode 已不再支持 Binance 合约，现货旧 testnet 端点也失效了。
  现在统一改用 Binance Demo Trading 的新端点：
    - 现货 demo: https://demo-api.binance.com
    - 合约 demo: https://demo-fapi.binance.com
  Demo Trading 平台 **一套 key 同时支持现货+合约**。
  如果你有两套 key（旧 testnet 分开申请的），现货用 SPOT_KEYS，合约用 FUTURES_KEYS。
"""
import ccxt
from config.settings import SPOT_KEYS, FUTURES_KEYS, TRADING_MODE

# Binance Demo Trading 新端点
DEMO_SPOT_BASE = "https://demo-api.binance.com"
DEMO_FAPI_BASE = "https://demo-fapi.binance.com"


def make_spot_exchange():
    """现货实例。

    分两步创建（与合约相同策略）：
      1. 无 auth 创建 → load_markets（走生产环境公共端点，免费无需 key）
      2. 替换 urls["api"] 为 demo 端点 + 注入 auth key

    因为 Demo Trading 的 sapi 端点不完整（margin/allPairs 等 404），
    不能直接在 demo 端点上 load_markets，必须先在生产环境加载。
    """
    # 第一步：无 auth 创建，从生产环境装载市场数据
    ex = ccxt.binance({
        "enableRateLimit": True,
        "options": {
            "defaultType": "spot",
            "adjustForTimeDifference": True,
        },
    })
    if TRADING_MODE == "testnet":
        ex.set_sandbox_mode(False)   # 走生产环境
    ex.load_markets()

    # 第二步：替换 API URL 为 Demo Trading 端点 + 注入密钥
    if TRADING_MODE == "testnet":
        ex.urls["api"] = {
            "public": DEMO_SPOT_BASE + "/api/v3",
            "private": DEMO_SPOT_BASE + "/api/v3",
            "v1": DEMO_SPOT_BASE + "/api/v1",
            # fapi 端点（持仓查询等会用到）
            "fapiPublic": DEMO_FAPI_BASE + "/fapi/v1",
            "fapiPublicV2": DEMO_FAPI_BASE + "/fapi/v2",
            "fapiPublicV3": DEMO_FAPI_BASE + "/fapi/v3",
            "fapiPrivate": DEMO_FAPI_BASE + "/fapi/v1",
            "fapiPrivateV2": DEMO_FAPI_BASE + "/fapi/v2",
            "fapiPrivateV3": DEMO_FAPI_BASE + "/fapi/v3",
        }
        ex.options["fetchCurrencies"] = False
        ex.has["fetchCurrencies"] = False

    ex.apiKey = SPOT_KEYS["apiKey"]
    ex.secret = SPOT_KEYS["secret"]

    return ex


def make_futures_exchange():
    """合约实例（USDⓈ-M）。

    分两步创建：
      1. 无 auth 创建 → load_markets（走公共端点）
      2. 替换 urls["api"] 为 demo 端点 + 注入 auth key

    这是因为 ccxt 的 set_sandbox_mode 对 Binance 合约已失效，
    必须手动替换 urls["api"]。
    """
    # 第一步：无 auth 创建，只装载市场数据
    ex = ccxt.binance({
        "enableRateLimit": True,
        "options": {
            "defaultType": "future",
            "adjustForTimeDifference": True,
            "hedgeMode": True,          # ★ 对冲模式：允许同时持有 long + short
        },
    })
    if TRADING_MODE == "testnet":
        # set_sandbox_mode(False) 防止 ccxt 指向旧 testnet 端点
        ex.set_sandbox_mode(False)
    ex.load_markets()

    # 第二步：替换 API URL 为 Demo Trading 端点 + 注入密钥
    if TRADING_MODE == "testnet":
        ex.urls["api"] = {
            # 现货端点（合约也需要这些：查余额、查市场等可能走 sapi）
            "public": DEMO_SPOT_BASE + "/api/v3",
            "private": DEMO_SPOT_BASE + "/api/v3",
            "v1": DEMO_SPOT_BASE + "/api/v1",
            # 合约 API 端点 —— 注意 V1/V2/V3 路径不同！
            "fapiPublic": DEMO_FAPI_BASE + "/fapi/v1",
            "fapiPublicV2": DEMO_FAPI_BASE + "/fapi/v2",
            "fapiPublicV3": DEMO_FAPI_BASE + "/fapi/v3",
            "fapiPrivate": DEMO_FAPI_BASE + "/fapi/v1",
            "fapiPrivateV2": DEMO_FAPI_BASE + "/fapi/v2",
            "fapiPrivateV3": DEMO_FAPI_BASE + "/fapi/v3",
        }

    # 注入密钥（load_markets 之后才设置，因为 demo 端点的公共接口不需要 auth）
    ex.apiKey = FUTURES_KEYS["apiKey"]
    ex.secret = FUTURES_KEYS["secret"]

    return ex


# 单例
_spot = None
_futures = None


def get_spot():
    global _spot
    if _spot is None:
        _spot = make_spot_exchange()
    return _spot


def get_futures():
    global _futures
    if _futures is None:
        _futures = make_futures_exchange()
    return _futures
