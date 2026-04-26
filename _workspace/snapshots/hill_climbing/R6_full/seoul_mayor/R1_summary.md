# Hill-Climbing Round 0 + Round 1 Summary

Generated: 2026-04-26T07:02:34.406962+00:00
Personas: n=10 (seoul)
Wall: 7.3s
Official target (NESDC weighted_v1, intersection-renormalized): 정원오 0.5702 / 오세훈 0.4298

## Variant comparison

| variant | MAE | RMSE | KL(sim‖off) | leader_match | sim leader share | abstain | n_rated |
|---|---:|---:|---:|---|---|---:|---:|
| v4_v2_nesdc_plus_policy | 0.0298 | 0.0298 | 0.0018 | True | c_seoul_dpk 60.0% | 0 | 10 |
| v4_v2_kg | 0.1298 | 0.1298 | 0.0357 | True | c_seoul_dpk 70.0% | 0 | 10 |

## Best variant: **v4_v2_nesdc_plus_policy**
- MAE: 0.0298
- leader_match: True
- sim leader: ('c_seoul_dpk', 0.6)