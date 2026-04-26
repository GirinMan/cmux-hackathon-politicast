# Voter Context Audit (read-only, 2026-04-26 14:50 KST)

Author: sim-engineer (Claude)
Trigger: user paradigm shift — 5/5 region 100%-sweep is unacceptable; need prompt enrichment loop.
Status: read-only audit. No fires until enrichment patches land.

---

## 1. Symptoms (what the gate caught)

| region (rated) | sim winner | sim share | official leader | leader_match | MAE |
|---|---|---|---|---|---|
| seoul_mayor | c_seoul_ppp (오세훈) | **100%** | c_seoul_dpk (정원오) | ❌ | 0.5702 |
| busan_buk_gap | c_busan_indep_han (한동훈) | **100%** | c_busan_dpk (하정우) | ❌ | 0.4444 |
| daegu_mayor | c_daegu_ppp_choo (추경호) | **100%** | c_daegu_dpk (김부겸) | ❌ | 0.5052 |
| gwangju_mayor | c_gwangju_dpk | **100%** | (no NESDC) | n/a | n/a |
| daegu_dalseo_gap | c_dalseo_ppp_kim | **100%** | (no NESDC) | n/a | n/a |

- 5/5 regions show **100%-sweep** (one candidate wins ≥99% across **all** age × education × district subgroups in the demographic breakdown).
- Persona pool diversity: across 200 personas in seoul_mayor we see 5 age groups, 7 education levels, 25 districts — and yet 100%/100%/100%/100%/100% break to the same candidate. The ablation evidence is incompatible with persona-driven heterogeneity.
- Trajectory snapshot (seoul, t=0 → t=1): support {dpk:6.3% → 3.0%, ppp:93.7% → 97.0%, rebuild:0% → 0%}. Even t=0 already has 93.7% PPP — the collapse happens **before bandwagon/underdog can amplify**.
- parse_fail_rate = 0%, abstain_rate ≈ 1% — the LLM is producing valid JSON. The model is **answering coherently but answering identically**.

---

## 2. Voter prompt (verbatim, current)

### `system_prompt(self)` — `src/sim/voter_agent.py:238`

```text
당신은 한국 유권자입니다. 아래 페르소나를 1인칭으로 체화하여 답하세요.
- 거주: {province} {district}
- 연령: {age}, 성별: {sex}
- 직업: {occupation}, 학력: {education_level}
- 가족: {marital_status}

=== 서사 ===
{persona_text.persona}
{persona_text.professional_persona}
{persona_text.family_persona}
{persona_text.cultural_background}

=== 규칙 ===
1. 제공된 컨텍스트(이슈·여론조사·이벤트) 외 정보를 사용하지 마세요.
2. 출마를 포기한 후보는 선택할 수 없습니다.
3. 미래 결과를 안다고 가정하지 마세요. 페르소나의 가치관·관심사로만 추론하세요.
4. 반드시 단일 JSON 객체로만 응답합니다 (코드펜스 금지). 스키마: …
```

### `user_prompt(...)` — `src/sim/voter_agent.py:264`

```text
=== {region_label} (timestep t={timestep}) ===
[모드] {mode}
{mode_block}        # poll_response | secret_ballot | virtual_interview

[후보]
- {cand_id} | {name} ({party})         # for each candidate
- ...

[컨텍스트 (t≤{timestep})]
{context_block}    # ← KG retrieval + last poll consensus + gov approval + seed events
```

---

## 3. Diagnosed defects (root-cause list)

### D1. Candidates are nearly identity-only

The candidate block surfaces **only `id | name (party)`**. No `background`, no `key_pledges`, no slogan, no incumbency tag. The scenario JSON (`_workspace/data/scenarios/seoul_mayor.json`) **already has** rich fields per candidate — they are just never injected:

```json
{
  "id": "c_seoul_dpk", "name": "정원오", "party": "p_dem",
  "background": "전 서울 성동구청장(3선). 2026-04-19 박주민·전현희 누르고 본선 후보 확정. 슬로건 '오세훈 무능 심판'.",
  "key_pledges": ["기본사회 서울", "지방행정 실무 경험"]
}
```

To the LLM, the contest is: pick one of `(c_seoul_dpk, 정원오, 더불어민주당)` vs `(c_seoul_ppp, 오세훈, 국민의힘)` vs `(c_seoul_rebuild, 한민수, 조국혁신당)`. With **no policy or biographical signal**, lite-tier Gemini falls back on its strongest prior — name recognition + incumbency + ruling-party-of-2026 — which collapses every voter onto the most-recognized name (오세훈/한동훈/추경호/etc.).

### D2. Persona pool is rich-as-prose but blind-as-politics

`persona_core` columns have **zero direct political fields**. Sample row (seoul, uuid=73f75d…, age=71, occupation=회계 사무원):

```
sex, age, marital_status, military_status, family_type, housing_type,
education_level, bachelors_field, occupation, district, province, country,
persona, cultural_background, skills_and_expertise, hobbies_and_interests,
career_goals_and_ambitions
```

`persona_text` adds: `professional_persona, sports_persona, arts_persona, travel_persona, culinary_persona, family_persona`.

There is **no field** for: party leaning, ideology, key issue priorities, media diet, prior vote history, government-approval sentiment. The Nemotron-Personas-Korea schema does not include these — they are out-of-distribution synthesis prompts that need to be **derived** from the existing fields (e.g., 71세 + 회계 사무원 + 서초구 + 4년제 대학교 → likely PPP-leaning; or 28세 + 환경운동가 + 광주 → likely DPK-leaning), and then **explicitly written into the prompt**.

The `system_prompt` injects the prose persona, but Gemini lite **does not derive politics from prose under JSON-mode + thinking-disabled**. Anecdotally Gemini-3.1-flash-lite without thinking is exactly the model class that "answers the easy question" (recognize the name, ignore the prose).

### D3. KG retrieval injects only events, not entity descriptions

`KGRetriever.subgraph_at(...)` returns **5 bullet lines**, format:
```
- [2026-04-18] (PressConference) 오세훈, 국민의힘 서울시장 후보로 최종 선출 — 정서:긍정(+0.30) / 대상: 오세훈 / 프레임: 현 시정 연속성
- [2026-04-19] (PressConference) 정원오, 민주당 서울시장 후보 확정 ... — 정서:부정(-0.30) / 대상: 정원오 / 프레임: 정권심판
```

Issues:
- Events are **announcement-class only** (PressConference, PollPublication). No biography, no policy, no scandal/verdict (those node classes exist in ontology but no instances seeded).
- "정서:부정(-0.30)" applied to 정원오's "오세훈 무능 심판" announcement is structurally wrong — that's *positive sentiment for 정원오 supporters*, not negative for 정원오. The retriever is reading sentiment **from the event polarity** but the prompt user has no way to know whose side is who.
- The events_used list (from V8c seoul) shows only **5 events total across all timesteps**. That's the entire "Korean 6-month media discourse" the voter sees.

### D4. Rule #1 is a gag order against priors

System prompt rule 1: `"제공된 컨텍스트(이슈·여론조사·이벤트) 외 정보를 사용하지 마세요."`

This **explicitly tells the model to discard its own background knowledge** about Korean elections, party platforms, candidate biographies, ideological geography. Combined with D1+D3 (the context is starvation rations), the model is told "don't use what you know, only use what we give you" — and what we give you is "오세훈 vs 정원오 vs 한민수 (placeholder)".

When forced to guess from name alone, lite-tier collapses on the strongest token recognition. **This rule is the firewall enforcement instrument** (so we don't cheat by giving the LLM future knowledge), but it has no escape valve for *historical* knowledge that is legitimately in-distribution at cutoff_ts.

### D5. Bandwagon poll feedback amplifies the wrong direction

When `last_consensus` exists (t ≥ 1), the prompt appends:
```
[직전 여론조사 합의치]
- 정원오 (p_dem): 여론조사 평균 6.3% (ΔU_poll=-0.13)
- 오세훈 (p_ppp): 여론조사 평균 93.7% (ΔU_poll=+0.19)
- 한민수 (p_rebuild): 여론조사 평균 0.0% (ΔU_poll=-0.20)
```

This is **simulated consensus** (from the voter LLMs themselves), not external/official polls. Once the model has collapsed at t=0, the t=1 prompt now tells voters "오세훈 is at 93.7%, ΔU_poll=+0.19" — bandwagon **rewards the collapse**. The official NESDC poll consensus (정원오 57%, 오세훈 43%) is **never injected into the voter prompt** — it only appears in the post-hoc `_inject_validation_metrics` step.

### D6. No party platform / ideology priors

Scenario JSON has parties with ideology scores: `{"party_id": "p_dem", "ideology": -0.4}, {"party_id": "p_ppp", "ideology": 0.5}, {"party_id": "p_rebuild", "ideology": -0.6}`. None of this lands in the prompt. Even the basic mapping "더불어민주당 = 진보 / 국민의힘 = 보수 / 조국혁신당 = 진보-검찰개혁축" — common-knowledge priors — is **suppressed by Rule 1**.

---

## 4. Enrichment recommendations (priority order)

**P0 — code-path patches (no new data needed)**:

1. **Rewrite candidate block in `user_prompt`** to inject from scenario:
   ```
   [후보]
   - c_seoul_dpk | 정원오 (더불어민주당, 진보)
       배경: 전 서울 성동구청장(3선), 2026-04-19 본선 후보 확정
       핵심공약: 기본사회 서울, 지방행정 실무 경험
       슬로건: 오세훈 무능 심판
   - c_seoul_ppp | 오세훈 (국민의힘, 보수)
       배경: 현 서울시장(재선), 4선 도전
       핵심공약: 현 시정 연속성, 재개발/규제 완화
   ```
   ETA: ~30 LOC change in `voter_agent.py`. Cost: prompt size +~400 tokens × 200 voters × 3 waves = bounded.

2. **Inject party ideology from `scenario.parties`** as a separate `[정당 성향]` block: `더불어민주당 ideology -0.4 (진보), 국민의힘 +0.5 (보수)`. Lets voters anchor without rule-1 gag.

3. **Soften Rule 1 from "context-only" to "future-fact-only"**:
   ```
   1. 미래 사실(예: 선거 결과, 컷오프 이후 사건)은 사용하지 마세요.
      과거 정치 상식(정당 강령, 후보 이력, 지역 성향)은 자유롭게 활용 가능합니다.
   ```
   Keeps the firewall (which kg-engineer's `firewall.py` enforces structurally on KG nodes) without gagging in-distribution priors. **Important**: cutoff_ts must still bind LLM responses; consider adding `[Cutoff: t={cutoff_iso}]` line so the model knows the temporal frame.

4. **Surface persona's plausible political prior heuristics** in system prompt:
   - From age + region + occupation → "60대 서울 강남구 회계 사무원 → 보수 성향 가능성 높음"
   - From education + age → "30대 4년제 대학 졸업 → 진보 성향 가능성 높음"
   - This is currently absent. Could be added as a small `political_prior_hint` field computed by `data-engineer` per persona OR derived inline by a Python heuristic in `voter_agent` from `(age, region, education, occupation)`.
   - **Better but slower**: a one-shot LLM call per persona (cached) that synthesizes a "정치 성향 한 줄" from the prose. ~$0.001 × 1000 personas = $1 one-time cost.

5. **Inject NESDC poll consensus as the t=0 anchor**, not just sim-internal consensus. Rationale: real polls show 정원오 57 vs 오세훈 43 — voters should see *that* as the bandwagon prior at t=0, not the LLM's own 93.7% collapse. Pulled from `poll_consensus_daily` at `cutoff_ts - 1d` (or as_of_date). **This addresses the validation set as the simulator's anchor, exactly what the user's loop premise needs.**

**P1 — KG enrichment (additional data work)**:

6. **More events**: scandal, policy speech, debate excerpt, news article summary nodes. Currently only 5 events in 6-month seoul window. Even a per-candidate `key_pledges` → `Speech` node (timestamped at announcement date) would 3x the visible KG.

7. **Tag-based event filter for persona issue priorities**: voter currently sees top-5 by score; with richer KG, score by issue-overlap with persona occupation/region/concerns.

8. **나무위키/뉴스 wiki-style biography blocks** as `Candidate` node `description` field (data-engineer scope) — KG retriever already has the slot, just needs to inject candidate description on request. P1 because requires new ingestion.

**P2 — methodology**:

9. **Improvement loop**: every iteration N → patch → fire seoul (n=200, T=2, cutoff 4-26) → measure MAE → iterate. Patch budget per iteration ~15 min wall ($0). Accept iteration if MAE drops by ≥10% AND leader_match flips for ≥1 region.

10. **Ablation table**: same patch suite measured against gpt-5.4-nano (prod path) — to verify the lite-tier sweep is not a fundamental simulator failure but a model-tier failure. This requires user GO since it costs OpenAI credits.

---

## 5. Concrete next-step proposal (sim-engineer scope)

**Patch v2.1 (sim-engineer, ~30 min wall, code-only)**:
- `voter_agent.py user_prompt`: inject candidate `background` + `key_pledges` (P0 #1)
- `voter_agent.py user_prompt`: inject `[정당 성향]` from `scenario.parties` (P0 #2)
- `voter_agent.py system_prompt rule 1`: soften to future-fact-only + add `[Cutoff: t]` line (P0 #3)
- `election_env.py _build_context`: add `[공식 NESDC 여론조사 합의 (t={cutoff_date})]` block reading from DuckDB `poll_consensus_daily` at `as_of_date <= cutoff_date - 1` to avoid leakage of the *target* (P0 #5 with leakage guard — anchor on **prior** consensus, not the validation target).

**Stretch: persona political-prior derivation** (P0 #4) — depends on whether user/data-engineer wants per-persona LLM-derived hint vs. lightweight heuristic.

**Excluded from this patch**: KG content enrichment (kg-engineer scope), 나무위키/뉴스 ingestion (data-engineer scope).

After patch, fire seoul_mayor (n=200, T=2, cutoff 4-26) as v2.1 iteration #1. Compare MAE to v2.0 baseline (0.5702). Goal of iteration #1: MAE < 0.40 + leader_match flip in any rated region. Successful → iterate. Stuck → escalate for KG/persona work.

---

## 6. Summary table for paper §5 Limitations

| Failure mode | Evidence | Fix scope |
|---|---|---|
| Candidate identity-only prompt | seoul user_prompt L20–22 has no policy/background | P0 sim-engineer (~5 LOC) |
| Persona blind to politics | persona_core 19 cols, 0 political | P0 inline heuristic OR P1 LLM-derived hint |
| KG event sparsity (5 nodes / 6mo seoul) | kg_events_used has 5 entries total | P1 kg-engineer + data-engineer |
| Rule 1 gags priors | system_prompt L19 explicitly forbids non-context | P0 sim-engineer (rephrase) |
| Bandwagon amplifies sim-internal consensus | poll_trajectory t=0 93.7% PPP → t=1 97% PPP | P0 sim-engineer (anchor on NESDC prior, not sim self-consensus) |
| Lite-tier model collapse | 100% sweep in 5/5 regions; thinking disabled | P2 (try gpt-5.4-nano prod path post-enrichment) |

---

End of audit. Awaiting user GO on patch v2.1 scope.
