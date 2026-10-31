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


class AutonomousCrucibleWorkshop:
    def __init__(self, count=3, max_generations=2, registry=None, strict=False):
        from .combinator import HyperPrecisionCombinator
        from .crucible import MultiDomainCrucible
        from .mutator import EvolutionaryMutator
        if max_generations < 0:
            raise ValueError('max_generations must be non-negative')
        self.count, self.max_generations, self.strict = count, max_generations, strict
        self.combinator = HyperPrecisionCombinator(registry)
        self.crucible = MultiDomainCrucible()
        self.mutator = EvolutionaryMutator()
        self.candidates = []

    def run_cycle(self, topic, domain=None):
        from .models import Domain as WorkshopDomain
        if domain is None:
            t = topic.lower()
            domain = (WorkshopDomain.BINANCE_ALGO if any(x in t for x in ('trading', 'binance', 'orderbook')) else
                      WorkshopDomain.SOLANA_INFRA if 'solana' in t else
                      WorkshopDomain.OFFENSIVE_SEC if any(x in t for x in ('security', 'injection', 'secret')) else
                      WorkshopDomain.LOW_LATENCY_DISTRIBUTED if any(x in t for x in ('latency', 'distributed')) else WorkshopDomain.GENERAL)
        self.candidates = []
        survivors = []
        for idea in self.combinator.combine(domain, self.count):
            idea.problem_statement += f' Workshop topic: {topic}.'
            for generation in range(self.max_generations + 1):
                self.crucible.audit(idea)
                self.candidates.append(idea)
                if idea.status == IdeaStatus.VALIDATED:
                    survivors.append(idea)
                    break
                if generation == self.max_generations or idea.iteration_depth >= 3:
                    break
                child = self.mutator.mutate(idea, idea.falsification_reason)
                # Unknown failures cannot be repaired by blind retries.
                if (child.problem_statement, child.causal_mechanism, child.invariant_contract, child.title, child.baseline_reference, child.cheapest_falsification_test) == (idea.problem_statement, idea.causal_mechanism, idea.invariant_contract, idea.title, idea.baseline_reference, idea.cheapest_falsification_test):
                    break
                idea = child
        return survivors
