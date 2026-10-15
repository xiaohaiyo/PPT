# AI 写作助手

一个以用户资料为事实边界、以对话为业务入口的 AI 内容工作台。支持基于资料的问答、摘要，并生成 PPTX 演示文稿、DOCX 通用文稿和 SVG/PNG 思维导图。

## 核心能力

- PDF、DOCX、TXT、Markdown 解析及知识库管理
- 基于所选资料的多轮问答、摘要和来源引用
- 结合对话语义识别问答、分析、生成、确认和修改意图
- Creative Brief 需求确认与异步生成任务
- 基于 Skill 的 PPT、文章和思维导图生成管线
- 产物预览、下载、来源快照和版本修改

## 项目结构

```text
app.html / app.js / app*.css   Web 前端
backend/                       FastAPI 后端及内容生成 Skill
data/                          本地运行数据（自动创建）
doc/                           中文模块文档
run.py                         服务入口
```

模块设计见 [doc/README.md](doc/README.md)。

## 快速部署

要求 Python 3.11 及以上版本。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env`：

```env
AI_API_KEY=你的密钥
AI_BASE_URL=https://aiapi.market/v1
AI_MODEL=模型名称
```

启动服务：

```bash
.venv/bin/python run.py
```

访问 <http://127.0.0.1:4098>。停止服务时在启动终端按 `Ctrl+C`。详细配置见 [部署运维](doc/部署运维/README.md)。

## 使用流程

1. 在左侧上传资料并勾选本轮引用范围。
2. 在中间对话区提问、要求分析或描述目标产物。
3. 确认系统整理的需求草案并创建生成任务。
4. 在右侧查看进度、预览和下载产物。
5. 从产物预览中选择“基于此修改”生成新版本。

## 数据与安全

- `.env` 包含密钥，不应提交到代码仓库。
- 上传文件、任务、产物和来源快照保存在 `data/`。
- 当前 RAG 使用本地稀疏检索，不依赖外部向量数据库。
- 扫描型 PDF 需要预先 OCR。
- 生产环境建议使用数据库、对象存储、鉴权和反向代理。
