# Hill-Climbing Round 0 + Round 1 Summary

Generated: 2026-04-26T06:34:35.794839+00:00
Personas: n=10 (seoul)
Wall: 6.2s
Official target (NESDC weighted_v1, intersection-renormalized): 정원오 0.5702 / 오세훈 0.4298

## Variant comparison

| variant | MAE | RMSE | KL(sim‖off) | leader_match | sim leader share | abstain | n_rated |
|---|---:|---:|---:|---|---|---:|---:|
| R0 | 0.4386 | 0.5074 | 0.9903 | False | c_daegu_ppp_choo 90.0% | 0 | 10 |
| v4_nesdc_inject | 0.3052 | 0.3456 | 0.4988 | False | c_daegu_ppp_choo 70.0% | 0 | 10 |
| v4_v2_nesdc_plus_policy | 0.2386 | 0.2654 | 0.3338 | False | c_daegu_ppp_choo 60.0% | 0 | 10 |

## Best variant: **v4_v2_nesdc_plus_policy**
- MAE: 0.2386
- leader_match: False
- sim leader: ('c_daegu_ppp_choo', 0.6)