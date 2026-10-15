# 内容生成技能

生成能力位于 `backend/skills/`。模型负责理解、规划和内容生成，程序负责校验、版式及文件输出，不让模型直接编写操作 PPT 的代码。

## 公共流程

1. 结合上下文识别问答、分析、新建、修改或确认意图。
2. Brief Builder 整理主题、用途、受众、观点和限制。
3. 创建任务并冻结需求与来源快照。
4. 根据 `presentation`、`article`、`mindmap` 选择 Skill。
5. 校验结构化内容，由 Renderer 输出文件。

## PPT Skill

- `requirement.py`：规范化页数、风格和生成要求。
- `planner.py`：规划封面、目录、内容页和总结页。
- `slides.py`：生成单页内容、选择版式、绑定证据并处理图表/图片。
- `renderer.py`：使用 `python-pptx` 输出可编辑 PPTX。

`writing.py` 负责 Markdown 文章和层级思维导图。文章可导出 DOCX，导图可导出 SVG 和 PNG。图片模型未配置时，PPT 会安全降级为无生成图片的版式。
