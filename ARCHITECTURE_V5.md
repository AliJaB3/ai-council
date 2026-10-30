# AI Council v5: Calibrated Adaptive Deliberation Framework (CADF)
## Technical Specification for Codex Implementation

### 1. New Core Modules to Add in `ai_council/engine/`:

#### A. `ai_council/engine/drift_auditor.py`:
- `AuditResult`: dataclass with `total_claims: int`, `supported_claims: int`, `unsupported_claims: int`, `support_ratio: float`, `status: str` ('VALID' if support_ratio >= 0.75 else 'DEFICIT'), `unsupported_details: list[dict]`, `kill_switch_triggered: bool`.
- `DriftAuditor`: class that audits a list of `Claim` or `SeatOpinion` against `grounding` dictionaries (from `read_files(...)`).
  - Checks if claim keywords, file references, or code identifiers match the grounded source code.
  - If a claim references a non-existent function, file, or has zero match with grounded evidence while asserting factual code claims, flags it as unsupported.
  - If total claims > 0 and support_ratio < 0.75, sets `kill_switch_triggered = True` with status `'DEFICIT'`.

#### B. `ai_council/engine/info_delphi.py`:
- `InfoDelphi`: provides strict blind cognitive isolation during Phase 1.
- In multi-file grounding, can slice evidence symmetrically or asymmetrically so seats evaluate without cognitive contamination.
- Enforces zero cross-seat visibility until the Blind Phase is locked.

#### C. `ai_council/engine/armor_engine.py`:
- `ArmorEngine`: implements adaptive routing & sycophancy detection.
- `evaluate_consensus(opinions: list[SeatOpinion]) -> dict`:
  - Computes stance distribution and consensus entropy.
  - Detects "Premature Sycophancy" if all seats agree with high confidence without substantial cross-checking or when zero opposing claims are raised.
  - If sycophancy risk is high, triggers an adversarial perturbation flag (`adversarial_injection_needed = True`).
  - If consensus is genuine and strong (e.g. all seats agree with verifiable grounding), flags `can_early_exit = True`.

#### D. `ai_council/engine/dag_router.py`:
- `DAGRouter`: dynamically schedules deliberation steps as a DAG.
  - If `early_exit=True` and `can_early_exit=True`, skips Phase 2 to optimize token usage and latency.
  - If conflict or sycophancy detected, schedules an adversarial challenge branch.

### 2. Updates to `ai_council/models.py`:
- Add `AuditReport` dataclass or field on `CouncilVerdict` (`audit_report: dict = field(default_factory=dict)`).
- Add `early_exit: bool = False` to `CouncilVerdict`.

### 3. Updates to `ai_council/store/database.py`:
- Protect all SQLite mutations and queries with a local `threading.RLock()` to guarantee thread safety across concurrent requests, while ensuring the lock is never held during external network I/O.
- Store `audit_report` in `ccaa_decisions`.

### 4. Updates to `ai_council/engine/orchestrator.py`:
- Wire the 5 CADF layers into `CouncilOrchestrator.deliberate(...)`:
  1. `InfoDelphi` runs blind evaluation.
  2. `DriftAuditor` audits claims against grounding. If `kill_switch_triggered`, marks verdict status as `EVIDENCE_DEFICIT_WARNING` or stops execution when strict mode enabled.
  3. `ArmorEngine` evaluates consensus entropy and early-exit conditions.
  4. `DAGRouter` decides whether to run Phase 2 (Dialectical Cross-Exam) or early-exit.
  5. Arbiter synthesizes the final verdict.

### 5. Updates to `ai_council/cli.py`:
- Add flags:
  - `--early-exit`: allow adaptive early exit when unanimous grounded consensus is reached.
  - `--audit`: print detailed DRIFT evidence audit table.
  - `--strict-audit`: abort or reject verdict if evidence deficit (>25% unsupported claims) is detected.
- Render DRIFT Evidence Score (e.g. `🎯 DRIFT Evidence Score: 92% [VALID]`) and Armor Consensus status in terminal output.

### 6. Tests in `tests/test_cadf.py`:
- Test DriftAuditor with supported and unsupported claims, verify kill-switch at <75% support ratio.
- Test InfoDelphi isolation.
- Test ArmorEngine sycophancy detection and early-exit.
- Test thread-safe RLock in Database.
- Test full orchestrator CADF pipeline and CLI flags.
- Ensure 100% test pass rate.
