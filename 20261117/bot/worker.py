import asyncio
import os

import httpx
from dotenv import load_dotenv
from redis.asyncio import Redis
from redis.exceptions import ResponseError

from use_MCP import create_agent_mcp, get_mcp_tools

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "runtime", ".env"))
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
REDIS_STREAM = os.getenv("REDIS_STREAM", "dingtalk:mcp:{inbox}")
GROUP = "bot-workers"
CONSUMER = "worker-1"


async def reply_text(http, job, text):
    # 用钉钉消息里带的 sessionWebhook 回复，并 @ 发消息的人
    data = {
        "msgtype": "text",
        "text": {"content": text},
        "at": {"atUserIds": [job["sender_staff_id"]]}
    }
    await http.post(job["session_webhook"], json=data)


async def handle_job(redis, http, tools, msg_id, job):
    print("收到任务：", msg_id, job["text"])
    try:
        agent = create_agent_mcp(tools, job["sender_staff_id"])
        result = await agent.ainvoke({"messages": [("user", job["text"])]})
        answer = result["messages"][-1].content
        print("回复：", answer)
        await reply_text(http, job, answer)
    except Exception as e:
        print("处理失败：", e)
        try:
            await reply_text(http, job, "出错了，请稍后再试")
        except Exception:
            pass
    # 处理完就确认，并从队列里删掉
    await redis.xack(REDIS_STREAM, GROUP, msg_id)
    await redis.xdel(REDIS_STREAM, msg_id)


async def main():
    redis = Redis.from_url(REDIS_URL, decode_responses=True)

    # 创建消费组，已经存在会报错，忽略就行
    try:
        await redis.xgroup_create(REDIS_STREAM, GROUP, id="0", mkstream=True)
    except ResponseError:
        pass

    tools = await get_mcp_tools()

    async with httpx.AsyncClient(timeout=30) as http:
        print("worker 已启动，等待消息...")
        while True:
            # 一次最多拿 5 条，没消息就阻塞等 5 秒
            res = await redis.xreadgroup(GROUP, CONSUMER, {REDIS_STREAM: ">"}, count=5, block=5000)
            if not res:
                continue
            for stream, messages in res:
                # 几条消息一起并发处理
                tasks = [handle_job(redis, http, tools, msg_id, job) for msg_id, job in messages]
                await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
