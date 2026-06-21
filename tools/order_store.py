"""
订单记录（阶段 5）—— SQLite 存储每笔操作，用于审计和复盘
========================================================
记录完整链路：订单意图 → 护栏结果 → 人工决定 → 执行结果。
交易场景下可审计性很重要，每个动作都要留痕。
"""
import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "orders.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS order_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            user_query TEXT,
            order_intent TEXT,
            guardrail_pass INTEGER,
            guardrail_reason TEXT,
            human_decision TEXT,
            execution_result TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_order(user_query, order_intent, guardrail_pass, guardrail_reason,
              human_decision=None, execution_result=None):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO order_log (ts, user_query, order_intent, guardrail_pass, "
        "guardrail_reason, human_decision, execution_result) VALUES (?,?,?,?,?,?,?)",
        (datetime.now().isoformat(),
         user_query,
         json.dumps(order_intent, ensure_ascii=False),
         1 if guardrail_pass else 0,
         guardrail_reason,
         human_decision,
         json.dumps(execution_result, ensure_ascii=False) if execution_result else None),
    )
    conn.commit()
    conn.close()


def recent_orders(limit=10):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM order_log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
