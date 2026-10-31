"""Configuration for the council and its model seats."""
from dataclasses import dataclass, field
import os
from pathlib import Path

@dataclass(frozen=True)
class SeatConfig:
    role: str
    title: str
    avatar: str
    model_family: str
    model: str
    fallbacks: tuple[str, ...] = ()
    timeout: float = 120.0

SEATS = (
    SeatConfig("architect", "Architect", "🏛️", "OpenAI", "codex/gpt-6.1-sol", ("codex/gpt-6-astra", "antigravity/claude-sonnet-4-6", "zro/deepseek-v4.1-flash", "zro/glm-5.3-flash"), timeout=150.0),
    SeatConfig("quant", "Quant", "📊", "Cerebras", "cerebras/gpt-oss-120b", ("groq/openai/gpt-oss-120b", "zro/glm-5.3-flash", "antigravity/gemini-3.8-flash-high", "zro/deepseek-v4.1-flash"), timeout=120.0),
    SeatConfig("innovator", "Innovator", "💡", "Anthropic", "antigravity/claude-sonnet-4-6", ("zro/glm-5.3-flash", "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free", "zro/deepseek-v4.1-flash", "codex/gpt-6-astra"), timeout=150.0),
    SeatConfig("red_team", "Red Team", "🔴", "DeepSeek", "zro/deepseek-v4.1-flash", ("unorouter/deepseek-r1-distill-qwen-32b:free", "zro/glm-5.3-flash", "codex/gpt-6.1-sol", "cloudflare-playground/deepseek-ai/deepseek-r1-distill-qwen-32b"), timeout=120.0),
    SeatConfig("implementer", "Implementer", "🛠️", "Qwen", "zro/glm-5.3-flash", ("unorouter/qwen2.5-coder-32b:free", "mistral/codestral-latest", "zro/deepseek-v4.1-flash", "cloudflare-playground/qwen/qwen2.5-coder-32b-instruct"), timeout=120.0),
)
ARBITER = SeatConfig("arbiter", "High Bench Arbiter / Chief Justice", "⚖️", "Cerebras", "cerebras/gpt-oss-120b", ("antigravity/gemini-3.8-flash-high", "zro/deepseek-v4.1-flash", "codex/gpt-6.1-sol", "zro/glm-5.3-flash", "groq/openai/gpt-oss-120b"), timeout=180.0)

@dataclass
class Settings:
    base_url: str = field(default_factory=lambda: os.getenv("OMNIROUTE_BASE_URL", "http://localhost:20128/v1"))
    api_key: str = field(default_factory=lambda: os.getenv("OMNIROUTE_API_KEY", ""))
    db_path: str = field(default_factory=lambda: os.getenv("AI_COUNCIL_DB_PATH", os.getenv("COUNCIL_DB_PATH", str(Path.home() / ".hermes" / "council_decisions.sqlite"))))
    seats: tuple[SeatConfig, ...] = SEATS
    arbiter: SeatConfig = ARBITER
