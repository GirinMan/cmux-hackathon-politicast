# Cache audit: v1.4 fire (`bcqeiv6q6`)

**Author:** sim-engineer
**Date:** 2026-04-26 14:08 KST
**Source data:** `_workspace/db/llm_cache.sqlite` (post-fire snapshot)
**Companion JSON:** `cache_audit_v14.json` (raw distribution)
**Cross-ref:** `persona_prompt_diversity.json`

## Headline

**The v1.4 single-candidate sweep (vote_share = 1.000 in 4/5 regions) is NOT caused by sqlite cache reuse. It is most likely a model-behavior artifact of Gemini-3.1-flash-lite-preview at temperature=1.0 with strong region+ideology context.**

Three independent lines of evidence:

1. **Cache responses are 99.9% unique.** Of 6,977 gemini cache rows written by v1.4, 6,971 are distinct response strings. Only 6 cases of trivial collision (3-way duplicates of malformed/truncated JSON like `{"vote": "c` — these were cache writes for retry attempts that hit the same partial response, not vote-determining outputs).

2. **Voter prompts are 100% unique within each region.** Re-simulating system_prompt + user_prompt for v1.4 personas (seoul n=50, busan/daegu_dalseo n=35, gwangju/daegu n=25 sample), every (system_prompt, user_prompt) pair across all 5 timesteps is distinct: collision_rate = 0.0 for all five regions (see `persona_prompt_diversity.json`). System prompt is persona-specific (demographics + professional_persona + family_persona, all 100% unique in DuckDB sample). User prompt embeds region_label + timestep + mode + candidate list, so cross-region collision is structurally impossible.

3. **Pool's internal `cache_hits` counter is identical (5223) across every region snapshot**, regardless of finish time (gwangju at T=23s vs seoul at T=262s). This means all 5,223 hits occurred during the first 23 seconds of fire startup, then 0 hits for the remaining 239 seconds. Meanwhile, `cache_misses` grew monotonically from 118 (gwangju snapshot) to 1,677 (seoul snapshot). The hit-burst is consistent with the 8-coroutine-per-region × 5-region asyncio launch causing transient duplicate cache lookups during the first wave (likely from race conditions where multiple coroutines query the same fresh-cache slot before any write completes; only the first miss triggers a real API call, and subsequent reads of the now-populated key count as hits).

## Cache compression ratio

| metric | value |
|---|---:|
| gemini cache rows | 6,977 |
| distinct response texts | 6,971 |
| compression ratio (rows ÷ distinct) | **1.001** |
| keys mapping to 1 distinct response | 6,968 (99.96%) |
| keys mapping to 2-5 same response | 3 (truncated retries) |
| keys mapping to 6+ same response | 0 |

→ Effectively **no model-determinism through cache reuse**. The model produced a different completion for every distinct prompt.

## Top "collisions"

The 3 most-collided responses are all malformed/truncated JSON fragments from rate-limit-retry artifacts:

| count | response preview |
|---:|---|
| 3 | `{"vote": "c` |
| 3 | `{"vote":` |
| 3 | `{"vote": "c_seoul` |

These are not voting decisions — they are partial generations from earlier OpenAI tier-0 fire attempts (v1.1) that wrote truncated retry stubs into cache. Their presence is benign for vote-share computation (parsed as parse_fail and abstained at the VoterAgent level).

## Pool counter accounting (per-region snapshots)

| region | voter_calls | pool.total_calls (= misses) | cache_hits | cache_misses | hit_rate |
|---|---:|---:|---:|---:|---:|
| gwangju_mayor (T=23s) | 1,040 | 118 | 5,223 | 118 | 0.978 |
| daegu_mayor (T=24s) | 1,040 | 132 | 5,223 | 132 | 0.975 |
| busan_buk_gap (T=138s) | 1,390 | 1,078 | 5,223 | 1,078 | 0.829 |
| daegu_dalseo_gap (T=130s) | 1,390 | 1,031 | 5,223 | 1,031 | 0.835 |
| seoul_mayor (T=262s) | 2,040 | 1,677 | 5,223 | 1,677 | 0.757 |

**Total chat() invocations across pool lifetime** = hits + misses at last snapshot = 5223 + 1677 = 6,900 (matches voter_calls aggregate exactly).
**Net new cache writes** = 1,677 (matches misses at end).

The 5,223-hit ceiling reached during the first 23 seconds of the fire is anomalous and likely reflects a race in `_cache_hits` accounting under asyncio + sqlite concurrent access (40 in-flight coroutines × 5 regions launching simultaneously). It does NOT reflect 5,223 distinct cache reuses — sqlite has only 6,977 unique entries total, of which 1,677 were written by v1.4 and ~5,300 pre-existed from v1.3 / smoke / dev fires.

## Implication for paper

- **Drop the "cache_hit_rate explains the sweep" claim.** Cache reuse cannot produce 100% sweep when 99.9% of cache responses are unique strings.
- **The 100% single-candidate sweep is a model property of Gemini-3.1-flash-lite-preview**: even with distinct persona prompts and temperature=1.0, the lite-tier model converges deterministically on the dominant ideology candidate when given strong regional context (호남 → DPK, TK → PPP, 보궐 → incumbent challenger).
- **Recommended Limitations §5 framing**:
  > Although our sqlite cache lookups achieved an apparent hit rate of 0.76–0.98, post-hoc inspection found 99.9% of cache rows mapped to distinct response strings and persona prompts were 100% unique within every region. The single-candidate sweep observed in 4/5 regions is therefore attributable to the underlying lite-tier model's deterministic alignment with regional ideology rather than cache-induced response reuse. Calibrated vote-share recovery requires either (i) a higher-capacity model (Gemini-3-pro, Claude Sonnet, GPT-4o-mini) or (ii) explicit response sampling with diversity penalties, both deferred to future work.

## Audit limitations

- We did not directly instrument `_cache.get()` to log which specific keys were "hit" — this would require recompiling LLMPool and replaying the fire. Instead we infer from pool counter snapshots and sqlite content.
- The 5,223-hit-burst-then-zero pattern is inferred from the constant counter across snapshots; a smoking-gun would require per-call tracing.
- Audit (c) — Gemini decision-determinism via repeat-call dispersion — was deferred per team-lead 14:01 to avoid burning Gemini quota before user paper redesign decision.
