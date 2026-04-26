# `LLMPool` 3-key Gemini round-robin bug

**Author:** sim-engineer
**Date:** 2026-04-26 14:08 KST
**Status:** Diagnosed; fix deferred to v2.0 spec per team-lead 13:50.
**Severity:** Operational (RPM ceiling 1× instead of 3×). No correctness impact.

## Symptom

In the v1.4 fire (`bcqeiv6q6`) all 5 region result snapshots report:

```json
"meta": {
  "actual_keys_used": 1,
  "pool_stats": { "n_keys": 1, "provider": "openai", "model": "gpt-5.4-nano" }
}
```

despite the docker container exposing **3 valid Gemini keys**:

```sh
docker compose run --rm app python -c "import os; print(len(os.environ['GEMINI_API_KEYS'].split(',')))"
# → 3
```

Verified container env (key prefixes): `AIzaSyDT...`, `AIzaSyCG...`, `AIzaSyDy...`.

## Root cause

Two compounding issues in `src/llm/llm_pool.py`:

### 1. Init-time provider mismatch

`LLMPool.__init__` reads `LITELLM_MODEL` env (set in `.env` to `gpt-5.4-nano` for the persona-conditional voter routing) and infers `provider="openai"` via `_derive_provider()`. It then calls `_collect_keys("openai")` → reads `OPENAI_API_KEYS` (1 key) → builds `_states = [_KeyState(api_key=<openai-key>)]`. The 3 Gemini keys are never loaded into `_states`.

This is by-design under the assumption that prod fires use OpenAI, and dev fires use only Gemini overrides. But the dev override path (next section) was incomplete.

### 2. Cross-provider override never round-robins

When `POLITIKAST_ENV=dev`, `LLMPool.chat()` overrides `effective_model` to `DEV_OVERRIDE_MODEL` (Gemini). In `_call_with_retry`, the cross-provider branch:

```python
elif _provider_uses_keys(eff_provider):
    override_keys = self._collect_keys(eff_provider)  # → 3 Gemini keys
    if not override_keys:
        ...raise...
    kwargs["api_key"] = override_keys[0]   # ← BUG: always first key
```

`override_keys[0]` is always selected. There is no rotation counter, no use of `self._next_key()`, and no propagation back into the pool's RPM-tracking `_states` list. All 6,977 v1.4 Gemini API calls used **key 1 of 3**.

The pool's `_next_key()` method does have a working round-robin for same-provider calls (it cycles `self._rr_idx` through `self._states`), but it was bypassed entirely in the cross-provider override branch.

## Quantitative impact

- **RPM ceiling**: capacity v3 measured ~46 RPM single-key. With 3-key round-robin we expected ~138 RPM. v1.4 ran at 1×.
- **Wall time impact for v1.4**: minimal because cache hits dominated. The 1,677 actual API calls completed in 262 s = 6.4 calls/s = 384 RPM peak (well above 46 RPM single-key — Gemini's preview tier appears to be tolerant of short bursts beyond steady-state RPM, so the bug did not cause throttling for this small fire). The bug would have bitten on a clean-cache full-spec fire (~7,000 unique calls).
- **Correctness**: zero. All keys are valid and rotate within the pool would just spread load.

## Two-line fix options

**(A) Operational, zero code change.** Set `LITELLM_MODEL=gemini/gemini-3.1-flash-lite-preview` in `.env`. `LLMPool.__init__` will then infer `provider="gemini"`, load `GEMINI_API_KEYS` (3 keys) into `_states`, and `_next_key()` round-robin works automatically. The dev override becomes a no-op (effective_model already matches init).

  **Trade-off**: prod path (OpenAI nano/mini) needs different `LITELLM_MODEL` per environment, which complicates the .env story.

**(B) Code patch in `_call_with_retry` (5 lines).** Add a counter for cross-provider override:

```python
# init: self._override_rr_idx: dict[str, int] = {}

elif _provider_uses_keys(eff_provider):
    override_keys = self._collect_keys(eff_provider)
    if not override_keys:
        ...raise...
    with self._lock:
        i = self._override_rr_idx.get(eff_provider, 0)
        self._override_rr_idx[eff_provider] = (i + 1) % len(override_keys)
    kwargs["api_key"] = override_keys[i]
```

  **Trade-off**: doesn't update per-key RPM tracking (override path uses pseudo-state), so the pool's RPM throttling is still based on the init provider's `_states`. For Gemini override that means RPM throttling effectively disabled for cross-provider calls — relying on Gemini's server-side rate limiting (which v1.4 evidence suggests is forgiving for bursts).

**(C) Both.** Set `.env LITELLM_MODEL=gemini/...` AND patch (B). Most defensive.

## Recommendation

Per team-lead 13:50, no code changes during user paper redesign window. Apply **(A) only** when the new fire spec lands, since it requires zero code change and unlocks the 3-key headroom immediately. (B) can be added in a follow-up if a same-deployment dev/prod toggle is needed later.

## Related cosmetic bug: `meta.features` missing `virtual_interview`

`election_env._read_features()` defaults to `"bandwagon,underdog,second_order,kg_retrieval"` (4 items). `virtual_interview` is governed by `n_interviews > 0` rather than the feature flag set, so the interview wave **does** run (confirmed by `meta.voter_stats.calls_by_model.sonnet = 40` and 40 entries in `result["virtual_interviews"]` for every v1.4 region). However the published `meta.features` list omits it, which dashboard-engineer's coverage gauge interpreted as "virtual_interview disabled."

**Fix (1 line, deferred to v2.0):** add `virtual_interview` to the `_read_features` default OR have `run_scenario` propagate `policy.json.feature_flags.virtual_interview` into `POLITIKAST_FEATURES` env before constructing the env. No correctness impact; only provenance / dashboard caption.
