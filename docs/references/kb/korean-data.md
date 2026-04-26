# 한국 데이터 / 뉴스 KB

수집 기준일: 2026-04-26 KST. `docs/references/manifests/korean-data.txt`의 중복 제거 URL 34개를 처리했다. 로컬 `curl -L -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15" --max-time 30` 실행은 전 URL에서 DNS 해석 실패가 발생했으므로, 새 raw 파일에는 curl 실패 상태와 기존 raw cache의 추출 메모를 함께 보존했다. 원문 전문 복제 대신 요약과 PolitiKAST 활용 포인트 중심으로 정리한다.

Raw 파일 위치: `docs/references/raw/korean-data/`. 감사 로그: `docs/references/raw/korean-data/_fetch-log.md`.

## 선거 데이터 (NEC, 행안부 등)

**생성형 AI 신기술 도입에 따른 선거 규제 연구 결과보고서**
source: 중앙선거관리위원회 / URL: https://www.nec.go.kr/site/nec/ex/bbs/View.do?cbIdx=1132&bcIdx=196009

중앙선관위 연구자료 페이지에 게시된 정책연구 결과보고서다. 연구기관은 부경대학교 산학협력단, 연구책임자는 김주희, 연구기간은 2023년 10월부터 12월까지로 기록되어 있다. 페이지는 보고서 PDF 첨부와 공공누리 조건을 표시하며, 연구보고서가 선관위의 공식 입장과 반드시 일치하지 않을 수 있음을 고지한다.

PolitiKAST 활용 포인트: 생성형 AI 기반 선거 시뮬레이션의 법적 위험, 합성 이미지·음성·영상, 선거결과 예측 공표의 한계를 설명하는 정책 KG 노드로 사용한다. 대시보드 출력 문구와 면책 고지의 근거 자료로 연결한다.

**생성형 AI 신기술 도입에 따른 선거 규제 연구 보고서 PDF**
source: 중앙선거관리위원회 / URL: https://www.nec.go.kr/common/board/Download.do?bcIdx=264815&cbIdx=1132&streFileNm=acdcbd92-3e9a-42b1-baef-f411f9c120fa.pdf

NEC 연구자료 본문에 연결된 PDF 첨부로 보인다. 이번 로컬 환경에는 `pdftotext`와 `pypdf`가 없어 PDF 본문 추출을 수행하지 못했고, 기존 cache도 파일 바이트를 확보하지 못한 partial 상태다.

PolitiKAST 활용 포인트: PDF를 확보하면 선거법 리스크 taxonomy, 허위사실·딥페이크·AI 예측 공표 관련 조항을 정책 KG와 RAG 문서 chunk로 넣는다.

**생성형 AI 활용 선거운동 운용기준 PDF**
source: 중앙선거관리위원회 / URL: https://nec.go.kr/common/board/Download.do?bcIdx=266339&cbIdx=1107&streFileNm=4ef84cc3-f936-4b25-a0cb-4b1cdf33b58c.pdf

중앙선관위가 생성형 AI를 활용한 선거운동 관련 운용기준으로 공개한 PDF 첨부로 추정된다. 로컬 curl과 PDF 추출 도구 모두 사용할 수 없어 본문 추출은 실패했다.

PolitiKAST 활용 포인트: AI 산출물이 선거여론조사처럼 오인되지 않게 하는 UI 문구, citation 요구, 허위사실 방지 guardrail의 직접 근거 후보로 둔다.

**공직선거법 일부개정법률안**
source: 국회 입법예고 / URL: https://opinion.lawmaking.go.kr/gcom/nsmLmSts/out/2216025/detailRP

생성형 AI와 선거 관련 규율을 다루는 공직선거법 개정안 페이지다. 기존 추출 메모는 AI 생성 선거 콘텐츠, 공표 책임, 허위사실, 선거결과 예측과 여론조사 오인 가능성을 PolitiKAST가 주의해야 할 쟁점으로 정리한다.

PolitiKAST 활용 포인트: `policy_events`와 `kg_triples`에 법안, 적용 대상, 금지·주의 행위, 책임 주체를 노드/관계로 보존한다. 결과 검증 단계에서 "실제 여론조사가 아님" 고지를 강제하는 규칙으로 사용한다.

## 여론조사 (NESDC, 갤럽, 리얼미터 등)

**여론조사 결과는 왜 각각 다를까?**
source: 통계청 통계의 창 2024 여름호 / URL: https://shi.kostat.go.kr/window/2024a/main/2024_sum_01.html

정치 여론조사 결과가 표본추출 frame, 조사 방식, 질문 문항, 문항 순서, 응답률, 가중치에 따라 달라진다는 점을 설명한다. ARS와 전화면접, RDD와 안심번호의 차이를 비교하며, 같은 시점의 조사라도 방법론 차이를 함께 보지 않으면 수치를 단순 비교하기 어렵다고 강조한다.

PolitiKAST 활용 포인트: `poll_observations.methodology_json`에 조사모드, 표본 frame, 표본수, 응답률, 가중치, 질문 문구, 조사기간을 필수 필드로 둔다. 시뮬레이션 결과 검증 시 여론조사 원자료의 방법론 메타데이터가 없는 경우 신뢰도를 낮춘다.

**한국갤럽 reportContent seqNo=888**
source: 한국갤럽 / URL: http://www.gallup.co.kr/gallupdb/reportContent.asp?seqNo=888

manifest에는 한국갤럽 리포트 URL이 포함되어 있으나, 이번 curl은 DNS 실패했고 기존 cache도 인코딩 문제로 본문을 얻지 못했다. 갤럽 자료는 조사일, 표본, 조사방법, 질문 문구, 결과 수치를 모두 함께 저장해야 하는 여론조사 검증 소스다.

PolitiKAST 활용 포인트: 접근 회복 후 `poll_observations`에 정례조사 결과와 방법론을 넣는다. 원문 재배포 없이 링크, 메타데이터, 수치, 질문 문구 수준으로 보존한다.

**KASR survey_SR 17_1_5 / 23_1_5 / 25_2_1**
source: KASR / URLs: http://kasr.skyd.co.kr/survey_SR/17_1_5, http://kasr.skyd.co.kr/survey_SR/23_1_5, http://kasr.skyd.co.kr/survey_SR/25_2_1

한국 선거·정치 관련 조사자료로 보이는 세 URL이다. 이번 curl은 DNS 실패했고 기존 cache는 502 Bad Gateway로 기록되어 있어 본문과 수치를 확인하지 못했다.

PolitiKAST 활용 포인트: 접근 회복 전까지 수치 검증에는 사용하지 않는다. 회복 후 조사 단위, 지역, 시계열, 질문 문항을 추출해 synthetic voter trajectory의 calibration 후보로 둔다.

## 인구·통계 데이터 (KOSIS, 통계청)

**통계청 통계의 창 여론조사 방법론 자료**
source: 통계청 / URL: https://shi.kostat.go.kr/window/2024a/main/2024_sum_01.html

manifest에서 직접 확인 가능한 통계청 URL은 KOSIS 통계표나 인구 API가 아니라 여론조사 방법론 설명 자료다. 직접 인구·소득·연령 시계열은 이 manifest에 포함되어 있지 않다.

PolitiKAST 활용 포인트: 인구·통계 실측값은 KOSIS, SGIS, MDIS, 행안부 주민등록 인구통계 등 별도 공식 endpoint를 추가 수집해야 한다. 현재 자료는 통계 수치 자체보다 polling metadata schema 설계에 사용한다.

**서울선거, 소득에 따른 계급선거로 바뀌었다**
source: GDS Korea / URL: https://gdskorea.co.kr/최근-3년-서울선거-분석해-보니③-서울선거-소득에-따/

최근 3년 서울 선거를 소득과 지역의 관점에서 분석한 글이다. 기존 cache는 서울 선거에서 소득·주거·지역 격차가 정치 선택과 연결되는 분석 관점을 보존하고 있다.

PolitiKAST 활용 포인트: 서울 region scenario에서 소득 proxy, 주거비, 자치구 단위 계층 균열을 persona prior와 scenario seed로 사용한다. 실제 수치 입력 전에는 해석 가설로만 사용한다.

## 6.3 지방선거 (서울/광주/대구/의왕/보궐) 관련 보도

**AI가 2분 만에 표심 읽어... 여론조사, 사람 필요없다?**
source: 조선일보 / URL: https://www.chosun.com/economy/tech_it/2026/04/02/WXT7KWRDGFEZVCAZKO7A2EU4FU/

2026년 지방선거와 미국 중간선거를 배경으로 다중 에이전트 기반 여론·소비자 행동 시뮬레이션을 소개한 기사다. 기존 cache는 원 조선일보 페이지가 partial이고 Daum syndication에서 더 나은 요약을 확보한 상태다.

PolitiKAST 활용 포인트: PolitiKAST를 "여론조사"가 아니라 "합성 페르소나 기반 시나리오 시뮬레이션"으로 설명해야 한다는 narrative seed로 사용한다. 결과 화면에는 정확한 득표 예측이 아니라 입력 가정에 따른 궤적이라는 고지를 붙인다.

**AI가 2분 만에 표심 읽어... 여론조사, 사람 필요없다? Daum 배포본**
source: Daum / 조선일보 / URL: https://v.daum.net/v/20260402153657042

Daum-hosted 조선일보 기사로, MiroFish, Aaru, Intellisia, Stanford Smallville, Simile, Nielsen, Ipsos 등 public opinion simulation 또는 adjacent 사례를 언급한다. AI persona를 만들고 변수 투입 후 행동 변화를 관찰하는 workflow를 설명한다.

PolitiKAST 활용 포인트: 이벤트 KG 노드 `2026-04-02 Korean media coverage of AI polling simulation`으로 사용한다. 대시보드 설명 문구와 limitation disclosure를 강화하는 근거다.

**AI가 2분 만에 표심 읽어... print/공유 URL**
source: Daum / 조선일보 / URL: https://v.daum.net/v/20260402153657042?f=p

동일 기사로 보이는 print/share variant다. manifest에는 별도 URL로 포함되어 있으며 raw 처리도 별도 파일로 남겼다.

PolitiKAST 활용 포인트: 중복 소스이므로 KG에는 canonical URL 하나만 남기고, source alias로 연결한다.

**MiroFish 관련 뉴스통 보도**
source: 뉴스통 / URL: https://www.newstong.co.kr/mobile/NewsViewShare.aspx?seq=14288282

중국 대학생이 짧은 기간에 만든 미래 예측 시스템 MiroFish와 투자 유치를 다룬 기사다. 기존 cache는 AI agent, knowledge graph, 토론·설득·의견형성 기반 예측 흐름을 요약한다.

PolitiKAST 활용 포인트: multi-agent simulation의 narrative reference로 사용한다. PolitiKAST의 기술 설명에서 정확도 과장 대신 가능성 탐색 도구라는 framing을 유지한다.

**MiroFish 관련 Newsis/Daum 보도**
source: Daum / 뉴시스 / URL: https://v.daum.net/v/FplQvCFY5r

MiroFish 보도 중 하나로, 현실 데이터 입력, 지식그래프, AI 에이전트가 토론·설득·의견형성을 거쳐 예측 보고서를 생성하는 흐름을 설명한다.

PolitiKAST 활용 포인트: event KG에서 외부 사례 노드로 연결하고, PolitiKAST engine 설명에서 agent interaction, KG retrieval, scenario reporting 구성요소를 비교하는 데 사용한다.

**Nemotron Personas Korea 관련 보도 묶음**
source: Asiae, MK, EDaily, Daum/Herald / URLs: https://www.asiae.co.kr/en/article/2026042117324089969, https://www.mk.co.kr/en/business/12023113, https://www.edaily.co.kr/News/Read?newsId=05192246645418416&mediaCodeNo=257, https://v.daum.net/v/20260421180940689, https://v.daum.net/v/HHnshO4qHH

NVIDIA Nemotron Developer Days Seoul과 한국형 AI 생태계 지원, Nemotron Personas Korea 공개를 다룬 보도 묶음이다. 기사별로 600만 record, 700만 persona 등 표현 차이가 있으므로 프로젝트 내부 수치는 실제 parquet manifest와 ingestion 결과를 기준으로 삼아야 한다.

PolitiKAST 활용 포인트: synthetic persona prior의 출처 설명과 media event KG 노드로 사용한다. 데이터 규모 claim은 `source_claims`에 별도 저장하고, 실제 ingestion count와 혼동하지 않는다.

**인공지능을 정치에 어떻게 활용해 볼까?**
source: 프레시안 / URL: https://www.pressian.com/pages/articles/2024020814560006080

정치 영역에서 AI를 어떻게 활용할지 논의하는 기사다. 기존 cache는 AI 정치 활용의 기대와 위험을 함께 다룬 참고 자료로 보존되어 있다.

PolitiKAST 활용 포인트: 정책·사회적 수용성 맥락의 이벤트 KG 노드로 사용한다. 모델 출력이 정치적 판단을 대체하지 않는다는 설명을 강화한다.

## 후보자 / 정당 정보

**공직선거법 일부개정법률안**
source: 국회 입법예고 / URL: https://opinion.lawmaking.go.kr/gcom/nsmLmSts/out/2216025/detailRP

후보자·정당 자체의 프로필 데이터는 아니지만, 후보자·정당 관련 AI 생성물과 선거운동 표현의 책임 문제를 연결하는 법규 자료다. 후보자와 공모관계가 있는 경우 책임 귀속이 문제될 수 있다는 쟁점을 시뮬레이션 guardrail로 보존한다.

PolitiKAST 활용 포인트: 후보자·정당 KG에는 사실 검증된 공식 후보자 정보만 넣고, AI가 생성한 후보자 관련 주장에는 출처 citation을 요구한다.

**중앙선관위, 생성형 AI를 활용한 선거운동 관련 운용기준 마련**
source: 국회도서관 최신정책정보 / URL: https://nsp.nanet.go.kr/trend/latest/detail.do?latestTrendControlNo=TREN0000001591

중앙선관위가 생성형 AI를 활용한 선거운동 관련 운용기준을 마련했다는 정책정보 페이지다. 기존 cache는 AI 활용 선거운동이 허용되는 범위, 허위사실과 책임, 예측 결과 공표 시 한계 고지 필요성을 요약한다.

PolitiKAST 활용 포인트: 후보자·정당 관련 생성 텍스트의 검증 정책, 시뮬레이션 결과의 오인 방지 문구, 법규 RAG citation의 seed 자료로 사용한다.

**[중앙선관위] 챗GPT 등 생성형 AI 활용 관련 법규운용기준**
source: NEPLA / URL: https://www.nepla.ai/wiki/국가와-민주주의/국회-선거-정당/-중앙선관위-챗gpt-등-생성형-ai-활용-관련-법규운용기준-vekno0g27n7q

NEC 운용기준을 재게시·정리한 페이지다. AI 생성 선거운동 자료가 선거법상 허용 범위 안에서 가능하더라도 허위사실, 책임 주체, 여론조사 오인 가능성이 별도로 문제될 수 있음을 요약한다.

PolitiKAST 활용 포인트: 후보자·정당 관련 facts는 official source와 뉴스 source를 분리해 저장하고, generated claim은 `needs_verification` 상태로 둔다.

## 정치 사건 / 스캔들 보도

**생성형 AI와 선거보도 리스크**
source: NEC, 국회도서관, NEPLA / URLs: https://www.nec.go.kr/site/nec/ex/bbs/View.do?cbIdx=1132&bcIdx=196009, https://nsp.nanet.go.kr/trend/latest/detail.do?latestTrendControlNo=TREN0000001591, https://www.nepla.ai/wiki/국가와-민주주의/국회-선거-정당/-중앙선관위-챗gpt-등-생성형-ai-활용-관련-법규운용기준-vekno0g27n7q

manifest에는 서울·광주·대구·의왕·보궐 후보별 스캔들 기사나 사건 chronicle URL은 직접 포함되어 있지 않다. 대신 생성형 AI 선거보도와 허위사실·예측 결과 오인 리스크를 다루는 정책 자료가 포함되어 있다.

PolitiKAST 활용 포인트: 사건 KG의 `risk_policy` branch로 사용한다. 실제 정치 사건·스캔들 node는 별도 manifest로 수집하고, 사실관계와 시간축을 독립 검증해야 한다.

**선거 보안이란 무엇입니까? 선거 인프라를 보호하는 방법**
source: Fortinet / URL: https://www.fortinet.com/kr/resources/cyberglossary/election-security

선거 인프라 보호와 사이버 보안 위협을 설명하는 개요 자료다. 직접적인 한국 선거 사건 보도는 아니지만, 선거 시스템 신뢰, 정보보안, 공격 표면을 이해하는 배경 자료로 쓸 수 있다.

PolitiKAST 활용 포인트: `election_security` KG 노드, misinformation/cyber-risk scenario seed, 결과 해석의 보안·신뢰 위험 설명에 사용한다.

## 학술 한국 정치 자료

**생성형 AI 신기술 도입에 따른 선거 규제 연구 결과보고서**
source: 중앙선거관리위원회 / URL: https://www.nec.go.kr/site/nec/ex/bbs/View.do?cbIdx=1132&bcIdx=196009

정책연구 보고서 성격의 한국 선거·AI 규제 참고문헌이다. 연구기간, 수행기관, 책임연구자, 연구 발주부서가 명시되어 있어 논문 reference와 policy background로 쓰기 좋다.

PolitiKAST 활용 포인트: paper의 related policy context, limitation, legal compliance section에 인용 후보로 둔다.

**문화다양성협약 국내 이행을 위한 논의: 유튜브에서 AI까지**
source: 유네스코한국위원회 / URL: https://unesco.or.kr/wp-content/uploads/2024/06/문화다양성협약-국내-이행을-위한-논의-유튜브에서-AI까지-21세기-한국에서의-문화다양성.pdf

PDF URL은 manifest에 포함되어 있으나 로컬 PDF 추출 도구가 없어 본문 텍스트를 확보하지 못했다. 기존 cache도 텍스트 라인을 얻지 못한 partial 상태다.

PolitiKAST 활용 포인트: AI와 한국 사회·문화 다양성 맥락의 paper background 후보로 두되, 본문 확보 전까지 직접 인용하지 않는다.

**생성형AI 법률 지식기반 관계 데이터**
source: AIHub / URL: https://www.aihub.or.kr/aihubdata/data/view.do?currMenu=115&topMenu=100&dataSetSn=71722

법률 도메인의 텍스트 데이터셋으로, CSV 원천과 JSON triple labeling 구조를 제공한다. 기존 cache는 39,035건의 source/labeled data, 1,003,263개 triple label, 법령·판례·행위·처분 등 entity와 관계 예시를 보존한다.

PolitiKAST 활용 포인트: 선거법·정책 KG의 schema reference로 사용한다. 조항, 행위, 책임, 제재, 예외를 SPO 구조로 모델링할 때 참고한다.

**LLM-Ko-Datasets README**
source: GitHub / URL: https://github.com/gyunggyung/LLM-Ko-Datasets/blob/main/README.md

한국어 LLM 학습·평가 데이터셋을 모은 README다. Korean Wikipedia, WanJuan-Korean, KORMo 계열, synthetic datasets 등 한국어 언어 적응 후보를 찾는 index로 사용할 수 있다.

PolitiKAST 활용 포인트: 한국어 처리 baseline, corpus discovery, model adaptation 자료 조사에 사용한다. 각 데이터셋은 라이선스와 정치·선거 사용 가능 여부를 별도로 검토해야 한다.

**자연어 처리는 법률 시스템을 어떻게 개선할 수 있을까?**
source: Huffon blog / URL: https://huffon.github.io/2020/05/23/legal-nlp/

법률 NLP에서 지식 모델링, 추론, 해석 가능성이 중요하다는 관점을 제공하는 참고 글이다. 직접 선거 데이터는 아니지만 법률 문서 처리 pipeline을 설계할 때 유용하다.

PolitiKAST 활용 포인트: 선거법 RAG를 단순 embedding 검색으로 끝내지 않고 조문·행위·제재 관계를 명시적 KG로 보존하는 설계 근거로 사용한다.

## 접근 실패

이번 실행의 공통 실패: 로컬 sandbox에서 모든 manifest URL에 대해 `curl` DNS 해석 실패가 발생했다. 따라서 HTML markdown 변환, CP949/EUC-KR 재디코딩, PDF 텍스트 추출은 새로 수행하지 못했다. 기존 raw cache의 prior extraction notes가 있는 경우에만 KB 요약에 사용했다.

개별 접근 실패 또는 partial 상태:

- `http://www.gallup.co.kr/gallupdb/reportContent.asp?seqNo=888`: curl DNS 실패. 기존 cache는 Unicode decoding error.
- `http://kasr.skyd.co.kr/survey_SR/17_1_5`: curl DNS 실패. 기존 cache는 502 Bad Gateway.
- `http://kasr.skyd.co.kr/survey_SR/23_1_5`: curl DNS 실패. 기존 cache는 502 Bad Gateway.
- `http://kasr.skyd.co.kr/survey_SR/25_2_1`: curl DNS 실패. 기존 cache는 502 Bad Gateway.
- `https://www.chosun.com/economy/tech_it/2026/04/02/WXT7KWRDGFEZVCAZKO7A2EU4FU/`: curl DNS 실패. 기존 cache는 partial.
- `https://www.chosun.com/economy/tech_it/2026/04/02/WXT7KWRDGFEZVCAZKO7A2EU4FU/?outputType=amp`: curl DNS 실패. 기존 cache는 failed. 요청 slug 첫 60자 기준으로 원 URL과 충돌하여 raw 파일은 `...WXT7KWRDGFEZVCAZKO-2.md`로 저장했다.
- `https://www.chosun.com/english/industry-en/2026/04/02/WJ5VST6GR5DN5MRQNIEBEOHZVA/`: curl DNS 실패. 기존 cache는 partial.
- `https://www.inthenews.co.kr/news/article.html?no=85160`: curl DNS 실패. 기존 cache는 403 Forbidden.
- `https://news.nate.com/view/20260421n32098`: curl DNS 실패. 기존 cache는 Unicode decoding error.
- `https://v.daum.net/v/20260410144202657`: curl DNS 실패. 기존 cache는 failed/cache miss.
- `https://www.klri.re.kr/cmm/fms/FileDown.do?atchFileId=FILE_0000000000285708ekUR&fileSn=0&stat=&data_no=`: curl DNS 실패. 기존 cache는 failed/partial.
- `https://unesco.or.kr/wp-content/uploads/2024/06/문화다양성협약-국내-이행을-위한-논의-유튜브에서-AI까지-21세기-한국에서의-문화다양성.pdf`: curl DNS 실패. 기존 cache는 PDF 텍스트 미확보.

추가 메모:

- `pandoc`, `pdftotext`, `lynx`, `beautifulsoup4`, `markdownify`, `pypdf`가 로컬 환경에 설치되어 있지 않았다.
- raw slug rule에 따라 새 파일을 생성했으며, 기존 사람이 읽기 쉬운 이름의 cache 파일은 삭제하지 않았다.
