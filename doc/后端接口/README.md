# 后端接口

后端基于 FastAPI，入口为 `run.py`，主要路由和任务编排位于 `backend/main.py`。

## 主要模块

- `config.py`：环境变量和运行配置。
- `llm.py`：OpenAI-compatible 文本、JSON 和图片模型客户端。
- `models.py`：Pydantic 请求、Brief、页面和任务契约。
- `main.py`：HTTP 接口、任务调度和导出。
- `renderer.py`：PPTX 及预览渲染。

## 关键接口

| 接口 | 作用 |
|---|---|
| `GET /api/health` | 健康状态与能力探测 |
| `POST /api/documents` | 上传并解析资料 |
| `POST /api/intent` | 结合对话识别用户意图 |
| `POST /api/chat` | 基于检索证据进行多轮问答 |
| `POST /api/summarize` | 总结所选资料 |
| `POST /api/brief` | 增量构建创作需求草案 |
| `POST /api/generations` | 创建生成任务 |
| `POST /api/generations/{id}/revise` | 创建产物修改版 |
| `GET /api/generations` | 查询任务与产物记录 |

模型服务异常、校验错误和生成错误会返回明确状态。API Key 只从服务端环境变量读取，不下发前端。
