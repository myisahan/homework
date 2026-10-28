import asyncio
import logging
import os

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from langchain.chat_models import init_chat_model
from openai import APIConnectionError, APIStatusError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("homework.log", encoding="utf-8")],
)
logger = logging.getLogger(__name__)

# 密钥从环境变量读取，不写进代码。
model = init_chat_model(
    model=os.environ["MAIN_MODEL_NAME"],
    base_url=os.environ["MAIN_BASE_URL"],
    api_key=os.environ["MAIN_API_KEY"],
    model_provider="openai",
    max_retries=0,  # 由下面的循环控制重试次数
    timeout=30,
)

model2 = None
if os.getenv("BACKUP_BASE_URL"):
    model2 = init_chat_model(
        model=os.environ["BACKUP_MODEL_NAME"],
        base_url=os.environ["BACKUP_BASE_URL"],
        api_key=os.environ["BACKUP_API_KEY"],
        model_provider="openai",
        max_retries=0,
        timeout=30,
    )

app = FastAPI()


@app.post("/users")
async def user_chat(request: Request):
    logger.info("收到请求")
    try:
        data = await request.json()
    except ValueError:
        logger.warning("400：请求体不是有效的 JSON")
        raise HTTPException(400, "请求体必须是有效的 JSON")

    messages = data.get("messages") if isinstance(data, dict) else None
    if not isinstance(messages, list) or not messages:
        logger.warning("400：messages 缺失或格式错误")
        raise HTTPException(400, "messages 必须是非空列表")

    # 最多尝试3次：第一次调用 + 两次重试。
    for i in range(3):
        try:
            response = await model.ainvoke(messages)
            if not response.content:
                logger.warning("主模型返回空内容")
                raise HTTPException(502, "模型返回空内容")
            logger.info("主模型调用成功，第 %d 次", i + 1)
            return {"ai_content": response.content}

        except APIStatusError as e:
            # 模型服务报错时，从异常中读取状态码。
            if e.status_code == 400:
                logger.warning("400：模型请求参数错误，不重试")
                raise HTTPException(400, "请检查模型请求参数")
            elif e.status_code == 401:
                logger.error("401：模型密钥无效，不重试")
                raise HTTPException(401, "请检查服务端模型密钥")
            elif e.status_code == 500:
                logger.warning("500：主模型调用失败，第 %d 次", i + 1)
                if i < 2:
                    await asyncio.sleep(1)
            else:
                logger.error("模型服务返回状态码：%d", e.status_code)
                raise HTTPException(502, "模型服务调用失败")
        except APIConnectionError:
            logger.error("模型连接失败或超时")
            raise HTTPException(503, "无法连接模型服务")

    # 连续3次500后，调用一次备用模型。
    if model2 is None:
        logger.error("主模型重试失败，未配置备用模型")
        raise HTTPException(500, "重试失败，未配置备用模型")

    logger.warning("切换备用模型")
    try:
        response = await model2.ainvoke(messages)
        if not response.content:
            logger.error("备用模型返回空内容")
            raise HTTPException(500, "备用模型返回空内容")
        logger.info("备用模型调用成功")
        return {"ai_content": response.content}
    except APIStatusError as e:
        logger.error("备用模型失败，状态码：%d", e.status_code)
        raise HTTPException(500, "主模型和备用模型均调用失败")
    except APIConnectionError:
        logger.error("备用模型连接失败或超时")
        raise HTTPException(500, "备用模型连接失败")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)
