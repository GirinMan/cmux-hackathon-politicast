# Hill-Climbing Round 0 + Round 1 Summary

Generated: 2026-04-26T06:33:50.793118+00:00
Personas: n=10 (seoul)
Wall: 11.5s
Official target (NESDC weighted_v1, intersection-renormalized): 정원오 0.5702 / 오세훈 0.4298

## Variant comparison

| variant | MAE | RMSE | KL(sim‖off) | leader_match | sim leader share | abstain | n_rated |
|---|---:|---:|---:|---|---|---:|---:|
| R0 | 0.2872 | 0.305 | 0.4111 | False | c_busan_ppp 70.0% | 0 | 10 |
| v4_nesdc_inject | 0.3538 | 0.3905 | 0.7691 | False | c_busan_ppp 80.0% | 0 | 10 |
| v4_v2_nesdc_plus_policy | 0.135 | 0.1456 | 0.0855 | True | c_busan_dpk 60.0% | 0 | 10 |

## Best variant: **v4_v2_nesdc_plus_policy**
- MAE: 0.135
- leader_match: True
- sim leader: ('c_busan_dpk', 0.6)