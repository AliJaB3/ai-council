from ..config import SEATS, ARBITER
from .base import BaseSeat, SeatError

class ArchitectSeat(BaseSeat):
    def __init__(self, settings=None, client=None): super().__init__(SEATS[0], settings, client)
class QuantSeat(BaseSeat):
    def __init__(self, settings=None, client=None): super().__init__(SEATS[1], settings, client)
class InnovatorSeat(BaseSeat):
    def __init__(self, settings=None, client=None): super().__init__(SEATS[2], settings, client)
class RedTeamSeat(BaseSeat):
    def __init__(self, settings=None, client=None): super().__init__(SEATS[3], settings, client)
class ImplementerSeat(BaseSeat):
    def __init__(self, settings=None, client=None): super().__init__(SEATS[4], settings, client)
class ArbiterSeat(BaseSeat):
    def __init__(self, settings=None, client=None): super().__init__(ARBITER, settings, client)
    def synthesize(self, topic, opinions, turns, graph, grounding):
        from dataclasses import asdict
        from ..models import CouncilVerdict
        data, model, _ = self._ask("You are the High Bench Arbiter. Synthesize the evidence and disagreements. Return confidence_score (0-10), executive_verdict, emergent_architecture, consensus_analysis, implementation_blueprint, risk_matrix, kill_switch_criteria.", {"topic": topic, "opinions": [asdict(o) for o in opinions], "dialectic": [asdict(t) for t in turns], "claim_graph": graph, "grounding": grounding})
        keys = ("confidence_score", "executive_verdict", "emergent_architecture", "consensus_analysis", "implementation_blueprint", "risk_matrix", "kill_switch_criteria")
        return CouncilVerdict(topic=topic, judge_model=model, **{k: data[k] for k in keys if k in data})
