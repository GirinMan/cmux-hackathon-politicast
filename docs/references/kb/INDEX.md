# PolitiKAST 참고문헌 INDEX

> 4개 카테고리 KB(`academic.md`, `mirofish.md`, `korean-data.md`, `tooling.md`)와 raw 캡처(`docs/references/raw/`)에 대한 마스터 인덱스.
> 작성: 2026-04-26 (해커톤 당일).
> **수집 환경 주의:** 이 호스트는 외부 DNS가 부분/전부 차단되었고 `pandoc`/`pdftotext`/`lynx` 등 변환 도구도 부재했음. 따라서 raw 디렉토리에 들어 있는 파일 중 일부는 fresh 본문 대신 fetch 실패 로그 + codex 사전지식 요약이며, KB 본문도 동일한 fallback에 기댄 항목이 섞여 있음. 실제 인용 단계에서는 paper-writer 에이전트가 각 URL을 다시 검증할 것.

---

## 카테고리별 통계

| 카테고리 | manifest URL | raw 파일 수 | KB 항목 (대략) | KB 내 명시 실패 | KB 링크 |
|---|---:|---:|---:|---:|---|
| 학술 논문 (Academic) | 61 | 61 | 61 | 26 | [academic.md](./academic.md) |
| MiroFish 생태계 | 25 | 50 (+sub-pages) | 24 | ≤4 | [mirofish.md](./mirofish.md) |
| 한국 데이터·뉴스 | 34 | 69 (+sub-pages, 감사 로그) | 26 | 14 | [korean-data.md](./korean-data.md) |
| 도구·프레임워크 (Tooling) | 31 | 30 | 21 | 31* | [tooling.md](./tooling.md) |
| **합계** | **151** | **210** | **132** | **75+** | — |

\* tooling 카테고리는 모든 URL이 fresh fetch에 실패했고, KB는 codex의 사전지식 + 공식 문서 스니펫으로 보강됨. 인용 시 raw 본문 재확인 권장.

raw 파일 슬러그 규칙: `<scheme 제거 + /:?#&=. → -, 60자 truncate>.md`. 모든 raw 파일은 `# Source: <ORIGINAL_URL>` 헤더로 시작.

---

## 카테고리 요약

### [학술 논문 → academic.md](./academic.md)
선거 시뮬레이션 논문(ElectionSim, ABM forecasting, LLM Voting), 정치 스캔들·여론조사 효과(bandwagon/underdog), second-order 지방선거 이론, 한국 선거 분석(split-ticket, valence, strategic voting), 정치 KG 사례, knowledge cutoff/temporal reasoning까지 9개 서브섹션. 논문 elex-kg-final.tex 의 **서론·관련연구·모델·실험** 모든 절에서 인용 후보가 가장 많은 카테고리.

### [MiroFish 생태계 → mirofish.md](./mirofish.md)
MiroFish multi-agent prediction 엔진의 README/DeepWiki/제품 사이트, swarm 패턴 사례, 한국어 리뷰. PolitiKAST의 **차별점 비교 베이스라인**(우리는 KG-augmented + Temporal Firewall + 한국 5 region 풀스펙) 및 **대시보드 UX 참고**용으로 사용.

### [한국 데이터·뉴스 → korean-data.md](./korean-data.md)
중앙선관위·KOSIS·갤럽·리얼미터 공식 데이터, 6.3 지방선거(서울/광주/대구/의왕/보궐) 보도, 후보·정당·정치사건. **데이터 인제션 매핑(DuckDB 테이블/필드)**, **시나리오 시드**, **이벤트 KG 노드**, **결과 검증** 단계의 1차 소스.

### [도구·프레임워크 → tooling.md](./tooling.md)
Nemotron-Personas-Korea(라이센스/스키마/BibTeX), CAMEL multi-agent, Gemini API rate limit·structured output, DuckDB, NetworkX/GraphRAG/Neo4j, FastAPI/React, scipy/sklearn/statsmodels. **VoterAgent / GeminiPool / KG builder / 대시보드** 모듈에 직접 매핑되는 구현 레퍼런스.

---

## PolitiKAST 논문 핵심 인용 후보 (Top 15)

`paper/elex-kg-final.tex` 갱신 시 우선 추가할 BibTeX 후보. 키 이름은 제안값이며, paper-writer가 BibTeX 파일을 모을 때 정식 메타데이터(저자/연도/venue)로 검증해야 함.

| # | 제안 BibTeX key | 제목 (요약) | URL | 인용 위치 |
|---|---|---|---|---|
| 1 | `bhattacharjee2024nemotron` | Nemotron-Personas-Korea: 한국 인구통계 기반 페르소나 데이터셋 | https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea | 데이터 / 실험 (CC BY 4.0 인용 의무) |
| 2 | `li2023camel` | CAMEL: Communicative Agents for Mind Exploration | https://github.com/camel-ai/camel | 모델 / 시스템 |
| 3 | `liu2024electionsim` | ElectionSim: LLM-driven population election simulation | https://arxiv.org/abs/2410.20746 | 관련연구 / 베이스라인 |
| 4 | `yang2024llmvoting` | LLM Voting: Human Choices and AI Collective Decision Making | https://arxiv.org/abs/2402.01766 | 관련연구 |
| 5 | `gergaud2022abmelections` | Forecasting Elections with Agent-Based Modeling (PLOS ONE) | https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0270194 | 관련연구 / 모델 |
| 6 | `barnfield2021bandwagon` | The Bandwagon Effect in an Online Voting Experiment | https://academic.oup.com/ijpor/article/33/2/412/5857291 | 모델 (poll consensus 효과) |
| 7 | `morton2020underdog` | Voting for the Underdog or Jumping on the Bandwagon? | https://www.aeaweb.org/conference/2020/preliminary/paper/i4a3Qy36 | 모델 |
| 8 | `hansen2016polls` | How are Voters Influenced by Opinion Polls? | http://www.kaspermhansen.eu/Work/wps_2016.pdf | 모델 |
| 9 | `garz2019scandals` | Political Scandals, Newspapers, and the Election Cycle | https://www.marcelgarz.com/wp-content/uploads/Political-Scandals-Apr2019-web.pdf | 이벤트 KG / 모델 |
| 10 | `solaz2018scandalmeta` | The Electoral Consequences of Scandals: A Meta-Analysis | https://researchnow.flinders.edu.au/en/publications/the-electoral-consequences-of-scandals-a-meta-analysis/ | 이벤트 KG / 배경 |
| 11 | `reif1980secondorder` | Second-order elections (foundational concept) | https://en.wikipedia.org/wiki/Second-order_election | 배경 (지방선거 동기) |
| 12 | `choi2010strategic` | Institutional Interaction and Strategic Voting in Korea | https://s-space.snu.ac.kr/bitstream/10371/96444/1/7.Institutional-Interaction-and-Strategic-Voting-in-Koreas-New-Mixed-Electoral-System-JungugChoi.pdf | 한국 정치 / 배경 |
| 13 | `splitticket_korea` | Determinants of Split Ticket Voting — Korea | https://scholar.kyobobook.co.kr/article/detail/4010021624486 | 한국 정치 / 모델 |
| 14 | `ukparl_election_ontology` | UK Parliament Election Ontology | (tooling.md 항목) | KG 스키마 |
| 15 | `hagberg2008networkx` | NetworkX: Network Structure & Dynamics in Python | https://networkx.org/documentation/stable/ | 시스템 / 구현 |

추가 후보(상황 따라 16~20위로 승격 가능): Agent-Based Simulation of District-based Elections (arXiv 2205.14400), Scandal Potential (Cambridge), Malk 한국어 법령 KG 멀티에이전트 프레임워크, Rappler 정치 KG 사례, NVIDIA Nemotron Nano 2 (모델 카드).

---

## 다음 단계 (paper-writer 통합 가이드)

1. **BibTeX 파일 정비.** 위 Top 15의 raw 파일을 `docs/references/raw/{academic,tooling}/` 에서 다시 열어 정식 저자/연도/venue 추출 → `paper/elex-kg-final.bib` (또는 동등 파일)에 추가. DNS 차단으로 raw 본문이 비어 있는 항목은 paper-writer가 다른 호스트에서 재확인.
2. **서론/관련연구 보강.** academic.md 의 "Election forecasting / LLM voting / Second-order elections / Korean elections" 섹션을 그대로 단락 시드로 활용. \\cite{liu2024electionsim,yang2024llmvoting,barnfield2021bandwagon,morton2020underdog,reif1980secondorder} 같은 다중 인용을 우선 채워두면 본문 흐름이 빨리 잡힘.
3. **데이터 섹션.** Nemotron-Personas-Korea 인용 의무 문장을 `update-paper` 스킬의 가이드대로 추가. korean-data.md 의 NEC/KOSIS/갤럽 항목을 표 형태로 정리해 5 region 시나리오 시드 출처 명시.
4. **모델 섹션.** CAMEL `ChatAgent`/`RolePlaying` 매핑, GeminiPool capacity 정책, KG temporal firewall 의 근거 인용으로 `garz2019scandals`, `hansen2016polls` 등을 사용.
5. **한계/Discussion.** mirofish.md 의 비교 단락 + tooling.md 의 Gemini rate-limit 주의사항을 인용해 reproducibility/한계 단락에 반영.
