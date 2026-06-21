"""
LangGraph 只读 Agent（阶段 2）
==============================
把自然语言 → LLM function calling → 调用只读查询工具。
这一版【只接只读工具】，问行情/余额/持仓，零风险。
下单 + 护栏 + HITL 在下一阶段加（图结构会扩展，但只读部分不变）。

LLM 支持 OpenAI 和 DeepSeek（都是 OpenAI 兼容接口），在 .env / settings 里切换。
"""
from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from config.settings import LLM_PROVIDER, LLM_CONFIG
from tools.query_tools import (
    get_spot_ticker, get_spot_balance, get_futures_ticker,
    get_futures_balance, get_positions, get_funding_rate,
)


# ---------- 1. 把普通函数包装成 LangChain tool ----------
# @tool 装饰器会把函数的 docstring 作为 description 给 LLM
spot_ticker = tool(get_spot_ticker)
spot_balance = tool(get_spot_balance)
fut_ticker = tool(get_futures_ticker)
fut_balance = tool(get_futures_balance)
positions = tool(get_positions)
funding = tool(get_funding_rate)

TOOLS = [spot_ticker, spot_balance, fut_ticker, fut_balance, positions, funding]


# ---------- 2. LLM（支持 OpenAI / DeepSeek 切换）----------
def build_llm():
    cfg = LLM_CONFIG[LLM_PROVIDER]
    kwargs = {"model": cfg["model"], "api_key": cfg["api_key"], "temperature": 0}
    if cfg.get("base_url"):
        kwargs["base_url"] = cfg["base_url"]
    return ChatOpenAI(**kwargs).bind_tools(TOOLS)


# ---------- 3. 状态 ----------
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


# ---------- 4. 节点 ----------
SYSTEM_PROMPT = """你是一个数字货币交易助手（当前为只读查询阶段，还不能下单）。
用户用自然语言提问，你要调用合适的工具查询信息并用简洁中文回答。
- 涉及现货价格/余额用现货工具，涉及合约/持仓/杠杆用合约工具。
- 如果用户想下单/开仓/平仓，礼貌说明"下单功能在下个阶段开放，当前只能查询"。
- 回答用中文，简洁清楚，带上关键数字。"""

llm = build_llm()

def agent_node(state: AgentState):
    msgs = state["messages"]
    # 首次注入 system prompt
    if not any(getattr(m, "type", None) == "system" for m in msgs):
        from langchain_core.messages import SystemMessage
        msgs = [SystemMessage(content=SYSTEM_PROMPT)] + msgs
    response = llm.invoke(msgs)
    return {"messages": [response]}


# ---------- 5. 组装图 ----------
def build_graph():
    g = StateGraph(AgentState)
    g.add_node("agent", agent_node)
    g.add_node("tools", ToolNode(TOOLS))
    g.add_edge(START, "agent")
    # tools_condition：agent 若发起 tool_call 就去 tools，否则结束
    g.add_conditional_edges("agent", tools_condition)
    g.add_edge("tools", "agent")   # 工具执行完回 agent 总结
    return g.compile()
