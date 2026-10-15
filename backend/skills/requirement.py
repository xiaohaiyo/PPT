from __future__ import annotations

from ..models import GenerationRequest, RequirementSpec
from .base import SkillContext
from .helpers import keywords


class RequirementSkill:
    name = "requirement"
    label = "需求理解"
    description = "识别主题、受众、页数、风格和模板要求"

    async def run(self, context: SkillContext, payload: GenerationRequest) -> RequirementSpec:
        fallback = RequirementSpec(
            topic=payload.topic or payload.instruction or (keywords(context.source_text, 1) or ["演示文稿"])[0],
            purpose=payload.purpose or "清晰呈现核心内容",
            audience=payload.audience,
            page_count=payload.page_count,
            style=payload.style,
            template_id=payload.template_id,
            need_images=payload.need_images,
            need_charts=payload.need_charts,
            constraints=list(dict.fromkeys([*payload.constraints, *([payload.instruction] if payload.instruction else [])])),
            key_messages=payload.key_messages,
        )
        if not context.llm.enabled:
            return fallback
        try:
            data = await context.llm.json(
                "你是演示文稿需求分析师。根据输入补全需求，字段必须与给定 JSON 一致。",
                f"用户请求：{payload.model_dump_json()}\n资料摘要：{context.source_text[:6000]}\n默认值：{fallback.model_dump_json()}",
            )
            return RequirementSpec.model_validate({**fallback.model_dump(), **data})
        except ValueError:
            return fallback
