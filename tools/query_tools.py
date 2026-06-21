"""
只读查询工具层（阶段 1）
========================
只含【只读】操作，零风险。下单类写操作在下一阶段配合护栏单独加。
每个函数的 docstring 写得很明确，因为它会作为 description 给 LLM 做 function calling，
描述清楚"什么时候用我、返回什么"，直接影响 LLM 选得对不对。
"""
from exchange import get_spot, get_futures


def _norm_spot_symbol(symbol: str) -> str:
    """把 'BTC' / 'btc/usdt' 统一成 'BTC/USDT'。"""
    s = symbol.upper().replace(" ", "")
    if "/" not in s:
        s = f"{s}/USDT"
    return s


def _norm_swap_symbol(symbol: str) -> str:
    """合约永续统一成 'BTC/USDT:USDT'。"""
    s = symbol.upper().replace(" ", "")
    base = s.split("/")[0].split(":")[0]
    return f"{base}/USDT:USDT"


# ============ 现货只读 ============

def get_spot_ticker(symbol: str) -> dict:
    """查询【现货】某交易对的最新行情价格。
    参数 symbol 如 'BTC' 或 'BTC/USDT'。返回最新价、买一价、卖一价、24h涨跌幅。"""
    ex = get_spot()
    sym = _norm_spot_symbol(symbol)
    t = ex.fetch_ticker(sym)
    return {
        "symbol": sym, "last": t["last"], "bid": t["bid"],
        "ask": t["ask"], "percentage_24h": t.get("percentage"),
    }


def get_spot_balance(currency: str = "") -> dict:
    """查询【现货】账户余额。可选 currency 参数筛选币种（如 'BTC'、'USDT'）。
    不填则返回所有非零余额。"""
    ex = get_spot()
    bal = ex.fetch_balance()
    total = bal.get("total", {})
    if currency:
        cur = currency.upper()
        val = total.get(cur, 0)
        return {cur: val} if val > 0 else {}
    return {k: v for k, v in total.items() if v and v > 0}


# ============ 合约只读 ============

def get_futures_ticker(symbol: str) -> dict:
    """查询【合约】某永续合约的最新行情。参数 symbol 如 'BTC'。
    返回最新价和资金费率相关信息。用于合约交易前看价。"""
    ex = get_futures()
    sym = _norm_swap_symbol(symbol)
    t = ex.fetch_ticker(sym)
    return {"symbol": sym, "last": t["last"], "bid": t["bid"], "ask": t["ask"]}


def get_futures_balance(currency: str = "USDT") -> dict:
    """查询【合约】账户保证金余额。默认查 USDT，可传其他币种。"""
    ex = get_futures()
    bal = ex.fetch_balance()
    cur = currency.upper()
    return {f"{cur}_total": bal.get(cur, {}).get("total", 0),
            f"{cur}_free": bal.get(cur, {}).get("free", 0)}


def get_positions(symbol: str = "") -> list:
    """查询【合约】当前持仓。可选 symbol 参数筛选（如 'BTC'）。
    不填则返回所有持仓。返回方向、数量、开仓均价、未实现盈亏。"""
    ex = get_futures()
    syms = [_norm_swap_symbol(symbol)] if symbol else None
    positions = ex.fetch_positions(syms)
    result = []
    for p in positions:
        contracts = p.get("contracts") or 0
        if contracts and contracts != 0:   # 只返回有实际仓位的
            # Binance 不直接返回 leverage 字段，用 initialMarginPercentage 反算
            imp = p.get("initialMarginPercentage")
            leverage = round(1.0 / imp) if imp and imp > 0 else None
            result.append({
                "symbol": p["symbol"],
                "side": p["side"],            # long / short
                "contracts": contracts,
                "entry_price": p.get("entryPrice"),
                "unrealized_pnl": p.get("unrealizedPnl"),
                "leverage": leverage,
                "margin_mode": p.get("marginMode"),
            })
    return result


def get_funding_rate(symbol: str) -> dict:
    """查询【合约】某永续合约的当前资金费率。参数 symbol 如 'BTC'。"""
    ex = get_futures()
    sym = _norm_swap_symbol(symbol)
    fr = ex.fetch_funding_rate(sym)
    return {"symbol": sym, "funding_rate": fr.get("fundingRate"),
            "next_funding_time": fr.get("fundingDatetime")}


# ============ 工具注册表（供 agent 绑定）============
# 这一阶段全是只读工具，is_write 都是 False
READ_TOOLS = [
    {"func": get_spot_ticker, "is_write": False},
    {"func": get_spot_balance, "is_write": False},
    {"func": get_futures_ticker, "is_write": False},
    {"func": get_futures_balance, "is_write": False},
    {"func": get_positions, "is_write": False},
    {"func": get_funding_rate, "is_write": False},
]
