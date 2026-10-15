from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ..llm import LLMProvider


@dataclass
class SkillContext:
    llm: LLMProvider
    source_text: str
    documents: list[dict[str, Any]]
    inline_content: str = ""


class Skill(Protocol):
    name: str
    label: str
    description: str

    async def run(self, context: SkillContext, payload: Any) -> Any: ...
