# 05. External Verification Update (2026-04-26)

> Method: Perplexity MCP search, 2026-04-26 KST. Purpose: close or narrow provenance open items from `INDEX.md` §7.

## Findings

### Confirmed / strengthened

- NVIDIA's public Nemotron page describes Nemotron Personas datasets as fully synthetic, privacy-safe personas grounded in demographic, geographic, and cultural distributions. Source: https://developer.nvidia.com/nemotron
- Secondary summaries of the Hugging Face/NVIDIA announcement consistently report `Nemotron-Personas-Korea` as 1M base records expanded to 7M personas, 26 fields, 17 provinces, 2,000+ occupations, CC BY 4.0, generated with NeMo Data Designer plus a PGM statistical grounding layer and Gemma-4-31B Korean narrative generation. Sources:
  - https://theagenttimes.com/articles/nvidia-ships-7-million-synthetic-korean-personas-to-ground-o-5a257af0
  - https://24-ai.news/en/vijest/2026-04-21/nvidia-nemotron-personas-korea-agenti/
- The same secondary summaries attribute source statistics to KOSIS, Supreme Court of Korea, NHIS, KREI, and NAVER Cloud, matching the existing local research notes.

### Still unresolved

- Exact PGM structure remains unspecified. Search results support "Probabilistic Graphical Model / statistical grounding" but do not identify Bayesian network vs. MRF vs. another implementation.
- OCEAN Korean calibration remains unspecified. No source found confirming whether Big-5/OCEAN latent distributions are Korean-calibrated or reused from another locale.
- `military_status` grounding remains unspecified. No source found naming Military Manpower Administration or another direct source.
- The 40+ advertised-field mismatch remains best treated as a public-description vs. released train-split discrepancy. Local schema inspection remains authoritative for this repo: 26 parquet columns, null-free.

## Actionable Doc Position

Use the stronger public claim only for high-level provenance. Keep the three unresolved items in Limitations / Open Items instead of presenting them as confirmed facts.
