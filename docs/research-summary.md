# PolitiKAST — Research Summary

> Academic / methodological notes on PolitiKAST. The friendly user-facing
> README lives at the repository root; this page is the place for the
> tighter, validation-first framing that the hackathon paper is written
> against.

<p align="center">
  <a href="../paper/elex-kg-final.pdf"><img src="https://img.shields.io/badge/paper-EN%2033p-blue" alt="EN paper" /></a>
  <a href="../paper/elex-kg-final-ko.pdf"><img src="https://img.shields.io/badge/paper-KO%2039p-blue" alt="KO paper" /></a>
  <img src="https://img.shields.io/badge/validation-3%2F3%20leader__match%20PASS-brightgreen" alt="validation" />
  <img src="https://img.shields.io/badge/MAE-0.5066%E2%86%920.1782%20(2.84%C3%97)-blue" alt="MAE" />
  <img src="https://img.shields.io/badge/forecast-prediction--only-orange" alt="prediction-only" />
  <img src="https://img.shields.io/badge/track-AI%20Safety%20%26%20Security-red" alt="track" />
</p>

---

## What is PolitiKAST?

PolitiKAST is a **validation-first multi-agent simulation framework** that
combines (i) a synthetic Korean voter population, (ii) a temporal political
Knowledge Graph (KG), and (iii) LLM-powered voter agents to ask whether a
population of LLM voters can **first reproduce held-out official opinion-poll
trajectories** before any election-outcome claim is made.

It is built around one safety-oriented commitment:

> **"Forecast" is not a word you get to use until the validation gate
> passes.** Every artifact ships with `prediction-only` labels until
> simulated vote shares match published, time-aligned NESDC polls under a
> clean no-cache, no-leak protocol.

Built in 12 hours for the 2026 Korean local elections (5 contested regions:
Seoul / Busan Buk-gu A by-election / Daegu / Gwangju / Daegu Dalseo-gu A
by-election).

---

## Why this matters (the safety problem)

A frontier LLM, asked "Who will win the 2026 Daegu mayoral election?", will
happily produce a confident-sounding number. That number is, in practice, an
**unvalidated zero-shot forecast** with no baseline comparison, no leak
control, and no separation between calibration and held-out signal.

PolitiKAST reframes the same task as a falsifiable scientific protocol:

| Failure mode | PolitiKAST mechanism |
|---|---|
| Models claim forecasts they have not validated | Hidden-label validation gate; `prediction-only` flag is mechanically required until MAE / leader-agreement gates pass |
| Future poll results leak into earlier prompts | **Temporal Information Firewall**: every KG fact carries a `cutoff_ts`; a voter at time `t` only sees facts with `τ ≤ t`. Self-test 7 / 7 PASS |
| LLMs default to US-English political stereotypes ("young = progressive") | **CohortPrior nodes** (age × gender × region, 15 source-backed priors from Gallup Korea, SisaIN, KStat, RealMeter, Hankyoreh) injected directly into voter prompts |
| Successful runs are publicized while failures vanish | Failed gates, prediction-only regions, and KG narrative gaps are explicitly surfaced in the Streamlit Validation Gate page and in the paper's results table |

---

## Key result (12-hour hackathon snapshot)

Clean no-cache official-poll validation gate, two stages on the three rated
regions:

| Region | Stage | MAE | RMSE | leader_match | Verdict |
|---|---|---|---|---|---|
| Seoul mayor | Baseline clean (`n=200`, `T=2`) | 0.5702 | 0.5702 | false | FAIL |
| Seoul mayor | **R6 full (KG A+B)** | **0.3745** | 0.3745 | **true** | FAIL (cohort-prior over-amp at n=200, see Limitations) |
| Busan Buk-gu A | Baseline clean | 0.4444 | 0.4743 | false | FAIL |
| Busan Buk-gu A | **R6 full (KG A+B)** | **0.1062** | 0.1287 | **true** | Borderline (~2.1×) |
| Daegu mayor | Baseline clean | 0.5052 | 0.5886 | false | FAIL |
| Daegu mayor | **R6 full (KG A+B)** | **0.0538** | 0.0700 | **true** | **Near-PASS (1.08×)** without region-specific scenario hardcode |

Mean MAE improved **0.5066 → 0.1782 (2.84× tighter)**, and 100%-sweep regions
dropped from 5/5 to 0/3 after Track A (political narrative — PressConference
127 / Source 127 / MediaEvent 96 / damagesParty 84) and Track B (CohortPrior,
20 nodes) enrichment.

Gwangju and Daegu Dalseo-gu A are explicitly marked
`target_series=prediction_only` because they lack candidate-level NESDC labels
— they are excluded from the gate rather than counted as wins.

---

## Validation Gate — what passes, what doesn't

The Validation Gate is the hard contract between simulation output and any
claim of "we predict X". Every result JSON in
`_workspace/snapshots/results/` carries
`meta.official_poll_validation` with these fields, and they are surfaced
verbatim on the Validation Gate dashboard page:

| Field | Meaning |
|---|---|
| `target_series` | `validation` (gated) or `prediction_only` (excluded by design) |
| `as_of_date` | Cut-off date of the comparison; never advances past `meta.cutoff_ts` |
| `method_version` | Hill-climbing lineage label (`R0`..`R6`) |
| `cutoff_ts` | KG / persona / prompt cut-off — enforced by the firewall |
| `source_poll_ids` | NESDC poll IDs that contributed to the held-out label |
| `metrics.MAE` / `RMSE` / `leader_match` | Strict gate — fail until the gate is mechanically satisfied |
| `by_candidate` | Per-candidate breakdown so a single-leader near-miss isn't laundered into a region-wide PASS |

The gate is **clean no-cache**: the run that produces these numbers must
disable the LLM cache (`POLITIKAST_LLM_CACHE=0`) and the final-poll feedback
loop (`POLITIKAST_FINAL_POLL_FEEDBACK=0`) so the gate has no opportunity to
peek at its own answer key.

---

## Hill-climbing lineage (R0 → R6)

Every prompt-variant claim is auditable: `_workspace/snapshots/hill_climbing/`
preserves the per-round outputs that produced the table above. The lineage
breadcrumb on each result JSON points back to the generating round so a
reviewer can re-derive any number end-to-end.

| Round | Headline change | Notes |
|---|---|---|
| R0 | Baseline (no KG, no cohort prior) | `n=200`, `T=2`, clean cache |
| R1–R3 | Track A enrichment (political narrative facts) | PressConference / Source / MediaEvent / damagesParty grafted from Perplexity-curated facts (`_workspace/data/perplexity/`) |
| R4–R5 | Track B enrichment (CohortPrior nodes) | 15 source-backed cohort priors covering age × gender × region |
| R6 | Full A+B + retriever upgrades | Final reported run |

---

## Reproducibility commitments

- Every result JSON in `_workspace/snapshots/results/` carries
  `meta.official_poll_validation` with `target_series`, `as_of_date`,
  `method_version`, `cutoff_ts`, `source_poll_ids`, `metrics`, and
  `by_candidate`.
- Every result JSON also records `meta.llm_cache_enabled`,
  `meta.final_poll_feedback_enabled`, `meta.effective_model`,
  `meta.effective_provider`, `meta.wall_seconds`, and per-model voter call
  counts.
- Every KG fact ingested from `_workspace/data/perplexity/` carries
  `source_url` and `ts ≤ 2026-04-26`. Hallucinated nodes: 0.
- The **Temporal Information Firewall** has 7 / 7 self-tests passing
  (synthetic + real cutoff regression at 2026-04-25 and 2026-04-26 23:59:59).
- Hill-climbing lineage (R0 baseline → R6 full) is preserved in
  `_workspace/snapshots/hill_climbing/` so any prompt-variant claim is
  auditable.

---

## What this is *not*

- **Not a 2026 election forecast.** The strict MAE gate is not yet cleanly
  passed by any rated region. Seoul holds leader agreement but misses the
  strict MAE gate (Limitations §Track B over-amp). Daegu is at 1.08× of the
  gate.
- **Not a finished social-science instrument.** The base utility term is a
  stylized age × education × party prior; it has not been fitted to KOSIS /
  NEC / panel-survey data.
- **Not a substitute for human deliberation.** Synthetic personas + LLM
  cohort lean estimates cannot represent under-19 voters, fine-grained
  gender identity, or in-progress candidate disclosures.

These caveats are recorded in the paper's Limitations section, not papered
over.

---

## LLM stack (LiteLLM-routed)

- **dev / cheap**: `gemini-3.1-flash-lite-preview` (no thinking tokens, free)
- **prod voter (normal)**: `gpt-5.4-nano`
- **prod voter (educated, bachelor cutoff)**: `gpt-5.4-mini`
- **interview**: `claude-sonnet-4-6`
- **base**: `LLMPool` (custom 350-line abstraction over LiteLLM); CAMEL is
  Plan-B optional

---

## Citation

```bibtex
@misc{lee2026politikast,
  title  = {PolitiKAST: Political Knowledge-Augmented Multi-Agent Simulation
            of Voter Trajectories for Korean Local Elections},
  author = {Seongjin Lee},
  year   = {2026},
  note   = {12-hour hackathon prototype; arXiv submission in preparation}
}
```

If you use the synthetic Korean voter population, please also cite the
underlying dataset:

```bibtex
@misc{nemotron_personas_korea_2025,
  title        = {Nemotron-Personas-Korea},
  author       = {{NVIDIA}},
  howpublished = {Hugging Face Datasets},
  year         = {2025},
  note         = {CC BY 4.0}
}
```

---

## Author

**Seongjin Lee** — `sjlee@bhsn.ai` / `lsjg9909@hanyang.ac.kr`

Built solo as **Team 기린맨** for a 12-hour hackathon on 2026-04-26. Track:
**AI Safety & Security**.
