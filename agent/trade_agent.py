"""
完整交易 Agent（阶段 3+4+5 整合）
==================================
流程（图）：
  agent ──┬─ 只读查询 → tools → 回 agent
          └─ 下单意图 → guardrail(护栏硬校验)
                          ├─ 拒绝 → 回 agent 告知用户
                          └─ 通过 → human_confirm(interrupt 暂停等人)
                                      ├─ reject → 回 agent
                                      └─ approve → execute(真正下单) → 记录 → 回 agent

★ 安全核心：LLM 只能调用"只读工具"和一个特殊的"propose_order(提议订单)"工具。
   propose_order 不下单，只把订单意图结构化。真正下单在 execute 节点，
   且必经 护栏 + 人工确认。LLM 无论如何都碰不到真实下单动作。
"""
from typing import Annotated, Optional
from typing_extensions import TypedDict

from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

from config.settings import LLM_PROVIDER, LLM_CONFIG, Guardrails
from tools.query_tools import (
    get_spot_ticker, get_spot_balance, get_futures_ticker,
    get_futures_balance, get_positions, get_funding_rate,
)
from tools.guardrails import check_order, needs_confirmation
from tools import trade_tools
from tools.trade_tools import set_leverage_tool
from tools.order_store import init_db, log_order


# ============ 只读工具（LLM 可自由调用）============
spot_ticker = tool(get_spot_ticker)
spot_balance = tool(get_spot_balance)
fut_ticker = tool(get_futures_ticker)
fut_balance = tool(get_futures_balance)
positions = tool(get_positions)
funding = tool(get_funding_rate)


# ============ 提议订单工具（关键！不下单，只结构化意图）============
@tool
def propose_order(
    market: str, action: str, symbol: str,
    amount_usdt: Optional[float] = None,
    amount: Optional[float] = None,
    price: Optional[float] = None,
    leverage: Optional[int] = None,
    stop_loss: Optional[float] = None,
    side: Optional[str] = None,
) -> str:
    """当用户想下单/开仓/平仓/撤单/设止盈止损时调用此工具，把订单意图结构化。
    【此工具不会真正下单】，只是提交一个待护栏校验和人工确认的订单意图。

    参数说明：
    - market: 'spot'(现货) 或 'futures'(合约)
    - action: 现货用 'buy'/'sell'/'limit_buy'/'limit_sell'/'cancel'；
              合约用 'open_long'/'open_short'/'close'/'set_leverage'
    - symbol: 币种，如 'BTC'/'ETH'/'BNB'
    - amount_usdt: 按 USDT 金额下单时填（如"买100 USDT的BTC"）
    - amount: 按币的数量下单时填（如"开0.1个ETH多单"；平仓时可指定部分数量）
    - price: 限价单价格（现货限价单用；合约平仓时填了就是止盈/止损限价单）
    - leverage: 合约杠杆（1-20）
    - stop_loss: 合约开仓时附带的止损触发价
    - side: 合约平仓时用 'long'/'short' 指定平哪个方向，不填则平所有方向
    """
    return "ORDER_PROPOSED"   # 实际处理在 guardrail 节点，这里只占位


READ_TOOLS = [spot_ticker, spot_balance, fut_ticker, fut_balance, positions, funding]
ALL_TOOLS = READ_TOOLS + [propose_order]


# ============ LLM ============
def build_llm():
    cfg = LLM_CONFIG[LLM_PROVIDER]
    kwargs = {"model": cfg["model"], "api_key": cfg["api_key"], "temperature": 0}
    if cfg.get("base_url"):
        kwargs["base_url"] = cfg["base_url"]
    return ChatOpenAI(**kwargs).bind_tools(ALL_TOOLS)

llm = build_llm()


# ============ 状态 ============
class TradeState(TypedDict):
    messages: Annotated[list, add_messages]
    pending_order: Optional[dict]
    last_user_query: Optional[str]


SYSTEM_PROMPT = f"""你是数字货币交易助手，操作 Binance testnet（现货+合约）。
风控限制（硬性，你无法突破）：单笔≤{Guardrails.MAX_ORDER_USDT} USDT，
杠杆≤{Guardrails.MAX_LEVERAGE}x，只允许 {Guardrails.ALLOWED_SYMBOLS}，合约逐仓。

规则：
- 查询类问题（价格/余额/持仓/资金费率）直接调只读工具，简洁中文回答。
- 用户想下单/开仓/平仓/撤单时，调用 propose_order 把意图结构化（这不会真下单，
  会先经过护栏和人工确认）。把用户的自然语言准确转成 propose_order 的参数。
- 例："5倍杠杆开多0.1个ETH止损3000" →
  propose_order(market='futures', action='open_long', symbol='ETH',
                amount=0.1, leverage=5, stop_loss=3000)
- 例："把BTC合约杠杆设为10倍" →
  propose_order(market='futures', action='set_leverage', symbol='BTC', leverage=10)
- 例："平掉一半ETH多单" →
  propose_order(market='futures', action='close', symbol='ETH',
                side='long', amount=0.05)
- 例："BTC跌到60000就止损平仓" →
  propose_order(market='futures', action='close', symbol='BTC',
                side='long', price=60000)
  （注意：平仓不传 amount 表示平全部，传 amount 表示部分平仓；
   price 是限价止盈/止损价，不传则是市价平仓）
- 护栏拒绝或用户否决后，如实告知用户原因，不要重复尝试绕过。"""


# ============ 节点 ============
def agent_node(state: TradeState):
    msgs = state["messages"]
    if not any(getattr(m, "type", None) == "system" for m in msgs):
        msgs = [SystemMessage(content=SYSTEM_PROMPT)] + msgs
    response = llm.invoke(msgs)
    return {"messages": [response]}


def route_after_agent(state: TradeState):
    """agent 之后：无 tool_call → 结束；调了 propose_order → 护栏；调了只读工具 → 执行只读。"""
    last = state["messages"][-1]
    if not getattr(last, "tool_calls", None):
        return END
    for tc in last.tool_calls:
        if tc["name"] == "propose_order":
            return "guardrail"
    return "read_tools"


def read_tools_node(state: TradeState):
    """执行只读工具（agent 选中的）。"""
    last = state["messages"][-1]
    out = []
    read_map = {t.name: t for t in READ_TOOLS}
    for tc in last.tool_calls:
        if tc["name"] in read_map:
            try:
                result = read_map[tc["name"]].invoke(tc["args"])
            except Exception as e:
                result = f"查询出错: {e}"
            out.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
    return {"messages": out}


def guardrail_node(state: TradeState):
    """护栏硬校验。从 propose_order 的 tool_call 取订单意图。"""
    last = state["messages"][-1]
    tc = next(t for t in last.tool_calls if t["name"] == "propose_order")
    order = dict(tc["args"])
    order["_tool_call_id"] = tc["id"]

    ok, reason = check_order(order)
    print(f"  [护栏] {reason}")

    if not ok:
        # 拒绝：记录 + 把结果作为 ToolMessage 回给 agent
        log_order(state.get("last_user_query", ""), order, False, reason)
        msg = ToolMessage(content=f"订单被护栏拒绝：{reason}", tool_call_id=tc["id"])
        return {"messages": [msg], "pending_order": None}

    return {"pending_order": order}


def route_after_guardrail(state: TradeState):
    return "human_confirm" if state.get("pending_order") else "agent"


def human_confirm_node(state: TradeState):
    """HITL：interrupt 暂停，把订单详情交给人确认。"""
    order = state["pending_order"]
    if not needs_confirmation(order):
        return Command(goto="execute")

    decision = interrupt({
        "type": "confirm_order",
        "order": {k: v for k, v in order.items() if not k.startswith("_")},
        "prompt": "请确认是否执行此订单（approve / reject）",
    })

    tcid = order["_tool_call_id"]
    if str(decision).lower().strip() in {"approve", "yes", "y", "确认", "是"}:
        return Command(goto="execute")
    # 否决
    log_order(state.get("last_user_query", ""), order, True, "护栏通过", "rejected")
    msg = ToolMessage(content="用户否决了该订单，未执行。", tool_call_id=tcid)
    return Command(goto="agent", update={"pending_order": None, "messages": [msg]})


def execute_node(state: TradeState):
    """真正下单。只有护栏通过 + 人工批准才会到这里。"""
    order = state["pending_order"]
    tcid = order["_tool_call_id"]
    try:
        result = _dispatch_order(order)
        log_order(state.get("last_user_query", ""), order, True, "护栏通过",
                  "approved", result)
        content = f"✅ 订单已执行：{result}"
    except Exception as e:
        content = f"❌ 下单失败：{e}"
        log_order(state.get("last_user_query", ""), order, True, "护栏通过",
                  "approved", {"error": str(e)})
    msg = ToolMessage(content=content, tool_call_id=tcid)
    return {"messages": [msg], "pending_order": None}


def _dispatch_order(order: dict):
    """把订单意图分发到具体的 trade_tools 函数。"""
    m, a, sym = order["market"], order["action"], order["symbol"]

    if m == "spot":
        if a == "buy":
            return trade_tools.spot_market_buy(sym, order["amount_usdt"])
        if a == "sell":
            return trade_tools.spot_market_sell(sym, order["amount"])
        if a in ("limit_buy", "limit_sell"):
            side = "buy" if a == "limit_buy" else "sell"
            return trade_tools.spot_limit_order(sym, side, order["amount"], order["price"])
        if a == "cancel":
            return trade_tools.spot_cancel(sym, order.get("order_id"))

    elif m == "futures":
        if a == "open_long":
            return trade_tools.futures_open(sym, "long", order["amount"],
                                            order["leverage"], order.get("stop_loss"))
        if a == "open_short":
            return trade_tools.futures_open(sym, "short", order["amount"],
                                            order["leverage"], order.get("stop_loss"))
        if a == "close":
            return trade_tools.futures_close(
                sym, order.get("side"), order.get("amount"), order.get("price"))
        if a == "set_leverage":
            return set_leverage_tool(sym, order["leverage"])

    raise ValueError(f"不支持的操作: market={m}, action={a}")


# ============ 组装图 ============
def build_graph():
    init_db()
    g = StateGraph(TradeState)
    g.add_node("agent", agent_node)
    g.add_node("read_tools", read_tools_node)
    g.add_node("guardrail", guardrail_node)
    g.add_node("human_confirm", human_confirm_node)
    g.add_node("execute", execute_node)

    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", route_after_agent,
                            {"read_tools": "read_tools", "guardrail": "guardrail", END: END})
    g.add_edge("read_tools", "agent")
    g.add_conditional_edges("guardrail", route_after_guardrail,
                            {"human_confirm": "human_confirm", "agent": "agent"})
    g.add_edge("execute", "agent")

    # TODO: 生产环境建议换成 SqliteSaver（需 pip install langgraph-checkpoint-sqlite）
    #   from langgraph.checkpoint.sqlite import SqliteSaver
    #   import sqlite3
    #   checkpointer = SqliteSaver(sqlite3.connect("data/checkpoints.db"))
    return g.compile(checkpointer=MemorySaver())
