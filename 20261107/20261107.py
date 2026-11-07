import json
from pathlib import Path
from typing import Annotated, TypedDict

import pymysql
import sqlglot
from sqlglot import exp
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, START, END

# 1. 基础配置
model = ChatOpenAI(
    model="deepseek-flash",
    api_key="DeepSeek API Key",
    base_url="https://api.deepseek.com",
    extra_body={"thinking": {"type": "disabled"}},
)

db_config = {
    "host": "127.0.0.1",
    "port": 13306,
    "user": "sql_reader",
    "password": "sql_reader",
    "database": "employees_homework",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

schema = json.loads(Path("schema.json").read_text(encoding="utf-8"))
MAX_ATTEMPTS = 3


# 2. 状态定义
class State(TypedDict, total=False):
    question: str
    tables: list[str]
    table_info: str
    query: str
    result: list[dict]
    error: str
    answer: str
    attempts: int


class Intent(TypedDict):
    allowed: Annotated[bool, "问题是否可以通过查询当前员工数据库回答"]
    tables: Annotated[list[str], "查询需要用到的表名（包含多表关联的中间表）"]
    reason: Annotated[str, "无法回答的原因，正常查询时为空"]


class Review(TypedDict):
    passed: Annotated[bool, "SQL逻辑和查询结果是否正确回答了用户问题"]
    reason: Annotated[str, "判断理由，如果不通过请说明怎么修改SQL"]


# 3. 工具函数
def ask_llm(template, values, output_schema=None):
    llm = model.with_structured_output(output_schema, method="function_calling") if output_schema else model
    res = (PromptTemplate.from_template(template) | llm).invoke(values)
    return res if output_schema else res.content.strip()


def run_sql(sql):
    with pymysql.connect(**db_config) as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            return list(cursor.fetchall())


# 4. 节点函数
def check_intent(state: State):
    res = ask_llm("""
你是一个数据库助手，请判断用户的问题是否可以通过查询下面的员工数据库来回答，并选出需要用到的表。
只允许正常的查询请求，不能修改数据。如果是多表关联查询，记得把中间表也选上。

数据库表结构：{schema}
用户问题：{question}
""", {"schema": json.dumps(schema, ensure_ascii=False), "question": state["question"]}, Intent)

    tables = [t for t in res["tables"] if t in schema]
    if not res["allowed"] or not tables:
        return {"tables": [], "answer": res["reason"] or "这个问题无法通过当前员工数据库回答，请换个问题。"}
    return {"tables": list(set(tables)), "answer": ""}


def select_schema(state: State):
    # 第一次用选出来的表，如果报错重试就把所有表都给模型，防止漏表
    tables = list(schema.keys()) if state.get("error") else state["tables"]
    print("使用的表：", tables)
    info = "\n\n".join(schema[t] for t in tables)
    return {"tables": tables, "table_info": info}


def write_query(state: State):
    attempts = state["attempts"] + 1
    print(f"第 {attempts} 次生成 SQL...")
    sql = ask_llm("""
请根据下面的表结构和用户问题，写一条 MySQL 查询语句。
要求：
1. 只输出纯 SQL 语句，不要带 markdown 代码块。
2. 只能写普通的 SELECT 查询（可以用 JOIN 和子查询，不要用 WITH 或 UNION）。
3. 查明细数据最多返回 10 条；注意区分历史记录和当前记录，关联时避免重复统计。
4. 如果有上次报错信息，请针对性修改 SQL。

表结构：
{table_info}

用户问题：{question}
上次生成的SQL：{query}
上次的报错信息：{error}
""", {k: state.get(k, "") for k in ("table_info", "question", "query", "error")})
    return {"query": sql, "error": "", "result": [], "answer": "", "attempts": attempts}


def validate_query(state: State):
    try:
        parsed = sqlglot.parse(state["query"], read="mysql")
        if len(parsed) != 1 or not isinstance(parsed[0], exp.Select):
            return {"error": "SQL校验失败：只能执行单条 SELECT 语句"}

        tree = parsed[0]
        if tree.args.get("with_"):
            return {"error": "SQL校验失败：暂不支持 WITH 语法，请改用子查询或 JOIN"}

        # 检查表名是否在 schema 里
        for table in tree.find_all(exp.Table):
            if table.name not in schema:
                return {"error": f"SQL校验失败：不存在表 {table.name}"}

        # 限制最多返回 10 条
        limit = tree.args.get("limit")
        count = min(10, int(limit.expression.this)) if limit else 10
        return {"query": tree.limit(count).sql(dialect="mysql"), "error": ""}
    except Exception as e:
        return {"error": f"SQL语法解析失败：{e}"}


def explain_query(state: State):
    try:
        plan = run_sql("EXPLAIN " + state["query"])
        print("EXPLAIN 通过，执行计划行数：", len(plan))
        return {"error": ""}
    except Exception as e:
        return {"error": f"EXPLAIN 检查失败：{e}"}


def execute_query(state: State):
    try:
        return {"result": run_sql(state["query"]), "error": ""}
    except Exception as e:
        return {"result": [], "error": f"SQL执行失败：{e}"}


def check_result(state: State):
    review = ask_llm("""
请检查下面的 SQL 语句和查询结果是否准确回答了用户的问题（比如关联条件、过滤条件、聚合方式是否正确）。
注意：如果 SQL 逻辑没问题，就算查出来是空结果或者 0 也是正常的，直接判通过即可。

问题：{question}
表结构：{table_info}
SQL：{query}
查询结果：{result}
""", {**state, "result": json.dumps(state["result"], ensure_ascii=False, default=str)}, Review)
    print("结果检查：", review["reason"])
    return {"error": "" if review["passed"] else f"结果不太对：{review['reason']}"}


def generate_answer(state: State):
    if not state["result"]:
        return {"answer": "没有查到符合条件的数据。"}
    answer = ask_llm("""
请根据下面的 SQL 查询结果，用自然语言简短回答用户的问题。

问题：{question}
SQL：{query}
查询结果：{result}
""", {**state, "result": json.dumps(state["result"], ensure_ascii=False, default=str)})
    return {"answer": answer}


# 5. 路由逻辑
def route_step(state: State):
    if not state.get("error"):
        return "next"
    print("遇到错误：", state["error"])
    return "retry" if state["attempts"] < MAX_ATTEMPTS else "end"


# 6. 构建 LangGraph
builder = StateGraph(State)
for fn in [check_intent, select_schema, write_query, validate_query,
           explain_query, execute_query, check_result, generate_answer]:
    builder.add_node(fn.__name__, fn)

builder.add_edge(START, "check_intent")
builder.add_conditional_edges(
    "check_intent",
    lambda s: "select_schema" if s.get("tables") else END
)
builder.add_edge("select_schema", "write_query")
builder.add_edge("write_query", "validate_query")

steps = [
    ("validate_query", "explain_query"),
    ("explain_query", "execute_query"),
    ("execute_query", "check_result"),
    ("check_result", "generate_answer"),
]
for src, dst in steps:
    builder.add_conditional_edges(src, route_step, {"next": dst, "retry": "select_schema", "end": END})

builder.add_edge("generate_answer", END)
app = builder.compile()


if __name__ == "__main__":
    q = input("请输入查询问题：").strip()
    if q:
        res = app.invoke({"question": q, "attempts": 0})
        print("\n--- 运行结果 ---")
        print("尝试次数：", res.get("attempts"))
        print("最终 SQL：", res.get("query"))
        print("查询数据：", res.get("result"))
        print("最终回答：", res.get("error") or res.get("answer"))
