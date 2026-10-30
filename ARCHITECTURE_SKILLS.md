# AI Council: Full-Spectrum Agent Mastery (BFSMA) Implementation Specification
## Architecture for Codex Autonomous Implementation

### 1. New Directory & Modules: `ai_council/skills/`

#### A. `ai_council/skills/models.py`:
- `Domain`: Enum (`ENGINEERING`, `FINANCE`, `SECURITY`, `ARCHITECTURE`, `RESEARCH`, `GENERAL`).
- `BlastRadius`: Enum (`READ_ONLY`, `WORKSPACE_WRITE`, `ISOLATED_SANDBOX`, `FULL_SYSTEM`).
- `ToolContract`:
  - `name: str`, `domain: Domain`, `blast_radius: BlastRadius`, `timeout_s: float = 10.0`, `read_only: bool = True`.
- `SkillDefinition`:
  - `name: str`, `version: str`, `domain: Domain`, `description: str`, `blast_radius: BlastRadius`, `tools: list[ToolContract]`, `negative_constraints: list[str]`.

#### B. `ai_council/skills/registry.py`:
- `SkillRegistry`:
  - Maintains registered built-in and dynamic skills.
  - `register(skill: SkillDefinition)`
  - `get(name: str) -> SkillDefinition | None`
  - `list_skills(domain: Domain | None = None) -> list[SkillDefinition]`
  - `detect_domain(text: str) -> Domain`: detects inquiry domain based on keywords (e.g. trading/orderbook/funding -> FINANCE; code/ast/refactor/deadlock -> ENGINEERING; injection/vuln/secret/sandbox -> SECURITY; etc.).
  - `resolve_jit(domain: Domain) -> list[SkillDefinition]`: returns skills matching domain.

#### C. `ai_council/skills/harness.py`:
- `PreFlightHarness`:
  - `verify_candidate(candidate_code: str, test_runner_fn = None) -> dict`:
    - Checks regression rate: must be 0.0% against baseline.
    - Security scan: checks for hardcoded secret patterns (e.g. `sk-`, `ghp_`, `AKIA`), prompt injection delimiters (`<|im_start|>`, `[SYSTEM]`, `system:`), and unauthorized system calls.
    - Financial sanity scan (if domain == FINANCE): enforces presence of slippage/fee checks and flags hardcoded unconstrained leverage or missing drawdown limits.
    - Returns `status: 'PASS' | 'FAIL'`, `regression_rate: float`, `violations: list[str]`.

#### D. `ai_council/skills/builtins.py`:
- Pre-registers standard verified domain skills:
  - `SystemsEngineeringSkill`: Domain `ENGINEERING`, blast radius `ISOLATED_SANDBOX`, constraints against holding locks during I/O.
  - `QuantFinanceSkill`: Domain `FINANCE`, blast radius `READ_ONLY`, constraints against curve fitting without walk-forward and missing slippage/fees.
  - `AdversarialSecuritySkill`: Domain `SECURITY`, blast radius `ISOLATED_SANDBOX`, constraints against raw prompt concatenation and secret exposure.

### 2. Integration with `ai_council/engine/orchestrator.py`:
- Add `skill_domain: str | None = None` to `CouncilOrchestrator.deliberate(...)`.
- If `skill_domain` is None, auto-detect domain via `SkillRegistry.detect_domain(topic)`.
- Retrieve active JIT skills and format negative constraints and blast radius into the system instructions for seats.
- If candidate code is evaluated under SEAL, run it through `PreFlightHarness`.

### 3. Updates to `ai_council/cli.py`:
- Add CLI flags:
  - `--skill-domain {auto,engineering,finance,security,architecture,research}`
  - `--list-skills`: prints a clean table/list of registered skills with domain, version, and blast radius.
  - `--preflight`: enforce pre-flight safety & regression checks.
- Render active domain skill badges in terminal output (e.g. `🎯 Active Domain Skill: QuantFinance (v1.0.0 · READ_ONLY)`).

### 4. Test Suite:
- `tests/test_skills.py`:
  - Test domain detection on sample queries.
  - Test SkillRegistry registration, lookup, and JIT resolution.
  - Test PreFlightHarness: passes clean code, rejects code with secrets, rejects prompt injections, enforces financial fee/drawdown constraints.
  - Test orchestrator with domain skills active.
- Verify 100% of all tests pass with `/root/kaggle-llm-orchestrator/.venv/bin/pytest tests/`.
