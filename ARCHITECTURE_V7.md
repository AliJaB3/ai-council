# AI Council v7 Evolution: Streaming, Counterfactual Git Fork & LMSR Shadow Market
## Architecture & Technical Specification for Codex Autonomous Implementation (Decision 722c7519)

### 1. New Core Modules in `ai_council/engine/`:

#### A. `ai_council/engine/streaming.py`:
- `DeliberationEvent`:
  - `seq: int`
  - `event_id: str`
  - `correlation_id: str`
  - `timestamp: str`
  - `event_type: str` (e.g. `SESSION_STARTED`, `SEAT_COMMITTED`, `CLAIM_ADDED`, `OBJECTION_LINKED`, `EXPERIMENT_EMITTED`, `VERDICT_SYNTHESIZED`)
  - `payload: dict`
- `DeliberationEventStream`:
  - `emit(event_type: str, correlation_id: str, payload: dict)`
  - `subscribe(listener_fn)`: registers callback for live streaming (WebSockets / stdout).
  - `get_history(correlation_id: str | None = None) -> list[DeliberationEvent]`

#### B. `ai_council/engine/git_fork.py`:
- `ExecutionReceipt`:
  - `correlation_id: str`
  - `branch_name: str`
  - `status: str` ('PASSED', 'FAILED', 'SECURITY_VIOLATION')
  - `exit_code: int`
  - `stdout: str`
  - `duration_ms: float`
- `CounterfactualForkManager`:
  - `fork_and_test(repo_path: str, patch_dict: dict[str, str], test_command: str, correlation_id: str, timeout_s: float = 10.0) -> ExecutionReceipt`:
    - Validates patch files with `ASTSecurityGate`.
    - Spawns isolated temporary worktree `git worktree add ...` on branch `council/fork-<id>`.
    - Applies patch files into the worktree.
    - Runs `test_command` with strict timeout.
    - Cleans up worktree (`git worktree remove --force`) and branch (`git branch -D`).
    - Returns `ExecutionReceipt`.

#### C. `ai_council/engine/lmsr_market.py`:
- `LMSRShadowMarket`:
  - Logarithmic Market Scoring Rule:
    - Liquidity parameter $b > 0$ (default $100.0$).
    - Shares: $q_{yes}, q_{no}$.
    - Cost: $C(q) = b \cdot \ln(e^{q_{yes}/b} + e^{q_{no}/b})$.
    - Probability $P(yes) = \frac{e^{q_{yes}/b}}{e^{q_{yes}/b} + e^{q_{no}/b}}$.
  - Methods:
    - `open_market(claim_id: str, correlation_id: str, b: float = 100.0)`
    - `place_bet(claim_id: str, seat: str, stance: str, confidence: int)`: calculates $\Delta q$ proportional to confidence and adds to market.
    - `get_market_state(claim_id: str) -> dict`: returns probabilities, shares, and cost.
    - `settle(claim_id: str, outcome_yes: bool) -> dict`: calculates payoffs and shadow Brier calibration.

#### D. `ai_council/engine/pareto_scaler.py`:
- `ParetoScaler`:
  - `compute_budget(topic: str, deep: bool) -> dict`:
    - Returns optimal `max_seats`, `max_rounds` (1 or 2), and `token_budget` based on topic complexity.

### 2. Integration with `ai_council/engine/orchestrator.py`:
- Integrate `DeliberationEventStream`: emit events at each phase of `deliberate(...)`.
- When contested claims arise, optionally initialize `LMSRShadowMarket` on the contested claims.
- If `--git-fork` is specified with repo path and candidate code, run `CounterfactualForkManager`.

### 3. Updates to `ai_council/cli.py`:
- Add CLI flags:
  - `--stream-events`: stream live JSON deliberation events to stdout.
  - `--git-fork REPO_PATH`: test candidate in a counterfactual temporary git worktree.
  - `--lmsr-shadow`: print shadow LMSR market probabilities on contested claims.

### 4. Tests in `tests/test_v7_evolution.py`:
- Test `DeliberationEventStream` emission, ordering, and callback subscription.
- Test `LMSRShadowMarket` cost function, probability calculation ($P(yes)+P(no)=1.0$), and settlement.
- Test `CounterfactualForkManager` creating and cleaning up worktrees cleanly.
- Test `ParetoScaler` budget allocation.
- Run `/root/kaggle-llm-orchestrator/.venv/bin/pytest tests/` to confirm 100% pass rate.
