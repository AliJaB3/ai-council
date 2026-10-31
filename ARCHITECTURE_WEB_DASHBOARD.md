# AI Council Real-Time Web Dashboard Specification (Decision 1bb044ab)
## Architecture for Codex Autonomous Implementation

### Objective
Implement the complete standalone web dashboard for `ai-council` in `ai_council/web/`:
1. FastAPI ASGI server with REST API & Server-Sent Events (SSE) streaming.
2. Background worker execution decoupling computation from web event-loop.
3. Mobile-first, responsive, Dark Mode single-page dashboard (HTML5/Canvas/SVG) with RTL/Persian support.
4. CLI command `ai-council serve --port 8787` to launch the dashboard.

---

### 1. New Directory & Modules in `ai_council/web/`:

#### A. `ai_council/web/contracts.py`:
- `StreamEvent`: `event_id: str`, `run_id: str`, `seq: int`, `timestamp: float`, `event_type: str`, `payload: dict`.
- `RunSnapshot`: `run_id: str`, `topic: str`, `status: str`, `confidence_score: float`, `duration_s: float`, `created_at: str`, `verdict: dict`, `opinions: list[dict]`, `graph: dict`, `seat_weights: dict`, `experiment_spec: dict | None`.
- `SeatTelemetry`: `role: str`, `title: str`, `avatar: str`, `model: str`, `latency_ms: float`, `brier_score: float | None`, `weight: float`, `status: str`.

#### B. `ai_council/web/server.py`:
- FastAPI application with:
  - CORS and security headers middleware.
  - Endpoints:
    - `GET /`: returns the interactive Single-Page Dashboard HTML.
    - `GET /api/v1/runs`: lists recent runs from SQLite store.
    - `GET /api/v1/runs/{run_id}/snapshot`: returns full atomic snapshot of a run.
    - `GET /api/v1/runs/{run_id}/stream`: SSE endpoint streaming live deliberation events.
    - `POST /api/v1/convene`: accepts `{"topic": str, "deep": bool, "fast_path": bool}`, launches deliberation in background thread/process, and returns `{"run_id": str, "status": "PENDING"}`.
    - `GET /api/v1/search?q={query}`: FTS5 full-text search with Persian normalization.
    - `GET /api/v1/seats/status`: returns telemetry for all 5 seats + Arbiter.
    - `GET /api/v1/workshop/ideas`: returns recent IdeaCards.
    - `POST /api/v1/workshop/run`: triggers a workshop ideation cycle.
    - `GET /api/v1/evomem/status`: returns quarantined/validated memory stats.

#### C. `ai_council/web/static/dashboard.html`:
- Modern, clean, OLED Dark Theme dashboard:
  - Mobile-first responsive layout (collapsible sidebar / tabs on mobile).
  - RTL-native for Persian, with LTR code/math blocks.
  - Tabs:
    1. **🏛️ تالار زنده شورا (Live Chamber):**
       - Input for new deliberation topic + buttons for "مناظره عمیق (Deep)" and "مسیر سریع (Fast)".
       - Real-time progress bar and SSE event log.
       - 5-Seat dynamic status cards with avatars, models, and latency.
       - SVG CEO Graph visualizer (Claims, Evidence, Objections).
       - Arbiter final verdict markdown card with confidence meter.
    2. **📊 تله‌متری صندلی‌ها (Seat Telemetry):**
       - Brier scores table, circuit breaker status, active model checkpoints.
    3. **💡 کارگاه ایده‌سازی (Ideation Workshop):**
       - Interactive IdeaCards with Axiomatic Tier-0 badges, Causal Mechanism, and Falsification tests.
    4. **🔍 جستجو و آرشیو (FTS5 Archive):**
       - High-speed search bar with live filtering and historical decision viewer drawer.
    5. **🧠 مموری و قرنطینه (EvoMem):**
       - Quarantined memories list with promotion buttons.

#### D. CLI Integration (`ai_council/cli.py`):
- Add subcommand / flag:
  - `ai-council serve [--host 0.0.0.0] [--port 8787]`: launches Uvicorn ASGI server.

---

### 2. Tests in `tests/test_web_dashboard.py`:
- Test FastAPI app initialization and routes.
- Test `GET /` returns 200 with dashboard HTML.
- Test `GET /api/v1/runs` and `GET /api/v1/seats/status`.
- Test `POST /api/v1/convene` accepts topic and generates run_id.
- Test FTS5 search endpoint `/api/v1/search?q=...`.
- Run `/root/kaggle-llm-orchestrator/.venv/bin/pytest tests/` to confirm 100% pass rate.
