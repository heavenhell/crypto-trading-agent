"""
下单执行工具（阶段 4）—— 真正调 ccxt 下单
==========================================
★ 重要：这些函数【不】直接暴露给 LLM 选择！
   它们只在"护栏通过 + 人工确认"之后，由图的 execute 节点调用。
   LLM 只负责解析出"订单意图"，碰不到真正的下单动作。

包含 ccxt 的几个工程要点（来自实测）：
  - 设杠杆/保证金模式要【单独调用】set_leverage / set_margin_mode，
    不能指望塞进 create_order 的 params（Binance 会忽略）
  - 保证金模式已是 isolated 时再设会报 -4046，要捕获忽略
  - 止损用单独的 reduceOnly STOP_MARKET 触发单
"""
from exchange import get_spot, get_futures


def _spot_symbol(symbol: str) -> str:
    base = symbol.upper().split("/")[0].split(":")[0]
    return f"{base}/USDT"

def _swap_symbol(symbol: str) -> str:
    base = symbol.upper().split("/")[0].split(":")[0]
    return f"{base}/USDT:USDT"


# ===================== 现货下单 =====================

def spot_market_buy(symbol: str, amount_usdt: float) -> dict:
    """现货市价买入，按 USDT 金额（quote）下单。"""
    ex = get_spot()
    sym = _spot_symbol(symbol)
    # Binance 现货市价买支持用 cost(USDT) 下单
    order = ex.create_order(sym, "market", "buy", None, None,
                            {"quoteOrderQty": amount_usdt})
    return _summarize(order)

def spot_market_sell(symbol: str, amount: float) -> dict:
    """现货市价卖出，按币的数量下单。"""
    ex = get_spot()
    sym = _spot_symbol(symbol)
    order = ex.create_order(sym, "market", "sell", amount)
    return _summarize(order)

def spot_limit_order(symbol: str, side: str, amount: float, price: float) -> dict:
    """现货限价单。side 为 'buy'/'sell'，amount 为币的数量，price 为限价。"""
    ex = get_spot()
    sym = _spot_symbol(symbol)
    order = ex.create_order(sym, "limit", side, amount, price)
    return _summarize(order)

def spot_cancel(symbol: str, order_id: str) -> dict:
    """撤销现货订单。"""
    ex = get_spot()
    sym = _spot_symbol(symbol)
    res = ex.cancel_order(order_id, sym)
    return {"canceled": order_id, "symbol": sym}


# ===================== 合约下单 =====================

def _prepare_futures(symbol: str, leverage: int):
    """下合约单前：设逐仓 + 设杠杆。已是 isolated 的 -4046 错误忽略。"""
    ex = get_futures()
    sym = _swap_symbol(symbol)
    try:
        ex.set_margin_mode("isolated", sym)
    except Exception as e:
        if "-4046" not in str(e) and "No need to change" not in str(e):
            raise   # 其他错误才抛
    ex.set_leverage(leverage, sym)
    return ex, sym


def futures_open(symbol: str, side: str, amount: float, leverage: int,
                 stop_loss: float = None) -> dict:
    """
    合约开仓。side='long' 开多 / 'short' 开空；amount 为合约数量（币）；
    leverage 杠杆；stop_loss 可选，设了就同时挂一个止损触发单。
    """
    ex, sym = _prepare_futures(symbol, leverage)
    order_side = "buy" if side == "long" else "sell"

    # 主仓位（市价开）
    order = ex.create_order(sym, "market", order_side, amount, None,
                            {"marginMode": "isolated"})
    result = {"position": _summarize(order)}

    # 可选止损：反向的 reduceOnly STOP_MARKET
    if stop_loss is not None:
        sl_side = "sell" if side == "long" else "buy"
        sl = ex.create_order(sym, "STOP_MARKET", sl_side, amount, None,
                             {"stopPrice": stop_loss, "reduceOnly": True})
        result["stop_loss"] = _summarize(sl)

    return result


def futures_close(symbol: str, side: str = None, amount: float = None,
                  price: float = None) -> dict:
    """
    平仓。
    - side: 'long' 只平多 / 'short' 只平空 / None 平所有方向
    - amount: 指定平仓数量（合约张数/币数），不传则平全部
    - price: 指定限价（用于止盈/止损），不传则市价平
    """
    ex = get_futures()
    sym = _swap_symbol(symbol)
    positions = ex.fetch_positions([sym])
    closed = []
    for p in positions:
        contracts = abs(float(p.get("contracts") or 0))
        if contracts <= 0:
            continue
        pos_side = p["side"]   # long / short
        if side and side != pos_side:
            continue
        # 决定平仓数量
        qty = min(contracts, amount) if amount else contracts
        if qty <= 0:
            continue
        # 反向 reduceOnly 单
        close_side = "sell" if pos_side == "long" else "buy"
        if price:
            # 限价平仓（止盈/止损）
            order = ex.create_order(sym, "limit", close_side, qty, price,
                                    {"reduceOnly": True})
        else:
            # 市价平仓
            order = ex.create_order(sym, "market", close_side, qty, None,
                                    {"reduceOnly": True})
        closed.append(_summarize(order))
    return {"closed_positions": closed or "没有匹配的持仓"}


def set_leverage_tool(symbol: str, leverage: int) -> dict:
    """单独设置某合约的杠杆。"""
    ex, sym = _prepare_futures(symbol, leverage)
    return {"symbol": sym, "leverage": leverage, "margin_mode": "isolated"}


# ===================== 辅助 =====================

def _summarize(order: dict) -> dict:
    """从 ccxt 返回里挑关键字段，避免回给用户一大坨。"""
    return {
        "id": order.get("id"),
        "symbol": order.get("symbol"),
        "side": order.get("side"),
        "type": order.get("type"),
        "amount": order.get("amount"),
        "price": order.get("price") or order.get("average"),
        "status": order.get("status"),
    }
