# 钉钉 MCP 机器人作业

钉钉消息 → `dingtalk_bot.py` 放进 Redis 队列 → `worker.py` 从队列取出来，交给 Agent 调用 MCP 工具 → 回复到钉钉。

| 文件 | 作用 |
| --- | --- |
| `mcp_server.py` | MCP 服务端，用 `@mcp.tool()` 写了 6 个工具，SSE 方式启动 |
| `get_acctoken_id.py` | 获取钉钉 accessToken 和 unionid（异步） |
| `use_MCP.py` | 连接 MCP 拿工具，创建 Agent |
| `dingtalk_bot.py` | 钉钉 Stream 机器人，收到消息后 `xadd` 到 Redis |
| `worker.py` | 用 `xreadgroup` 读队列，调用 Agent，回复钉钉后 `xack` |

## 运行

先启动 Redis：

```bash
docker compose -f runtime/compose.redis.yml up -d
```

再开三个终端：

```bash
# 终端 1：MCP 服务
runtime/.venv-server/bin/python bot/mcp_server.py

# 终端 2：worker
runtime/.venv/bin/python bot/worker.py

# 终端 3：钉钉机器人
runtime/.venv/bin/python bot/dingtalk_bot.py
```

## 测试

| 工具 | 钉钉里发 |
| --- | --- |
| add | 3 加 5 等于几？ |
| get_current_beijing_time | 现在几点？ |
| datetime_to_timestamp_ms | 把 2026-11-20 18:00:00 转成毫秒时间戳 |
| date_difference_days | 11 月 17 日到 11 月 30 日差几天？ |
| count_text | 统计「MCP 作业」有多少字 |
| create_todo_task | 帮我创建一个「提交 MCP 作业」的待办，截止 11 月 20 日 18 点 |
