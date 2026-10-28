# FastAPI 聊天接口：状态码容错与日志

FastAPI 接收 `POST /users`，读取 `messages`，调用聊天模型，成功返回 `ai_content`。调用失败时，从 `APIStatusError` 异常读取状态码。

## 状态码与处理

| 情况 | 处理方式 |
| --- | --- |
| 请求体不是有效 JSON、messages 不是非空列表，或模型服务返回 400 | 记录 WARNING，返回 400，提示检查参数，不原样重试 |
| 模型服务返回 401 | 记录 ERROR，返回 401，提示检查服务端模型凭证，不原样重试。此处的 401 指**上游模型服务**认证失败。 |
| 模型服务返回 500 | 记录 WARNING，主模型最多尝试 3 次；仍失败时尝试已配置的备用模型一次。没有备用模型或备用模型失败时返回受控错误。 |
| 网络连接失败或超时 | 没有收到 HTTP 状态码，记录 ERROR，接口返回 503。 |
| 成功 | 记录 INFO，接口返回 200 和 `ai_content`。 |

日志打印在终端，也保存在启动目录的 `homework.log`。密钥通过环境变量读取。

## 配置和运行

需要 Python 环境和可访问的 OpenAI 兼容模型服务，以及模型名称、接口地址和密钥。以下为 Windows PowerShell 命令。

在本目录创建独立环境并安装依赖（不会修改你原有环境中的包）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

在启动服务端的同一个终端中配置主模型（把尖括号内容替换成自己的实际配置）：

```powershell
$env:MAIN_MODEL_NAME = "<模型名称>"
$env:MAIN_BASE_URL = "<OpenAI兼容接口地址>"
$env:MAIN_API_KEY = "<自己的密钥>"
.\.venv\Scripts\python.exe server.py
```

启动前必须设置三项主模型配置，缺少时程序会提示对应环境变量名称并停止启动。要启用备用模型，还需设置 `BACKUP_MODEL_NAME`、`BACKUP_BASE_URL` 和 `BACKUP_API_KEY`；不设置 `BACKUP_BASE_URL` 就不启用备用模型。

保持服务端终端运行，在另一个终端进入本目录后执行：

```powershell
.\.venv\Scripts\python.exe client.py
```

输入问题开始聊天，输入 `quit` 结束。服务地址是 `http://127.0.0.1:8002/users`。
