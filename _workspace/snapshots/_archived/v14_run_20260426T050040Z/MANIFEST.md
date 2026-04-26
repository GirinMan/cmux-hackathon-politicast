# v1.4 fire archive

**Archive timestamp (UTC):** 2026-04-26T05:00:40Z (= 2026-04-26 14:00:40 KST)
**Archived by:** sim-engineer per team-lead 14:01 directive (preserve + clear results/ for v2.0)

## Why archived

Per team-lead 13:50, the user is redesigning the paper experimental structure to a validation-first / rolling-origin official-poll gate. v1.4's zero-shot prediction structure no longer matches the planned headline. v2.0 fire will produce new results in `_workspace/snapshots/results/` so this directory was vacated.

## Why preserved

Per team-lead 14:01: "preserve = 영구 보존, archive = 현재 results/ 디렉토리에서 빼서 v2.0 fire가 새로 박제할 자리 만듦, 둘 충돌 아님." These results remain valuable as paper Limitations §5 evidence and as comparison baseline for v2.0.

## Contents

5 region result files + 5 mirror files (10 JSON total) from `bcqeiv6q6` background fire that completed at 2026-04-26T04:38Z.

| file | region | n | T | winner | top vote_share | wall (s) | cache_hit_rate |
|---|---|---:|---:|---|---:|---:|---:|
| seoul_mayor__seoul_mayor_2026.json | seoul_mayor | 400 | 4 | c_seoul_ppp | 0.995 | 262.1 | 0.757 |
| busan_buk_gap__busan_buk_gap_2026.json | busan_buk_gap | 270 | 4 | c_busan_indep_han | 1.000 | 138.0 | 0.829 |
| daegu_dalseo_gap__daegu_dalseo_gap_2026.json | daegu_dalseo_gap | 270 | 4 | c_dalseo_ppp_kim | 1.000 | 129.6 | 0.835 |
| gwangju_mayor__gwangju_mayor_2026.json | gwangju_mayor | 200 | 4 | c_gwangju_dpk | 1.000 | 23.1 | 0.978 |
| daegu_mayor__daegu_mayor_2026.json | daegu_mayor | 200 | 4 | c_daegu_ppp_choo | 1.000 | 23.9 | 0.975 |

Total: 1,340 personas × T=4 = 5,360 voter slots + 200 sonnet interview = 6,900 voter calls. Wall 266 s, $0 (Gemini-3.1-flash-lite-preview dev override).

## Provenance / known artifacts

- **Single-key Gemini round-robin bug** — `actual_keys_used = 1` despite 3 keys configured. See `_workspace/research/llmpool_3key_bug.md`. Operational impact only; correctness unaffected.
- **100% sweep in 4/5 regions** — model behavior, not cache reuse. See `_workspace/research/cache_audit_v14.md` (99.9% unique cache responses, 100% unique persona prompts).
- **`meta.features` missing `virtual_interview`** — cosmetic; interview wave actually ran (40 entries × 5 regions).
- **`policy_version: v1.4_gemini_3key`** — declared 3-key but actually 1-key due to above bug.

## Index status

`_workspace/snapshots/results_index.json` had its 5 `is_mock=false` v1.4 entries removed at archive time so the dashboard's freshest-tier resolution shows mock baselines until v2.0 results land.
