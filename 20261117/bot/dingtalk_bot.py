import argparse
import logging
import os

from dingtalk_stream import AckMessage
import dingtalk_stream
from dotenv import load_dotenv
from redis.asyncio import Redis


load_dotenv(os.path.join(os.path.dirname(__file__), "..", "runtime", ".env"))
DINGDING_ID = os.getenv("DINGDING_ID")
DINGDING_SECRET = os.getenv("DINGDING_SECRET")
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
# worker.py 从同一个 stream 里取消息
REDIS_STREAM = os.getenv("REDIS_STREAM", "dingtalk:mcp:{inbox}")


def setup_logger():
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter('%(asctime)s %(name)-8s %(levelname)-8s %(message)s [%(filename)s:%(lineno)d]'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def define_options():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--client_id', default=DINGDING_ID, dest='client_id',
        help='app_key or suite_key from https://open-dev.digntalk.com'
    )
    parser.add_argument(
        '--client_secret', default=DINGDING_SECRET, dest='client_secret',
        help='app_secret or suite_secret from https://open-dev.digntalk.com'
    )
    options = parser.parse_args()
    return options


class EchoTextHandler(dingtalk_stream.ChatbotHandler):
    def __init__(self, logger: logging.Logger = None):
        super(dingtalk_stream.ChatbotHandler, self).__init__()
        if logger:
            self.logger = logger
        # 异步的 redis 客户端，
        self.redis = Redis.from_url(REDIS_URL, decode_responses=True)

    async def process(self, callback: dingtalk_stream.CallbackMessage):
        incoming_message = dingtalk_stream.ChatbotMessage.from_dict(callback.data)
        text = incoming_message.text.content.strip()
        print(text)

        # 获取用户的 staffId (这是钉钉的 userId)，创建待办要用
        userid = callback.data.get('senderStaffId')
        print(userid)

        # 这里不直接调 agent，把消息放进 redis 队列，交给 worker.py 去处理和回复
        job = {
            "text": text,
            "session_webhook": incoming_message.session_webhook,
            "sender_staff_id": userid or "",
        }
        try:
            job_id = await self.redis.xadd(REDIS_STREAM, job)
            print("消息已入队：", job_id)
        except Exception as e:
            print("redis 入队失败：", e)
            return AckMessage.STATUS_SYSTEM_EXCEPTION, 'redis error'

        return AckMessage.STATUS_OK, 'OK'


def main():
    logger = setup_logger()
    options = define_options()

    credential = dingtalk_stream.Credential(options.client_id, options.client_secret)
    client = dingtalk_stream.DingTalkStreamClient(credential)
    client.register_callback_handler(dingtalk_stream.chatbot.ChatbotMessage.TOPIC, EchoTextHandler(logger))
    client.start_forever()


if __name__ == '__main__':
    main()
