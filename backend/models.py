from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field


class Citation(BaseModel):
    document_id: str
    document_name: str
    page: int | None = None
    quote: str = ""


class RequirementSpec(BaseModel):
    topic: str = "演示文稿"
    purpose: str = "清晰呈现核心内容"
    audience: str = "通用受众"
    language: str = "zh-CN"
    page_count: int = Field(default=8, ge=3, le=30)
    style: str = "professional"
    tone: str = "简洁、专业"
    template_id: str = "corporate-blue"
    need_images: bool = False
    need_charts: bool = True
    constraints: list[str] = Field(default_factory=list)
    key_messages: list[str] = Field(default_factory=list)


class ChartSpec(BaseModel):
    type: Literal["column", "line", "pie"] = "column"
    categories: list[str] = Field(default_factory=list)
    values: list[float] = Field(default_factory=list)
    series_name: str = "数值"
    unit: str = ""
    source: str = ""
    source_page: int | None = None
    evidence_rows: list[dict] = Field(default_factory=list)


class SlideSpec(BaseModel):
    page: int
    type: Literal["cover", "agenda", "section", "bullets", "two-column", "chart", "summary"]
    layout: str
    title: str
    subtitle: str = ""
    bullets: list[str] = Field(default_factory=list)
    speaker_notes: str = ""
    chart: ChartSpec | None = None
    citations: list[Citation] = Field(default_factory=list)
    image_path: str = ""
    image_alt: str = ""


class PresentationSpec(BaseModel):
    title: str
    requirement: RequirementSpec
    slides: list[SlideSpec]


class GenerationRequest(BaseModel):
    skill: Literal["presentation", "article", "mindmap"]
    document_ids: list[str] = Field(default_factory=list)
    inline_content: str = ""
    topic: str = ""
    audience: str = "通用受众"
    page_count: int = Field(default=8, ge=3, le=30)
    style: str = "professional"
    template_id: str = "corporate-blue"
    need_images: bool = False
    need_charts: bool = True
    instruction: str = ""
    purpose: str = ""
    key_messages: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class CreativeBrief(BaseModel):
    clarification_question: str = ""
    output_type: Literal["presentation", "article", "mindmap"] = "presentation"
    topic: str = ""
    purpose: str = "清晰呈现资料中的核心内容"
    audience: str = "通用受众"
    key_messages: list[str] = Field(default_factory=list, max_length=6)
    constraints: list[str] = Field(default_factory=list, max_length=6)
    page_count: int = Field(default=8, ge=3, le=30)
    style: str = "professional"
    template_id: str = "corporate-blue"
    need_charts: bool = True
    need_images: bool = False


class BriefRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    document_ids: list[str] = Field(default_factory=list)
    inline_content: str = ""
    current: CreativeBrief | None = None
    history: list["ChatMessage"] = Field(default_factory=list, max_length=12)


class TaskRecord(BaseModel):
    id: str
    skill: str
    title: str
    status: str = "pending"
    stage: str = "等待处理"
    progress: int = 0
    error: str = ""
    artifact_id: str | None = None
    preview_text: str = ""
    preview_html: str = ""
    citations: list[Citation] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=16000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    document_ids: list[str] = Field(default_factory=list)
    inline_content: str = ""
    history: list[ChatMessage] = Field(default_factory=list, max_length=12)


class SummaryRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list)
    inline_content: str = ""


class SaveSummaryRequest(BaseModel):
    title: str = "文档摘要"
    summary: str
    citations: list[Citation] = Field(default_factory=list)


class GenerationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    content: str | None = Field(default=None, max_length=200_000)


class RevisionRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class KnowledgeBaseUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    document_ids: list[str]
