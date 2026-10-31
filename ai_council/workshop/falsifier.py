"""Fast, conservative checks for plainly implausible proposals."""
import re

from .models import IdeaCard, IdeaStatus


class FalsificationInquisitor:
    def audit(self, idea: IdeaCard) -> IdeaCard:
        text = ' '.join(str(value) for value in (idea.title, idea.problem_statement, idea.causal_mechanism, idea.baseline_reference, idea.cheapest_falsification_test, idea.metrics)).lower()
        sharpe_values = re.findall(r'\bsharpe(?:\s+ratio)?\s*(?:of|is|=|:|>|at)?\s*(\d+(?:\.\d+)?)', text)
        sharpe_metric = idea.metrics.get('sharpe', idea.metrics.get('sharpe_ratio'))
        try:
            metric_too_high = float(sharpe_metric) > 4.5
        except (TypeError, ValueError):
            metric_too_high = False
        reason = ''
        if metric_too_high or any(float(value) > 4.5 for value in sharpe_values) or re.search(r'\b(?:zero[- ]risk returns?|guaranteed alpha)\b', text):
            reason = 'Unrealistic financial claim.'
        elif re.search(r'\bzero[- ]latency\b.*\b(?:wan|wide area network)\b|\b(?:wan|wide area network)\b.*\bzero[- ]latency\b|\bo\s*\(\s*1\s*\)\s+arbitrary\s+search\b', text):
            reason = 'Physically or computationally impossible claim.'
        elif re.search(r'\bunbounded blast radius\b', text) and not re.search(r'\b(?:sandbox(?:ed|ing)?|isolat(?:ed|ion))\b', text):
            reason = 'Unbounded blast radius without safety sandboxing.'
        idea.status = IdeaStatus.FALSIFIED if reason else IdeaStatus.VALIDATED
        idea.falsification_reason = reason
        return idea
