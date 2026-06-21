"""
命令行入口（完整版：查询 + 下单 + 护栏 + 人工确认）
==================================================
python main.py

查询示例：
  - BTC 现货多少钱？   / 查我的合约余额   / 我有哪些持仓？
下单示例（会先护栏校验，再让你确认）：
  - 买 50 USDT 的 BTC 现货
  - 5倍杠杆开多 0.01 个 ETH，止损 2000
  - 平掉所有 BTC 多单
输入 quit 退出。
"""
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from agent.trade_agent import build_graph

CONFIG = {"configurable": {"thread_id": "cli-session"}}


def print_ai(messages):
    """打印最后一条 AI 文本回复。"""
    for m in reversed(messages):
        if getattr(m, "type", None) == "ai" and m.content:
            print(f"\n助手 > {m.content}")
            return


def main():
    print("=" * 58)
    print("数字货币交易助手 · 完整版（testnet 假钱）")
    print("查询直接问；下单会先护栏校验再请你确认。quit 退出。")
    print("=" * 58)

    graph = build_graph()

    while True:
        try:
            user = input("\n你 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见"); break
        if user.lower() in {"quit", "exit", "q"}:
            print("再见"); break
        if not user:
            continue

        try:
            result = graph.invoke(
                {"messages": [HumanMessage(content=user)],
                 "last_user_query": user, "pending_order": None},
                CONFIG,
            )

            # 处理下单确认的 interrupt 暂停
            while "__interrupt__" in result:
                intr = result["__interrupt__"][0].value
                order = intr["order"]
                print("\n" + "─" * 50)
                print("⚠️  待确认订单（护栏已通过）：")
                for k, v in order.items():
                    print(f"     {k}: {v}")
                print("─" * 50)
                decision = input("  批准请输入 approve，否决输入 reject > ").strip()
                result = graph.invoke(Command(resume=decision), CONFIG)

            print_ai(result["messages"])

        except Exception as e:
            print(f"\n[出错] {e}")


if __name__ == "__main__":
    main()
