# Autonomous Ideation Workshop Specification
## Technical Specification for Codex Autonomous Implementation

### Objective
Implement the `ai_council/workshop/` subsystem to support the Autonomous Ideation & Innovation Workshop approved in Council Decision `b396b5ed`.

### 1. New Directory & Modules: `ai_council/workshop/`

#### A. `ai_council/workshop/models.py`:
- `Anomaly`:
  - `id: str`, `source: str`, `metric: str`, `z_score: float`, `details: dict`, `created_at: str`.
- `IdeaStatus`: Enum (`PROPOSED`, `FALSIFIED`, `VALIDATED`, `PROTOTYPED`).
- `IdeaCard`:
  - `id: str`, `title: str`, `domain: Domain`, `problem_statement: str`, `causal_mechanism: str`, `baseline_reference: str`, `cheapest_falsification_test: str`, `token_budget: int = 5000`, `status: IdeaStatus = IdeaStatus.PROPOSED`, `falsification_reason: str = ''`, `metrics: dict = field(default_factory=dict)`, `created_at: str = ''`.

#### B. `ai_council/workshop/combinator.py`:
- `MorphologicalCombinator`:
  - Dimensions:
    - `PROBLEMS`: `["liquidity_fragmentation", "flaky_concurrency", "token_budget_exhaustion", "sycophancy_in_debate", "slippage_during_volatility"]`
    - `MECHANISMS`: `["batch_auction", "circuit_breaker", "stratified_replay", "adversarial_red_teaming", "negative_constraint_pruning", "zk_proof_verification"]`
  - `combine(domain: Domain, count: int = 3) -> list[IdeaCard]`:
    - Generates novel, structured `IdeaCard` instances combining problems and mechanisms.
    - Ensures causal mechanism and baseline reference are explicitly formulated.

#### C. `ai_council/workshop/falsifier.py`:
- `FalsificationInquisitor`:
  - Evaluates an `IdeaCard` against fast rejection heuristics:
    - Unrealistic financial claims (Sharpe > 4.5, zero-risk returns, guaranteed alpha).
    - Physical/computational impossibilities (zero latency over WAN, O(1) arbitrary search).
    - Unbounded blast radius without safety sandboxing.
  - `audit(idea: IdeaCard) -> IdeaCard`:
    - If suspicious or violating heuristics, sets `status = IdeaStatus.FALSIFIED` and sets `falsification_reason`.
    - If passing pre-filter, sets `status = IdeaStatus.VALIDATED`.

#### D. `ai_council/workshop/pipeline.py`:
- `IdeationWorkshop`:
  - `run_cycle(topic: str, domain: Domain | None = None, seed_anomalies: list[Anomaly] | None = None) -> list[IdeaCard]`:
    - Detects domain or uses provided domain.
    - Generates candidate `IdeaCard`s via `MorphologicalCombinator`.
    - Applies `FalsificationInquisitor` to eliminate flawed/shallow candidates.
    - Returns surviving validated ideas.

### 2. Integration with `ai_council/cli.py`:
- Add CLI arguments:
  - `--workshop`: run an ideation workshop cycle on the topic.
  - `--workshop-count`: number of ideas to generate (default 3).
- When `--workshop` is passed, run `IdeationWorkshop.run_cycle(...)` and format the surviving and falsified `IdeaCard`s cleanly in terminal with badges, mechanisms, and cheapest falsification tests.

### 3. Tests in `tests/test_workshop.py`:
- Test `MorphologicalCombinator` generation.
- Test `FalsificationInquisitor` rejecting unrealistic claims (Sharpe > 4.5, zero latency) and passing viable ideas.
- Test `IdeationWorkshop.run_cycle` end-to-end.
- Test CLI `--workshop` flag.
- Run `/root/kaggle-llm-orchestrator/.venv/bin/pytest tests/` to ensure 100% of all existing and new tests pass.
