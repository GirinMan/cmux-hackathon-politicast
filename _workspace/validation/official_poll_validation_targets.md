# Official Poll Validation Targets

> **Source of truth (post-hackathon):** DuckDB `official_poll` view +
> `election_result` table (`src/data/ground_truth.py`). Validation metrics
> are computed by `src/eval/metrics.py`. This document is a human-readable
> summary; downstream consumers should query the tables / call the loader.

Updated: 2026-04-26 16:12 KST

Purpose: PolitiKAST must validate against official pre-election poll targets before any 2026 local-election forecast is treated as credible. A current-election run without this step is effectively a zero-shot simulation.

## Official Registry

- Primary source: National Election Survey Deliberation Commission (NESDC), "여론조사결과 보기"
  - https://www.nesdc.go.kr/portal/bbs/B0000005/list.do?menuNo=200467
- 2026 local-election filtered query:
  - `pollGubuncd=VT026`
  - `searchTime=3` = survey date
  - `sdate=2025-12-03`, `edate=2026-04-26`
  - https://www.nesdc.go.kr/portal/bbs/B0000005/list.do?menuNo=200467&searchTime=3&sdate=2025-12-03&edate=2026-04-26&pdate=&pollGubuncd=VT026&searchCnd=&searchWrd=&pageIndex=1
- As of 2026-04-26, the filtered list returns 1,487 registered poll records.
- NESDC caveat: registered poll reports are not pre-verified by the commission; treat them as official registered disclosure records, not as truth-certified measurements.

## Date Rules

- Election day: 2026-06-03, 06:00-18:00.
- Six calendar months before election: 2025-12-03.
- Statutory 180-day trigger used by NEC materials: 2025-12-05.
- Poll-result publication blackout: 2026-05-28 through 2026-06-03 18:00, under Public Official Election Act Article 108.

Sources:
- NEC schedule: https://www.nec.go.kr/site/nec/ex/bbs/View.do?cbIdx=1147&bcIdx=298999
- NEC 180-day guidance: https://www.nec.go.kr/site/nec/ex/bbs/View.do?cbIdx=1084&bcIdx=297297
- Public Official Election Act Article 108: https://www.law.go.kr/LSW/lsLawLinkInfo.do?lsJoLnkSeq=900418770&chrClsCd=010202&lsId=001725&print=print

## Initial Direct Validation Labels

| Scope | Fieldwork / publication | Target numbers | Use |
|---|---|---|---|
| Seoul mayor | 2026-04-22 to 2026-04-23 / 2026-04-24 | Jung Won-oh 45.6%, Oh Se-hoon 35.4%; local-election camp choice pro-government 46.6%, anti-government 37.2% | Direct validation label if candidate mapping matches |
| Seoul / Daegu / Busan metro races | April 2026 / 2026-04-13 | Seoul Jung 52 vs Oh 37; Busan Jeon Jae-soo 51 vs Park Hyung-joon 40; Daegu Kim Boo-kyum 53-54 vs conservative alternatives 35-37 | Direct validation if simulated candidate sets match |
| Busan mayor | 2026-04-12 to 2026-04-13 / 2026-04-16 | Jeon Jae-soo 48.0%, Park Hyung-joon 35.2%; JTBC summary Jeon 45%, Park 35% | Direct validation label |
| Daegu mayor | 2026-04-18 to 2026-04-19 / 2026-04-20 | Kim Boo-kyum 45.3%, Lee Jin-sook 17.2%, Choo Kyung-ho 16.2%, Joo Ho-young 7.4%; two-way Kim vs Choo 49.2:35.1, Kim vs Joo 50.1:26.9 | Direct label if candidate alternatives included; otherwise scenario prior |
| Gwangju mayor | 2025-12-27 to 2025-12-29 / 2026-01-01 | Min Hyung-bae 33%, Kang Ki-jung 14%, Jung Jun-ho 6%, Moon In 5%, undecided/none 32% | Prediction-only media-poll prior; not validation |
| Daegu Dalseo-gu A by-election | 2026-04-17 to 2026-04-25 / press reports | Seo Jae-heon announced for conditional Daegu by-election; if Yoo Young-ha vacates Dalseo-gu A, Hong Seong-ju reported as likely PPP replacement. Kim Min-soo remains a non-active parachute-rumor context; Lee Jin-sook is removed from the candidate pool after her Daegu mayoral withdrawal and PPP-nominee support statement. | Prediction-only candidate-field prior; no NESDC target |
| National local-election mood | 2026-01 and 2026-04 Gallup waves | Ruling-party win expectation and party ID series | Macro prior / second-order term calibration |

## Prediction-Only Missing-Target Contract

`gwangju_mayor` and `daegu_dalseo_gap` are now explicitly marked with `prediction_only_assumption.not_for_validation=true` in their scenario JSON. Their media/poll article inputs are source-backed KG priors only. They may be used to run hypothetical one-candidate-per-party simulations, but they must not be used as training labels, held-out validation labels, or evidence of forecast accuracy.

Sources added for this branch:

- Gwangju mayor media poll: https://kjmbc.co.kr/NewsArticle/1498852
- Gwangju corroborating summary: https://www.newsis.com/view/NISX20260101_0003462213
- Daegu by-election Seo Jae-heon announcement: https://www.edaily.co.kr/News/Read?newsId=05336566645417104&mediaCodeNo=257
- Daegu Dalseo/Dalseong conditional by-election field: https://v.daum.net/v/20260423173036753?f=p
- Kim Min-soo parachute-rumor coverage: https://www.kbmaeil.com/article/20260422500671
- Lee Jin-sook Daegu mayoral withdrawal and PPP-nominee support statement: https://www.chosun.com/politics/politics_general/2026/04/25/FK53IBR3X5FNDOT2LQ445P2YDE/

## Clean Validation Status (2026-04-26)

Clean rerun conditions:

- `POLITIKAST_ENV=dev`
- `POLITIKAST_LLM_CACHE=0`
- `POLITIKAST_VALIDATION_CUTOFF_TS=2026-04-26T00:00:00+09:00`
- `sample_n=200`, `timesteps=2`
- All three available clean runs below had `cache_hits=0` and `parse_fail=0`.

| Region | Target series | Source polls | MAE | RMSE | Margin error | Leader match | Status |
|---|---|---|---:|---:|---:|---|---|
| `seoul_mayor` | `poll_consensus_daily` | `nesdc-16198`, `nesdc-16200` | 0.5702 | 0.5702 | 0.8596 | false | FAIL |
| `busan_buk_gap` | `poll_consensus_daily` | `nesdc-16169` | 0.4444 | 0.4743 | 0.9359 | false | FAIL |
| `daegu_mayor` | `poll_consensus_daily` | `nesdc-16158` | 0.5052 | 0.5886 | 0.5650 | false | FAIL |
| `gwangju_mayor` | `prediction_only` | media prior only | null | null | null | null | EXCLUDED |
| `daegu_dalseo_gap` | `prediction_only` | candidate-field prior only | null | null | null | null | EXCLUDED |

Interpretation:

- The current model is not validated for forecasting. In the three available regions, the simulator collapsed to a single candidate at 100% vote share while the official poll consensus showed competitive or opposite leadership.
- Because `cache_hits=0` and `parse_fail=0`, the failure should be treated as behavioral/calibration failure, not cache contamination or parser failure.
- Root cause follow-up found that final ballot and virtual interview prompts were consuming the previous simulated wave as if it were poll context. The simulator now records `meta.final_poll_feedback_enabled`; default `POLITIKAST_FINAL_POLL_FEEDBACK=0` omits endogenous simulated-poll feedback from final ballot/interview prompts while preserving an opt-in ablation path.
- `gwangju_mayor` has local `raw_poll` metadata but no candidate-level `raw_poll_result` rows mapped into `poll_consensus_daily`; it cannot enter the gate until candidate names are mapped to scenario candidate IDs.
- `daegu_dalseo_gap` has no local official candidate-level target in the current NESDC ingestion; keep it unavailable rather than fabricating a validation label from party ID, mayoral, or district-office polls.

Artifacts:

- Seoul/Busan clean run log: `_workspace/snapshots/v10_clean_consensus_run.log`
- Daegu clean run log: `_workspace/snapshots/v11_daegu_clean_consensus_run.log`
- Clean result JSONs:
  - `_workspace/snapshots/results/seoul_mayor__seoul_mayor_2026.json`
  - `_workspace/snapshots/results/busan_buk_gap__busan_buk_gap_2026.json`
  - `_workspace/snapshots/results/daegu_mayor__daegu_mayor_2026.json`

## Integration Contract

Use existing DuckDB contract table names:

```sql
raw_poll(
  poll_id text primary key,
  contest_id text not null,
  region_id text not null,
  field_start date,
  field_end date,
  publish_ts timestamp,
  pollster text,
  sponsor text,
  source_url text,
  mode text,
  sample_size integer,
  population text,
  margin_error float,
  quality float,
  is_placeholder boolean default false
);

raw_poll_result(
  poll_id text,
  candidate_id text,
  share float,
  undecided_share float,
  primary key (poll_id, candidate_id)
);

poll_consensus_daily(
  contest_id text,
  region_id text,
  as_of_date date,
  candidate_id text,
  p_hat float,
  variance float,
  n_polls integer,
  method_version text,
  source_poll_ids text,
  primary key (contest_id, region_id, as_of_date, candidate_id)
);
```

Result JSON extension:

```json
"official_poll_validation": {
  "target_series": "poll_consensus_daily",
  "as_of_date": "YYYY-MM-DD",
  "method_version": "weighted_v1",
  "cutoff_ts": "YYYY-MM-DDTHH:MM:SS+09:00",
  "source_poll_ids": ["nesdc-..."],
  "metrics": {
    "mae": 0.0,
    "rmse": 0.0,
    "margin_error": 0.0,
    "leader_match": false
  },
  "by_candidate": {
    "candidate_id": {
      "simulated_share": 0.0,
      "official_consensus": 0.0,
      "error": 0.0
    }
  }
}
```
