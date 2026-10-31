# AI Council: Batch 2 Skills Specification
## Technical Runbook for Codex Autonomous Implementation

### Objective
Register the 4 Batch 2 skills and add SHA-256 test-result memoization to `PreFlightHarness`.

### 1. New Skills to Add to `ai_council/skills/builtins.py`:
1. `SystematicRefactoringSkill`:
   - Name: `'SystematicRefactoring'`
   - Version: `'1.0.0'`
   - Domain: `Domain.ENGINEERING`
   - Description: `'Safe AST-based code improvement and dead-code pruning.'`
   - Blast Radius: `BlastRadius.WORKSPACE_WRITE`
   - Negative Constraints:
     - `'Do not alter observable program behavior without explicit intent.'`
     - `'Do not accept refactored code without passing baseline tests.'`

2. `MemoryDistillationSkill`:
   - Name: `'MemoryDistillation'`
   - Version: `'1.0.0'`
   - Domain: `Domain.RESEARCH`
   - Description: `'Hierarchical memory summarization and token economy.'`
   - Blast Radius: `BlastRadius.READ_ONLY`
   - Negative Constraints:
     - `'Do not discard grounded evidence citations during distillation.'`
     - `'Do not invent ungrounded generalizations.'`

3. `ChaosResilienceSkill`:
   - Name: `'ChaosResilience'`
   - Version: `'1.0.0'`
   - Domain: `Domain.ENGINEERING`
   - Description: `'Fault injection and network partition resilience.'`
   - Blast Radius: `BlastRadius.ISOLATED_SANDBOX`
   - Negative Constraints:
     - `'Do not execute destructive chaos tests in production.'`
     - `'Do not leak chaos state across test suites.'`

4. `LiquidityMicrostructureSkill`:
   - Name: `'LiquidityMicrostructure'`
   - Version: `'1.0.0'`
   - Domain: `Domain.FINANCE`
   - Description: `'Order flow imbalance and predatory flow defense.'`
   - Blast Radius: `BlastRadius.READ_ONLY`
   - Negative Constraints:
     - `'Do not ignore order flow imbalance (OFI) signals.'`
     - `'Do not execute market orders during wide bid-ask spread regimes.'`

### 2. Update `builtin_registry()` in `ai_council/skills/builtins.py`:
- Register all 9 skills:
  - `SystemsEngineeringSkill`
  - `QuantFinanceSkill`
  - `AdversarialSecuritySkill`
  - `ProbabilisticRiskSkill`
  - `DialecticConsensusSkill`
  - `SystematicRefactoringSkill`
  - `MemoryDistillationSkill`
  - `ChaosResilienceSkill`
  - `LiquidityMicrostructureSkill`

### 3. Update `ai_council/skills/registry.py`:
- In `detect_domain(text: str)`:
  - Map keywords `'refactor'`, `'clean'`, `'ast'`, `'dead code'`, `'chaos'`, `'resilience'`, `'fault'` to `Domain.ENGINEERING`.
  - Map keywords `'distill'`, `'distillation'`, `'summarize'`, `'compress memory'` to `Domain.RESEARCH`.
  - Map keywords `'microstructure'`, `'orderbook'`, `'ofi'`, `'order flow'`, `'spoofing'` to `Domain.FINANCE`.

### 4. Enhance `PreFlightHarness` in `ai_council/skills/harness.py`:
- Add SHA-256 memoization cache:
  - Hash `candidate_code` (and test parameters if provided).
  - If previously verified and clean, return cached verification result instantly to avoid redundant CPU/test overhead.

### 5. Tests:
- In `tests/test_skills.py`:
  - Assert `len(builtin_registry().list_skills()) == 9`.
  - Verify detection of new domains for refactoring, chaos, distillation, and microstructure.
  - Verify `PreFlightHarness` memoization cache works as expected.
- Run `/root/kaggle-llm-orchestrator/.venv/bin/pytest tests/` to ensure 100% of all tests pass.
