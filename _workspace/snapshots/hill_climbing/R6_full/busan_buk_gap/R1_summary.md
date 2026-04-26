# Hill-Climbing Round 0 + Round 1 Summary

Generated: 2026-04-26T07:02:44.799946+00:00
Personas: n=10 (seoul)
Wall: 9.7s
Official target (NESDC weighted_v1, intersection-renormalized): 정원오 0.5702 / 오세훈 0.4298

## Variant comparison

| variant | MAE | RMSE | KL(sim‖off) | leader_match | sim leader share | abstain | n_rated |
|---|---:|---:|---:|---|---|---:|---:|
| v4_v2_nesdc_plus_policy | 0.135 | 0.1456 | 0.0855 | True | c_busan_dpk 60.0% | 0 | 10 |
| v4_v2_kg | 0.2684 | 0.3044 | 0.5002 | True | c_busan_dpk 80.0% | 0 | 10 |

## Best variant: **v4_v2_nesdc_plus_policy**
- MAE: 0.135
- leader_match: True
- sim leader: ('c_busan_dpk', 0.6)