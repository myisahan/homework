

import time

import requests

URL = "http://127.0.0.1:8000/add_one"
DEMO_TOKEN = "demo-token"

# 最多尝试3次 = 第一次请求 + 最多2次重试。
MAX_ATTEMPTS = 3
RETRY_DELAY = 1  # 两次尝试之间等待1秒，避免立即连续请求。


def get_error_message(response):
    """从错误响应里读取说明；对方没有返回JSON时也能显示文本。"""
    try:
        body = response.json()
    except ValueError:
        return response.text
    if isinstance(body, dict):
        return str(body.get("detail", body))
    return str(body)


def send_request(data, token):
    """发送请求，成功返回结果字典，失败返回None。"""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"第{attempt}次尝试")

        try:
            response = requests.post(
                URL,
                headers={"x-acs-dingtalk-access-token": token},
                json=data,
                timeout=5,
            )
        except requests.RequestException:
            # 连不上、超时等情况，可能根本没有收到HTTP响应。
            # 不能把这些情况一律当成500。
            print("网络连接失败或超时，请检查服务是否已启动。")
            return None

        # response是requests的HTTP响应对象，所以可以读取status_code。
        status = response.status_code
        print(f"收到状态码：{status}")

        if status == 200:
            # 成功：取出返回的数据，并结束整个函数。
            result = response.json()
            print("请求成功：", result)
            return result

        elif status == 400:
            
            print("参数错误：", get_error_message(response))
            print("请检查number是否填写，以及它是不是数字。")
            return None  # return会结束函数，因此不会再重试。

        elif status == 401:
            
            print("身份验证失败：", get_error_message(response))
            print("请检查请求头中的凭证；本例正确值为demo-token。")
            return None

        elif status == 500:
            print("服务端错误：", get_error_message(response))

            if attempt < MAX_ATTEMPTS:
                print(f"等待{RETRY_DELAY}秒后重试。")
                time.sleep(RETRY_DELAY)
                continue  

            print(f"已尝试{MAX_ATTEMPTS}次仍失败，请稍后再试。")
            return None

        else:
            # 其他状态码也给出提示，避免程序无声结束。
            print(f"收到未专门处理的状态码{status}：", get_error_message(response))
            return None


if __name__ == "__main__":
    # 正常情况：预期200，结果为51。
    print("\n例1：正常请求")
    send_request({"number": 50}, DEMO_TOKEN)

    # 400：故意不传number；只尝试1次，然后提示修正参数。
    print("\n例2：缺少参数，演示400")
    send_request({}, DEMO_TOKEN)
    
    # 401：参数正确，但凭证错误；只尝试1次，然后提示检查凭证。
    print("\n例3：错误凭证，演示401")
    send_request({"number": 50}, "wrong-token")

    print("\n例4：服务端错误，演示500的限次重试")
    send_request({"number": 50, "simulate_500": True}, DEMO_TOKEN)
