"""OpenAI-compatible model client and seat protocols."""
from dataclasses import asdict
import json
import re
import time
import httpx
from ..config import Settings, SeatConfig
from ..models import SeatOpinion, DialecticTurn

class SeatError(RuntimeError):
    pass

def _json_object(content):
    if isinstance(content, dict):
        return content
    text = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL | re.IGNORECASE).strip()
    if text.startswith("```") and "\n" in text:
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise
        result = json.loads(match.group())
    if not isinstance(result, dict):
        raise ValueError("model response must be a JSON object")
    return result

class BaseSeat:
    def __init__(self, config: SeatConfig, settings: Settings | None = None, client=None):
        self.config = config
        self.settings = settings or Settings()
        self.client = client

    def _ask(self, instruction, payload):
        errors = []
        for model in (self.config.model, *self.config.fallbacks):
            start = time.monotonic()
            try:
                kwargs = dict(json={"model": model, "messages": [
                    {"role": "system", "content": instruction + " Respond with a JSON object only."},
                    {"role": "user", "content": json.dumps(payload, default=str)}],
                    "response_format": {"type": "json_object"}},
                    headers={"Authorization": f"Bearer {self.settings.api_key}"} if self.settings.api_key else {},
                    timeout=self.config.timeout)
                if self.client is not None:
                    response = self.client.post(self.settings.base_url.rstrip("/") + "/chat/completions", **kwargs)
                else:
                    response = httpx.post(self.settings.base_url.rstrip("/") + "/chat/completions", **kwargs)
                response.raise_for_status()
                data = _json_object(response.json()["choices"][0]["message"]["content"])
                return data, model, (time.monotonic() - start) * 1000
            except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
                errors.append(f"{model}: {exc}")
        raise SeatError(f"{self.config.role} failed: {'; '.join(errors)}")

    def evaluate(self, topic, grounding=None):
        data, model, latency = self._ask(
            f"You are the {self.config.title}. Evaluate the proposal independently. Return stance (SUPPORT, OPPOSE, AMEND), confidence (1-10), argument, novel_insight, key_risk, condition, and claims. Each claim has text, source, confidence, dependencies, invalidation_conditions.",
            {"topic": topic, "grounding": grounding or []})
        allowed = {k: data[k] for k in ("stance", "confidence", "argument", "novel_insight", "key_risk", "condition", "claims") if k in data}
        try:
            return SeatOpinion(role=self.config.role, title=self.config.title, avatar=self.config.avatar, model_family=self.config.model_family, model_used=model, latency_ms=latency, **allowed)
        except (TypeError, ValueError) as exc:
            raise SeatError(f"{self.config.role} returned invalid opinion: {exc}") from exc

    def cross_examine(self, topic, opinions):
        data, _, _ = self._ask(f"You are the {self.config.title}. Challenge another seat and find a synergy. Return challenge_target, challenge_point, synergy_target, synergy_point, evolved_stance (SUPPORT, OPPOSE, AMEND), text.", {"topic": topic, "opinions": [asdict(o) for o in opinions]})
        allowed = {k: data[k] for k in ("challenge_target", "challenge_point", "synergy_target", "synergy_point", "evolved_stance", "text") if k in data}
        try:
            return DialecticTurn(seat_role=self.config.role, **allowed)
        except (TypeError, ValueError) as exc:
            raise SeatError(f"{self.config.role} returned invalid dialectic: {exc}") from exc
