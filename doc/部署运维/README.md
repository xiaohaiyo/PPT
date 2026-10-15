# 部署运维

## 安装

要求 Python 3.11+。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

在 `.env` 中填写 `AI_API_KEY`、`AI_BASE_URL` 和 `AI_MODEL`。可通过 `APP_HOST`、`APP_PORT` 调整监听地址和端口。不要提交真实 `.env`。

## 启动与停止

```bash
.venv/bin/python run.py
```

访问 <http://127.0.0.1:4098>。前台启动时按 `Ctrl+C` 停止；后台部署应交给 systemd、Supervisor 或容器平台管理。

## 健康检查

```bash
curl http://127.0.0.1:4098/api/health
```

`ok: true` 表示应用可用，`llmConfigured` 表示模型配置是否完整。

## 常见问题

- 模型失败：检查密钥、Base URL、模型名称和网络。
- PDF 无答案：确认资料已勾选，并检查 PDF 是否有文本层。
- 页面加载旧样式：强制刷新或清除站点缓存。
