# Model Fallbacks, Timeout & Prompt Compaction Specification
## Technical Runbook for Codex Autonomous Implementation

### Objective
Resolve the 3 root causes identified in OmniRoute log analysis:
1. Timeout cutoff (Error 499) on heavy reasoning models (`gpt-6.1-sol`, `nemotron`).
2. Prompt Too Long (Error 502/400) on Cloudflare Playground (max 6000 chars) and UnoRouter free tier.
3. JSON mode rejection (Error 400) on Groq and Cerebras (`json mode cannot be combined with tool/function calling`).
4. Expand reliable fallbacks for each seat using the high-capacity, high-speed Zro, Cerebras, and Codex models.

---

### 1. Updates to `ai_council/config.py`:
- In `SeatConfig`:
  - Change default `timeout: float = 120.0`.
- In `SEATS`:
  - `architect`:
    - model: `'codex/gpt-6.1-sol'`
    - fallbacks: `('codex/gpt-6-astra', 'antigravity/claude-sonnet-4-6', 'zro/deepseek-v4.1-flash', 'zro/glm-5.3-flash')`
    - timeout: `150.0`
  - `quant`:
    - model: `'cerebras/gpt-oss-120b'`
    - fallbacks: `('groq/openai/gpt-oss-120b', 'zro/glm-5.3-flash', 'antigravity/gemini-3.8-flash-high', 'zro/deepseek-v4.1-flash')`
    - timeout: `120.0`
  - `innovator`:
    - model: `'antigravity/claude-sonnet-4-6'`
    - fallbacks: `('zro/glm-5.3-flash', 'openrouter/nvidia/nemotron-3-ultra-550b-a55b:free', 'zro/deepseek-v4.1-flash', 'codex/gpt-6-astra')`
    - timeout: `150.0`
  - `red_team`:
    - model: `'zro/deepseek-v4.1-flash'` (native deep reasoning, 128k context, zero length limits)
    - fallbacks: `('unorouter/deepseek-r1-distill-qwen-32b:free', 'zro/glm-5.3-flash', 'codex/gpt-6.1-sol', 'cloudflare-playground/deepseek-ai/deepseek-r1-distill-qwen-32b')`
    - timeout: `120.0`
  - `implementer`:
    - model: `'zro/glm-5.3-flash'` (fast 128k coding/tool model)
    - fallbacks: `('unorouter/qwen2.5-coder-32b:free', 'mistral/codestral-latest', 'zro/deepseek-v4.1-flash', 'cloudflare-playground/qwen/qwen2.5-coder-32b-instruct')`
    - timeout: `120.0`
- In `ARBITER`:
  - model: `'cerebras/gpt-oss-120b'`
  - fallbacks: `('antigravity/gemini-3.8-flash-high', 'zro/deepseek-v4.1-flash', 'codex/gpt-6.1-sol', 'zro/glm-5.3-flash', 'groq/openai/gpt-oss-120b')`
  - timeout: `180.0`

---

### 2. Updates to `ai_council/seats/base.py`:
- **JSON mode fix:**
  - For models whose provider is `'groq'` (starts with `'groq/'`) or `'cerebras'` (starts with `'cerebras/'`), DO NOT pass `"response_format": {"type": "json_object"}` in the payload. Instead, rely on the system prompt directive: `"Respond with a valid JSON object only."` (the `_json_object` method already strips markdown code blocks and uses regex fallback `\{[\s\S]*\}`).
  - For other models, keep `"response_format": {"type": "json_object"}`.
- **Prompt Too Long fix:**
  - For models with strict character limits (e.g. models starting with `'cloudflare-playground/'` or `'unorouter/'`):
    - If serialized `content` exceeds 5,500 characters, automatically compact it: keep the first 3,800 characters and the last 1,400 characters, separated by `"\n\n[...context compacted to fit provider limits...]\n\n"`. This guarantees the prompt stays below 5,500 chars, completely preventing 502/400 errors.

---

### 3. Verification:
- Run `/root/kaggle-llm-orchestrator/.venv/bin/pytest tests/` to ensure all existing and new tests pass 100%.
