# Hill-Climbing Round 0 + Round 1 Summary

Generated: 2026-04-26T06:39:07.423139+00:00
Personas: n=10 (seoul)
Wall: 4.1s
Official target (NESDC weighted_v1, intersection-renormalized): 정원오 0.5702 / 오세훈 0.4298

## Variant comparison

| variant | MAE | RMSE | KL(sim‖off) | leader_match | sim leader share | abstain | n_rated |
|---|---:|---:|---:|---|---|---:|---:|
| v4_v2_nesdc_plus_policy | 0.2386 | 0.2654 | 0.3338 | False | c_daegu_ppp_choo 60.0% | 0 | 10 |
| v4_v2_daegu_local | 0.1486 | 0.1596 | 0.1676 | True | c_daegu_dpk 90.0% | 0 | 10 |

## Best variant: **v4_v2_daegu_local**
- MAE: 0.1486
- leader_match: True
- sim leader: ('c_daegu_dpk', 0.9)