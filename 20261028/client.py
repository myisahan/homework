import requests

URL = "http://127.0.0.1:8002/users"
messages = [{"role": "system", "content": "你是一位耐心的学习助手。"}]


def user_chat():
    print("输入问题开始对话；输入 quit 结束。")
    while True:
        question = input("请输入你的问题：").strip()
        if question.lower() == "quit":
            break
        if not question:
            print("问题不能为空。")
            continue

        # 请求成功后再保存对话历史。
        pending = messages + [{"role": "user", "content": question}]
        try:
            response = requests.post(URL, json={"messages": pending}, timeout=180)
        except requests.RequestException:
            print("连接接口失败，请检查 FastAPI 服务是否已启动。")
            continue

        if response.status_code != 200:
            try:
                detail = response.json().get("detail", "请查看服务端日志")
            except ValueError:
                detail = "请查看服务端日志"
            print(f"请求失败，状态码 {response.status_code}：{detail}")
            continue

        answer = response.json()["ai_content"]
        print("AI：", answer)
        messages.extend([{"role": "user", "content": question},
                         {"role": "assistant", "content": answer}])


if __name__ == "__main__":
    user_chat()
