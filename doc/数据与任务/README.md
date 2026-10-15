# 数据与任务

## 本地数据

- `data/documents.json`：资料元数据和解析内容。
- `data/knowledge-bases.json`：知识库及成员关系。
- `data/tasks.json`：任务、状态和请求快照。
- `data/artifacts.json`：产物元数据。
- `data/uploads/`：上传原文件。
- `data/artifacts/`：生成文件。
- `data/source-snapshots/`：提交任务时冻结的资料内容。

这些运行数据已通过 `.gitignore` 排除，不应作为源码提交。

## 任务生命周期

```text
pending → running → completed
                  ↘ failed
```

任务创建时保存不可变请求快照和来源快照，避免用户改变选择或删除资料导致结果漂移。服务重启时未完成任务会标记为失败，已完成产物保持不变。

修改产物会创建带父任务关系的新任务，不覆盖原文件。PPT 保存结构化 `artifact_ir`，明确指定页面的修改可以复用未变页面。
