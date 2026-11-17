#MCP 只能异步使用

import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "runtime", ".env"))
MCP_PORT = os.getenv("MCP_PORT", "18765")

model = ChatOpenAI(
    model=os.getenv("DEEPSEEK_MODEL", "deepseek-flash"),
    base_url="https://api.deepseek.com",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    use_responses_api=False,  # deepseek 没有 responses 接口
    extra_body={"thinking": {"type": "disabled"}},
)

mcp_server = MultiServerMCPClient(
    {
        "homework": {
            "transport": "sse",
            "url": f"http://127.0.0.1:{MCP_PORT}/sse"
        }
    }
)


async def get_mcp_tools():
    tools = await mcp_server.get_tools()
    print("可用工具:", [t.name for t in tools])
    return tools


def create_agent_mcp(tools, userid):
    system_prompt = f"""你是钉钉课堂机器人，必要时调用工具，根据工具结果简短回答。

【当前用户】
钉钉 userid：{userid}

规则：
- 问现在几点、今天几号、星期几，先调用 get_current_beijing_time
- 两个数相加用 add，日期相差几天用 date_difference_days，统计文本用 count_text
- 用户要创建待办时，先把截止时间换成 YYYY-MM-DD HH:MM:SS，再用 datetime_to_timestamp_ms 转成毫秒时间戳
- 说的是"明天""下周五"这种相对日期，先调用 get_current_beijing_time
- create_todo_task 的 user_id 只能填上面的 userid，不能给别人创建待办
- 缺少标题或截止时间就问用户
"""
    return create_agent(model, tools, system_prompt=system_prompt)
