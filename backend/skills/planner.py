from __future__ import annotations

from ..models import Citation, PresentationSpec, RequirementSpec, SlideSpec
from ..storage import retrieve
from .base import SkillContext
from .helpers import sentences


class PlannerSkill:
    name = "planner"
    label = "PPT 规划"
    description = "生成完整、可校验的页面清单"

    async def run(self, context: SkillContext, requirement: RequirementSpec) -> PresentationSpec:
        if context.llm.enabled:
            data = await context.llm.json(
                "你是 PPT Planner。生成完整页面清单。必须有封面、目录、内容页、总结页；页面数严格一致，且按封面、目录、内容、总结顺序。type 只能是 cover, agenda, section, bullets, two-column, chart, summary；chart 页面必须输出 chart 对象，包含 type、categories、values、series_name、unit、source、source_page。只有资料明确出现的数据才可进入图表，source 必须是资料文件名；直接输入的资料请填写 source='用户输入'。source_page 只能填整数页码或 null，不要写文件名或说明文字。layout 按类型选择：cover-centered、agenda-grid、section-divider、title-bullets/cards-grid、two-column、chart-left-text-right/chart-right-text-left、summary-cards。不要编造输入资料中不存在的数据。",
                f"需求：{requirement.model_dump_json()}\n参考资料：{context.source_text[:12000]}\n输出格式：{{\"title\":\"...\",\"slides\":[{{\"page\":1,\"type\":\"cover\",\"layout\":\"cover-centered\",\"title\":\"...\",\"subtitle\":\"...\",\"bullets\":[],\"chart\":null}}]}}",
            )
            normalized_slides = []
            for raw_slide in data.get("slides", []):
                item = dict(raw_slide)
                if isinstance(item.get("chart"), dict):
                    chart = dict(item["chart"])
                    chart_type = str(chart.get("type", "column")).lower()
                    chart["type"] = {"bar": "column", "column_chart": "column", "line_chart": "line", "pie_chart": "pie"}.get(chart_type, chart_type)
                    source_page = chart.get("source_page")
                    chart["source_page"] = source_page if isinstance(source_page, int) else None
                    item["chart"] = chart
                normalized_slides.append(SlideSpec.model_validate(item))
            slides = normalized_slides
            if len(slides) != requirement.page_count:
                raise ValueError(f"Planner 应输出 {requirement.page_count} 页，实际得到 {len(slides)} 页")
            if slides[0].type != "cover" or slides[1].type != "agenda" or slides[-1].type != "summary":
                raise ValueError("Planner 必须按顺序生成封面、目录和总结页")
            slides = [slide.model_copy(update={"page": index + 1}) for index, slide in enumerate(slides)]
            doc_ids = [x["id"] for x in context.documents]
            validated = []
            for slide in slides:
                refs = retrieve(" ".join([slide.title, *slide.bullets]), doc_ids, 3, context.inline_content, context.documents)
                citations = [Citation(**{k: item[k] for k in ("document_id", "document_name", "page", "quote")}) for item in refs if item.get("score", 0) > 0]
                validated.append(slide.model_copy(update={"citations": citations}))
            return PresentationSpec(title=data.get("title", requirement.topic), requirement=requirement, slides=validated)
        return self._fallback(context, requirement)

    def _fallback(self, context: SkillContext, req: RequirementSpec) -> PresentationSpec:
        facts = sentences(context.source_text, max(4, req.page_count * 2)) or ["请在此补充核心资料和业务结论。"]
        content_count = req.page_count - 3
        buckets = [[] for _ in range(content_count)]
        for index, fact in enumerate(facts):
            buckets[index % content_count].append(fact)
        slides = [
            SlideSpec(page=1, type="cover", layout="cover-centered", title=req.topic, subtitle=f"面向{req.audience} · {req.tone}"),
            SlideSpec(page=2, type="agenda", layout="agenda-grid", title="目录", bullets=["背景与目标", "核心内容", "重点洞察", "总结与行动"]),
        ]
        for index, page_facts in enumerate(buckets):
            if not page_facts:
                page_facts = ["本页待补充资料中的相关内容。"]
            title = page_facts[0][:22].rstrip("。；，")
            refs = retrieve(" ".join(page_facts), [x["id"] for x in context.documents], 2, context.inline_content, context.documents)
            citations = [Citation(**{k: r[k] for k in ("document_id", "document_name", "page", "quote")}) for r in refs]
            slides.append(SlideSpec(page=index + 3, type="bullets", layout="title-bullets", title=title, bullets=[x[:80] for x in page_facts[:4]], citations=citations))
        slides.append(SlideSpec(page=req.page_count, type="summary", layout="summary-cards", title="总结与下一步", bullets=["统一核心共识", "明确行动责任", "持续跟踪与复盘"]))
        return PresentationSpec(title=req.topic, requirement=req, slides=slides)
