# MiroFish 생태계 KB

수집 주석: 현재 실행 환경에서는 외부 DNS가 막혀 manifest 전체에 대한 fresh `curl` fetch가 실패했다. `docs/references/raw/mirofish/`에는 요청한 slug 규칙의 canonical markdown 파일을 생성했으며, 본 KB는 같은 URL의 기존 raw capture를 fallback 원문으로 사용해 정리했다. 실제 본문이 확보되지 않은 URL은 마지막 접근 실패 목록에만 모았다.

## 미로피쉬 본 사이트 / 회사 소개

**MiroFish 공식 GitHub README**
URL: https://github.com/666ghj/MiroFish

MiroFish는 "A Simple and Universal Swarm Intelligence Engine, Predicting Anything"을 표방하는 오픈소스 멀티 에이전트 예측 엔진이다. 뉴스, 정책 초안, 금융 신호, 분석 리포트, 소설 같은 seed 자료를 입력하면 GraphRAG 기반 지식 구조와 에이전트 환경을 만들고, 다수의 에이전트가 소셜 플랫폼형 공간에서 상호작용한 뒤 예측 리포트를 생성하는 흐름을 제시한다.

공식 README의 워크플로우는 Graph Building, Environment Setup, Simulation, Report Generation, Deep Interaction의 5단계다. 런타임은 Node/Vue 프론트엔드, Python/Flask 백엔드, OpenAI SDK 호환 LLM API, Zep Cloud 장기 기억, CAMEL-AI OASIS 시뮬레이션 엔진 조합으로 설명된다.

PolitiKAST 활용 포인트: PolitiKAST 논문/대시보드에서 "범용 seed 기반 사회 시뮬레이션" 비교 베이스라인으로 사용한다. 특히 5단계 파이프라인을 한국 선거 특화 KG, voter trajectory, 투표 집계 레이어로 치환하는 차별화 설명에 적합하다.

**DeepWiki MiroFish Architecture Digest**
URL: https://deepwiki.com/666ghj/MiroFish

DeepWiki는 MiroFish의 구조를 압축적으로 설명한다. Vue 3/Vite/D3/Tailwind 프론트엔드, Flask REST API 백엔드, OASIS 시뮬레이션, Zep Cloud memory, OpenAI-compatible LLM orchestration으로 구성된 split architecture를 정리한다.

5단계 lifecycle도 공식 README와 유사하게 정리되어 있으며, seed material에서 엔티티/관계를 뽑아 GraphRAG KG를 만들고, Twitter/Reddit형 플랫폼에서 멀티 에이전트 상호작용을 실행한 뒤 ReportAgent가 예측 리포트를 만든다고 설명한다.

PolitiKAST 활용 포인트: 엔진 아키텍처 비교표의 근거로 사용한다. PolitiKAST의 `src/data`, `src/llm`, `src/sim`, `src/kg`, Streamlit dashboard 구조를 MiroFish의 frontend/backend/simulation/memory layer와 나란히 보여줄 수 있다.

**MiroFish Product Site**
URL: https://mirofish.my

본 사이트는 "Upload Any Report. Simulate The Future Instantly."라는 제품 메시지를 앞세운다. 문서, 리포트, 정책 초안, 소설 등을 평행 세계로 바꾸고, 기억과 동기와 사회적 행동을 가진 에이전트가 Twitter/Reddit 스타일 환경에서 상호작용한다는 제품 claim을 제공한다.

사이트는 1M+ parallel agents per run, 변수 주입, trajectory inspection, prediction report, ReportAgent/agent 인터뷰 같은 데모 관점을 강조한다. 다만 1M+ scale은 재현 가능한 벤치마크라기보다 제품/마케팅 주장으로 취급하는 것이 안전하다.

PolitiKAST 활용 포인트: 대시보드 시연에서 "MiroFish식 product claim"과 PolitiKAST의 검증 가능한 run artifact, DuckDB snapshot, 지역별 선거 시뮬레이션을 대비시키는 자료로 쓴다.

**GitHub Releases**
URL: https://github.com/666ghj/MiroFish/releases

release 페이지는 MiroFish의 초기 버전 상태와 배포 성숙도를 확인하는 자료다. raw capture 기준 v0.1.2 등 초기 release 맥락이 확인되며, 공식 README의 기능 설명이 실제 배포 주기와 얼마나 맞물리는지 판단하는 보조 근거가 된다.

기술 논문 인용의 핵심 근거로 쓰기보다는, "활발하게 공개된 초기 오픈소스 프로젝트"라는 생태계 상태를 보여주는 자료에 가깝다.

PolitiKAST 활용 포인트: 발표에서 MiroFish를 완성 제품이 아니라 빠르게 확산된 오픈소스 실험으로 위치시키고, PolitiKAST도 해커톤 산출물이므로 run freeze와 reproducibility를 명시한다는 설명에 활용한다.

## 정치 시뮬레이션 / 선거 시나리오

**GitHub Discussions Polls Category**
URL: https://github.com/666ghj/MiroFish/discussions/categories/polls

GitHub Discussions의 Polls category는 MiroFish 커뮤니티가 예측/투표형 사용 사례를 논의하는 표면 자료다. 정적 raw capture에서는 구체적인 poll 본문까지 충분히 확보되지는 않았지만, MiroFish가 단순 코드 저장소를 넘어 커뮤니티 예측 실험을 유도한다는 정황으로 볼 수 있다.

선거 예측 자체의 검증 근거로 쓰기에는 약하다. 대신 예측 엔진이 사용자 참여형 poll/discussion과 결합될 수 있다는 UX/커뮤니티 패턴을 보여준다.

PolitiKAST 활용 포인트: PolitiKAST dashboard에 region별 scenario poll, 후보 이벤트 shock 선택, run comparison voting 같은 데모 요소를 넣을 때 참고한다.

**Dev.to Review: MiroFish Builds Digital Worlds**
URL: https://dev.to/arshtechpro/mirofish-the-open-source-ai-engine-that-builds-digital-worlds-to-predict-the-future-ki8

이 리뷰는 MiroFish를 "digital worlds"를 만들어 미래 경로를 실험하는 오픈소스 엔진으로 소개한다. OASIS scale, social actions, GraphRAG 기반 grounding, multi-agent report generation 같은 장점을 설명하면서도 공개 accuracy benchmark 부족과 herd behavior bias를 함께 언급한다.

정치 시뮬레이션 관점에서는 한 번의 LLM 예측이 아니라 여러 에이전트의 상호작용을 통해 경로를 관찰한다는 점이 핵심이다. 그러나 결과를 확률 예측으로 과대해석하지 말고 scenario exploration으로 해석해야 한다는 경고도 중요하다.

PolitiKAST 활용 포인트: "선거 결과 맞히기"보다 "지역/세대/이슈별 voter trajectory stress test"로 PolitiKAST 목적을 설명할 때 비교 베이스라인으로 사용한다.

**Beitroot: Open-Source Swarm Intelligence Engine**
URL: https://www.beitroot.co/blog/mirofish-open-source-swarm-intelligence-engine

Beitroot 글은 MiroFish를 business/architecture 관점에서 해석한다. seed material ingestion, knowledge graph, persona generation, social interaction, report generation이라는 큰 흐름과 함께 운영 비용, model call 수, production readiness 같은 현실적인 부담을 다룬다.

특히 run size가 커질수록 LLM 비용과 rate limit이 병목이 된다는 점은 PolitiKAST 해커톤 환경과 직접 맞닿아 있다. 1M agent claim보다 capacity probe와 downscale policy가 더 중요하다는 논리를 뒷받침한다.

PolitiKAST 활용 포인트: `capacity_probe.json`, `policy.json`, downscale mode를 논문/발표에서 설명할 때 "대규모 agent simulation은 비용/처리량 제약을 먼저 측정해야 한다"는 근거로 쓴다.

**My Weird Prompts: Agent Simulation Limits**
URL: https://www.myweirdprompts.com/episode/mirofish-agent-simulation-limits/

이 글은 MiroFish의 5단계 구조를 설명하면서도 persona collapse, herd-behavior bias, 시뮬레이션 결과의 과도한 확률 해석 위험을 강조한다. 에이전트들이 장기 라운드에서 서로 비슷한 의견으로 수렴하거나 실제 사람보다 더 순응적으로 행동할 수 있다는 지적이 핵심이다.

정치/선거 시뮬레이션에서는 이 한계가 치명적이다. 유권자 모델은 확신층, 부동층, 무관심층, 전략적 투표자, 비응답자, 투표 포기자를 구분해야 하며, 공개 발화와 실제 투표 선택도 분리해야 한다.

PolitiKAST 활용 포인트: 논문의 limitations와 dashboard의 confidence/uncertainty 표시 설계에 사용한다. 특히 turnout uncertainty, non-response, contrarian voter, 지역별 이질성을 명시하는 근거로 적합하다.

**Velog MiroFish 정리: 현실을 시뮬레이션하는 AI 예측 엔진**
URL: https://velog.io/@okorion/MiroFish-정리-멀티-에이전트로-현실을-시뮬레이션하는-AI-예측-엔진-6gbmig5n

한국어로 MiroFish의 핵심 아이디어를 설명하는 요약 글이다. 단일 LLM에게 정답을 묻는 방식이 아니라, 가능한 사회적 전개를 멀티 에이전트 환경에서 리허설하고 그 결과를 분석한다는 메시지가 이해하기 쉽다.

한국어 발표 자료나 README에서 "왜 단일 프롬프트 예측이 아니라 agent simulation인가"를 설명할 때 유용하다. 다만 기술적 세부 수치나 벤치마크 근거로는 공식 자료보다 낮은 우선순위로 둔다.

PolitiKAST 활용 포인트: 발표 도입부에서 PolitiKAST를 "한국 지방선거 경로를 리허설하는 voter simulation"으로 설명하는 문장에 참고한다.

**Judy AI Lab: MiroFish 멀티 에이전트 예측**
URL: https://judyailab.com/ko/posts/mirofish-multi-agent-prediction/

Judy AI Lab 글은 MiroFish의 개념과 기술 스택을 한국어로 풀어 설명한다. GraphRAG, OASIS, Zep memory, ReportAgent 등 구성요소를 비전문가에게 설명하기 좋은 자료이며, 비용과 편향, simulation과 reality의 차이도 언급한다.

한국어 독자를 대상으로 MiroFish와 PolitiKAST의 차이를 설명할 때 특히 유용하다. PolitiKAST는 범용 social world보다 한국 선거 제도, 후보/정당/지역 이슈, 여론조사 메타데이터의 grounding을 강조해야 한다.

PolitiKAST 활용 포인트: 한국어 발표 준비, 논문 supplementary note, Streamlit sidebar의 "비교 대상: MiroFish" 설명에 활용한다.

## 후보자 / 인물 분석

**GitHub Issue #421: Production Readiness / Feature Ideas**
URL: https://github.com/666ghj/MiroFish/issues/421

Issue #421은 MiroFish를 production-ready하게 만들기 위한 개선점과 위험을 다룬다. async execution, auth/input validation, filesystem IPC, AGPL exposure 같은 엔지니어링 이슈와 함께 posting style, active hours, stance, opinion drift, influence weight 같은 persona 다양성 anchor가 언급된다.

후보자/인물 분석 관점에서는 이 persona anchor를 유권자뿐 아니라 후보/캠프/미디어 행위자 모델로 번역할 수 있다. 후보의 공약, 리스크, 지역 기반, 노출 이벤트가 agent state와 어떻게 상호작용하는지 설계하는 데 실마리를 준다.

PolitiKAST 활용 포인트: candidate/campaign actor schema, voter archetype, issue salience, opinion drift parameter를 설계할 때 참고한다. 대시보드에는 후보별 shock/event 카드와 영향 추적 UI로 연결할 수 있다.

**Amadad MiroFish Fork**
URL: https://github.com/amadad/mirofish

amadad fork는 CLI 중심의 영어권 변형으로, run artifact를 JSON/Markdown/SVG 형태로 고정 저장하는 구조가 raw capture에 정리되어 있다. 원본 MiroFish보다 연구 재현성, batch run, artifact review 관점에서 참고하기 쉽다.

후보자/인물 분석에서는 후보별 narrative, timeline, social graph, simulation log, final report를 run directory에 함께 저장하는 패턴이 중요하다. 후보별 설명을 대시보드에서 다시 열람하려면 artifact naming과 schema가 안정적이어야 한다.

PolitiKAST 활용 포인트: `_workspace/snapshots/`와 region별 run directory 설계의 비교 베이스라인으로 쓴다. 후보/지역별 simulation output을 발표 직전에 빠르게 검토하는 운영 구조에 참고한다.

**LinkedIn: Anmol Gupta MiroFish Adaptation**
URL: https://www.linkedin.com/posts/anmol-gupta-21875a89_mirofish-simulates-1-million-ai-agents-to-activity-7451591386610540544-a3Uh

LinkedIn 게시물은 MiroFish의 1M agent/elections/markets claim을 바탕으로 audience simulation 또는 decision support tool로 응용하는 커뮤니티 반응을 보여준다. 원문은 MiroFish를 선거, 시장, 캠페인 반응 예측에 쓸 수 있는 도구로 해석한다.

공식 기술 근거라기보다 생태계 반응과 응용 방향을 보여주는 자료다. 후보자/캠페인 분석 시 "audience simulation"이라는 제품 언어가 어떻게 소비되는지 확인할 수 있다.

PolitiKAST 활용 포인트: 후보 캠페인 메시지 A/B scenario, 지역별 audience reaction dashboard, 발표용 demo narrative에 참고한다.

**LinkedIn: Zhuohan Yu MiroFish Reception**
URL: https://www.linkedin.com/posts/zhuohan-yu-a689488b_github-666ghjmirofish-a-simple-and-universal-activity-7437527515876933632-gh5o

이 LinkedIn 게시물은 GitHub MiroFish를 OASIS, GraphRAG, OpenAI-compatible LLM API 기반의 범용 예측 엔진으로 소개하는 커뮤니티 반응이다. investment/product launch use case와 함께 다수 에이전트가 사회적 반응을 시뮬레이션한다는 메시지를 강조한다.

인물 분석 관점에서는 후보나 캠페인을 "제품 출시"처럼 다루는 비유를 조심해서 차용할 수 있다. 후보 메시지를 seed로 넣고 유권자 집단 반응을 관찰하는 구조는 유사하지만, 선거는 제도/지역/투표율 제약이 강하다.

PolitiKAST 활용 포인트: 후보 메시지와 정책 발표 이벤트를 seed/shock으로 넣는 시나리오 설계에 참고하되, 선거 제약과 투표 비밀성을 PolitiKAST 차별점으로 강조한다.

## 한국 정치 데이터 / 여론조사 통합

**Kivoloid Notion: 여론조사 기초 참고자료**
URL: https://kivoloid.notion.site/194512210ea78000bdfed50cc0e95f76

이 자료는 MiroFish 직접 자료는 아니지만 한국 여론조사 해석에 필요한 기본 개념을 정리한 참고자료다. 표본오차, 신뢰수준, 조사방법, 여론조사 메타데이터를 결과 해석과 분리해서 다뤄야 한다는 점이 중요하다.

PolitiKAST가 단순 agent vote share만 출력하면 실제 한국 선거/여론조사 맥락과 연결이 약하다. 조사기관, 조사기간, 표본, 조사방법, 가중 방식 같은 메타데이터를 별도 layer로 두고 simulation 결과와 비교해야 한다.

PolitiKAST 활용 포인트: polling consensus layer, dashboard의 poll metadata table, 논문 validation protocol에 활용한다.

**Hacker News Korea: Ontology / RAG Discussion**
URL: https://news.hada.io/topic?id=28044

Hada News 자료는 MiroFish 직접 자료는 아니지만 RAG와 ontology의 차이를 설명하는 데 유용하다. 단순 문서 검색이 아니라 엔티티, 관계, 제약, 개념 구조를 명시하는 것이 왜 필요한지 보여주는 배경 자료로 쓸 수 있다.

PolitiKAST는 한국 선거의 후보, 정당, 지역, 이슈, 여론조사, 시간 이벤트를 KG로 묶어야 한다. 이 자료는 "RAG만 붙인 챗봇"이 아니라 election ontology를 가진 simulation engine이라는 차별화 논리를 보강한다.

PolitiKAST 활용 포인트: KG/ontology 설계 섹션, 논문 methodology의 knowledge-augmented 설명, 대시보드의 fact grounding view에 참고한다.

**Naver Premium: MiroFish 한국어 기사**
URL: https://contents.premium.naver.com/aidx/aix/contents/260323171039480wb

Naver Premium 기사는 한국어 독자에게 MiroFish를 비즈니스/기술 관점으로 소개한다. raw capture 기준 OASIS 1M agent, 23 social actions, 투자/선거 예측 응용 가능성 같은 주장을 담고 있다.

다만 일부 수치와 투자/상업화 관련 claim은 공식 benchmark나 1차 자료로 재검증하는 것이 필요하다. PolitiKAST 문서에서는 hype source로 분류하고, 기술적 근거는 공식 repo와 architecture source를 우선한다.

PolitiKAST 활용 포인트: 한국어 미디어에서 MiroFish가 어떻게 받아들여지는지 보여주는 보조 자료로 쓴다. 정치/선거 응용 claim을 소개하되, PolitiKAST의 검증/재현성 설계를 차별점으로 둔다.

**BigGo Finance: Nvidia Korean Persona Dataset**
URL: https://finance.biggo.com/news/-Z2otJ0BvbjfYyetzrrz

이 기사는 MiroFish 직접 자료는 아니지만 PolitiKAST 데이터셋과 직접 관련된다. Nvidia가 한국 Nemotron 생태계 확장을 추진하며 7M synthetic Korean persona records를 공개했다는 내용을 다룬다.

PolitiKAST는 `/Users/girinman/datasets/Nemotron-Personas-Korea/data/*.parquet`의 7M personas를 사용하므로, 한국 synthetic persona 기반 voter simulation의 데이터 배경을 설명하는 데 중요하다. 단, 실제 논문 인용은 dataset 원문/라이선스와 함께 해야 한다.

PolitiKAST 활용 포인트: 데이터 섹션, persona sampling 설명, 한국 특화 voter agent 생성 근거에 활용한다.

## 사용자 인터페이스 / UX 참고

**Velog Setup Guide / Troubleshooting**
URL: https://velog.io/@takuya/mirofish-setup-guide-troubleshooting

이 글은 MiroFish 실행 환경과 troubleshooting을 한국어로 정리한다. Node, Python, uv, Zep, API key 등 실제 구동에 필요한 요소와 운영 비용/환경 변수 문제를 다룬다.

UX 관점에서는 강력한 simulation tool일수록 onboarding, key 설정, run 상태 확인, 실패 복구가 중요하다는 점을 보여준다. PolitiKAST 해커톤 데모도 복잡한 환경을 사용자에게 노출하기보다 dashboard와 snapshot 중심으로 안정적으로 보여줘야 한다.

PolitiKAST 활용 포인트: Streamlit sidebar의 run status, API key/capacity warning, frozen artifact viewer, troubleshooting note 설계에 참고한다.

**MiroFish 공식 사이트 Workflow / Deep Interaction UX**
URL: https://mirofish.my

공식 사이트는 ontology generation, graph construction, parallel simulation, report generation, deep interaction을 제품 단계로 보여준다. 사용자가 업로드한 자료가 world, agent, report, interactive query로 변환되는 흐름을 전면에 둔다.

PolitiKAST도 사용자가 region과 scenario를 선택하면 simulation run, aggregate, KG evidence, narrative report로 자연스럽게 이동해야 한다. 단순 표/차트 나열보다 "어떤 입력이 어떤 근거를 통해 어떤 결과로 갔는지"를 추적할 수 있어야 한다.

PolitiKAST 활용 포인트: 대시보드의 run flow, region selector, KG evidence panel, ReportAgent-style narrative summary UI에 참고한다.

**Amadad Fork Artifact UX**
URL: https://github.com/amadad/mirofish

CLI fork의 artifact 구조는 UI보다 운영 UX에 가깝다. simulation input, ontology/KG, timeline, logs, final report를 고정 경로에 남기면 프론트엔드가 없어도 결과를 재검토할 수 있다.

PolitiKAST 해커톤에서는 새 기능보다 제출 가능한 artifact가 중요하다. raw run 결과, aggregate JSON, figures, paper table을 한 번에 확인할 수 있는 구조가 발표 리스크를 줄인다.

PolitiKAST 활용 포인트: `_workspace/snapshots/`와 Streamlit artifact browser 설계에 참고한다.

## 미디어 / 보도

**TopAIProduct: GitHub Trending Coverage**
URL: https://topaiproduct.com/2026/03/07/mirofish-just-hit-github-trending-and-its-unlike-any-ai-tool-ive-seen/

이 글은 MiroFish가 GitHub Trending에서 주목받았다는 초기 보도/리뷰 성격의 자료다. 기술 구조보다는 "새로운 AI tool로 빠르게 화제가 되었다"는 생태계 반응을 보여준다.

기술적 인용 우선순위는 낮지만, MiroFish가 왜 PolitiKAST의 비교 대상으로 의미가 있는지 설명하는 배경 자료로는 쓸 수 있다.

PolitiKAST 활용 포인트: 발표 도입부의 관련 작업/생태계 맥락, "AI swarm prediction engine" 유행과 PolitiKAST의 연구형 구현 차이를 설명할 때 참고한다.

**ManagerKim News: MiroFish AI Swarm Prediction Engine**
URL: https://managerkim.com/news/2026-03-16-mirofish-ai-swarm-prediction-engine

한국어 뉴스 형태로 MiroFish의 AI swarm prediction engine 개념을 소개한다. 마케팅, 정책, 여론 use case와 God View 변수 주입 같은 설명이 비교적 쉽게 정리되어 있다.

정확한 기술 근거보다는 대중적 설명 자료에 가깝다. PolitiKAST가 일반 청중에게 "시나리오 shock을 넣고 결과 궤적을 보는 도구"로 설명될 때 유사한 언어를 참고할 수 있다.

PolitiKAST 활용 포인트: 발표용 시나리오 문구, dashboard demo narrative, 정책 발표/스캔들/후보 단일화 같은 shock event 설명에 활용한다.

**Reddit OpenClawInstall: MiroFish Trending Discussion**
URL: https://www.reddit.com/r/OpenClawInstall/comments/1rwv2kq/mirofish_just_hit_1_on_github_trending_it_spawns/

Reddit/OpenClaw community 글은 MiroFish를 trading/research signal layer와 연결해 설명한다. consensus drift, alignment bias, 시뮬레이션 결과의 과신 위험도 함께 언급된다.

커뮤니티 반응 자료이므로 검증된 기술 문서로 쓰기보다는 "사용자들이 MiroFish를 어떻게 해석하고 어떤 위험을 우려하는지"를 보여주는 자료로 적합하다.

PolitiKAST 활용 포인트: dashboard에서 uncertainty와 caveat를 노출해야 하는 이유, 발표 Q&A에서 "예측 엔진의 한계"를 답변할 때 참고한다.

## 접근 실패 list failed URLs

- https://openclawapi.org/ko/blog/2026-03-17-mirofish-guide
  기존 raw capture 기준 본문 접근 실패. 웹 fetch가 `Cache miss`를 반환했고, 현재 환경에서도 fresh `curl`이 DNS 제한으로 실패했다.

- https://s11.hubnews.co.kr/index.php/news/2026031907194246214.32
  기존 raw capture 기준 본문 접근 실패. 검색은 HubNews 홈페이지 수준만 노출했고 원문 기사 본문은 확보되지 않았다.

- https://www.facebook.com/leebisu/posts/-오픈소스-ai-예측-엔진인-mirofish가-핫합니다️-현재-github글로벌-트렌딩-1위-단기간에-star-18000개-포크-1900개-기록/26523443990624409/
  기존 raw capture 기준 본문 접근 실패. Facebook 렌더링/접근 제한 가능성이 있으며, 현재 환경의 fresh `curl`도 DNS 제한으로 실패했다.

- Fresh curl note: 이번 실행에서는 manifest의 25개 URL 모두 `Could not resolve host`로 fresh fetch가 실패했다. 단, 위 3개를 제외한 URL은 기존 raw capture가 있어 canonical slug markdown과 KB 요약을 생성했다. 상세 실패 로그는 `docs/references/raw/mirofish/_curl_failures.txt`에 남겼다.
