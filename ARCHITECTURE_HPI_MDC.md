# Hyper-Precision Ideation & Multi-Domain Crucible (HPI-MDC)
## Architecture & Technical Specification for Codex Implementation

### Objective
Upgrade `ai_council/workshop/` from simple combinatorics into the **Hyper-Precision Ideation & Multi-Domain Crucible (HPI-MDC)** as decided in Council Decision `c8d5ea61`.

### 1. Modules in `ai_council/workshop/`:

#### A. `ai_council/workshop/models.py`:
- `Domain` (Enum): `BINANCE_ALGO`, `SOLANA_INFRA`, `LOW_LATENCY_DISTRIBUTED`, `OFFENSIVE_SEC`, `AI_MODELS`, `GENERAL`.
- `IdeaStatus` (Enum): `PROPOSED`, `TIER_0_REJECTED`, `TIER_1_REJECTED`, `TIER_2_FALSIFIED`, `VALIDATED`, `PROTOTYPED`.
- `VerificationLevel` (Enum): `HYPOTHESIS`, `SIMULATED`, `HISTORICAL_REPLAY`, `EMPIRICALLY_PROVEN`.
- `InvariantContract`:
  - `preconditions: list[str] = field(default_factory=list)`
  - `postconditions: list[str] = field(default_factory=list)`
  - `complexity_time: str = 'O(1)'`
  - `complexity_space: str = 'O(1)'`
  - `max_latency_budget_ns: int = 100_000`
  - `max_capital_risk_usd: float = 0.0`
- `CausalMechanism`:
  - `trigger_event: str`
  - `causal_node: str`
  - `intervention: str`
  - `predicted_outcome: str`
  - `falsification_metric: str`
  - `falsification_threshold: float`
- `IdeaCard`:
  - `id: str`
  - `title: str`
  - `domain: Domain`
  - `secondary_domains: list[Domain] = field(default_factory=list)`
  - `problem_statement: str`
  - `causal_mechanism: CausalMechanism`
  - `invariant_contract: InvariantContract`
  - `baseline_reference: str`
  - `cheapest_falsification_test: str`
  - `status: IdeaStatus = IdeaStatus.PROPOSED`
  - `verification_level: VerificationLevel = VerificationLevel.HYPOTHESIS`
  - `falsification_reason: str = ''`
  - `iteration_depth: int = 0`
  - `created_at: str = ''`

#### B. `ai_council/workshop/registry.py`:
- `DimensionRegistry`:
  - Dynamic registration of primitives, problems, mechanisms, and invariants by domain.
  - Built-in domain packs:
    - `BINANCE_ALGO`: primitives (`L2/L3 orderbook depth`, `maker-taker latency delta`, `queue position decay`), problems (`spread collapse`, `toxic order flow`, `api rate limit burst`), mechanisms (`stochastic queue positioning`, `kernel bypass socket`, `cancel-replace pipelining`).
    - `SOLANA_INFRA`: primitives (`Proof of History`, `Tower BFT`, `Turbine`), problems (`tpu packet loss`, `block packing inefficiency`), mechanisms (`jito bundle auction`, `raw quic client`).
    - `LOW_LATENCY_DISTRIBUTED`: primitives (`io_uring`, `LMAX Disruptor`, `cache line padding`), problems (`cascading GC pause`, `tail latency amplification`), mechanisms (`lock-free SPSC ring`, `SQPOLL io_uring`).
    - `OFFENSIVE_SEC`: primitives (`taint analysis`, `canary tokens`), problems (`prompt injection`, `secret leak`), mechanisms (`differential prompt sandboxing`, `formal grammar pruning`).

#### C. `ai_council/workshop/combinator.py`:
- `HyperPrecisionCombinator`:
  - Cross-domain structural transposition (e.g. applying Solana mempool-less forwarding to distributed consensus, or ring buffer cache line padding to orderbook processing).
  - Emits `IdeaCard` with formal `InvariantContract` and `CausalMechanism`.

#### D. `ai_council/workshop/crucible.py`:
- `MultiDomainCrucible`:
  - `audit_tier_0_axiomatic(idea: IdeaCard) -> tuple[bool, str]`:
    - Speed of light axiom: WAN latency cannot be zero or faster than speed of light in fiber (`distance_km / 200,000`).
    - Thermodynamic / Financial axiom: Sharpe > 4.5 without tail risk is rejected.
    - Information theory axiom: O(1) search across unindexed arbitrary datasets is rejected.
  - `audit_tier_1_contract(idea: IdeaCard) -> tuple[bool, str]`:
    - Checks invariant consistency: capital risk must be $0.00 during test, latency budget must be >= 0.
  - `audit(idea: IdeaCard) -> IdeaCard`:
    - Runs Tier 0 and Tier 1 audits. Updates `status` to `TIER_0_REJECTED`, `TIER_1_REJECTED`, or `VALIDATED`.

#### E. `ai_council/workshop/mutator.py`:
- `EvolutionaryMutator`:
  - `mutate(idea: IdeaCard, failure_reason: str) -> IdeaCard`:
    - If `iteration_depth < 3`, applies causal mutation operators (relaxing unrealistic latency/budget, adjusting algorithm complexity) and returns a mutated candidate with `iteration_depth + 1`.

#### F. `ai_council/workshop/pipeline.py`:
- `AutonomousCrucibleWorkshop`:
  - End-to-end execution:
    1. Generates candidate cards via `HyperPrecisionCombinator`.
    2. Audits through `MultiDomainCrucible`.
    3. Re-routes rejected cards with viable potential to `EvolutionaryMutator` (up to max_generations = 2).
    4. Returns surviving and mutated validated `IdeaCard`s.

### 2. CLI Integration (`ai_council/cli.py`):
- Support `--workshop`, `--workshop-domain`, `--workshop-count`, `--crucible-strict`.
- Pretty-print terminal output with badges: `[AXIOMATIC: PASS]`, `[CONTRACT: PASS]`, `[STATUS: VALIDATED]`, displaying the causal mechanism and invariant contract.

### 3. Tests (`tests/test_workshop_crucible.py`):
- Test Tier 0 rejects impossible latency / speed of light violations.
- Test Tier 0 rejects impossible Sharpe (> 4.5 zero risk).
- Test Tier 1 validates invariant contracts (capital risk == $0 during test).
- Test EvolutionaryMutator refines an initially rejected idea into a valid one within 3 generations.
- Test full workshop cycle with domain routing.
- Run `/root/kaggle-llm-orchestrator/.venv/bin/pytest tests/` to confirm 100% pass rate.
