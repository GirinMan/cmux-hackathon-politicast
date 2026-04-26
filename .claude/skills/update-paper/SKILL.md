---
name: update-paper
description: PolitiKAST 논문(paper/elex-kg-final.tex) 갱신 — Nemotron-Personas-Korea BibTeX, 5 region 데이터 섹션, KG 스키마 표, Limitations(19+/PGM/gender/leakage), 결과 placeholder 표·그림 슬롯, Reproducibility appendix. paper-writer 에이전트가 Phase 1~4 비동기로 호출. 명시적 논문 작업 요청("논문", "tex", "BibTeX", "결과 채우기", "Limitations") 시에만 트리거.
---

# update-paper

## 트리거 시점
- orchestrator의 Phase 1 시작 신호 (병렬 비동기)
- 명시적 호출 ("논문 갱신", "BibTeX 추가", "결과 표 채워")
- 다른 에이전트의 메트릭 박제 시 (sim-engineer 결과 도착 → 표 placeholder 교체)

## 작업 우선순위

### P0 (Phase 1 완료까지)
1. **Nemotron BibTeX 추가** — README의 `@software{nvidia/Nemotron-Personas-Korea, ...}` 변환 (LaTeX `\bibitem` 형식, `\href` 포함)
2. **데이터 섹션 보강** — 다음 fact box를 Methods§Data에 추가:
   - 1M records / 7M personas / 26 fields / 17 provinces / 252 districts
   - 7 persona text columns: persona, professional, sports, arts, travel, culinary, family
   - 6 attribute fields: cultural_background, skills_and_expertise(_list), hobbies_and_interests(_list), career_goals_and_ambitions
   - 12 demographic fields + 1 uuid
   - **19+ adults only** (선거권 18세와 mismatch — Limitations로)
3. **5 region target table** — region × type × rationale × P0 sample n
4. **Limitations 절 강화** (3개 이상):
   - 19세 미만 부재
   - PGM 합성 → 변수 교호작용 미반영(예: sex × major)
   - Gender(≠ sex) 정보 부재
   - LLM knowledge cutoff vs Temporal Information Firewall — internal prior leakage 가능성
   - Rate-limit 기반 sample size 제약 (capacity probe 결과 인용)

### P1 (Phase 2~3)
5. **KG 섹션 — ontology table** (kg-engineer dataclass → LaTeX table)
6. **결과 placeholder 표·그림 슬롯** — `% TODO: fill` 주석 + 더미 figure box
7. **Reproducibility appendix** — GeminiPool 설정, capacity probe 표, prompt template 발췌

### P2 (시간 남으면)
8. Acknowledgements (BHSN 소속 표기 정비)
9. 추가 BibTeX (CAMEL, ElectionSim, MiroFish, scandal meta-analysis 등)

## LaTeX 스니펫 예시

### Nemotron BibTeX (inline)
```latex
\bibitem{nemotron-personas-korea}
H.~Kim, J.~Ryu, J.~Lee, et~al.,
``Nemotron-Personas-Korea: Synthetic Personas Aligned to Real-World Distributions for Korea,''
NVIDIA, April 2026.
\href{https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea}{huggingface.co/datasets/nvidia/Nemotron-Personas-Korea}.
```

### Data 섹션 fact box
```latex
\paragraph{Synthetic Population.}
We use Nemotron-Personas-Korea~\cite{nemotron-personas-korea} (CC BY 4.0), a synthetic population of \textbf{1M records} with \textbf{7M persona descriptions}, grounded in KOSIS, Supreme Court of Korea, NHIS, and KREI distributions. Each record carries 26 fields: 7 narrative persona fields (concise, professional, sports, arts, travel, culinary, family), 6 attribute fields (cultural background, skills/expertise, hobbies/interests, career goals), and 12 demographic and geographic fields covering 17 provinces and 252 districts. The dataset includes only adults aged 19 and above.
```

### 5 region target table
```latex
\begin{table}[t]
\centering
\caption{Target contests for PolitiKAST hackathon experiments.}
\begin{tabular}{llll}
\toprule
Region & Type & Rationale & Sample n \\
\midrule
서울시장 & Metropolitan mayor & National baseline & % TODO \\
광주시장 & Metropolitan mayor & Progressive-leaning baseline & % TODO \\
대구시장 & Metropolitan mayor & Conservative-leaning baseline & % TODO \\
의왕시장 & Basic mayor & Tight race / hypothetical candidates & % TODO \\
보궐선거 & National Assembly by-election & Issue/scandal effect testing & % TODO \\
\bottomrule
\end{tabular}
\end{table}
```

### Limitations
```latex
\section{Limitations}
\textbf{(L1) Adults-only dataset.} Nemotron-Personas-Korea includes only personas aged 19+, while South Korea's voting age is 18. We exclude first-time young voters, which may attenuate effects driven by the youngest cohort.
\textbf{(L2) Independence assumptions in PGM.} The synthetic dataset assumes independence between demographic factors when assigning detailed occupations (e.g., sex × major interactions are not modeled).
\textbf{(L3) No gender (vs.\ sex) signal.} Korean public statistics do not provide comprehensive gender data distinct from biological sex; our personas inherit this limitation.
\textbf{(L4) Knowledge leakage risk.} Although we enforce a Temporal Information Firewall ($\mathcal{D}_{\le t}$) on retrieved context, the base LLM may internally retain post-cutoff facts about real candidates, parties, and outcomes.
\textbf{(L5) Sample-size constraint by rate limits.} Per-project Gemini preview-tier rate limits (10–50 RPM) bound the persona × timestep budget; we report the capacity probe and the resulting sample sizes per region (Appendix~\ref{app:capacity}).
```

## Downscale 인지
- 결과 섹션은 placeholder 유지 가능 — 실험 미완을 honest disclosure ("Empirical results pending; the framework is fully functional")
- BibTeX 9~12개 핵심으로 컷 가능
- KG ontology 표 → 본문 한 단락 텍스트로 대체

## 산출물 체크리스트
- [ ] `paper/elex-kg-final.tex` 갱신 (단일 파일, 컴파일 가능)
- [ ] 17:00 이후: 발표 outline (`_workspace/snapshots/presentation_outline.md`)
- [ ] `_workspace/snapshots/figures/` (placeholder PDF/PNG, 빌드 시 fallback `\fbox{}`)

## 컴파일 검증
- `cd paper && pdflatex elex-kg-final.tex` 또는 Overleaf 호환
- 컴파일 실패 시 minimal preamble로 폴백 + 오류 메시지 사용자에게

## 17:00 이후 발표 모드
사용자가 "발표 준비"라고 호출하면:
1. dashboard-engineer로부터 페이지별 스크린샷 가이드 수신
2. 5 region 결과 1슬라이드 outline 작성
3. "future work"로 미완 P2 항목 정리
4. 30초 elevator pitch 초안
