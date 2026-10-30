"""Registration and just-in-time selection of domain skills."""
import re
from .models import Domain, SkillDefinition


class SkillRegistry:
    def __init__(self, skills=()):
        self._skills = {}
        for skill in skills:
            self.register(skill)

    def register(self, skill: SkillDefinition):
        self._skills[skill.name] = skill

    def get(self, name: str) -> SkillDefinition | None:
        return self._skills.get(name)

    def list_skills(self, domain: Domain | None = None) -> list[SkillDefinition]:
        return [skill for skill in self._skills.values() if domain is None or skill.domain == domain]

    @staticmethod
    def detect_domain(text: str) -> Domain:
        keywords = {
            Domain.SECURITY: ('injection', 'vuln', 'vulnerability', 'secret', 'sandbox', 'exploit', 'security'),
            Domain.FINANCE: ('trading', 'trade', 'orderbook', 'funding', 'finance', 'financial', 'portfolio', 'slippage', 'leverage'),
            Domain.ENGINEERING: ('code', 'ast', 'refactor', 'deadlock', 'software', 'debug', 'engineering', 'bug'),
            Domain.ARCHITECTURE: ('architecture', 'architectural', 'design', 'scalability', 'distributed'),
            Domain.RESEARCH: ('research', 'hypothesis', 'literature', 'study', 'experiment', 'paper'),
        }
        words = set(re.findall(r'[a-z0-9_]+', text.lower()))
        scores = {domain: sum(any(word.startswith(term) for word in words) for term in terms) for domain, terms in keywords.items()}
        winner = max(scores, key=scores.get)
        return winner if scores[winner] else Domain.GENERAL

    def resolve_jit(self, domain: Domain) -> list[SkillDefinition]:
        return self.list_skills(domain)
