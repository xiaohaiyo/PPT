from __future__ import annotations

import asyncio
import re
from pathlib import Path

from ..models import Citation, SlideSpec
from ..storage import retrieve
from .base import SkillContext


LAYOUTS_BY_TYPE = {
    "cover": ("cover-centered",),
    "agenda": ("agenda-grid",),
    "section": ("section-divider",),
    "bullets": ("title-bullets", "cards-grid"),
    "two-column": ("two-column",),
    "chart": ("chart-left-text-right", "chart-right-text-left"),
    "summary": ("summary-cards",),
}


class SlideContentSkill:
    name = "slide_content"
    label = "单页内容编辑"
    description = "逐页精炼要点并保留来源"

    async def run(self, context: SkillContext, slide: SlideSpec) -> SlideSpec:
        if not context.llm.enabled or slide.type in {"cover", "agenda", "summary"}:
            return slide
        data = await context.llm.json(
            "你是 PPT 单页编辑。只根据参考资料精炼当前页，不得增加未经支持的事实。保留原有结构和来源，只输出 title、bullets、speaker_notes。",
            f"页面：{slide.model_dump_json()}\n参考资料：{context.source_text[:6000]}",
        )
        return slide.model_copy(update={
            "title": str(data.get("title") or slide.title)[:60],
            "bullets": [str(x)[:160] for x in data.get("bullets", slide.bullets)[:5]],
            "speaker_notes": str(data.get("speaker_notes") or slide.speaker_notes)[:1500],
        })


class EvidenceSkill:
    name = "evidence"
    label = "页面来源核验"
    description = "基于最终页面文案重新检索并绑定资料引用"

    async def run(self, context: SkillContext, slide: SlideSpec) -> SlideSpec:
        if slide.type in {"cover", "agenda"}:
            return slide.model_copy(update={"citations": []})
        refs = retrieve(" ".join([slide.title, *slide.bullets]), [doc["id"] for doc in context.documents], 3, context.inline_content, context.documents)
        citations = [
            Citation(**{key: ref[key] for key in ("document_id", "document_name", "page", "quote")})
            for ref in refs if ref.get("coverage", 0) >= 0.2
        ]
        return slide.model_copy(update={"citations": citations})


class LayoutSelectorSkill:
    name = "layout_selector"
    label = "版式选择"
    description = "从受控布局集合中选择安全版式"

    async def run(self, context: SkillContext, slide: SlideSpec) -> SlideSpec:
        if slide.type == "chart" and not slide.chart:
            return slide.model_copy(update={"type": "bullets", "layout": "title-bullets"})
        compatible = LAYOUTS_BY_TYPE[slide.type]
        if slide.layout in compatible:
            selected = slide.layout
        elif slide.type == "bullets" and 3 <= len(slide.bullets) <= 4 and all(len(item) <= 70 for item in slide.bullets):
            selected = "cards-grid"
        else:
            selected = compatible[0]
        return slide.model_copy(update={"layout": selected})


class MediaSkill:
    name = "media"
    label = "配图处理"
    description = "为页面查找或生成配图；未配置图像 Provider 时安全降级"

    async def run(self, context: SkillContext, request: dict) -> dict:
        if not getattr(context.llm, "image_enabled", False):
            return {"available": False, "reason": "尚未配置图像生成 Provider", "slides": request["slides"]}
        output_dir = Path(request["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        slides = request["slides"]
        candidates = [slide for slide in slides if slide.type in {"bullets", "two-column", "section"}][:3]

        async def generate(slide: SlideSpec) -> tuple[int, str, str] | None:
            prompt = f"为中文商务演示文稿创作一张无文字、简洁专业、16:9 构图的配图。主题：{slide.title}。要点：{'；'.join(slide.bullets[:3])}"
            try:
                content = await context.llm.image(prompt)
                path = output_dir / f"slide-{slide.page}.png"
                path.write_bytes(content)
                return slide.page, str(path.resolve()), prompt
            except Exception:
                return None

        generated = [item for item in await asyncio.gather(*(generate(slide) for slide in candidates)) if item]
        assets = {page: (path, prompt) for page, path, prompt in generated}
        updated = [slide.model_copy(update={"image_path": assets[slide.page][0], "image_alt": assets[slide.page][1], "layout": "image-right-text-left"}) if slide.page in assets else slide for slide in slides]
        return {"available": bool(generated), "generated": len(generated), "requested": len(candidates), "slides": updated, "reason": "" if generated else "图片生成失败，已使用无图版式"}


class ChartSkill:
    name = "chart"
    label = "图表生成"
    description = "仅从带来源的结构化数据生成图表"

    async def run(self, context: SkillContext, slide: SlideSpec) -> SlideSpec:
        if slide.type != "chart":
            return slide
        if slide.chart is None or not slide.chart.source:
            return slide.model_copy(update={"chart": None, "type": "bullets", "layout": "title-bullets"})
        source_document = next((x for x in context.documents if x.get("name") == slide.chart.source), None)
        if source_document is None and slide.chart.source not in {"用户输入", "用户提供资料"}:
            return slide.model_copy(update={"chart": None, "type": "bullets", "layout": "title-bullets"})
        if len(slide.chart.categories) != len(slide.chart.values) or not slide.chart.values:
            return slide.model_copy(update={"chart": None, "type": "bullets", "layout": "title-bullets"})
        source_text = source_document.get("text", "") if source_document else context.inline_content
        # Bind each category/value to one explicit source statement. A number
        # occurring elsewhere in the document is not evidence for this series.
        rows = []
        for category, value in zip(slide.chart.categories, slide.chart.values):
            page = None
            matches = []
            for line in source_text.splitlines():
                marker = re.match(r"\[第\s*(\d+)\s*页\]", line)
                if marker:
                    page = int(marker.group(1))
                    continue
                if slide.chart.source_page is not None and page != slide.chart.source_page:
                    continue
                for statement in re.split(r"[，。；;\n]", line):
                    if not category or category not in statement:
                        continue
                    tail = statement.split(category, 1)[1]
                    number = re.search(r"-?\d[\d,]*(?:\.\d+)?", tail)
                    if not number or float(number.group().replace(",", "")) != float(value):
                        continue
                    if slide.chart.series_name != "数值" and slide.chart.series_name not in statement:
                        continue
                    if slide.chart.unit and not tail[number.end():].lstrip().startswith(slide.chart.unit):
                        continue
                    matches.append({"category": category, "value": value, "source": slide.chart.source, "page": page, "quote": statement.strip()})
            if len(matches) != 1:
                return slide.model_copy(update={"chart": None, "type": "bullets", "layout": "title-bullets"})
            rows.append(matches[0])
        return slide.model_copy(update={"chart": slide.chart.model_copy(update={"evidence_rows": rows})})


async def process_slides(context: SkillContext, slides: list[SlideSpec], registry) -> list[SlideSpec]:
    async def process(slide: SlideSpec) -> SlideSpec:
        edited = await registry.get("slide_content").run(context, slide)
        charted = await registry.get("chart").run(context, edited)
        evidenced = await registry.get("evidence").run(context, charted)
        return await registry.get("layout_selector").run(context, evidenced)
    processed = await asyncio.gather(*(process(slide) for slide in slides))
    return synchronize_agenda(processed)


def synchronize_agenda(slides: list[SlideSpec]) -> list[SlideSpec]:
    """Rebuild agenda entries from final edited slide titles."""
    content = [slide for slide in slides if slide.type not in {"cover", "agenda", "summary"}]
    entries = [f"{slide.page:02d}  {slide.title}" for slide in content[:8]]
    if len(content) > 8:
        entries[-1] = f"{content[7].page:02d}–{content[-1].page:02d}  其余 {len(content) - 7} 页内容"
    return [
        slide.model_copy(update={"bullets": entries, "citations": []}) if slide.type == "agenda" else slide
        for slide in slides
    ]
