# 4 Pillars Synthesis & Dissent-Guarded Evolution Specification
## Technical Specification for Codex Autonomous Implementation (Decision 6de7fc75)

### Objective
Implement the 4 pillars synthesis approved in Decision `6de7fc75`:
1. Dissent-guarded early stopping in VoIEngine (never stop if unresolved objections exist in CEO Graph).
2. Dynamic Brier seat weight propagation into Arbiter synthesis and consensus evaluation.
3. Two-tier quarantine memory promotion with golden regression safety validation.
4. CLI options and tests for dissent guarding and memory promotion.

### 1. Module Upgrades in `ai_council/`:

#### A. `ai_council/engine/router.py`:
- In `VoIEngine`:
  - Enhance `should_stop(turn_entropies: list[float], threshold: float = 0.05, unresolved_objections: int = 0) -> bool`:
    - If `unresolved_objections > 0`, return `False` (dissent guard prevents premature consensus).
    - If `unresolved_objections == 0` and marginal entropy delta < threshold, return `True`.

#### B. `ai_council/engine/brier_calibration.py` & `ai_council/engine/orchestrator.py`:
- In `CouncilOrchestrator`:
  - Retrieve dynamic weights for all active seats using `self.brier_engine.get_seat_weight(seat.config.role)`.
  - Pass seat calibration weights into opinions, CEO graph, and arbiter synthesis context.
  - In `CouncilVerdict`, include `seat_weights: dict[str, float]`.

#### C. `ai_council/engine/evomem/quarantine.py`:
- Enhance `QuarantineManager`:
  - `promote(record_id: str, regression_passed: bool = True) -> bool`:
    - Transitions memory from `QUARANTINED` to `VALIDATED` if `regression_passed` is True.
    - If `regression_passed` is False, transitions to `REVOKED` to prevent memory poisoning.

#### D. Updates to `ai_council/cli.py`:
- Add CLI flag:
  - `--promote-memory RECORD_ID`: promotes a quarantined memory record if validation checks pass.
  - `--dissent-guard`: explicitly enforces dissent-guarded stopping.
- In terminal output:
  - Display `⚖️ Calibrated Seat Weights: architect=1.00, quant=1.00, ...`
  - Display `🛡️ Dissent Guard: Active (Unresolved Objections: N)`

### 2. Tests in `tests/test_dissent_and_evomem.py`:
- Test `VoIEngine.should_stop` returns `False` when `unresolved_objections > 0` even with 0 entropy.
- Test `VoIEngine.should_stop` returns `True` when `unresolved_objections == 0` and low entropy.
- Test `QuarantineManager.promote` validates or revokes based on regression outcome.
- Test Brier seat weights propagate into `CouncilVerdict.seat_weights`.
- Test CLI `--promote-memory` and `--brier-status`.
- Run `/root/kaggle-llm-orchestrator/.venv/bin/pytest tests/` to confirm 100% pass rate.
