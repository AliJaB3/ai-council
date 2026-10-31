# AI Council v7.1 Production Hardening Specification
## Technical Architecture for Codex Autonomous Implementation (Decision 2c6d952c)

### Objective
Implement the 5 technical hardening phases approved in Decision `2c6d952c`:
1. Deep Sandbox Hardening (RLIMIT resource caps & environment sanitization)
2. Single-Writer SQLite Queue & Persian FTS5 Normalizer
3. Circuit Breaker & Idempotency Outbox Manager
4. Native Zero-Trust MCP Client (JSON-RPC 2.0)
5. Bounded Ring Buffer Event Streaming

### 1. Modules in `ai_council/engine/` & `ai_council/store/`:

#### A. Deep Sandbox Hardening (`ai_council/engine/sandbox_runner.py`):
- `apply_resource_limits(max_memory_mb: int = 512, max_cpu_s: int = 5)`:
  - Uses `resource.setrlimit` on Linux for `RLIMIT_AS` and `RLIMIT_CPU` where supported.
- `sanitize_env() -> dict`:
  - Strips environment variables containing `KEY`, `TOKEN`, `SECRET`, `PASSWORD`, `AUTH`, `PROXY`.
- Updated `IsolatedSandboxRunner.run(...)`:
  - Spawns subprocess with `sanitize_env()`, preexec_fn for resource caps, and guaranteed cleanup.

#### B. SQLite Hardening & Persian Normalization (`ai_council/store/database.py`):
- `normalize_persian(text: str) -> str`:
  - Replaces Arabic 'ي' with 'ی', 'ك' with 'ک'.
  - Removes Arabic tashkeel/diacritics (`[\u064B-\u065F]`).
  - Normalizes zero-width non-joiner (`\u200c` to space).
- `SingleWriterQueue`:
  - Dedicated writer thread/lock ensuring all SQLite write operations (`INSERT`, `UPDATE`, `DELETE`) are processed sequentially through a single thread, preventing `SQLITE_BUSY` errors.
- PRAGMAs:
  - `PRAGMA journal_mode = WAL;`
  - `PRAGMA synchronous = NORMAL;`
  - `PRAGMA busy_timeout = 5000;`

#### C. Network Resilience & Idempotency (`ai_council/engine/resilience.py`):
- `CircuitBreaker`:
  - States: `CLOSED`, `OPEN`, `HALF_OPEN`.
  - Config: `failure_threshold: int = 3`, `recovery_timeout: float = 10.0`.
  - Methods: `record_success()`, `record_failure()`, `can_execute() -> bool`.
- `IdempotencyManager`:
  - `register(idempotency_key: str, payload_hash: str) -> bool`: returns False if duplicate in flight.
  - `complete(idempotency_key: str, result: dict)`
  - `get_cached(idempotency_key: str) -> dict | None`

#### D. Native Zero-Trust MCP Client (`ai_council/engine/mcp_client.py`):
- `MCPTool`: `name: str`, `description: str`, `input_schema: dict`, `is_mutating: bool`.
- `MCPClient`:
  - Implements JSON-RPC 2.0 message parsing (`tools/list`, `tools/call`).
  - Classifies tools: read-only (query/get/read/list/search) vs mutating (set/write/create/delete/exec).
  - Enforces policy: mutating tools require `allow_mutating=True` flag or throw `PermissionError`.

#### E. Bounded Ring Buffer Event Stream (`ai_council/engine/streaming.py`):
- `DeliberationEventStream`:
  - `max_events: int = 1000`
  - Uses `collections.deque(maxlen=max_events)` for bounded memory guarantee.
  - Drops oldest events gracefully when capacity is exceeded without throwing or leaking memory.

### 2. Integration with `ai_council/cli.py`:
- Add CLI flags:
  - `--mcp-server COMMAND`: connect to an external MCP server command.
  - `--circuit-status`: show circuit breaker state.

### 3. Tests in `tests/test_v7_hardening.py`:
- Test Persian text normalizer (unifies 'ی'/'ک', strips diacritics).
- Test SingleWriterQueue processes concurrent writes without lock errors.
- Test CircuitBreaker trips on 3 consecutive failures and recovers on timeout.
- Test IdempotencyManager prevents duplicate actions.
- Test MCPClient classifies read-only vs mutating tools and enforces permission error.
- Test DeliberationEventStream ring buffer does not exceed max_events.
- Run `/root/kaggle-llm-orchestrator/.venv/bin/pytest tests/` to confirm 100% pass rate.
