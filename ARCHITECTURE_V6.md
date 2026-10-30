# AI Council v6: SEAL & EvoMem Technical Specification
## Unified Architecture for Codex Autonomous Implementation

### Objective
Integrate v6-SEAL (Self-Evolving Autonomous Loop & Sandboxed Execution) and EvoMem (Poisoning-Resistant Continuous Learning Memory) into `ai_council`.

### Architectural Modules:

#### 1. `ai_council/contracts/`:
- `memory_provider.py`:
  - `MemoryProvider` (ABC):
    - `propose(record: MemoryRecord) -> str`
    - `retrieve(query: str, limit: int, tenant_id: str) -> list[MemoryRecord]`
    - `revalidate(record_id: str, is_valid: bool)`
    - `revoke(record_id: str)`
    - `snapshot() -> dict`
  - `NullMemoryProvider`: No-op provider when `--evomem` is disabled.
- `records.py`:
  - `MemoryRecord`: `id`, `schema_version`, `tenant_id`, `session_id`, `content_hash`, `payload`, `provenance`, `evidence_refs`, `drift_score`, `trust_state` (`QUARANTINED`, `VALIDATED`, `REVOKED`, `EXPIRED`), `created_at`, `expires_at`.
  - `ExperimentResult`: `candidate_hash`, `base_revision`, `sandbox_profile`, `metrics`, `verdict` (`PROMOTABLE`, `REJECTED`, `HARD_FAIL`).

#### 2. `ai_council/engine/seal/`:
- `candidate.py`:
  - `CandidateGenerator`: generates structured unified diffs / patches targeted strictly to specified code files. Rejects patches that alter security configs, baseline test suites, or files outside the target workspace.
- `runner.py`:
  - `IsolatedSandboxRunner`: runs tests/code in an isolated workspace with timeout, memory limit, and non-destructive execution. If execution times out or throws unhandled error, returns `status='FAILED'`.
- `evaluator.py`:
  - `RegressionEvaluator`: runs baseline tests against candidates. Rejects candidates if baseline tests fail or regress.

#### 3. `ai_council/engine/evomem/`:
- `quarantine.py`:
  - `QuarantineManager`: all new incoming memories enter `QUARANTINED` status. Can transition to `VALIDATED` only after passing the anti-poisoning filter and DRIFT verification.
- `validator.py`:
  - `MemoryValidator`: validates incoming memories against prompt injection patterns (`<|im_start|>`, `[SYSTEM]`), verifies evidence hashes, and rejects circular citations (memory citing memory without external grounding).
- `replay.py`:
  - `LayeredReplayBuffer`: stratified sampling:
    - 50% Recent experiences
    - 30% Verified Reference decisions
    - 20% Post-mortem failures (negative constraints to avoid repeat mistakes).
- `store.py`:
  - SQLite persistence for EvoMem with thread-safe RLock protection.

#### 4. `ai_council/engine/orchestrator.py`:
- Support feature flags:
  - `enable_seal: bool = False`
  - `enable_evomem: bool = False`
- When `enable_evomem` is True, retrieves validated memory records and provides them as inert context references (`untrusted_memory_evidence`) in the prompt.
- When `enable_seal` is True, allows pre-verdict sandbox validation of code candidates.

#### 5. `ai_council/cli.py`:
- Add CLI flags:
  - `--seal`: enable v6-SEAL candidate testing.
  - `--evomem`: enable EvoMem continuous learning.
  - `--evomem-status`: show memory stats (quarantined, validated, revoked count).
  - `--quarantine-clear`: admin action to purge revoked memories.

#### 6. Tests:
- `tests/test_seal_isolation.py`: tests candidate generation, sandbox execution, and regression evaluation.
- `tests/test_evomem_poisoning.py`: tests quarantine state machine, prompt injection blocking, layered replay buffer, and circular validation prevention.
- Ensure 100% of all tests pass with `/root/kaggle-llm-orchestrator/.venv/bin/pytest`.
