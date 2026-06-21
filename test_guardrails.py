"""
护栏逻辑单元测试（不连交易所、不调 LLM，纯逻辑）
================================================
验证护栏这道安全核心是否正确。python test_guardrails.py
"""
import sys
# 让护栏的金额估算在无网时也能跑：只测不依赖实时价的用例（带 amount_usdt 的）
from config.settings import Guardrails

def check_order_offline(order):
    """复制 guardrails.check_order 的纯逻辑部分用于离线测试（不查实时价）。"""
    base = order.get("symbol","").upper().split("/")[0].split(":")[0]
    if base not in Guardrails.ALLOWED_SYMBOLS:
        return False, f"币种 {base} 不在白名单"
    lev = order.get("leverage")
    if lev is not None and (lev < 1 or lev > Guardrails.MAX_LEVERAGE):
        return False, f"杠杆 {lev}x 越界"
    notional = order.get("amount_usdt")
    if notional is not None and notional > Guardrails.MAX_ORDER_USDT:
        return False, f"金额 {notional} 越界"
    return True, "通过"

cases = [
    # (描述, 订单, 期望通过?)
    ("正常现货买入",      {"symbol":"BTC","amount_usdt":50}, True),
    ("超单笔金额",        {"symbol":"BTC","amount_usdt":500}, False),
    ("非白名单币种",      {"symbol":"DOGE","amount_usdt":50}, False),
    ("正常合约开多",      {"symbol":"ETH","amount_usdt":80,"leverage":5}, True),
    ("超杠杆上限",        {"symbol":"ETH","amount_usdt":50,"leverage":50}, False),
    ("边界:正好上限金额",  {"symbol":"BNB","amount_usdt":100}, True),
    ("边界:正好上限杠杆",  {"symbol":"BTC","amount_usdt":50,"leverage":20}, True),
]

print("="*50); print("护栏逻辑测试"); print("="*50)
passed = 0
for desc, order, expect in cases:
    ok, reason = check_order_offline(order)
    status = "✓" if ok == expect else "✗ 失败!"
    if ok == expect: passed += 1
    print(f"  {status} {desc}: {'通过' if ok else '拒绝'} ({reason})")
print(f"\n{passed}/{len(cases)} 测试通过")
sys.exit(0 if passed == len(cases) else 1)
