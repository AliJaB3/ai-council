# Apex Council Architecture & Implementation Specification
## Technical Blueprint for Codex Autonomous Implementation (Decision d0ba9a70)

### Objective
Implement the Apex Council system across 4 modular layers:
1. `ai_council/contracts.py`: Immutable data contracts.
2. `ai_council/deliberation/search.py`: Tree of Deliberation (Multi-Agent MCTS with UCB falsification penalty).
3. `ai_council/evidence/pump.py` & `gateway.py`: Mid-Flight Evidence Pumping with zero-trust MCP read-only gateway.
4. `ai_council/falsification/harness.py`: Counter-Example Falsification Harness in sandboxed runner.
5. `ai_council/governance/delegation.py` & `quadratic.py`: Liquid Delegation DAG (cycle-free) & Quadratic Voting (Shadow Mode).

---

### Detailed Module Specifications:

#### 1. `ai_council/contracts.py`:
- `Claim`: `claim_id: str`, `author_role: str`, `proposition: str`, `confidence: float = 0.5`, `evidence_refs: list[str] = field(default_factory=list)`.
- `EvidenceEnvelope`: `evidence_id: str`, `source_uri: str`, `content: str`, `is_trusted: bool = False`, `version: int = 1`, `timestamp: float = 0.0`.
- `SearchNode`: `node_id: str`, `parent_id: str | None = None`, `action: str = ''`, `state_snapshot: dict = field(default_factory=dict)`, `visits: int = 0`, `value_sum: float = 0.0`, `falsification_penalty: float = 0.0`.
- `ObjectionRecord`: `objection_id: str`, `target_claim_id: str`, `counter_code: str = ''`, `status: str = 'PENDING'`.
- `Ballot`: `voter_id: str`, `proposal_id: str`, `votes: float = 0.0`, `cost: float = 0.0`.

#### 2. `ai_council/deliberation/search.py`:
- `TreeOfDeliberation`:
  - Maintains a tree of `SearchNode`s.
  - `compute_ucb(node: SearchNode, parent_visits: int, c: float = 1.414, lam: float = 2.0) -> float`:
    - $Q = \text{node.value\_sum} / \max(1, \text{node.visits})$
    - $U = c \cdot \sqrt{\ln(\max(1, \text{parent\_visits})) / \max(1, \text{node.visits})}$
    - Returns $Q + U - \text{lam} \cdot \text{node.falsification\_penalty}$.
  - `expand(parent: SearchNode, actions: list[str]) -> list[SearchNode]`
  - `apply_falsification_penalty(node_id: str, penalty: float)`: increases node penalty and propagates to prune bad branches.
  - `best_path() -> list[SearchNode]`

#### 3. `ai_council/evidence/gateway.py` & `pump.py`:
- `EvidenceGateway`:
  - Wraps `MCPClient`.
  - Rejects mutating tools (`is_mutating == True`) with `PermissionError`.
  - Wraps tool outputs in `EvidenceEnvelope` with `is_trusted = False`.
- `EvidencePump`:
  - `should_pump(entropy: float, contested_claims_count: int, threshold_entropy: float = 0.8) -> bool`:
    - Returns True if entropy > threshold_entropy or contested_claims_count > 0.
  - `inject(query: str, gateway: EvidenceGateway, tool_name: str, args: dict) -> EvidenceEnvelope`

#### 4. `ai_council/falsification/harness.py`:
- `FalsificationOutcome`: Enum (`REFUTED`, `NOT_REFUTED`, `INCONCLUSIVE`, `EXECUTION_ERROR`).
- `CounterExampleHarness`:
  - `evaluate_objection(objection: ObjectionRecord, sandbox_runner) -> tuple[FalsificationOutcome, str]`:
    - If `counter_code` is empty, returns `(INCONCLUSIVE, 'No code')`.
    - Runs code in `sandbox_runner`.
    - If test code runs cleanly and assertion holds (refuting the target claim), returns `(REFUTED, output)`.
    - If assertion fails (target claim survives test), returns `(NOT_REFUTED, output)`.
    - If syntax/error/timeout, returns `(EXECUTION_ERROR, error)`.

#### 5. `ai_council/governance/delegation.py` & `quadratic.py`:
- `LiquidDelegation`:
  - Transitive delegation map: `delegates: dict[str, str]` (voter -> delegatee).
  - Cycle detection using DFS: prevents $A \to B \to A$.
  - `resolve_effective_votes(base_credits: dict[str, float]) -> dict[str, float]`: computes accumulated voting credits with concentration cap (max 40% of total pool).
- `QuadraticVoting`:
  - Budget: each voter has $B$ credits.
  - Cost for $V$ votes is $V^2$.
  - `cast_vote(voter_id: str, budget: float, votes: float) -> tuple[bool, str, float]`:
    - Validates $\text{cost} = \text{votes}^2 \le \text{budget}$.
    - Returns `(success, msg, cost)`.

---

### 6. Integration with Orchestrator & CLI:
- In `ai_council/cli.py`:
  - Add `--deliberation-mode {linear,tree,mcts}`
  - Add `--evidence-pump`
  - Add `--governance-shadow`
- When `--deliberation-mode tree` or `mcts` is set, uses `TreeOfDeliberation` to explore actions and apply falsification penalties.

---

### 7. Tests (`tests/test_apex_council.py`):
- Test `TreeOfDeliberation` UCB calculation, expansion, and falsification penalty pruning.
- Test `EvidenceGateway` enforces read-only and wraps `EvidenceEnvelope`.
- Test `CounterExampleHarness` produces `REFUTED`, `NOT_REFUTED`, `EXECUTION_ERROR`.
- Test `LiquidDelegation` detects cycles and enforces concentration cap.
- Test `QuadraticVoting` enforces quadratic cost $V^2 \le B$.
- Run `/root/kaggle-llm-orchestrator/.venv/bin/pytest tests/` to confirm 100% pass rate.
