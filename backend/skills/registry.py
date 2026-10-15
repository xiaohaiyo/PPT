from .planner import PlannerSkill
from .requirement import RequirementSkill
from .writing import ArticleSkill, MindmapSkill
from .slides import ChartSkill, EvidenceSkill, LayoutSelectorSkill, MediaSkill, SlideContentSkill


class SkillRegistry:
    def __init__(self):
        self._skills = {}

    def register(self, skill):
        self._skills[skill.name] = skill

    def get(self, name):
        return self._skills[name]

    def public(self):
        return [{"id": x.name, "label": x.label, "description": x.description} for x in self._skills.values() if x.name in {"article", "mindmap"}]


registry = SkillRegistry()
for item in (RequirementSkill(), PlannerSkill(), SlideContentSkill(), EvidenceSkill(), LayoutSelectorSkill(), ChartSkill(), MediaSkill(), ArticleSkill(), MindmapSkill()):
    registry.register(item)
