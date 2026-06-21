import ccxt
from config.settings import FUTURES_KEYS

fx = ccxt.binance({
    "apiKey": FUTURES_KEYS["apiKey"], "secret": FUTURES_KEYS["secret"],
    "options": {"defaultType": "future", "adjustForTimeDifference": True},
})

# 先打印所有 fapi 相关 URL 的【原始值】，看清楚 ccxt 默认指向哪
print("=== 替换前的 fapi URL ===")
for key in fx.urls["api"]:
    if isinstance(fx.urls["api"][key], str) and "fapi" in key.lower():
        print(f"  {key}: {fx.urls['api'][key]}")

# 把所有 fapi 相关 URL 里的生产域名替换成 demo 域名（多种可能域名都换）
def to_demo(u):
    return (u.replace("fapi.binance.com", "demo-fapi.binance.com")
             .replace("testnet.binancefuture.com", "demo-fapi.binance.com"))

for key in list(fx.urls["api"].keys()):
    if isinstance(fx.urls["api"][key], str) and "fapi" in key.lower():
        fx.urls["api"][key] = to_demo(fx.urls["api"][key])

print("\n=== 替换后的 fapi URL ===")
for key in fx.urls["api"]:
    if isinstance(fx.urls["api"][key], str) and "fapi" in key.lower():
        print(f"  {key}: {fx.urls['api'][key]}")

print("\n=== 尝试查询合约余额 ===")
try:
    print("  USDT:", fx.fetch_balance().get("USDT"), "✓ 成功")
except Exception as e:
    print("  ✗", e)