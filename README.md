<p align="center">
  <img src="assets/cover.png" alt="PolitiKAST — Agentic Simulation with Korean Political Knowledge Graph" width="900" />
</p>

<h1 align="center">PolitiKAST</h1>

<p align="center">
  <strong>Political Knowledge-Augmented Multi-Agent Simulation of Voter Trajectories for Korean Local Elections</strong>
</p>

<p align="center">
  <a href="paper/elex-kg-final.pdf"><img src="https://img.shields.io/badge/paper-EN%2033p-blue" alt="EN paper" /></a>
  <a href="paper/elex-kg-final-ko.pdf"><img src="https://img.shields.io/badge/paper-KO%2039p-blue" alt="KO paper" /></a>
  <img src="https://img.shields.io/badge/validation-3%2F3%20leader__match%20PASS-brightgreen" alt="validation" />
  <img src="https://img.shields.io/badge/MAE-0.5066%E2%86%920.1782%20(2.84%C3%97)-blue" alt="MAE" />
  <img src="https://img.shields.io/badge/forecast-prediction--only-orange" alt="prediction-only" />
  <img src="https://img.shields.io/badge/track-AI%20Safety%20%26%20Security-red" alt="track" />
</p>

---

## What is PolitiKAST?

PolitiKAST is a **validation-first multi-agent simulation framework** that combines (i) a synthetic Korean voter population, (ii) a temporal political Knowledge Graph (KG), and (iii) LLM-powered voter agents to ask whether a population of LLM voters can **first reproduce held-out official opinion-poll trajectories** before any election-outcome claim is made.

It is built around one safety-oriented commitment:

> **"Forecast" is not a word you get to use until the validation gate passes.**
> Every artifact ships with `prediction-only` labels until simulated vote shares match published, time-aligned NESDC polls under a clean no-cache, no-leak protocol.

Built in 12 hours for the 2026 Korean local elections (5 contested regions: Seoul / Busan Buk-gu A by-election / Daegu / Gwangju / Daegu Dalseo-gu A by-election).

---

## Why this matters (the safety problem)

A frontier LLM, asked "Who will win the 2026 Daegu mayoral election?", will happily produce a confident-sounding number. That number is, in practice, an **unvalidated zero-shot forecast** with no baseline comparison, no leak control, and no separation between calibration and held-out signal.

PolitiKAST reframes the same task as a falsifiable scientific protocol:

| Failure mode | PolitiKAST mechanism |
|---|---|
| Models claim forecasts they have not validated | Hidden-label validation gate; `prediction-only` flag is mechanically required until MAE / leader-agreement gates pass |
| Future poll results leak into earlier prompts | **Temporal Information Firewall**: every KG fact carries a `cutoff_ts`; a voter at time `t` only sees facts with `τ ≤ t`. Self-test 7 / 7 PASS |
| LLMs default to US-English political stereotypes ("young = progressive") | **CohortPrior nodes** (age × gender × region, 15 source-backed priors from Gallup Korea, SisaIN, KStat, RealMeter, Hankyoreh) injected directly into voter prompts |
| Successful runs are publicized while failures vanish | Failed gates, prediction-only regions, and KG narrative gaps are explicitly surfaced in the Streamlit Validation Gate page and in the paper's results table |

---

## Key result (12-hour hackathon snapshot)

Clean no-cache official-poll validation gate, two stages on the three rated regions:

| Region | Stage | MAE | RMSE | leader_match | Verdict |
|---|---|---|---|---|---|
| Seoul mayor | Baseline clean (`n=200`, `T=2`) | 0.5702 | 0.5702 | false | FAIL |
| Seoul mayor | **R6 full (KG A+B)** | **0.3745** | 0.3745 | **true** | FAIL (cohort-prior over-amp at n=200, see Limitations) |
| Busan Buk-gu A | Baseline clean | 0.4444 | 0.4743 | false | FAIL |
| Busan Buk-gu A | **R6 full (KG A+B)** | **0.1062** | 0.1287 | **true** | Borderline (~2.1×) |
| Daegu mayor | Baseline clean | 0.5052 | 0.5886 | false | FAIL |
| Daegu mayor | **R6 full (KG A+B)** | **0.0538** | 0.0700 | **true** | **Near-PASS (1.08×)** without region-specific scenario hardcode |

Mean MAE improved **0.5066 → 0.1782 (2.84× tighter)**, and 100%-sweep regions dropped from 5/5 to 0/3 after Track A (political narrative — PressConference 127 / Source 127 / MediaEvent 96 / damagesParty 84) and Track B (CohortPrior, 20 nodes) enrichment.

Gwangju and Daegu Dalseo-gu A are explicitly marked `target_series=prediction_only` because they lack candidate-level NESDC labels — they are excluded from the gate rather than counted as wins.

---

## Architecture

```
   Nemotron-Personas-Korea (7M)             NESDC official polls (1,487)
              │                                      │
              ▼                                      ▼
   ┌─────────────────────┐               ┌─────────────────────┐
   │  DuckDB persona     │               │ raw_poll +          │
   │  pool (region-aware │               │ raw_poll_result +   │
   │  sampling)          │               │ poll_consensus_daily│
   └─────────┬───────────┘               └──────────┬──────────┘
             │                                      │ (HIDDEN LABEL)
             ▼                                      │
   ┌─────────────────────┐    KG (τ ≤ t)            │
   │ Voter agents        │◀──────────────┐          │
   │ (LLMPool + LiteLLM) │               │          │
   │ persona-conditional │   ┌───────────┴──────┐   │
   │ routing:            │   │ Election +       │   │
   │  • nano = normal    │   │ Discourse        │   │
   │  • mini = educated  │   │ ontology         │   │
   │  • sonnet = interview│  │ + Track A facts  │   │
   └─────────┬───────────┘   │ + Track B cohort │   │
             │               │ priors           │   │
             │               └──────────────────┘   │
             ▼                                      │
   secret-ballot JSON  ────────► vote share ────────┴──► Validation Gate
                                                          (MAE / RMSE /
                                                           leader_match)
```

LLM stack (LiteLLM-routed):

- **dev / cheap**: `gemini-3.1-flash-lite-preview` (no thinking tokens, free)
- **prod voter (normal)**: `gpt-5.4-nano`
- **prod voter (educated, bachelor cutoff)**: `gpt-5.4-mini`
- **interview**: `claude-sonnet-4-6`
- **base**: `LLMPool` (custom 350-line abstraction over LiteLLM); CAMEL is Plan-B optional

---

## Repo layout

```
paper/                 elex-kg-final.{tex,pdf}            # English paper, 33 pages
                       elex-kg-final-ko.{tex,pdf}         # Korean paper, 39 pages
                       elex-kg-final.bib                  # 15 BibTeX entries

src/
  data/                DuckDB ingestion, persona sampler, NESDC scraper
  llm/                 LLMPool, LiteLLM wrapper, capacity probe
  sim/                 VoterAgent, ElectionEnv, run_scenario, poll consensus
  kg/                  Election + Discourse ontology, builder, retriever, firewall

ui/
  dashboard/           Streamlit, 8 pages incl. Validation Gate (page #8)
  eda-explorer/        React + FastAPI BFF: population hex map, KG ontology
                       graph, persona deck, results dashboard

_workspace/
  contracts/           data_paths / api_contract / result_schema / llm_strategy
  data/scenarios/      5 region scenario seeds + historical_outcomes
  data/perplexity/     Source-backed political narrative facts (cutoff ≤ 2026-04-26)
  data/cohort_priors/  CohortPrior(age × gender × region) source-backed priors
  db/                  politikast.duckdb, llm_cache.sqlite
  snapshots/           Run results (vote share, validation metrics, KG exports,
                       hill-climbing R0..R6 lineage)
  validation/          official_poll_validation_targets.md (the contract)
  checkpoints/         capacity_probe.json, policy.json, policy_log.md

output/                Presentation decks (3 .pptx variants)
docker-compose.yml     app + dashboard services
```

---

## Quick start

Requirements: Docker, a Gemini API key (for free dev runs) or OpenAI / Anthropic keys (for prod).

```bash
cp .env.example .env
# Fill in GEMINI_API_KEYS=key1,key2,key3,key4
#         OPENAI_API_KEY=...
#         ANTHROPIC_API_KEY=...

docker compose up -d                                     # app + dashboard

# Reproduce a single-region clean validation run (Seoul, dev / Gemini)
docker compose run --rm \
  -e POLITIKAST_ENV=dev \
  -e POLITIKAST_LLM_CACHE=0 \
  -e POLITIKAST_FINAL_POLL_FEEDBACK=0 \
  app python -m src.sim.run_scenario \
    --region seoul_mayor \
    --sample-n 200 --timesteps 2 \
    --cutoff-ts 2026-04-26T00:00:00+09:00

# Full 5-region prod run (gated by capacity policy)
docker compose run --rm \
  -e POLITIKAST_ENV=prod -e POLITIKAST_CONCURRENCY=2 \
  app python -m src.sim.run_scenario --region all
```

Open dashboards:

- Streamlit (presentation): http://localhost:8501 — page **8 Validation Gate** is the headline screen
- React EDA Explorer: http://localhost:8234 — `/population`, `/ontology`, `/results`, `/personas`

---

## Reproducibility commitments

- Every result JSON in `_workspace/snapshots/results/` carries `meta.official_poll_validation` with `target_series`, `as_of_date`, `method_version`, `cutoff_ts`, `source_poll_ids`, `metrics`, and `by_candidate`.
- Every result JSON also records `meta.llm_cache_enabled`, `meta.final_poll_feedback_enabled`, `meta.effective_model`, `meta.effective_provider`, `meta.wall_seconds`, and per-model voter call counts.
- Every KG fact ingested from `_workspace/data/perplexity/` carries `source_url` and `ts ≤ 2026-04-26`. Hallucinated nodes: 0.
- The **Temporal Information Firewall** has 7 / 7 self-tests passing (synthetic + real cutoff regression at 2026-04-25 and 2026-04-26 23:59:59).
- Hill-climbing lineage (R0 baseline → R6 full) is preserved in `_workspace/snapshots/hill_climbing/` so any prompt-variant claim is auditable.

---

## What this is *not*

- **Not a 2026 election forecast.** The strict MAE gate is not yet cleanly passed by any rated region. Seoul holds leader agreement but misses the strict MAE gate (Limitations §Track B over-amp). Daegu is at 1.08× of the gate.
- **Not a finished social-science instrument.** The base utility term is a stylized age × education × party prior; it has not been fitted to KOSIS / NEC / panel-survey data.
- **Not a substitute for human deliberation.** Synthetic personas + LLM cohort lean estimates cannot represent under-19 voters, fine-grained gender identity, or in-progress candidate disclosures.

These caveats are recorded in the paper's Limitations section, not papered over.

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

If you use the synthetic Korean voter population, please also cite the underlying dataset:

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

## License & attribution

- **Code**: MIT (see `LICENSE` if present, or treat as MIT for the hackathon snapshot).
- **Synthetic personas**: Nemotron-Personas-Korea (NVIDIA), CC BY 4.0. Required attribution is included in the paper.
- **NESDC poll metadata**: scraped from the public Korean National Election Survey Deliberation Commission registry (`여론조사결과 보기`, `pollGubuncd=VT026`) for academic validation use only. Original publishers retain rights.
- **Cohort priors**: aggregate cross-tabs cited from Gallup Korea, SisaIN, KStat, RealMeter, Hankyoreh. Each prior carries its `source_url`.

---

## Author

**Seongjin Lee** — `sjlee@bhsn.ai` / `lsjg9909@hanyang.ac.kr`

Built solo as **Team 기린맨** for a 12-hour hackathon on 2026-04-26. Track: **AI Safety & Security**.
