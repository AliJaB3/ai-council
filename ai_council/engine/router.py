"""Conservative, deterministic routing and value-of-information stopping."""
from enum import Enum
import re


class RouteType(str, Enum):
    FAST_PATH = "FAST_PATH"
    DEEP_PATH = "DEEP_PATH"


class DeliberationRouter:
    def route(self, topic: str, context: dict | None = None) -> RouteType:
        text = topic.casefold()
        if context and (context.get('deep') or context.get('contested')):
            return RouteType.DEEP_PATH
        if re.search(r'\b(architect(?:ure|ural)?|trade[ -]?offs?|financial|investment|risk|debate|controvers\w*|compare|design|should|versus|vs\.?|strategy)\b', text):
            return RouteType.DEEP_PATH
        if re.search(r'\b(status|version|lookup|look up|what is|what are|who is|when is|where is|how many|calculate|convert)\b', text):
            return RouteType.FAST_PATH
        return RouteType.DEEP_PATH


class VoIEngine:
    def should_stop(self, turn_entropies: list[float], threshold: float = 0.05) -> bool:
        return len(turn_entropies) >= 2 and abs(turn_entropies[-1] - turn_entropies[-2]) < threshold
