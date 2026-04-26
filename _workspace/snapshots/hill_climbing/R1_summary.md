# Hill-Climbing Round 0 + Round 1 Summary

Generated: 2026-04-26T06:15:59.391009+00:00
Personas: n=10 (seoul)
Wall: 5.7s
Official target (NESDC weighted_v1, intersection-renormalized): 정원오 0.5702 / 오세훈 0.4298

## Variant comparison

| variant | MAE | RMSE | KL(sim‖off) | leader_match | sim leader share | abstain | n_rated |
|---|---:|---:|---:|---|---|---:|---:|
| v2_2_kg_profile_high_salience | 0.3702 | 0.3702 | 0.2875 | False | c_seoul_ppp 80.0% | 0 | 10 |
| v4_v2_2_nesdc_plus_kg_profile_salient | 0.0702 | 0.0702 | 0.01 | True | c_seoul_dpk 50.0% | 0 | 10 |

## Best variant: **v4_v2_2_nesdc_plus_kg_profile_salient**
- MAE: 0.0702
- leader_match: True
- sim leader: ('c_seoul_dpk', 0.5)