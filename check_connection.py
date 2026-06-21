"""
阶段 0 自检 —— 只读、零风险。验证 testnet 连接是否通。
跑这个之前先：
  1. cp .env.example .env 并填好 key
  2. pip install -r requirements.txt
运行：python check_connection.py
"""
from exchange import get_spot, get_futures


def main():
    print("=" * 50)
    print("阶段 0：testnet 连通性自检（不涉及任何交易）")
    print("=" * 50)

    # --- 现货 ---
    try:
        spot = get_spot()
        ticker = spot.fetch_ticker("BTC/USDT")
        print(f"\n[现货] [OK] 连接成功")
        print(f"  BTC/USDT 最新价: {ticker['last']}")
        bal = spot.fetch_balance()
        usdt = bal.get("USDT", {}).get("free", 0)
        print(f"  现货 USDT 余额: {usdt}")
    except Exception as e:
        print(f"\n[现货] [FAIL] 失败: {e}")
        print("  排查：现货 key 是否来自 testnet.binance.vision？")

    # --- 合约 ---
    try:
        fut = get_futures()
        ticker = fut.fetch_ticker("BTC/USDT:USDT")
        print(f"\n[合约] [OK] 连接成功")
        print(f"  BTC 永续 最新价: {ticker['last']}")
        bal = fut.fetch_balance()
        usdt = bal.get("USDT", {}).get("free", 0)
        print(f"  合约 USDT 余额: {usdt}")
    except Exception as e:
        print(f"\n[合约] [FAIL] 失败: {e}")
        print("  排查：合约 key 是否来自 testnet.binancefuture.com？（与现货不同）")

    print("\n两个都显示 [OK] 就可以进入阶段 1/2 了。")


if __name__ == "__main__":
    main()
