# AI Council Engine Upgrade: CEO Graph & ExperimentSpec
## Technical Specification for Codex Autonomous Implementation

### Objective
Implement the internal Council upgrades decided in Council Decision `6b28c53f`:
1. Claim-Evidence-Objection (CEO) Graph
2. ExperimentSpec generation for contested empirical claims
3. Blind first-turn cognitive isolation
4. Correlation ID / Digital Thread linking

### 1. New & Enhanced Modules in `ai_council/engine/`:

#### A. Enhanced `ai_council/engine/claim_graph.py`:
- Classes:
  - `ClaimNode`: `id: str`, `seat: str`, `text: str`, `confidence: int`, `evidence_refs: list[str]`.
  - `EvidenceNode`: `id: str`, `source: str`, `content_hash: str`, `snippet: str`, `verified: bool`.
  - `ObjectionNode`: `id: str`, `objecting_seat: str`, `target_claim_id: str`, `rationale: str`, `status: str = 'UNRESOLVED'`.
- `ClaimGraph` class enhancements:
  - Methods:
    - `add_claim(node: ClaimNode)`
    - `add_evidence(node: EvidenceNode)`
    - `add_objection(node: ObjectionNode)`
    - `link_dialectical_turn(turn: DialecticTurn, opinions: list[SeatOpinion])`: creates `ObjectionNode` linking objecting seat to contested claims of target seat.
    - `get_contested_claims() -> list[dict]`: returns claims that have active objections.
    - `to_dict() -> dict`: includes `claims`, `evidence`, `objections`, `contested_claims`, `consensus_score`, `contradictions`.

#### B. `ai_council/engine/experiment_spec.py`:
- `ExperimentSpec`:
  - `spec_id: str`
  - `correlation_id: str`
  - `hypothesis: str`
  - `contested_claims: list[dict]`
  - `test_code_template: str`
  - `target_metric: str`
  - `pass_threshold: float`
  - `timeout_s: float = 10.0`
  - `abort_criteria: str`
  - `created_at: str`
- `ExperimentSpecGenerator`:
  - `generate(topic: str, contested_claims: list[dict], correlation_id: str) -> ExperimentSpec | None`:
    - If contested claims exist, synthesizes an executable `ExperimentSpec` with a Python test template, assertion criteria, and abort criteria to settle the dispute empirically.
    - If no contested claims, returns `None`.

#### C. `ai_council/models.py`:
- Add `correlation_id: str = field(default_factory=lambda: str(uuid4()))` to `CouncilVerdict`.
- Add `experiment_spec: dict | None = None` to `CouncilVerdict`.

#### D. `ai_council/engine/orchestrator.py`:
- Generate `correlation_id` at the beginning of deliberation.
- Pass `correlation_id` through opinions, graph, and verdict.
- Populate `ClaimGraph` with `ClaimNode`s, verify evidence nodes with `grounding`, and link `DialecticTurn`s as objections.
- If dialectic turns contain challenges, call `ExperimentSpecGenerator.generate(...)` and attach to `verdict.experiment_spec`.

### 2. Updates to `ai_council/cli.py`:
- Add CLI flag:
  - `--emit-experiment`: outputs generated `ExperimentSpec` in terminal or JSON.
- In terminal renderer:
  - Print `🔗 Correlation ID: {correlation_id}`
  - Print `📊 CEO Graph: {X} claims, {Y} evidence, {Z} objections ({C} contested)`
  - If `experiment_spec` exists, render an attractive box with the generated experiment hypothesis and test template.

### 3. Tests in `tests/test_council_upgrades.py`:
- Test CEO graph node creation, objection linking, and contested claims extraction.
- Test `ExperimentSpecGenerator` generates valid test template when contested claims exist.
- Test `correlation_id` persistence across verdict and store.
- Test CLI `--emit-experiment` flag.
- Run `/root/kaggle-llm-orchestrator/.venv/bin/pytest tests/` to confirm 100% pass rate across all test suites.
