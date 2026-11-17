import datetime
import os

import httpx2
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer

from get_acctoken_id import get_acctoken_id, get_union_id

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "runtime", ".env"))
DINGDING_ID = os.getenv("DINGDING_ID")
DINGDING_SECRET = os.getenv("DINGDING_SECRET")
MCP_PORT = int(os.getenv("MCP_PORT", "18765"))

BEIJING_TZ = datetime.timezone(datetime.timedelta(hours=8))

mcp = MCPServer("dingtalk-homework")


@mcp.tool()
def add(a: int, b: int) -> int:
    """计算两个整数的和"""
    return a + b


@mcp.tool()
def get_current_beijing_time() -> str:
    """获取当前北京时间，用于判断用户说的日期是过去还是未来。"""
    now = datetime.datetime.now(BEIJING_TZ)
    return now.strftime("%Y-%m-%d %H:%M:%S")


@mcp.tool()
def datetime_to_timestamp_ms(datetime_str: str) -> str:
    """将北京时间字符串(格式 YYYY-MM-DD HH:MM:SS)转换为 Unix 毫秒时间戳，供 create_todo_task 的 dueTime 使用。"""
    try:
        dt = datetime.datetime.strptime(datetime_str.strip(), "%Y-%m-%d %H:%M:%S")
        dt = dt.replace(tzinfo=BEIJING_TZ)
        return str(int(dt.timestamp() * 1000))
    except ValueError:
        return "转换失败：时间格式必须是 YYYY-MM-DD HH:MM:SS，例如 2026-07-05 17:00:00"


@mcp.tool()
def date_difference_days(start_date: str, end_date: str) -> str:
    """计算两个日期相差几天，日期格式 YYYY-MM-DD"""
    try:
        start = datetime.datetime.strptime(start_date.strip(), "%Y-%m-%d")
        end = datetime.datetime.strptime(end_date.strip(), "%Y-%m-%d")
    except ValueError:
        return "日期格式必须是 YYYY-MM-DD，例如 2026-11-20"
    return f"相差 {abs((end - start).days)} 天"


@mcp.tool()
def count_text(text: str) -> str:
    """统计一段文本的字符数和行数"""
    return f"字符数：{len(text)}，行数：{len(text.splitlines())}"


@mcp.tool()
async def create_todo_task(user_id: str, subject: str, dueTime: int, description: str = "", priority: int = 20) -> str:
    """
    创建钉钉待办任务。
    user_id: 钉钉用户的 userid
    subject: 待办标题
    dueTime: 截止时间，Unix 毫秒时间戳
    description: 待办描述
    priority: 优先级，10较低 20普通 30较高 40紧急
    """
    access_token = await get_acctoken_id(DINGDING_ID, DINGDING_SECRET)
    union_id = await get_union_id(access_token, user_id)

    url = f"https://api.dingtalk.com/v1.0/todo/users/{union_id}/tasks"
    headers = {
        "Content-Type": "application/json",
        "x-acs-dingtalk-access-token": access_token
    }
    data = {
        "subject": subject,
        "description": description,
        "dueTime": dueTime,
        "priority": priority,
        "executorIds": [union_id],  # 执行者设为自己
        "detailUrl": {
            "appUrl": "https://www.dingtalk.com",
            "pcUrl": "https://www.dingtalk.com"
        }
    }
    async with httpx2.AsyncClient() as http:
        response = await http.post(url, headers=headers, json=data)

    if response.status_code == 200:
        return "待办任务创建成功"
    else:
        return f"待办任务创建失败，错误信息：{response.json()}"


if __name__ == "__main__":
    mcp.run(transport="sse", host="127.0.0.1", port=MCP_PORT)
