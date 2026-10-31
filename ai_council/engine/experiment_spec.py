"""Produce an explicit, editable protocol for investigating contested claims."""
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class ExperimentSpec:
    spec_id: str
    correlation_id: str
    hypothesis: str
    contested_claims: list[dict]
    test_code_template: str
    target_metric: str
    pass_threshold: float
    abort_criteria: str
    created_at: str
    timeout_s: float = 10.0


class ExperimentSpecGenerator:
    def generate(self, topic: str, contested_claims: list[dict], correlation_id: str) -> ExperimentSpec | None:
        if not contested_claims:
            return None
        hypothesis = f"The contested claims about {topic} are supported by reproducible measurements: " + "; ".join(str(c.get('text', '')) for c in contested_claims)
        template = '''# Replace measure_support with a domain-specific, reproducible measurement.
def measure_support():
    raise NotImplementedError("Define the data, baseline, and measurement before running")


def test_contested_claims():
    support_fraction = measure_support()
    assert 0.0 <= support_fraction <= 1.0
    assert support_fraction >= 1.0
'''
        return ExperimentSpec(str(uuid4()), correlation_id, hypothesis, contested_claims, template,
                              "fraction of contested claims supported", 1.0,
                              "Abort if data or measurement is unavailable, invalid, or exceeds the timeout.",
                              datetime.now(timezone.utc).isoformat())
