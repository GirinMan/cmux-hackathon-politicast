# Top-15 참고문헌 본문 검증 리포트

작성일: 2026-04-26
범위: `docs/references/kb/INDEX.md`의 Top 15 후보와 지정 raw 파일 본문

## 요약

Top 15 후보 중 저자/연도/venue 또는 BibTeX key 의미가 KB/INDEX와 어긋나 정정한 항목은 10개다. 본문 메타데이터가 기존 후보와 일치해 확인만 한 항목은 3개(`yang2024llmvoting`, `hansen2016polls`, `garz2019scandals`)다. raw/date 예외 항목은 2개다. `ukparl_election_ontology`는 온톨로지 본문은 충분하지만 발행연도가 없고, `hagberg2008networkx`는 사용자 지시대로 로컬 raw 없이 canonical SciPy 2008 citation을 사용했다. 별도로 `splitticket_korea`는 Kyobo raw에 제목, 연도, venue, 페이지, 초록은 있으나 저자가 노출되지 않아 BibTeX에 manual verification note를 붙였다.

## 주요 불일치

- `bhattacharjee2024nemotron`: raw의 citation은 Bhattacharjee 2024가 아니라 Hyunwoo Kim 외 11인, 2026, Hugging Face dataset card다.
- `camelai2026camel`로 정리돼 있던 tooling KB 항목은 raw citation 기준 `li2023camel`, NeurIPS 2023 논문이다.
- `liu2024electionsim`: 제안 key는 Liu지만 raw 저자는 Xinnong Zhang 외 12인이다. key는 지시대로 유지했다.
- `gergaud2022abmelections`: raw PLOS 논문 저자는 Ming Gao, Zhongyuan Wang, Kai Wang, Chenhui Liu, Shiping Tang이다. Gergaud가 아니다.
- `barnfield2021bandwagon`: raw 실제 논문은 Mike Farjam 단독 저자의 2021 IJpor 논문이다. 지시대로 BibTeX key를 `farjam2021bandwagon`으로 교체했다.
- `morton2020underdog`: raw 실제 paper는 Somdeep Chatterjee, Jai Kamal의 2019년 12월 AEA 2020 preliminary paper다. Morton et al.은 Farjam 논문 내 참고문헌으로만 등장한다.
- `solaz2018scandalmeta`: raw 실제 논문은 Rodrigo Praino, Daniel Stockemer, 2022, Parliamentary Affairs다. Solaz 2018이 아니다.
- `reif1980secondorder`: raw는 Wikipedia 항목이지만, 본문과 참고문헌이 지시한 원전은 Reif & Schmitt 1980 EJPR 논문이다.
- `choi2010strategic`: raw PDF 첫 페이지 기준 Journal of International and Area Studies 13(2), 2006, pp.111-122다. 2010이 아니다. 지시대로 key를 `choi2006strategic`으로 교체했다.
- `splitticket_korea`: raw 본문에서 제목, 신아세아 제14권 제4호, 2007.12, pp.238-261은 확인되지만 저자명이 보이지 않는다. BibTeX에는 manual verification note를 남겼다.
- `ukparl_election_ontology`: raw에는 IRI, license, classes/properties가 확인되지만 발행연도가 없다. BibTeX year는 `n.d.`로 두고 manual verification note를 남겼다.

## PolitiKAST 활용 포인트

| BibTeX key | 논문 내 권장 위치 | 넣을 문장/근거 |
|---|---|---|
| `bhattacharjee2024nemotron` | Data / Persona source | Nemotron-Personas-Korea 설명 문장 끝: `... grounded in South Korean demographic and geographic distributions~\cite{bhattacharjee2024nemotron}.` |
| `li2023camel` | System / Multi-agent harness | CAMEL을 Plan-B 또는 society/workforce layer로 소개하는 문장 끝: `... framework-managed agent societies and tool orchestration~\cite{li2023camel}.` |
| `liu2024electionsim` | Related Work / LLM election simulation | ElectionSim 대비 문장: `ElectionSim demonstrates million-level LLM voter simulation for U.S. presidential scenarios~\cite{liu2024electionsim}, whereas PolitiKAST focuses on Korean local elections with KG-grounded temporal context.` |
| `yang2024llmvoting` | Related Work / LLM voter validity | LLM voter proxy 한계 문장 끝: `... ballot order, persona specification, and temperature can shift LLM collective outcomes~\cite{yang2024llmvoting}.` |
| `gergaud2022abmelections` | Related Work 또는 Model Motivation | ABM 정당화 문장 끝: `Agent-based election forecasting is useful because individual voters are otherwise mostly absent from aggregate forecasting exercises~\cite{gergaud2022abmelections}.` |
| `farjam2021bandwagon` | Model / Poll consensus effect | poll feedback calibration 문장: `We model poll feedback as a bounded bandwagon prior, motivated by online voting evidence that majority options gained additional votes after poll exposure~\cite{farjam2021bandwagon}.` |
| `morton2020underdog` | Model / Poll information shock | underdog scenario 문장 끝: `For multi-phase or repeated-information settings, we allow an underdog response when poll disclosure makes trailing candidates salient~\cite{morton2020underdog}.` |
| `hansen2016polls` | Model / Poll treatment priors | bandwagon 우선순위 문장 끝: `The default prior favors bandwagon over underdog effects because survey-experimental evidence finds consistent bandwagon effects and no underdog evidence~\cite{hansen2016polls}.` |
| `garz2019scandals` | KG / Event shock timing | scandal event edge weighting 문장: `Scandal salience is time-decayed and election-proximity weighted, reflecting evidence that government scandal coverage rises as elections near~\cite{garz2019scandals}.` |
| `solaz2018scandalmeta` | KG / Scandal penalty 또는 Limitations | scandal penalty 문장 끝: `We treat scandal effects as probabilistic penalties because meta-analytic evidence finds vote losses but ambiguous turnout effects~\cite{solaz2018scandalmeta}.` |
| `reif1980secondorder` | Introduction / Korean local-election motivation | 지방선거·보궐선거 framing 문장 끝: `Local and by-elections are modeled as second-order contests with lower turnout and protest-vote incentives~\cite{reif1980secondorder}.` |
| `choi2006strategic` | Korean Political Context / Strategic voting | 한국 혼합선거제 문장 끝: `Korean voters can exhibit strategic voting even when proportional and district ballots coexist~\cite{choi2006strategic}.` |
| `splitticket_korea` | Korean Political Context / Split-ticket behavior | split-ticket prior 문장 끝: `The split-ticket transition prior is justified by evidence that about 20 percent of Korean voters split their district and party-list votes in 2004~\cite{splitticket_korea}.` |
| `ukparl_election_ontology` | KG / Ontology schema | ontology design 문장: `The KG schema reuses election concepts such as election, candidacy, electorate, constituency, party, and result, aligned with public election ontology practice~\cite{ukparl_election_ontology}.` |
| `hagberg2008networkx` | System / KG implementation | NetworkX implementation sentence 끝: `The hackathon KG is compiled into an in-memory NetworkX MultiDiGraph for fast traversal and export~\cite{hagberg2008networkx}.` |

## Paper-writer 권장 작업

`paper/elex-kg-final.tex`는 현재 `thebibliography` 기반이므로, 제출 직전에는 `paper/elex-kg-final.bib`를 실제 빌드에 연결할지 아니면 15개 항목을 `thebibliography`로 옮길지 하나만 결정해야 한다. 우선순위는 데이터/시스템/관련연구/모델 근거를 빠르게 보강하는 것이다. 특히 현재 본문에 이미 등장하는 Nemotron, CAMEL, NetworkX 문장은 새 BibTeX key로 맞추고, 관련연구 단락에는 ElectionSim, LLM Voting, ABM forecasting을 한 문단으로 묶어 PolitiKAST의 차별점인 한국 지방선거, KG grounding, temporal firewall을 바로 대비시키는 편이 가장 효과적이다.
