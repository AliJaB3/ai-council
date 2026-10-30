# AI Council v4: Claim-Centric Adaptive Architecture (CCAA)
## Specification for Codex Autonomous Implementation

### Objective
Create a standalone, production-grade Python package `ai_council` that provides multi-agent deliberation, dialectical peer review, claim-centric grounding, and decision synthesis across heterogeneous frontier LLM families.

### Core Modules & Responsibilities:

1. `ai_council/config.py`:
   - Environment settings: `OMNIROUTE_BASE_URL` (default `http://localhost:20128/v1`), `OMNIROUTE_API_KEY`, SQLite DB path (`/root/.hermes/council_decisions.sqlite` or local override).
   - Seat definitions, model choices, fallbacks, and timeouts.

2. `ai_council/models.py`:
   - `Stance`: enum (`SUPPORT`, `OPPOSE`, `AMEND`).
   - `Claim`: text, source, confidence (1-10), dependencies, invalidation_conditions.
   - `SeatOpinion`: role, title, avatar, model_family, model_used, latency_ms, stance, confidence, argument, novel_insight, key_risk, condition, claims list.
   - `DialecticTurn`: seat role, challenge_target, challenge_point, synergy_target, synergy_point, evolved_stance, text.
   - `CouncilVerdict`: id, topic, status, confidence_score, executive_verdict, emergent_architecture, consensus_analysis, implementation_blueprint, risk_matrix, kill_switch_criteria, judge_model, duration_s, created_at.

3. `ai_council/seats/`:
   - `base.py`: `BaseSeat` with `evaluate(...)`, `cross_examine(...)`.
   - 5 Concrete Seats:
     1. `ArchitectSeat` (OpenAI / GPT-6.1 Sol)
     2. `QuantSeat` (Cerebras LPU / 120b)
     3. `InnovatorSeat` (Claude Sonnet 4.6 / Nemotron)
     4. `RedTeamSeat` (DeepSeek-R1 Distill)
     5. `ImplementerSeat` (Qwen Coder 32B)
   - `ArbiterSeat`: High Bench Arbiter / Chief Justice.

4. `ai_council/engine/`:
   - `orchestrator.py`: `CouncilOrchestrator` running Phase 1 (parallel evaluation), Phase 2 (dialectical cross-examination), Phase 3 (high bench synthesis).
   - `claim_graph.py`: Tracks claims, detects direct contradictions between seats, builds consensus score.
   - `grounding.py`: Reads files, extracts git commit hashes, verifies if files exist, checks for stale decisions when files change.

5. `ai_council/store/database.py`:
   - SQLite WAL mode, FTS5 full-text search.
   - Migration support from existing `/root/.hermes/council_decisions.sqlite`.
   - Invalidation tracking: mark decisions as STALE when grounded file or commit changes.

6. `ai_council/cli.py`:
   - CLI entrypoint: `ai-council [topic] [--file FILE] [--deep] [--history] [--search TERM] [--json] [--check-stale]`.

7. `pyproject.toml`:
   - Standard setuptools / wheel packaging with console script `ai-council = "ai_council.cli:main"`.

8. `tests/`:
   - Pytest suite covering all modules, mocks for HTTP calls to test without network, and integration tests.
