import json

import uvicorn
from fastapi import FastAPI, HTTPException, Request

app = FastAPI()
DEMO_TOKEN = "demo-token"


@app.post("/add_one")
async def add_one(request: Request):
    # 第一步：读取客户端通过 json=... 发送的请求体。
    # 如果发来的内容不是合法JSON，返回400，请客户端修正后再发。
    try:
        data = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="请求体必须是合法JSON")

    # 本接口约定请求体是字典，例如 {"number": 50}。
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="请求体必须是JSON对象")

    # 第二步：检查参数，对应400。
    # 不能写 if not number，因为合法数字0也会被误判为缺少参数。
    if "number" not in data:
        raise HTTPException(status_code=400, detail="缺少number参数")

    number = data["number"]
    # number必须是数字；Python把bool也视为int的一种，所以单独排除。
    if isinstance(number, bool) or not isinstance(number, (int, float)):
        raise HTTPException(status_code=400, detail="number必须是整数或小数")

    # 第三步：检查请求头里的身份凭证，对应401。
    # 请求头的名称沿用老师的例子；这里只验证课堂演示凭证。
    token = request.headers.get("x-acs-dingtalk-access-token")
    if token != DEMO_TOKEN:
        raise HTTPException(status_code=401, detail="身份凭证缺失或不正确")

    # 第四步：模拟服务端内部错误，对应500。
    # 客户端传 {"number": 50, "simulate_500": True} 就会走这里。
    # 这个开关属于补充教学内容，目的是稳定复现错误。
    if data.get("simulate_500") is True:
        raise HTTPException(status_code=500, detail="课堂模拟：服务端暂时出错")

    # 第五步：所有检查通过，正常计算并返回，HTTP状态码默认是200。
    return {"result": number + 1}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
