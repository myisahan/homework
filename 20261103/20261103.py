from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver

import requests

model = ChatOpenAI(model="qwen3.8-flash", api_key="eeeeeeeeeee",
base_url="https://ws-3mp3xmkmhy7akv9p.cn-beijing.maas.aliyuncs.com/compatible-mode/v1")
class Weather(BaseModel):
    city: str = Field(description="城市名")
@tool(args_schema=Weather)
def get_weather(city: str)-> str:
    """查询指定城市的当前天气。"""
    api_host = "mn44ucunh2.re.qweatherapi.com"
    api_key = "1111111111111111111111111111111111"
    headers = {"X-QW-Api-Key": api_key}
        # 根据城市名查询位置信息
    response = requests.get(
        url=f"https://{api_host}/geo/v2/city/lookup",
        headers=headers,
        params={"location": city, "lang": "zh"},
        timeout=10,
    )

    response.raise_for_status()
    data = response.json()
    if data["code"] != "200" or not data["location"]:
        return f"未找到城市 {city} 的位置信息。"
    location = data["location"][0]
    latitude = f"{float(location['lat']):.2f}"
    longitude = f"{float(location['lon']):.2f}"

    weather_response = requests.get(
        url=f"https://{api_host}/weather/v1/current/{latitude}/{longitude}",
        headers=headers,
        params={"lang": "zh"},
        timeout=10,
    )
    weather_response.raise_for_status()
    weather_data = weather_response.json()
    
    weather = weather_data["condition"]["text"]
    temperature = weather_data["temperature"]["value"] 
    unit = weather_data["temperature"]["unit"]

    attributions =", ".join(weather_data["metadata"]["attributions"])
    return(
        f"{location['adm1']}{location['name']}当前天气："
        f"{weather}，温度为{temperature}{unit}。"
        f"数据来源：和风天气；归因信息：{attributions}"
    )

graph = create_agent(
    model=model,
    tools=[get_weather],
    system_prompt=("你是一个有用的助手。查询天气时调用get_weather工具,"
    "根据工具结果来回答用户问题。"
    ),
    checkpointer=MemorySaver(),
)

def chat():
    while True:
        user_input = input("请输入: ")
        if user_input == "exit":
            break
        response = graph.invoke({"messages": [{"role": "user", "content": user_input}]},config={"configurable": {"thread_id": "user_001"}})
        print(response["messages"][-1].content)

if __name__ == "__main__":
    chat()
