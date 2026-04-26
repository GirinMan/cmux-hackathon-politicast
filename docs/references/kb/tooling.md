# 도구·프레임워크 KB

작성 기준: 초기 KB는 `docs/references/manifests/tooling.txt` fetch 실패 로그와 보조 지식으로 작성되었다. 2026-04-26 13:06 이후 Top-15에 포함된 tooling 항목(Nemotron-Personas-Korea, CAMEL, UK Parliament Election Ontology)은 fresh raw 본문으로 재검증했고, NetworkX는 사용자 지시대로 로컬 raw 없이 canonical SciPy 2008 citation을 사용했다.

## Nemotron-Personas-Korea (데이터셋, 라이센스, BibTeX)

**Nemotron-Personas-Korea Dataset** (✅ 본문 검증: 2026-04-26)
URL: https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea
저자/연도: Hyunwoo Kim, Jihyeon Ryu, Jinho Lee, Hyungon Ryu, Kiran Praveen, Shyamala Prayaga, Kirit Thadaka, Will Jennings, Bardiya Sadeghi, Ashton Sharabiani, Yejin Choi, Yev Meyer (2026)
Raw: `docs/references/raw/tooling/huggingface-co-datasets-nvidia-Nemotron-Personas-Korea.md`
요약: Hugging Face 데이터셋 카드 기준으로 NVIDIA가 공개한 한국어 합성 페르소나 데이터셋이다. 형식은 Parquet, 언어는 Korean, 라이선스는 CC BY 4.0, 기본 split은 `train`, 규모는 1M rows로 표시된다. 주요 필드는 `uuid`, 여러 도메인별 persona 문장, `sex`, `age`, `marital_status`, `housing_type`, `education_level`, `occupation`, `district`, `province`, `country` 등으로 PolitiKAST의 유권자 초기 상태 생성에 직접 연결하기 좋다.

PolitiKAST 활용 포인트: `src/data`의 DuckDB 인제션에서 Parquet를 바로 읽고, `VoterAgent` 초기 persona prompt에는 인구통계 필드와 생활 서사를 분리해 넣는다. 논문에는 CC BY 4.0 라이선스와 NVIDIA/Hugging Face 출처를 명시하고, synthetic persona라는 한계를 별도 서술한다.
핵심 인용: "open-source persona dataset (CC BY 4.0)"; "first large-scale Korean-language persona dataset"
BibTeX key: `bhattacharjee2024nemotron` (로컬 raw citation key는 `nvidia/Nemotron-Personas-Korea`)

**NVIDIA 블로그: 한국 인구통계 기반 Korean AI Agent 구축**
URL: https://huggingface.co/blog/nvidia/build-korean-agents-with-nemotron-personas
요약: Nemotron-Personas-Korea를 실제 한국 에이전트 grounding에 쓰는 방법을 설명하는 NVIDIA/Hugging Face 블로그다. 데이터셋을 단순 이름/나이 테이블이 아니라 지역, 직업, 가족, 취미, 문화 배경을 포함한 풍부한 persona source로 다루는 관점을 제공한다.

PolitiKAST 활용 포인트: `VoterAgent`의 system prompt를 "정치 성향"만이 아니라 생활 맥락, 지역 정체성, 미디어 소비, 가족 구성으로 구성하는 근거로 사용한다. synthetic persona를 실제 여론조사 대체물로 오해하지 않도록 `paper/elex-kg-final.tex`의 limitations에도 반영한다.
BibTeX key: `nvidia2026koreanAgentsNemotron`

**Nemotron-Personas-Japan / NGC / ModelScope 미러**
URL: https://huggingface.co/datasets/nvidia/Nemotron-Personas-Japan
요약: 일본어 버전도 Parquet, CC BY 4.0, 1M rows 규모로 공개되어 있어 Nemotron persona 계열의 다국가 스키마를 비교할 수 있다. NGC와 ModelScope URL은 동일 계열 리소스의 배포 채널로 보이나, 로컬 curl과 브라우저 접근 모두 제한적이었다.

PolitiKAST 활용 포인트: 이번 해커톤에서는 한국 데이터만 사용한다. 다만 스키마 비교는 향후 다국가 선거 시뮬레이션 확장성 설명에 쓸 수 있다.
BibTeX key: `nvidia2026nemotronPersonasJapan`

## CAMEL multi-agent framework

**CAMEL GitHub Repository** (✅ 본문 검증: 2026-04-26)
URL: https://github.com/camel-ai/camel
저자/연도: Guohao Li, Hasan Abed Al Kader Hammoud, Hani Itani, Dmitrii Khizbullin, Bernard Ghanem (2023, NeurIPS)
Raw: `docs/references/raw/tooling/github-com-camel-ai-camel.md`
요약: CAMEL은 role-playing 기반 multi-agent society, workforce, agent memory/toolkit 등을 제공하는 오픈소스 프레임워크다. 저장소 설명은 "multi-agent framework"와 agent scaling law 연구 방향을 강조한다.

PolitiKAST 활용 포인트: `src/sim`에서 지역별 `VoterAgent`, `CandidateAgent`, `ModeratorAgent`, `AnalystAgent`를 분리하고, CAMEL society/workforce 패턴으로 토론과 투표 전환 단계를 순차 실행한다. Gemini 모델 연결은 CAMEL native support가 확인된 경우만 쓰고, 실패 시 `GeminiPool` 래퍼로 degrade한다.
핵심 인용: "finding the scaling laws of agents"; "first LLM (Large Language Model) multi-agent framework"
BibTeX key: `li2023camel`

**CAMEL Societies Documentation**
URL: https://docs.camel-ai.org/key_modules/societies
요약: CAMEL societies 문서는 여러 agent가 role, task, environment를 공유하며 협업하는 구성을 설명한다. 단일 LLM 호출보다 agent 간 메시지 흐름과 task decomposition을 명시적으로 모델링하는 데 초점이 있다.

PolitiKAST 활용 포인트: 5개 region simulation을 같은 contract로 반복 실행할 때 society template을 두고 region seed만 교체한다. phase별 로그를 `_workspace/snapshots`에 남기면 논문 reproducibility와 dashboard replay에 같이 쓸 수 있다.
BibTeX key: `camelai2026societies`

**CAMEL Multi-agent Streamlit UI**
URL: https://github.com/camel-ai/multi-agent-streamlit-ui
요약: CAMEL 기반 multi-agent system을 Streamlit UI로 노출하는 예시 저장소다. agent 대화 상태를 사람이 관찰할 수 있는 대시보드로 만드는 데 참고할 수 있다.

PolitiKAST 활용 포인트: `ui/dashboard`에서 region별 agent trace, 최종 vote trajectory, 정책 이슈별 stance drift를 보여주는 구조의 선행 예시로 사용한다. 해커톤 시간상 코어 엔진을 우선하고 UI는 read-only result explorer로 제한하는 것이 현실적이다.
BibTeX key: `camelai2026streamlitUi`

## Gemini API / google-generativeai (rate limit, structured output)

**Gemini API Rate Limits**
URL: https://ai.google.dev/gemini-api/docs/rate-limits
요약: Gemini API rate limit은 RPM, TPM, RPD 같은 여러 축으로 적용되며, 프로젝트 단위로 평가된다. Google 문서는 preview/experimental 모델이 더 제한적일 수 있고, 실제 한도는 tier와 모델별로 달라지며 AI Studio에서 확인해야 한다고 설명한다.

PolitiKAST 활용 포인트: `GeminiPool`은 API key별 분산만 믿으면 안 된다. rate limit이 project 단위일 수 있으므로 capacity probe 결과를 `_workspace/checkpoints/capacity_probe.json`에 저장하고, `policy.json`에서 동시 region 수와 agent turn 수를 조정한다.
BibTeX key: `google2025geminiRateLimits`

**Gemini Structured Outputs**
URL: https://ai.google.dev/gemini-api/docs/structured-output
요약: Gemini structured output은 `response_mime_type: application/json`과 JSON Schema/Pydantic/Zod schema를 통해 응답 형식을 고정하는 기능이다. Gemini 3 계열에서는 structured output과 built-in tools 조합도 preview로 제공된다.

PolitiKAST 활용 포인트: `VoterAgent` 결과는 자유문장 대신 `{vote_intent, confidence, issue_salience, rationale, changed_from_previous}` 같은 JSON schema로 강제한다. `KG builder`는 entity/relation extraction도 schema 출력으로 받아 DuckDB/NetworkX에 넣기 쉽게 만든다.
BibTeX key: `google2026geminiStructuredOutput`

**Google GenAI SDK와 google-generativeai deprecation**
URL: https://ai.google.dev/gemini-api/docs/libraries
요약: Google 공식 문서는 Gemini API 개발에 `google-genai` SDK를 권장하며, legacy Python package인 `google-generativeai`는 2025년 11월 30일 이후 적극 유지보수 대상이 아니라고 안내한다. 최신 문서와 예시는 `from google import genai` 형태를 사용한다.

PolitiKAST 활용 포인트: `docker/requirements.txt`에는 가능하면 `google-genai`를 사용하고, 기존 CAMEL adapter가 `google-generativeai`를 요구하는 경우에만 compatibility layer로 격리한다. 논문/README에는 SDK 이름을 정확히 구분한다.
BibTeX key: `google2026geminiLibraries`

## DuckDB / parquet ingestion

**DuckDB Parquet Reader**
URL: https://duckdb.org/docs/lts/data/parquet/overview.html
요약: DuckDB는 Parquet 파일을 SQL에서 직접 읽을 수 있고, `read_parquet`, glob pattern, file list, `CREATE TABLE AS SELECT`, view 생성, metadata inspection을 지원한다. Parquet scan에는 projection pushdown과 filter pushdown이 적용되어 필요한 컬럼/row group만 읽는 최적화가 가능하다.

PolitiKAST 활용 포인트: `/Users/girinman/datasets/Nemotron-Personas-Korea/data/*.parquet`를 DuckDB view로 먼저 붙이고, 해커톤 중에는 지역/나이/성별 필터로 sample table을 materialize한다. `filename` virtual column과 `parquet_schema`를 기록하면 데이터 provenance와 schema drift 확인에 좋다.
BibTeX key: `duckdb2026parquetDocs`

## Knowledge graph 도구 (networkx, NetworkX, GraphRAG, neo4j)

**UK Parliament Election Ontology** (✅ 본문 검증: 2026-04-26)
URL: https://ukparliament.github.io/ontologies/election/election-ontology.html
저자/연도: UK Parliament (로컬 raw에 발행연도 미표시)
Raw: `docs/references/raw/tooling/ukparliament-github-io-ontologies-election-election-ontology.md`
요약: 선거, 후보, 선거구, 투표, 결과 같은 정치/선거 개념을 온톨로지로 모델링한 참고 자료다. 한국 지방선거와 완전히 같지는 않지만, entity/relation naming의 출발점으로 쓸 수 있다.

PolitiKAST 활용 포인트: `KG builder`의 최소 스키마를 `Region`, `District`, `Candidate`, `Issue`, `Party`, `VoterPersona`, `VoteEvent`로 두고, relation은 `lives_in`, `supports`, `opposes`, `mentions_issue`, `competes_in`처럼 제한한다.
핵심 인용: "An election to elect a person"; "A candidacy of a person standing in an election"
BibTeX key: `ukparl_election_ontology`

**NetworkX** (⚠️ raw 없음: 2026-04-26)
URL: https://networkx.org/en/
저자/연도: Aric A. Hagberg, Daniel A. Schult, Pieter J. Swart (2008, SciPy Proceedings)
요약: NetworkX는 Python에서 graph, directed graph, multigraph를 만들고 구조/중심성/연결성/커뮤니티 분석을 수행하는 라이브러리다. 노드와 엣지에 임의의 Python 객체나 속성을 붙일 수 있어 빠른 프로토타입에 적합하다.

PolitiKAST 활용 포인트: 해커톤 엔진에서는 Neo4j 서버를 띄우기보다 NetworkX로 in-memory KG를 구성하고, snapshot export를 JSON/GraphML로 남긴다. `VoterAgent` retrieval에는 ego graph, shortest path, issue-candidate neighborhood 같은 가벼운 질의를 우선한다.
핵심 인용: 로컬 raw 없음. BibTeX는 "Exploring Network Structure, Dynamics, and Function using NetworkX" canonical citation으로 갱신.
BibTeX key: `hagberg2008networkx`

**Neo4j GraphRAG Python**
URL: https://neo4j.com/docs/neo4j-graphrag-python/current/
요약: Neo4j GraphRAG Python은 Neo4j 기반의 knowledge graph construction, vector retriever, graph retrieval, KG builder pipeline을 제공하는 공식 패키지다. 최신 문서 기준 Python 3.10+와 Neo4j 5.18+ 계열을 대상으로 한다.

PolitiKAST 활용 포인트: 해커톤 제출물은 NetworkX로 충분하지만, 논문 future work와 full-scale 버전에서는 Neo4j GraphRAG로 candidate/issue graph를 저장하고 VectorCypher retrieval을 결합하는 방향을 제시할 수 있다.
BibTeX key: `neo4j2026graphragPython`

**Rappler 정치 Knowledge Graph 사례**
URL: https://www.ontotext.com/knowledgehub/case-studies/rappler-created-first-philippine-politics-knowledge-graph/
요약: Ontotext의 Rappler 사례는 정치 기사와 공적 정보를 knowledge graph로 연결해 정치인, 조직, 사건 관계를 탐색 가능하게 만든 사례다. 선거/정치 도메인에서 KG가 설명가능성과 탐색성을 높인다는 실무 근거로 쓸 수 있다.

PolitiKAST 활용 포인트: 한국 지방선거 이슈 문서, 후보 공약, 지역 이슈를 KG로 묶고, dashboard에서 "왜 이 persona가 이 후보로 이동했는가"를 graph path로 보여주는 UX 근거가 된다.
BibTeX key: `ontotext2024rapplerPoliticsKg`

## Streamlit / 대시보드 도구

**Streamlit Caching and State**
URL: https://docs.streamlit.io/develop/api-reference/caching-and-state
요약: Streamlit은 user interaction마다 스크립트를 다시 실행하므로, `st.cache_data`, `st.cache_resource`, `st.session_state`가 대시보드 성능과 상태 관리의 핵심이다. 데이터프레임 변환과 DB query는 cache_data, DuckDB connection 같은 전역 리소스는 cache_resource에 맞다.

PolitiKAST 활용 포인트: `ui/dashboard`는 snapshot JSON과 DuckDB query 결과를 캐시하고, region/agent/issue 선택 상태를 session_state에 둔다. build freeze 이후에는 입력 기능을 막고 read-only explorer로 유지한다.
BibTeX key: `streamlit2026cachingState`

**Election Data Visualization Basics**
URL: https://electionsgroup.com/resource/data-visualization-basics/
요약: 선거 데이터 시각화는 정확성, 오해 방지, 색상/범례/축의 일관성이 중요하다. 투표율, 후보별 득표, 지역 비교는 일반 사용자가 즉시 읽을 수 있는 형태로 설계해야 한다.

PolitiKAST 활용 포인트: 대시보드는 지도보다 먼저 region별 vote share, turnout proxy, issue salience trend, confidence interval을 표와 막대/선 그래프로 제공한다. 정치색 팔레트는 실제 정당색을 과도하게 쓰지 않고 범례를 명확히 둔다.
BibTeX key: `electionsgroup2026visualizationBasics`

## LLM caching / persistence

**SQLite persistence**
URL: https://docs.python.org/3/library/sqlite3.html
요약: Python `sqlite3`는 별도 서버 없이 파일 기반 DB를 제공하며 DB-API 2.0 인터페이스를 따른다. 작은 규모의 prompt/response cache, run metadata, deduplication key 저장에 적합하다.

PolitiKAST 활용 포인트: `_workspace/db/llm_cache.sqlite`에 prompt hash, model, temperature, schema version, response JSON, created_at을 저장한다. 재실행 시 같은 persona/region/round 조합은 cache hit로 처리해 Gemini RPM과 비용을 줄인다.
BibTeX key: `python2026sqlite3`

**Requesty caching/failover 개념 참고**
URL: https://www.requesty.ai/blog/camel-gpt-5-in-requesty-multi-agent-roleplay-for-complex-projects
요약: Requesty 블로그는 multi-agent 시스템에서 model routing, caching, failover, cost monitoring이 중요하다는 운영 관점을 제공한다. 특정 vendor 도입 근거라기보다 agent orchestration의 운영 리스크를 설명하는 참고 자료다.

PolitiKAST 활용 포인트: `GeminiPool`에 retry/backoff, cache lookup, failure logging, model fallback 플래그를 둔다. 실제 라우팅 SaaS는 이번 산출물 범위 밖으로 둔다.
BibTeX key: `requesty2025camelRouting`

## 평가 / 통계 도구 (scipy, sklearn, statsmodels)

**SciPy stats**
URL: https://docs.scipy.org/doc/scipy/reference/stats.html
요약: `scipy.stats`는 확률분포, 요약/빈도 통계, 상관, 통계검정, 커널밀도추정 등을 제공한다. 빠른 실험에서는 지역별 결과 차이, bootstrap, rank correlation 같은 기본 검정에 충분하다.

PolitiKAST 활용 포인트: region별 후보 지지율 변화가 단순 random seed 효과인지 확인하기 위해 bootstrap confidence interval, chi-square, Spearman correlation을 계산한다. 논문 figure에는 p-value보다 effect size와 uncertainty를 우선 표기한다.
BibTeX key: `virtanen2020scipy`

**scikit-learn model evaluation**
URL: https://scikit-learn.org/stable/modules/model_evaluation.html
요약: scikit-learn은 classification, regression, clustering 평가 metric과 cross-validation scoring API를 제공한다. metric 선택은 예측 목표와 decision target에 맞춰야 하며, baseline/dummy estimator와 비교하는 습관이 중요하다.

PolitiKAST 활용 포인트: 실제 정답 레이블이 제한적인 해커톤에서는 predictive accuracy보다 internal consistency를 본다. 예를 들어 persona demographics와 vote trajectory 간 clustering stability, issue salience classifier의 macro-F1, seed sensitivity를 평가한다.
BibTeX key: `pedregosa2011scikitLearn`

**statsmodels**
URL: https://www.statsmodels.org/stable/index.html
요약: statsmodels는 통계 모델 추정, 가설검정, 데이터 탐색을 위한 Python 패키지이며 OLS/GLS/WLS, time series, ANOVA, robust covariance 등 해석 중심 분석에 강하다.

PolitiKAST 활용 포인트: agent outcome을 설명하는 회귀식, 예를 들어 `vote_intent ~ age + province + education + issue_salience`를 fitting해 synthetic simulation의 방향성을 sanity check한다. `paper`에는 causal claim 대신 descriptive association으로 표현한다.
BibTeX key: `seabold2010statsmodels`

## 접근 실패.

로컬 `curl` 기준으로 manifest의 모든 URL이 `curl: (6) Could not resolve host` 또는 동일 계열 DNS 실패로 접근 실패했다. 이는 원격 사이트 문제가 아니라 현재 실행 환경의 네트워크/DNS 제한으로 판단된다. 또한 Perplexity MCP 검색은 도구 호출이 거부되어 사용할 수 없었다. 실패 로그는 `docs/references/raw/tooling/*.md`에 URL별로 저장했다.

중복 처리: `https://github.com/camel-ai/camel`와 `https://github.com/camel-ai/camel/`는 trailing slash만 다른 중복으로 보고 한 번만 처리했다. NVIDIA NGC의 `ko_kr`와 `en_sg` URL은 요구된 60자 slug가 충돌하여 두 번째 파일에 `-2` suffix를 붙였다.

접근 실패 URL:

- https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea
- https://huggingface.co/datasets/nvidia/Nemotron-Personas-Japan
- https://huggingface.co/blog/nvidia/build-korean-agents-with-nemotron-personas
- https://catalog.ngc.nvidia.com/orgs/nvidia/teams/nemotron-personas/resources/nemotron-personas-dataset-ko_kr
- https://catalog.ngc.nvidia.com/orgs/nvidia/teams/nemotron-personas/resources/nemotron-personas-dataset-en_sg
- https://www.modelscope.cn/datasets/AI-ModelScope/Nemotron-Personas
- https://www.nvidia.com/ko-kr/ai-data-science/foundation-models/nemotron/
- https://blogs.nvidia.co.kr/blog/korea-nvidia-nemotron-developer-days-seoul-2026/
- https://blogs.nvidia.co.kr/blog/nemotron-developer-days-seoul-2026-highlights-korean-leaders-accelerating-sovereign-ai/
- https://blogs.nvidia.co.kr/blog/nemotron-open-source-ai/
- https://nvidianews.nvidia.com/news/south-korea-ai-infrastructure
- https://developer.nvidia.com/ko-kr/blog/how-to-build-a-document-processing-pipeline-for-rag-with-nemotron/
- https://databubble.co/news/how-to-ground-a-korean-ai-agent-in-real-demographics-with-synthetic-personas
- https://kr.linkedin.com/posts/jayshin94_how-to-ground-a-korean-ai-agent-in-real-demographics-activity-7452377929340096512-3RM4
- https://theagenttimes.com/articles/nvidia-ships-7-million-synthetic-korean-personas-to-ground-o-5a257af0
- https://royzero.tistory.com/entry/nvidia-nemotron-3-open-model
- https://github.com/camel-ai/camel
- https://github.com/camel-ai
- https://github.com/camel-ai/multi-agent-streamlit-ui
- https://github.com/syntax-syndicate/camel-ai-multiagent-framework/blob/master/.env.example
- https://docs.camel-ai.org/key_modules/societies
- https://kitemetric.com/blogs/camel-ai-a-multi-agent-framework-for-collaborative-ai
- https://www.requesty.ai/blog/camel-gpt-5-in-requesty-multi-agent-roleplay-for-complex-projects
- https://dev.to/jauhar/simulating-a-united-nations-session-with-camel-multi-agent-systems-5dhi
- https://ukparliament.github.io/ontologies/election/election-ontology.html
- https://www.ontotext.com/knowledgehub/case-studies/rappler-created-first-philippine-politics-knowledge-graph/
- https://www.reddit.com/r/KnowledgeGraph/comments/16bnsby/campaign_strategy_with_knowledge_graphs/
- https://electionsgroup.com/resource/data-visualization-basics/
- https://infogram.com/create/election-data-visualization
- https://www.toucantoco.com/en/blog/data-visualization-influencing-election
