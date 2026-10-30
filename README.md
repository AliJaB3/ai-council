# 🏛️ AI Council v4: Claim-Centric Adaptive Architecture (CCAA)

[![Tests](https://img.shields.io/badge/tests-11%20passed-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()
[![License](https://img.shields.io/badge/license-MIT-purple.svg)]()

**AI Council** is a production-grade, multi-agent deliberation and dialectical peer-review framework. It convenes 5 heterogeneous frontier AI model families across complementary cognitive lenses to produce rigorous, novel, and battle-tested engineering decisions.

---

## 🌟 The 5 Cognitive Seats

| Seat | Role | Default Model | Lens & Cognitive Function |
| :--- | :--- | :--- | :--- |
| 🏛️ **Architect** | System Architect | `codex/gpt-6.1-sol` *(OpenAI Frontier)* | Modularity, systemic integrity, zero-mock guarantees, enterprise maintainability. |
| 📊 **Quant** | Quant & Market Specialist | `cerebras/gpt-oss-120b` *(Cerebras LPU)* | Quantitative rigor, orderbook mechanics, liquidity regimes, statistical edge. |
| 💡 **Innovator** | Innovation Provocateur | `antigravity/claude-sonnet-4-6` *(Anthropic Claude)* | Lateral thinking, breakthrough paradigms, cross-domain synthesis. |
| 🔴 **Red Team** | Adversarial Red Team | `unorouter/deepseek-r1-distill-qwen-32b:free` *(DeepSeek R1)* | Catastrophic failure modes, race conditions, exploit vectors, tail risks. |
| 🛠️ **Implementer** | Lead Implementer | `unorouter/qwen2.5-coder-32b:free` *(Qwen Coder)* | Runtime efficiency, zero-friction delivery, concrete code patterns. |
| ⚖️ **Chief Justice** | High Bench Arbiter | `cerebras/gpt-oss-120b` *(Cerebras / Gemini)* | Decisive synthesis, conflict resolution, concrete code roadmap, kill-switches. |

---

## 🔄 3-Phase Dialectical Process

1. **Phase 1: Divergent Specialist Ideation**
   - All 5 seats independently evaluate the inquiry and grounded codebase files concurrently.
   - Extracts structured stance (`SUPPORT`, `OPPOSE`, `AMEND`), confidence (1-10), arguments, novel insights, and key risks.
2. **Phase 2: Dialectical Cross-Pollination & Peer Challenge (`--deep`)**
   - Each specialist critiques a specific peer's blind spots and elevates another peer's breakthrough idea.
3. **Phase 3: High Bench Synthesis**
   - Chief Justice synthesizes an emergent architecture, resolving contradictions and providing a hardened code blueprint with risk mitigation and kill-switch abort criteria.

---

## ⚡ Grounding & Memory Invalidation

- **Source Code Grounding:** Pass files via `--file <path>` to ground deliberation in real repository code and Git commit hashes.
- **Decision Invalidation:** If source files or git commits change, past dependent decisions are automatically tracked and flagged as `STALE` via `--check-stale`.
- **SQLite WAL + FTS5 Store:** Persistent full-text search archive of all deliberations and decisions.

---

## 🚀 Installation & Usage

### Local Install:
```bash
git clone https://github.com/AliJaB3/ai-council.git
cd ai-council
pip install -e .
```

### CLI Commands:
```bash
# Fast deliberation
ai-council "Should Dollar Machine cache orderbook ticks in Redis or write to PostgreSQL?"

# Deep 2-round dialectical debate grounded in source code
ai-council --deep --file /path/to/engine.py "How to eliminate race conditions in live order execution?"

# Search past decisions using FTS5
ai-council --search "Redis"

# List deliberation history
ai-council --history

# Check for stale decisions whose grounded files have changed
ai-council --check-stale

# Machine-readable output for programmatic pipelines
ai-council --json "Evaluate zero-knowledge proof verification on Solana"
```

---

## 🧪 Testing

```bash
pytest -v tests/
```

100% test coverage across models, claim graph, grounding, store, and orchestration.
