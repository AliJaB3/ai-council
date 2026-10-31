# AI Council 4 Pillars Implementation Specification
## Architecture for Codex Autonomous Implementation (Decision 06f2d77f)

### 1. New Core Modules in `ai_council/engine/`:

#### A. `ai_council/engine/router.py`:
- `RouteType`: Enum (`FAST_PATH`, `DEEP_PATH`).
- `DeliberationRouter`:
  - `route(topic: str, context: dict | None = None) -> RouteType`:
    - Fast-path (<500ms): queries that are simple factual lookups, status checks, or have high confidence deterministic keywords without deep epistemological dispute.
    - Deep-path: complex architectural, multi-criteria trade-offs, financial risk, or contested topics.
- `VoIEngine`:
  - `should_stop(turn_entropies: list[float], threshold: float = 0.05) -> bool`:
    - If marginal entropy delta between turns is less than threshold, signals dynamic early-stopping.

#### B. `ai_council/engine/crypto_commit.py`:
- `CommitRevealManager`:
  - `generate_commitment(payload: dict, nonce: str) -> str`:
    - SHA256 of canonical JSON payload + nonce.
  - `verify_reveal(commitment: str, payload: dict, nonce: str) -> bool`:
    - Re-computes SHA256 and validates integrity. Returns False if tampered.

#### C. `ai_council/engine/sandbox_runner.py`:
- `ASTPolicyViolation`: Exception subclass of RuntimeError.
- `ASTSecurityGate(ast.NodeVisitor)`:
  - Validates Python code before execution.
  - Rejects: `Import`/`ImportFrom` of `os`, `sys`, `subprocess`, `socket`, `shutil`, `urllib`, `requests`.
  - Rejects: Calls to `eval`, `exec`, `open`, `compile`, `getattr`, `setattr`.
  - Rejects: Dunder attribute lookups (`__*__`).
- `IsolatedSandboxRunner`:
  - Runs safe code in subprocess with strict timeout (default 5.0s) and memory limits.
  - Invariant: NEVER hold threading locks or mutexes during subprocess execution.

#### D. `ai_council/engine/brier_calibration.py`:
- `BrierRecord`: `seat: str`, `claim_id: str`, `predicted_prob: float`, `outcome: int | None`, `correlation_id: str`.
- `BrierEngine`:
  - `record_forecast(seat: str, claim_id: str, prob: float, correlation_id: str)`
  - `resolve_outcome(claim_id: str, outcome: int)`
  - `compute_brier_score(seat: str) -> float | None`:
    - $BS = \frac{1}{N}\sum (p_i - o_i)^2$. Lower is better (0.0 = perfect calibration).
  - `get_seat_weight(seat: str, beta: float = 2.0) -> float`:
    - Returns calibrated weight $\exp(-\beta \cdot BS)$ if $N \ge 5$ (or smoothed default 1.0).

### 2. Integration with `ai_council/engine/orchestrator.py`:
- Wire `DeliberationRouter`: if `--fast-path` flag is passed or router selects `FAST_PATH`, executes single-pass fast synthesis.
- Wire `CommitRevealManager`: in Turn-0, seats compute commitment hashes before publishing full rationales.
- Wire `ASTSecurityGate` & `IsolatedSandboxRunner`: validates synthesized test templates.
- Wire `BrierEngine`: records forecasts and updates calibration metrics.

### 3. Updates to `ai_council/cli.py`:
- Add flags:
  - `--fast-path`: force fast-path execution.
  - `--brier-status`: print Brier calibration score table for all seats.

### 4. Tests in `tests/test_council_pillars.py`:
- Test `DeliberationRouter` fast-path and deep-path routing.
- Test `CommitRevealManager` commitment generation, reveal verification, and tamper detection.
- Test `ASTSecurityGate` passes clean math/stats code and blocks `os`, `eval`, `subprocess`, and dunder exploits.
- Test `BrierEngine` forecast recording, outcome resolution, and weight calibration.
- Run `/root/kaggle-llm-orchestrator/.venv/bin/pytest tests/` to confirm 100% pass rate.
