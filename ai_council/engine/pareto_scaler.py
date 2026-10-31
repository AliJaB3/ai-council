"""Small deterministic heuristic for sizing a deliberation."""
import re


class ParetoScaler:
    def compute_budget(self, topic, deep):
        if not isinstance(topic, str) or not topic.strip():
            raise ValueError('topic is required')
        words = re.findall(r'\w+', topic)
        complex_topic = len(words) > 20 or bool(re.search(r'\b(?:architecture|security|tradeoffs?|distributed|multi[- ]?system|migration)\b', topic, re.I))
        return {'max_seats': 5 if deep else 4 if complex_topic else 2,
                'max_rounds': 2 if deep or complex_topic else 1,
                'token_budget': 12000 if deep else 8000 if complex_topic else 4000}
