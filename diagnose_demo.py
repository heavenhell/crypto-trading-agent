"""
Demo 端点诊断脚本 —— 打印实际请求 URL，帮助定位连接问题。
python diagnose_demo.py
把完整输出贴出来即可定位。
"""
import ccxt
from config.settings import SPOT_KEYS, FUTURES_KEYS

DEMO_SPOT_URL = "https://demo-api.binance.com"
DEMO_FAPI_URL = "https://demo-fapi.binance.com"

print("ccxt 版本:", ccxt.__version__)
print("=" * 60)

# ---------- 现货 ----------
print("\n【现货】尝试连接 demo-api.binance.com")
try:
    ex = ccxt.binance({
        "apiKey": SPOT_KEYS["apiKey"],
        "secret": SPOT_KEYS["secret"],
        "enableRateLimit": True,
        "options": {"defaultType": "spot", "adjustForTimeDifference": True},
    })
    ex.urls["api"]["public"] = DEMO_SPOT_URL + "/api/v3"
    ex.urls["api"]["private"] = DEMO_SPOT_URL + "/api/v3"
    ex.options["fetchCurrencies"] = False
    ex.has["fetchCurrencies"] = False
    ex.load_markets()
    print("  load_markets ✓")
    bal = ex.fetch_balance()
    usdt = bal.get("USDT", {}).get("free", 0)
    print(f"  fetch_balance ✓  USDT可用: {usdt}")
except Exception as e:
    print(f"  ✗ {type(e).__name__}: {e}")
    # 打印它实际用的 URL，便于排查
    try:
        print("  当前 public URL:", ex.urls['api'].get('public'))
        print("  当前 private URL:", ex.urls['api'].get('private'))
    except Exception:
        pass

# ---------- 合约 ----------
print("\n【合约】尝试连接 demo-fapi.binance.com")
try:
    ex = ccxt.binance({
        "apiKey": FUTURES_KEYS["apiKey"],
        "secret": FUTURES_KEYS["secret"],
        "enableRateLimit": True,
        "options": {"defaultType": "future", "adjustForTimeDifference": True},
    })
    ex.urls["api"]["fapiPublic"] = DEMO_FAPI_URL + "/fapi/v1"
    ex.urls["api"]["fapiPrivate"] = DEMO_FAPI_URL + "/fapi/v1"
    ex.load_markets()
    print("  load_markets ✓")
    bal = ex.fetch_balance()
    usdt = bal.get("USDT", {}).get("free", 0)
    print(f"  fetch_balance ✓  USDT可用: {usdt}")
except Exception as e:
    print(f"  ✗ {type(e).__name__}: {e}")
    try:
        print("  fapi 相关 URL 键:", [k for k in ex.urls['api'] if 'fapi' in k.lower()])
    except Exception:
        pass

print("\n" + "=" * 60)
print("把以上完整输出贴出来，即可定位问题。")
