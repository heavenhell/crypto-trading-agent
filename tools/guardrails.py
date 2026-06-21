"""
护栏校验（阶段 3）—— 纯代码硬限制，LLM 无法绕过
================================================
所有下单意图在执行前必须先过这一关。越界直接拒，根本到不了人工确认。
这是"即使 LLM 解析错了也不会造成损失"的第一道防线。
"""
from config.settings import Guardrails
from exchange import get_spot, get_futures


def _base_of(symbol: str) -> str:
    """从 'BTC/USDT' 或 'BTC/USDT:USDT' 取出 base 币种 'BTC'。"""
    return symbol.upper().split("/")[0].split(":")[0]


def check_order(order: dict) -> tuple[bool, str]:
    """
    校验一个下单意图。order 是 LLM 解析出来的结构化字典，形如：
      {market: 'spot'/'futures', action: 'buy'/'sell'/'open_long'/...,
       symbol: 'BTC', amount_usdt: 50, leverage: 5, ...}
    返回 (是否通过, 原因)。
    """
    base = _base_of(order.get("symbol", ""))

    # 1. 白名单
    if base not in Guardrails.ALLOWED_SYMBOLS:
        return False, f"币种 {base} 不在允许列表 {Guardrails.ALLOWED_SYMBOLS} 内"

    # 2. 杠杆上限（合约才有）
    lev = order.get("leverage")
    if lev is not None:
        if lev < 1 or lev > Guardrails.MAX_LEVERAGE:
            return False, f"杠杆 {lev}x 超出允许范围 1~{Guardrails.MAX_LEVERAGE}x"

    # 3. 单笔金额上限（按名义价值 USDT 估算）
    notional = _estimate_notional(order)
    if notional is not None and notional > Guardrails.MAX_ORDER_USDT:
        return False, f"订单名义价值约 {notional:.2f} USDT，超过上限 {Guardrails.MAX_ORDER_USDT}"

    return True, "护栏校验通过"


def _estimate_notional(order: dict):
    """估算订单名义价值（USDT）。用于金额上限校验。"""
    # 如果用户直接给了 USDT 金额
    amount_usdt = order.get("amount_usdt")
    if amount_usdt is not None:
        return float(amount_usdt)
    # 如果给的是币的数量，用当前价估算
    amount = order.get("amount")
    if amount is not None:
        try:
            base = _base_of(order["symbol"])
            if order.get("market") == "futures":
                ex = get_futures()
                price = ex.fetch_ticker(f"{base}/USDT:USDT")["last"]
            else:
                ex = get_spot()
                price = ex.fetch_ticker(f"{base}/USDT")["last"]
            return float(amount) * float(price)
        except Exception:
            return None   # 估不出就不卡金额（但其他护栏仍生效）
    return None


def needs_confirmation(order: dict) -> bool:
    """是否需要人工确认。当前配置：所有写操作都要确认。"""
    return Guardrails.REQUIRE_CONFIRM_ALL_WRITES
