import os

import httpx2
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "runtime", ".env"))
DINGDING_ID = os.getenv("DINGDING_ID")
DINGDING_SECRET = os.getenv("DINGDING_SECRET")


#异步请求
async def get_acctoken_id(client_id, client_secret):
    url = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "appKey": client_id,
        "appSecret": client_secret
    }
    async with httpx2.AsyncClient() as http:
        response = await http.post(url, headers=headers, json=data)
    return response.json()["accessToken"]


async def get_union_id(access_token, user_id):
    url = "https://oapi.dingtalk.com/topapi/v2/user/get"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "charset": "utf-8"
    }
    data = {
        "access_token": access_token,
        "userid": user_id
    }
    async with httpx2.AsyncClient() as http:
        response = await http.post(url, headers=headers, data=data)
    return response.json()["result"]["unionid"]


if __name__ == "__main__":
    import asyncio
    print(asyncio.run(get_acctoken_id(DINGDING_ID, DINGDING_SECRET)))
