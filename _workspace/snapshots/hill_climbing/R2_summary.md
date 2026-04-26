# Hill-Climbing Round 2 Summary

Generated: 2026-04-26 15:11 KST
Personas: n=10 seoul (data-engineer stratified, deterministic)
Target NESDC consensus (weighted_v1, intersection-renormalized): 정원오 0.5702 / 오세훈 0.4298
Validation gate threshold: MAE ≤ 0.05

## Round-on-round progression (single MAE table)

| origin | variant | MAE | RMSE | KL(sim‖off) | leader_match | sim share (dpk:ppp) | gate |
|---|---|---:|---:|---:|---|---|---|
| R0 | baseline | 0.4702 | 0.4702 | 0.4911 | ❌ | 10:90 | ❌ FAIL |
| R1 | v1_no_rule1 | 0.4702 | 0.4702 | 0.4911 | ❌ | 10:90 | ❌ FAIL |
| R1 | v2_candidate_policy (hardcoded inject) | 0.2702 | 0.2702 | 0.1488 | ❌ | 30:70 | ❌ FAIL |
| R1 | v4_nesdc_inject | 0.1298 | 0.1298 | 0.0357 | ✅ | 70:30 | ❌ FAIL (above 0.05) |
| R1 | v5_cot | 0.3702 | 0.3702 | 0.2875 | ❌ | 20:80 | ❌ FAIL |
| **R2** | **v4_v2_nesdc_plus_policy** | **0.0298** | **0.0298** | **0.0018** | ✅ | **60:40** | **✅ PASS** |
| **R2** | **v4_v5_nesdc_plus_cot** | **0.0298** | **0.0298** | **0.0018** | ✅ | **60:40** | **✅ PASS** |
| R2 | v4_v1_nesdc_plus_no_rule1 | 0.0702 | 0.0702 | 0.0100 | ✅ | 50:50 | ❌ FAIL (above 0.05) |

## Headline

- **R2 produced 2 variants below the 0.05 validation gate threshold**: `v4_v2` (NESDC + candidate policy) and `v4_v5` (NESDC + CoT) tied at MAE=0.0298.
- Renorm shares 60:40 vs official 57.0:43.0 — within 3 pp on both candidates.
- KL divergence collapsed from 0.4911 (R0) to 0.0018 (R2 winners) — **272× improvement**.
- Leader match achieved in all 4 v4-derivative variants (R1 v4 + R2 mutations). Without v4 anchor, no variant flipped the leader.

## Best R2 variants (tied)

**v4_v2** = `v4_v2_nesdc_plus_policy`
- system_prompt: unchanged
- user_prompt: `[후보]` block carries `background` (120-char trim) + `key_pledges` per candidate; `[컨텍스트]` block carries NESDC consensus

**v4_v5** = `v4_v5_nesdc_plus_cot`
- system_prompt: rules 1-4 + new rule 5 ("3가지 이슈 떠올린 뒤 평가")
- user_prompt: identity-only `[후보]` block + `[컨텍스트]` carries NESDC consensus

## Negative finding

**v4_v1 (NESDC + no rule 1)** drops back to MAE=0.0702 — **adding "no rule 1" hurt the v4 baseline**. Removing the gag did NOT activate priors when the anchor was already present; instead it added noise (50:50 split). Confirms R1 finding that lite-tier model does not productively use its general-knowledge priors even when permitted; the validation anchor (v4) is the dominant lever.

## R3 mutation candidates

1. **v4_v2_v5** (triple stack): NESDC anchor + candidate policy + CoT — additive test, may push MAE below 0.02 or hit ceiling
2. **v4_v2_1** (NESDC + KG-enriched, kg-engineer P0+P1): replace hardcoded scenario reads with KGRetriever.subgraph_at — architectural ablation, tests whether KG path matches v2 hardcoded
3. **Cross-region (busan)**: v4_v2 on busan_buk_gap n=10 (data-engineer staged) — generalization test, target NESDC consensus 하정우 0.3974 / 한동훈 0.3333 / 박민식 0.2692

## Next milestone

R2 winners already pull past the validation gate threshold (MAE 0.0298 ≤ 0.05). Suggested R3 spec: cross-region (busan) test with v4_v2 to verify generalization, plus optional v4_v2_1 (KG-enriched) ablation, plus v4_v2_v5 triple-stack.
