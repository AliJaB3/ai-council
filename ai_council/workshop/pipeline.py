"""Orchestrate candidate generation and rapid falsification."""
from .combinator import MorphologicalCombinator
from .falsifier import FalsificationInquisitor
from .models import Anomaly, IdeaCard, IdeaStatus
from ..skills.models import Domain
from ..skills.registry import SkillRegistry


class IdeationWorkshop:
    def __init__(self, count: int = 3):
        self.count = count
        self.combinator = MorphologicalCombinator()
        self.falsifier = FalsificationInquisitor()
        self.candidates: list[IdeaCard] = []

    def run_cycle(self, topic: str, domain: Domain | None = None, seed_anomalies: list[Anomaly] | None = None) -> list[IdeaCard]:
        domain = domain if domain is not None else SkillRegistry.detect_domain(topic)
        self.candidates = []
        for idea in self.combinator.combine(domain, self.count):
            idea.problem_statement += f' Workshop topic: {topic}.'
            if seed_anomalies:
                idea.problem_statement += ' Observed anomalies: ' + '; '.join(f'{a.source}: {a.metric} (z={a.z_score:g})' for a in seed_anomalies) + '.'
                idea.metrics['seed_anomaly_ids'] = [a.id for a in seed_anomalies]
            self.candidates.append(self.falsifier.audit(idea))
        return [idea for idea in self.candidates if idea.status == IdeaStatus.VALIDATED]
