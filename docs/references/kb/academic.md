# 학술 논문 KB

## Election forecasting

- **ElectionSim: Massive Population Election Simulation Powered by Large Language Model Driven Agents** (✅ 본문 검증: 2026-04-26)
  - 저자/연도: Xinnong Zhang, Jiayu Lin, Libo Sun, Weihong Qi, Yihang Yang, Yue Chen, Hanjia Lyu, Xinyi Mou, Siming Chen, Jiebo Luo, Xuanjing Huang, Shiping Tang, Zhongyu Wei (2024)
  - URL: https://arxiv.org/abs/2410.20746
  - Raw: `docs/references/raw/academic/arxiv-org-abs-2410-20746.md`
  - 요약: LLM 기반 대규모 선거 시뮬레이션 프레임워크. 소셜미디어에서 구성한 백만 단위 유권자 풀, 인구통계 기반 샘플링, PPE 벤치마크를 결합해 미국 대선 시나리오를 평가한다. PolitiKAST의 유권자 풀, 지역별 표본 재가중, LLM 응답 집계 설계에 직접적인 선행연구다.
  - PolitiKAST 활용 포인트: 모델/실험: 대규모 persona pool, poll benchmark, state-level aggregation의 근거.
  - 핵심 인용: "million-level voter pool"; "poll-based presidential election benchmark"

- **Hugging Face paper card for ElectionSim**
  - 저자: Xinnong Zhang et al.
  - URL: https://huggingface.co/papers/2410.20746
  - Raw: `docs/references/raw/academic/huggingface-co-papers-2410-20746.md`
  - 요약: ElectionSim 논문의 Hugging Face 메타데이터 페이지. 제목, 저자, 공개일, 짧은 AI 요약과 arXiv/PDF 링크를 제공한다. 논문과 코드/모델 생태계 연결을 확인하는 보조 출처로 유용하다.
  - PolitiKAST 활용 포인트: 배경/실험: ElectionSim을 공개 연구 아티팩트로 소개할 때 보조 인용.
  - Raw quotes: "accurate and interactive predictions"

- **Moonlight Korean review of ElectionSim**
  - 저자: Moonlight AI review
  - URL: https://www.themoonlight.io/ko/review/electionsim-massive-population-election-simulation-powered-by-large-language-model-driven-agents
  - Raw: `docs/references/raw/academic/www-themoonlight-io-ko-review-electionsim-massive-population.md`
  - 요약: ElectionSim의 한국어 리뷰. 트위터 기반 유권자 풀, ANES/센서스/IPF 기반 인구통계 샘플링, GPT-4o 및 오픈소스 모델 비교, 47/51 주 예측 성과를 설명한다. 빠른 논문 파악과 한국어 논문 작성용 배경 정리에 적합하다.
  - PolitiKAST 활용 포인트: 서론/배경: PolitiKAST가 ElectionSim과 다른 한국 지방선거 지식증강 시뮬레이션임을 대비.
  - Raw quotes: "47/51 주"

- **Moonlight Traditional Chinese review of ElectionSim**
  - 저자: Moonlight AI review
  - URL: https://www.themoonlight.io/tw/review/electionsim-massive-population-election-simulation-powered-by-large-language-model-driven-agents
  - Raw: `docs/references/raw/academic/www-themoonlight-io-tw-review-electionsim-massive-population.md`
  - 요약: ElectionSim의 번체 중국어/영어 혼합 리뷰. 171M 트윗, 1,006,517명 유저, IPF 샘플링, Micro-F1/Macro-F1 평가와 battleground state 결과를 요약한다. 동일 논문의 다국어 리뷰로 핵심 수치 검증에 쓸 수 있다.
  - PolitiKAST 활용 포인트: 실험: 대규모 샘플링과 성능 수치 확인용 보조 출처.
  - Raw quotes: "47/51 states"

- **ElectionSim GitHub repository**
  - 저자: SII-JiayuLin / ElectionSim contributors
  - URL: https://github.com/amazingljy1206/ElectionSim
  - Raw: `docs/references/raw/academic/github-com-amazingljy1206-ElectionSim.md`
  - 요약: ElectionSim 구현 저장소. LLM 배포, individual-level simulation, state-level simulation, 샘플링 비율별 users 폴더, 상태별 시뮬레이션 스크립트 구조를 제공한다. PolitiKAST 엔진 구조와 결과 재현성을 설계할 때 코드 아티팩트 선례로 활용 가능하다. 이번 canonical raw 재수집에서는 로컬 DNS 제한으로 curl 접근이 실패했다.
  - PolitiKAST 활용 포인트: 모델/실험: 재현 가능한 시뮬레이션 CLI와 MIT 라이선스 코드 아티팩트 근거.
  - Raw quotes: 원문 미확보로 직접 인용 불가.

- **Forecasting elections with agent-based modeling: Two live experiments** (✅ 본문 검증: 2026-04-26)
  - 저자/연도: Ming Gao, Zhongyuan Wang, Kai Wang, Chenhui Liu, Shiping Tang (2022, PLOS ONE 17(6): e0270194)
  - URL: https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0270194
  - Raw: `docs/references/raw/academic/journals-plos-org-plosone-article-id-10-1371%2Fjournal-pone-.md`
  - 요약: 여론조사 중심 예측의 한계를 비판하고, 객관적 통계자료와 ABM으로 유권자 행동을 시뮬레이션하는 선거예측 플랫폼을 제안한다. 2020 대만 총통선거와 2020 미국 6개 주 선거를 실시간 예측 실험으로 다뤘다.
  - PolitiKAST 활용 포인트: 배경/모델: 여론조사 의존이 아닌 agent-based forecasting의 정당화.
  - 핵심 인용: "voters are mostly missing"; "two recent experiments of real-time election forecasting"

- **Printable PDF: Forecasting elections with agent-based modeling**
  - 저자: Ming Gao et al.
  - URL: https://journals.plos.org/plosone/article/file?type=printable&id=10.1371%2Fjournal.pone.0270194
  - Raw: `docs/references/raw/academic/journals-plos-org-plosone-article-file-type-printable-id-10-.md`
  - 요약: PLOS ONE 논문의 PDF/printable 버전. 본문과 동일하게 ABM 선거예측 플랫폼, 역사 선거 재현 모델 선택, 경제·고용·충격 이벤트 업데이트를 통한 선거 전 예측 절차를 담고 있다.
  - PolitiKAST 활용 포인트: 실험: 논문 PDF 인용 및 ABM 예측 실험 세부 확인.
  - Raw quotes: "two live experiments"

- **NASA ADS record for PLOS ONE ABM election forecasting**
  - 저자: Ming Gao et al.
  - URL: https://ui.adsabs.harvard.edu/abs/2022PLoSO..1770194G/abstract
  - Raw: `docs/references/raw/academic/ui-adsabs-harvard-edu-abs-2022PLoSO--1770194G-abstract.md`
  - 요약: NASA ADS 상세 레코드는 웹 fetch에서 Internal Error가 발생했다. 동일 논문의 PLOS 원문과 PDF는 접근 가능하므로 학술 메타데이터 보조 출처로만 취급한다.
  - PolitiKAST 활용 포인트: 접근 실패: PLOS 원문으로 대체.
  - Raw quotes: 원문 미확보로 직접 인용 불가.

- **PMC mirror for PLOS ONE ABM election forecasting**
  - 저자: Ming Gao et al.
  - URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC9246136/
  - Raw: `docs/references/raw/academic/pmc-ncbi-nlm-nih-gov-articles-PMC9246136-.md`
  - 요약: PMC 페이지가 reCAPTCHA/브라우저 확인으로 막혔다. 동일 DOI의 PLOS 원문과 printable PDF에서 필요한 정보를 확보했다.
  - PolitiKAST 활용 포인트: 접근 실패: PLOS 원문으로 대체.
  - Raw quotes: 원문 미확보로 직접 인용 불가.

- **Agent-Based Simulations of Online Political Discussions: A Case Study on Elections in Germany**
  - 저자: Abdul Sittar et al.
  - URL: https://arxiv.org/abs/2503.24199
  - Raw: `docs/references/raw/academic/arxiv-org-abs-2503-24199.md`
  - 요약: 독일 정치담론 트위터 데이터를 바탕으로 게시글/댓글 생성, 감성·아이러니·공격성 분류, myopic best-response 행동 모델을 결합한 온라인 정치토론 ABM 논문이다. arXiv에는 공동저자 동의 문제로 철회되었다고 표시되어 신뢰도 주의가 필요하다.
  - PolitiKAST 활용 포인트: 배경: 철회 논문이므로 직접 핵심 근거보다 online political discussion simulation의 위험 사례로 언급.
  - Raw quotes: "This paper has been withdrawn"

- **NVIDIA Nemotron Nano 2**
  - 저자: NVIDIA
  - URL: https://arxiv.org/html/2508.14444v2
  - Raw: `docs/references/raw/academic/arxiv-org-html-2508-14444v2.md`
  - 요약: Nemotron-Nano-9B-v2 기술보고서. hybrid Mamba-Transformer 구조, 128k 컨텍스트, multilingual/Korean 데이터 포함, post-training과 throughput 개선을 설명한다. PolitiKAST의 persona dataset 근거와 long-context 모델 선택 배경에 보조적으로 쓸 수 있다.
  - PolitiKAST 활용 포인트: 배경/모델: Nemotron-Personas-Korea 데이터셋 인용 주변 모델/데이터 생성 맥락.
  - Raw quotes: "Korean"

- **Agent-based Simulation of District-based Elections**
  - 저자: Adway Mitra
  - URL: https://arxiv.org/abs/2205.14400
  - Raw: `docs/references/raw/academic/arxiv-org-abs-2205-14400.md`
  - 요약: 지역구 선거에서 지지자의 공간 분포가 의석 결과를 바꾸는 문제를 ABM과 Monte Carlo sampling, Approximate Bayesian Computation으로 모델링한다. 득표율과 의석 전환, 지역별 분포 효과를 다루므로 한국 기초/광역 단위 시뮬레이션에 직접 관련된다.
  - PolitiKAST 활용 포인트: 모델/실험: 지역구 기반 outcome space, counterfactual, ABC calibration.
  - Raw quotes: "district-based elections"

- **The Complexity of Strategic Behavior in Primary Elections - review**
  - 저자: Moonlight AI review
  - URL: https://www.themoonlight.io/ko/review/the-complexity-of-strategic-behavior-in-primary-elections
  - Raw: `docs/references/raw/academic/www-themoonlight-io-ko-review-the-complexity-of-strategic-be.md`
  - 요약: 예비선거와 본선이 결합된 다단계 선거에서 전략적 행동의 계산복잡도를 설명한다. FPTP, fixed tie-breaking, multiple participation, best response와 Nash equilibrium 검증 문제를 다룬다.
  - PolitiKAST 활용 포인트: 배경/모델: 전략투표가 계산적으로 복잡하며 단순 sincere vote 가정이 취약하다는 근거.
  - Raw quotes: "NP-complete"

## LLM voting / agent simulations

- **LLM Voting: Human Choices and AI Collective Decision Making** (✅ 본문 검증: 2026-04-26)
  - 저자/연도: Joshua C. Yang, Damian Dailisan, Marcin Korecki, Carina I. Hausladen, Dirk Helbing (2024, AIES)
  - URL: https://arxiv.org/abs/2402.01766
  - Raw: `docs/references/raw/academic/arxiv-org-abs-2402-01766.md`
  - 요약: LLM 에이전트의 투표행태를 인간 참여예산 투표 실험과 비교한다. 투표 방식, 선택지 제시 순서, persona, temperature가 집단 결과와 인간 정렬에 영향을 주며, LLM 집단은 다양성이 낮아질 수 있다고 보고한다.
  - PolitiKAST 활용 포인트: 모델/실험: LLM 유권자 편향, persona 효과, ballot-order 민감도 통제 근거.
  - 핵심 인용: "presentation order influenced LLM voting outcomes"; "less diverse collective outcomes"

- **HTML: LLM Voting**
  - 저자: Joshua C. Yang et al.
  - URL: https://arxiv.org/html/2402.01766v1
  - Raw: `docs/references/raw/academic/arxiv-org-html-2402-01766v1.md`
  - 요약: LLM Voting 논문의 HTML 전문. multi-winner voting, participatory budgeting, persona creation, prompt template, Kendall tau/Jaccard 평가를 자세히 설명한다. PolitiKAST의 투표 규칙 및 집계 일관성 검증에 활용할 수 있다.
  - PolitiKAST 활용 포인트: 실험: prompt template, vote parsing, aggregation metrics 설계.
  - Raw quotes: "presentation of voting options"

- **Academia.edu copy: LLM Voting**
  - 저자: Joshua C. Yang et al.
  - URL: https://www.academia.edu/124529513/LLM_Voting_Human_Choices_and_AI_Collective_Decision_Making
  - Raw: `docs/references/raw/academic/www-academia-edu-124529513-LLM_Voting_Human_Choices_and_AI_C.md`
  - 요약: LLM Voting 논문의 Academia.edu 사본. GPT-4와 LLaMA-2의 투표 행태, persona로 일부 bias가 완화되는 현상, CoT가 정확도보다 설명가능성에 기여할 가능성을 요약한다.
  - PolitiKAST 활용 포인트: 배경/모델: LLM voter proxy의 한계와 persona 조정 필요성.
  - Raw quotes: "persona can reduce"

- **Agent-based Simulation of District-based Elections with Heterogeneous Populations**
  - 저자: Adway Mitra
  - URL: https://www.southampton.ac.uk/~eg/AAMAS2023/pdfs/p2730.pdf
  - Raw: `docs/references/raw/academic/www-southampton-ac-uk-~eg-AAMAS2023-pdfs-p2730-pdf.md`
  - 요약: AAMAS 확장초록 형태로 보이는 지역구 선거 ABM 논문. 이질적 인구와 지역구 구조가 의석 결과에 미치는 영향을 간략히 다룬다.
  - PolitiKAST 활용 포인트: 모델: heterogeneous voter population과 district seat conversion의 간단한 근거.
  - Raw quotes: "Heterogeneous Populations"

## Scandals & political shocks

- **Political Scandals, Newspapers, and the Election Cycle** (✅ 본문 검증: 2026-04-26)
  - 저자/연도: Marcel Garz, Jil Sörensen (2019, working paper)
  - URL: https://www.marcelgarz.com/wp-content/uploads/Political-Scandals-Apr2019-web.pdf
  - Raw: `docs/references/raw/academic/www-marcelgarz-com-wp-content-uploads-Political-Scandals-Apr.md`
  - 요약: 독일 전국 일간지 스캔들 기사 794건, 71개 스캔들을 분석해 선거가 가까워질수록 정부 스캔들 보도가 증가한다고 보고한다. 정보 공개 지연이 정치적 동기와 연결될 수 있음을 제시한다.
  - PolitiKAST 활용 포인트: 실험/배경: scandal shock timing과 선거주기 proximity 변수를 모델에 넣는 근거.
  - 핵심 인용: "one additional month closer to an election"; "effect is mostly driven by government scandals"

- **The Electoral Consequences of Scandals: A Meta-Analysis** (✅ 본문 검증: 2026-04-26)
  - 저자/연도: Rodrigo Praino, Daniel Stockemer (2022, Parliamentary Affairs 75(3): 469-491)
  - URL: https://researchnow.flinders.edu.au/en/publications/the-electoral-consequences-of-scandals-a-meta-analysis/
  - Raw: `docs/references/raw/academic/researchnow-flinders-edu-au-en-publications-the-electoral-co.md`
  - 요약: 정치 스캔들이 선거 결과에 미치는 정량 연구를 메타분석한다. 스캔들에 연루된 정치인은 득표가 줄고, 낙선 및 재선 실패 가능성이 커지며, turnout 효과는 혼재되어 있다고 정리한다.
  - PolitiKAST 활용 포인트: 배경/실험: scandal penalty prior와 turnout 효과 불확실성 근거.
  - 핵심 인용: "scandal-ridden politicians tend to get fewer votes"; "link between scandal and turnout is unclear"

- **Scandal Potential**
  - 저자: Brendan Nyhan
  - URL: https://www.cambridge.org/core/journals/british-journal-of-political-science/article/scandal-potential-how-political-context-and-news-congestion-affect-the-presidents-vulnerability-to-media-scandal/A6A03867465E764ACF9E97FB37C1A793
  - Raw: `docs/references/raw/academic/www-cambridge-org-core-journals-british-journal-of-political.md`
  - 요약: 대통령 스캔들이 단순한 잘못의 공개가 아니라 정치·뉴스 맥락에 의해 만들어지는 media scandal임을 이론화한다. 야당 지지자의 낮은 대통령 승인과 낮은 news congestion이 스캔들 발생 가능성을 높인다고 분석한다.
  - PolitiKAST 활용 포인트: 배경/모델: scandal salience를 evidence뿐 아니라 media congestion/context로 조정하는 근거.
  - Raw quotes: "political and news context"

- **PoliticalContext.pdf**
  - 저자: unknown
  - URL: http://webhotel4.ruc.dk/~henning/publications/PoliticalContext.pdf
  - Raw: `docs/references/raw/academic/webhotel4-ruc-dk-~henning-publications-PoliticalContext-pdf.md`
  - 요약: 웹 fetch에서 Internal Error. URL 제목상 정치적 맥락 관련 PDF로 보이나 원문을 확인하지 못했다.
  - PolitiKAST 활용 포인트: 접근 실패.
  - Raw quotes: 원문 미확보로 직접 인용 불가.

## Polls (bandwagon, underdog effects)

- **How are Voters Influenced by Opinion Polls?** (✅ 본문 검증: 2026-04-26)
  - 저자/연도: Jens Olav Dahlgaard, Jonas Hedegaard Hansen, Kasper M. Hansen, Martin V. Larsen (2016, World Political Science 12(2): 283-300)
  - URL: http://www.kaspermhansen.eu/Work/wps_2016.pdf
  - Raw: `docs/references/raw/academic/www-kaspermhansen-eu-Work-wps_2016-pdf.md`
  - 요약: 덴마크 유권자 3,011명 대상 survey experiment로 여론조사의 bandwagon/underdog 효과를 검증한다. 상승세인 정당에 투표·호감이 증가하는 bandwagon 효과를 발견하고 underdog 효과는 확인하지 못했다.
  - PolitiKAST 활용 포인트: 배경/실험: poll exposure treatment와 bandwagon prior 설정.
  - 핵심 인용: "no evidence for the underdog effect"; "consistent bandwagon effect"

- **The Bandwagon Effect in an Online Voting Experiment With Real Political Organizations** (✅ 본문 검증: 2026-04-26)
  - 저자/연도: Mike Farjam (2021, International Journal of Public Opinion Research 33(2): 412-421)
  - URL: https://academic.oup.com/ijpor/article/33/2/412/5857291
  - Raw: `docs/references/raw/academic/academic-oup-com-ijpor-article-33-2-412-5857291.md`
  - 요약: MTurk 기반 온라인 투표 실험에서 실제 정치단체에 자금 배분을 투표하게 하고 poll 결과 노출 효과를 측정한다. 다수 옵션은 평균적으로 추가 7% 득표를 얻어 강한 bandwagon 효과가 나타났다.
  - PolitiKAST 활용 포인트: 실험: poll feedback이 vote share에 미치는 treatment effect calibration.
  - 핵심 인용: "additional 7% of the votes"; "clear and unequivocal evidence"

- **Voting for the Underdog or Jumping on the Bandwagon?** (✅ 본문 검증: 2026-04-26)
  - 저자/연도: Somdeep Chatterjee, Jai Kamal (2019; AEA 2020 preliminary paper)
  - URL: https://www.aeaweb.org/conference/2020/preliminary/paper/i4a3Qy36
  - Raw: `docs/references/raw/academic/www-aeaweb-org-conference-2020-preliminary-paper-i4a3Qy36.md`
  - 요약: 인도 다단계 선거에서 2009년 exit poll 공표 금지를 자연실험으로 사용한다. 금지 이후 선두 후보 득표가 증가해, 금지가 없었다면 후발 후보가 더 많은 표를 얻었을 수 있다는 underdog voting 증거를 제시한다.
  - PolitiKAST 활용 포인트: 배경/실험: poll ban, multi-phase election, underdog response scenario.
  - 핵심 인용: "suggestive evidence of underdog voting"; "elections are usually much closer"

- **Information and election/polling resource**
  - 저자: unknown
  - URL: https://faculty.haas.berkeley.edu/rjmorgan/Information
  - Raw: `docs/references/raw/academic/faculty-haas-berkeley-edu-rjmorgan-Information.md`
  - 요약: 웹 fetch에서 Internal Error. Berkeley Haas 개인 페이지로 보이나 상세 내용을 확인하지 못했다. 이번 canonical raw 재수집에서는 로컬 DNS 제한으로 curl 접근이 실패했다.
  - PolitiKAST 활용 포인트: 접근 실패.
  - Raw quotes: 원문 미확보로 직접 인용 불가.

## Second-order elections

- **Second-order election** (✅ 본문 검증: 2026-04-26)
  - 저자/연도: Karlheinz Reif, Hermann Schmitt (1980, European Journal of Political Research 8: 3-44; raw는 Wikipedia 항목)
  - URL: https://en.wikipedia.org/wiki/Second-order_election
  - Raw: `docs/references/raw/academic/en-wikipedia-org-wiki-Second-order_election.md`
  - 요약: Reif and Schmitt의 second-order election 개념을 소개한다. 국가 권력을 직접 결정하지 않는 유럽의회·지방·보궐선거에서는 낮은 투표율, protest vote, 소수/주변 정당 지지, 정부 심판 효과가 나타난다는 틀이다.
  - PolitiKAST 활용 포인트: 배경: 지방선거와 보궐선거를 second-order 선거로 모델링하는 개념 정의.
  - 핵심 인용: "less important than national elections"; "turnout is expected to be lower"

- **HAL PDF 226**
  - 저자: unknown
  - URL: https://hal.science/hal-04862262v1/file/226.pdf
  - Raw: `docs/references/raw/academic/hal-science-hal-04862262v1-file-226-pdf.md`
  - 요약: HAL이 Anubis Access Denied를 반환했다. 원문 제목과 내용을 확인하지 못했다.
  - PolitiKAST 활용 포인트: 접근 실패.
  - Raw quotes: 원문 미확보로 직접 인용 불가.

- **Local Elections: Still Second-Order or in the Service of National Aspirations?**
  - 저자: Mihaela Ivănescu, Luiza-Maria Filimon
  - URL: https://cis01.ucv.ro/revistadestiintepolitice/files/numarul87_2025/10.pdf
  - Raw: `docs/references/raw/academic/cis01-ucv-ro-revistadestiintepolitice-files-numarul87_2025-1.md`
  - 요약: 2024년 루마니아 지방선거를 SOE 프레임으로 분석한다. 지방선거가 항상 second-order는 아니며, 선거 시기·정부 인기도·입법 개입 등 맥락에 따라 national aspirations의 도구로 1차 선거적 성격을 띨 수 있다고 주장한다.
  - PolitiKAST 활용 포인트: 배경/실험: 한국 지방선거도 nationalized local election 변수로 조정해야 한다는 근거.
  - Raw quotes: "cannot be considered the default"

- **PMC article on second-order/local elections**
  - 저자: unknown
  - URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC9912226/
  - Raw: `docs/references/raw/academic/pmc-ncbi-nlm-nih-gov-articles-PMC9912226-.md`
  - 요약: PMC가 reCAPTCHA/브라우저 확인으로 막혔다. 원문 내용을 확인하지 못했다.
  - PolitiKAST 활용 포인트: 접근 실패.
  - Raw quotes: 원문 미확보로 직접 인용 불가.

## Korean elections (split-ticket, valence)

- **Institutional Interaction and Strategic Voting in Korea’s New Mixed Electoral System** (✅ 본문 검증: 2026-04-26)
  - 저자/연도: Jungug Choi (2006, Journal of International and Area Studies 13(2): 111-122)
  - URL: https://s-space.snu.ac.kr/bitstream/10371/96444/1/7.Institutional-Interaction-and-Strategic-Voting-in-Koreas-New-Mixed-Electoral-System-JungugChoi.pdf
  - Raw: `docs/references/raw/academic/s-space-snu-ac-kr-bitstream-10371-96444-1-7-Institutional-In.md`
  - 요약: 2004년 한국 총선의 혼합형 선거제 도입 이후 SMD와 PR의 상호작용, 민주노동당 지지자의 전략투표를 분석한다. 소선거구에서는 여전히 전략투표가 유의하며, PR 동시선거가 소수정당 불리를 크게 완화하지 못한다고 본다.
  - PolitiKAST 활용 포인트: 배경/모델: 한국 유권자의 split-ticket/strategic voting 전이 규칙.
  - 핵심 인용: "no meaningful effect of institutional interaction"; "significant rate of strategic voting"

- **S-Space Korean election PDF item**
  - 저자: unknown
  - URL: https://s-space.snu.ac.kr/bitstream/10371/90256/1/2
  - Raw: `docs/references/raw/academic/s-space-snu-ac-kr-bitstream-10371-90256-1-2.md`
  - 요약: S-Space bitstream이 웹 fetch에서 Internal Error를 반환했다.
  - PolitiKAST 활용 포인트: 접근 실패.
  - Raw quotes: 원문 미확보로 직접 인용 불가.

- **Valence-related Korean election paper**
  - 저자: unknown
  - URL: https://scholarworks.bwise.kr/hanyang/bitstream/2021.sw.hanyang/197001/1/Valence
  - Raw: `docs/references/raw/academic/scholarworks-bwise-kr-hanyang-bitstream-2021-sw-hanyang-1970.md`
  - 요약: Hanyang scholarworks bitstream이 웹 fetch에서 Internal Error를 반환했다. URL상 valence voting 관련 논문으로 보이나 원문 확인 실패.
  - PolitiKAST 활용 포인트: 접근 실패.
  - Raw quotes: 원문 미확보로 직접 인용 불가.

- **선거결과 예측에 관한 연구: 19대 총선 종로구를 중심으로**
  - 저자: 김길수
  - URL: https://www.dbpia.co.kr/journal/articleDetail?nodeId=NODE02245487
  - Raw: `docs/references/raw/academic/www-dbpia-co-kr-journal-articleDetail-nodeId-NODE02245487.md`
  - 요약: 종로구 기존 선거자료와 휴리스틱 접근으로 19대 총선 결과를 예측한다. 단순 여론조사/출구조사뿐 아니라 지역구 특성과 투표자 수 기반 회귀식이 일정 수준의 예측력을 가질 수 있음을 보인다. 이번 canonical raw 재수집에서는 로컬 DNS 제한으로 curl 접근이 실패했다.
  - PolitiKAST 활용 포인트: 실험: 한국 지역구 단위 baseline forecasting 및 turnout-sensitive vote model.
  - Raw quotes: 원문 미확보로 직접 인용 불가.

- **자유로운 선거와 공정한 선거**
  - 저자: 류성진
  - URL: https://www.dbpia.co.kr/journal/articleDetail?nodeId=NODE09355965
  - Raw: `docs/references/raw/academic/www-dbpia-co-kr-journal-articleDetail-nodeId-NODE09355965.md`
  - 요약: 공직선거법상 여론조사 결과 공표 금지를 자유로운 선거와 공정한 선거의 충돌 관점에서 검토한다. 선거여론조사 등록·신고·표본 기준이 강화된 현재에는 7일 공표금지가 유권자의 알 권리와 공정성을 오히려 해칠 수 있다고 논한다. 이번 canonical raw 재수집에서는 로컬 DNS 제한으로 curl 접근이 실패했다.
  - PolitiKAST 활용 포인트: 배경: 한국 여론조사 공표규제와 poll information availability 변수.
  - Raw quotes: 원문 미확보로 직접 인용 불가.

- **사회-경제적 변수가 대통령 선거 득표율에 미치는 영향**
  - 저자: 정진영, 박배균
  - URL: https://www.dbpia.co.kr/journal/articleDetail?nodeId=NODE11724875
  - Raw: `docs/references/raw/academic/www-dbpia-co-kr-journal-articleDetail-nodeId-NODE11724875.md`
  - 요약: 17대~20대 대선의 서울 행정동별 득표와 사회경제 변수를 OLS로 분석한다. 부동산 실거래가와 대졸 이상 비율이 민주당·보수당 계열 후보 득표율에 일관된 방향으로 작용해 부동산/계급투표 강화 가능성을 보인다. 이번 canonical raw 재수집에서는 로컬 DNS 제한으로 curl 접근이 실패했다.
  - PolitiKAST 활용 포인트: 모델/실험: 서울 행정동 socio-economic covariate와 후보 득표 prior.
  - Raw quotes: 원문 미확보로 직접 인용 불가.

- **Malk: 법령 데이터 기반의 지식 그래프를 활용한 멀티 에이전트 프레임워크 제안**
  - 저자: 박선화, 최승민, 정유철
  - URL: https://www.dbpia.co.kr/journal/articleDetail?nodeId=NODE12025121
  - Raw: `docs/references/raw/academic/www-dbpia-co-kr-journal-articleDetail-nodeId-NODE12025121.md`
  - 요약: 한국 법령 데이터를 구조화해 KG를 만들고 RAG 기반 multi-agent framework를 구성하는 Malk를 제안한다. 선거 논문은 아니지만 한국어 법령/정책 텍스트 KG와 multi-agent RAG 구현의 국내 선례다. 이번 canonical raw 재수집에서는 로컬 DNS 제한으로 curl 접근이 실패했다.
  - PolitiKAST 활용 포인트: 모델: 공약·법령·정책 KG와 agent 역할 분담 설계.
  - Raw quotes: 원문 미확보로 직접 인용 불가.

- **한국선거예측의 방법론적 모색**
  - 저자: unknown
  - URL: https://kiss.kstudy.com/Detail/Ar?key=10903
  - Raw: `docs/references/raw/academic/kiss-kstudy-com-Detail-Ar-key-10903.md`
  - 요약: KISS 메타데이터/일부 본문에 따르면 단순 조사응답만으로 선거결과를 예측하는 한계를 지적하고, 투표선택 결정요인에 대한 인과적 연구와 한국 선거 일반이론 확립이 필요하다고 주장한다. 이번 canonical raw 재수집에서는 로컬 DNS 제한으로 curl 접근이 실패했다.
  - PolitiKAST 활용 포인트: 배경: 단순 poll prediction보다 causal voter-behavior model이 필요하다는 주장.
  - Raw quotes: 원문 미확보로 직접 인용 불가.

- **AccessON PDF ATN0004015411**
  - 저자: unknown
  - URL: https://accesson.kisti.re.kr/archive/pdfDown.do?arti_id=ATN0004015411
  - Raw: `docs/references/raw/academic/accesson-kisti-re-kr-archive-pdfDown-do-arti_id-ATN000401541.md`
  - 요약: KISTI AccessON PDF 다운로드 URL이 웹 fetch에서 Internal Error를 반환했다.
  - PolitiKAST 활용 포인트: 접근 실패.
  - Raw quotes: 원문 미확보로 직접 인용 불가.

- **Inha download item 122958**
  - 저자: unknown
  - URL: https://eee.inha.ac.kr/bbs/eee/3919/122958/download.do
  - Raw: `docs/references/raw/academic/eee-inha-ac-kr-bbs-eee-3919-122958-download-do.md`
  - 요약: Inha download URL이 웹 fetch에서 Internal Error를 반환했다.
  - PolitiKAST 활용 포인트: 접근 실패.
  - Raw quotes: 원문 미확보로 직접 인용 불가.

- **Determinants of Split Ticket Voting - The Case of South Korea** (✅ 본문 검증: 2026-04-26)
  - 저자/연도: 로컬 Kyobo raw에 저자 미표시 (2007, 신아세아 제14권 제4호: 238-261)
  - URL: https://scholar.kyobobook.co.kr/article/detail/4010021624486
  - Raw: `docs/references/raw/academic/scholar-kyobobook-co-kr-article-detail-4010021624486.md`
  - 요약: 2004년 국회의원 선거에서 약 20%의 한국 유권자가 지역구 후보와 비례대표 정당을 다르게 선택한 원인을 분석한다. 약한 당파심, 정부 성과 불만, 진보 이념, 대학생 집단이 분할투표와 관련된다고 요약된다.
  - PolitiKAST 활용 포인트: 배경/모델: split-ticket probability와 개인 특성 기반 voting rule.
  - 핵심 인용: "약 20%가 분할투표"; "weak partisanship and low satisfaction"

## Knowledge graphs / political ontologies

- **OntoKG: Ontology-Oriented Knowledge Graph Construction with Intrinsic-Relational Routing**
  - 저자: Prorata AI / OntoKG authors
  - URL: https://arxiv.org/html/2604.02618v1
  - Raw: `docs/references/raw/academic/arxiv-org-html-2604-02618v1.md`
  - 요약: Wikidata 규모의 KG를 intrinsic 속성과 relational edge로 라우팅해 모듈형 ontology schema를 만드는 방법을 제안한다. 정치 KG 자체 논문은 아니지만 PolitiKAST에서 후보·정당·이슈 속성과 관계를 분리하는 schema 원칙에 유용하다.
  - PolitiKAST 활용 포인트: 모델: entity 속성/관계 schema 분리와 LLM-guided extraction 설계.
  - Raw quotes: "intrinsic-relational routing"

- **Knowledge Graph Representation for Political Information Sources**
  - 저자: ACL PoliticalNLP authors
  - URL: https://arxiv.org/html/2404.03437v1
  - Raw: `docs/references/raw/academic/arxiv-org-html-2404-03437v1.md`
  - 요약: Breitbart와 New York Times 기사 텍스트에서 NER와 OpenIE로 entity hypergraph를 만들고, edge에 빈도·감성·주관성을 부여해 정치 뉴스 소스 차이를 비교한다. PolitiKAST의 정치 이벤트/인물 관계 KG 구축 선례다.
  - PolitiKAST 활용 포인트: 모델: 정치 뉴스 기반 KG, sentiment/subjectivity edge feature 설계.
  - Raw quotes: "frequency, polarity, and subjectivity"

- **Knowledge Graph Representation for Political Information Sources**
  - 저자: ACL Anthology metadata
  - URL: https://aclanthology.org/2024.politicalnlp-1.6/
  - Raw: `docs/references/raw/academic/aclanthology-org-2024-politicalnlp-1-6-.md`
  - 요약: PoliticalNLP 워크숍 논문의 ACL Anthology 페이지. 정치 뉴스 소스에서 KG를 구성해 미디어 담론 차이를 분석하는 연구의 공식 메타데이터다.
  - PolitiKAST 활용 포인트: 배경/모델: 정치 정보원별 KG 비교의 공식 출처.
  - Raw quotes: "Political Information Sources"

- **Towards Computable and Explainable Policies Using Semantic Web Standards**
  - 저자: OpenReview paper authors
  - URL: https://openreview.net/pdf?id=i4Jcu0p87D
  - Raw: `docs/references/raw/academic/openreview-net-pdf-id-i4Jcu0p87D.md`
  - 요약: 정책 문서를 semantic web standards로 계산 가능하고 설명 가능한 형태로 표현하는 논문. 선거공약/정책의 구조화와 설명 가능한 rule/KG 표현에 보조적으로 유용하다. 이번 canonical raw 재수집에서는 로컬 DNS 제한으로 curl 접근이 실패했다.
  - PolitiKAST 활용 포인트: 모델: 정책 claim을 KG/RDF 스타일로 구조화하는 근거.
  - Raw quotes: 원문 미확보로 직접 인용 불가.

- **Building Event-Centric Knowledge Graphs from News**
  - 저자: Marco Rospocher et al.
  - URL: https://adimen.ehu.eus/~rigau/publications/jws2016.pdf
  - Raw: `docs/references/raw/academic/adimen-ehu-eus-~rigau-publications-jws2016-pdf.md`
  - 요약: 뉴스 기사에서 event-centric KG를 자동 구축하는 방법을 제안한다. 사건을 중심 노드로 두고 참여자·시간·장소·출처를 연결해 장기적인 스토리라인과 다중 출처 provenance를 재구성한다.
  - PolitiKAST 활용 포인트: 모델: 선거 뉴스/스캔들/공약 이벤트를 시간축 KG로 표현하는 핵심 근거.
  - Raw quotes: "Event-Centric Knowledge Graphs"

- **PODIO: A Political Discourse Ontology**
  - 저자: PODIO authors
  - URL: https://ceur-ws.org/Vol-3967/PD_paper_159.pdf
  - Raw: `docs/references/raw/academic/ceur-ws-org-Vol-3967-PD_paper_159-pdf.md`
  - 요약: 정치 담론을 표현하기 위한 ontology 논문. 정치적 actor, claim, discourse object 등을 구조화하는 방향으로 PolitiKAST의 political ontology 설계에 참고할 수 있다.
  - PolitiKAST 활용 포인트: 모델: 후보·정당·정책·담론 엔티티 ontology 설계.
  - Raw quotes: "Political Discourse Ontology"

- **Agent-Based Simulations of Online Political Discussions**
  - 저자: Abdul Sittar et al.
  - URL: https://ceur-ws.org/Vol-3977/SemGenAge-6.pdf
  - Raw: `docs/references/raw/academic/ceur-ws-org-Vol-3977-SemGenAge-6-pdf.md`
  - 요약: 철회된 arXiv 논문과 유사한 CEUR PDF. 독일 선거 관련 온라인 정치토론을 에이전트 기반으로 시뮬레이션하며 대화 이력, 동기, 자원 제약을 포함한다. 이번 canonical raw 재수집에서는 로컬 DNS 제한으로 curl 접근이 실패했다.
  - PolitiKAST 활용 포인트: 배경: 온라인 담론 에이전트와 선거 시뮬레이션 연결 사례.
  - Raw quotes: 원문 미확보로 직접 인용 불가.

- **Leverage Knowledge Graph and LLM for Law Article Recommendation**
  - 저자: Moonlight AI review
  - URL: https://www.themoonlight.io/ko/review/leverage-knowledge-graph-and-large-language-model-for-law-article-recommendation-a-case-study-of-chinese-criminal-law
  - Raw: `docs/references/raw/academic/www-themoonlight-io-ko-review-leverage-knowledge-graph-and-l.md`
  - 요약: 중국 형법 조항 추천 사례에서 KG와 LLM을 결합하는 접근을 요약한다. 법률/정책 텍스트에서 구조화 지식을 만들고 LLM 추천을 보강하는 설계는 공약-이슈-법령 retrieval에 참고된다.
  - PolitiKAST 활용 포인트: 모델: KG+LLM RAG 기반 근거 검색과 추천/인용 설계.
  - Raw quotes: "Knowledge Graph and Large Language Model"

- **Supporting Newsrooms with Journalistic Knowledge Graph Platforms**
  - 저자: paper authors
  - URL: https://pdfs.semanticscholar.org/1e42/7bdafe3c01586cf6d0dfc930dc0259c2a72b.pdf
  - Raw: `docs/references/raw/academic/pdfs-semanticscholar-org-1e42-7bdafe3c01586cf6d0dfc930dc0259.md`
  - 요약: 뉴스룸에서 KG 플랫폼이 취재, 스토리 탐색, entity linking, provenance 관리를 어떻게 지원할 수 있는지 정리한다. 선거 뉴스 기반 지식증강과 설명 가능한 대시보드에 관련된다.
  - PolitiKAST 활용 포인트: 배경/모델: journalistic KG와 source provenance UI 설계.
  - Raw quotes: "Journalistic Knowledge Graph"

## Knowledge cutoff & temporal reasoning

- **Dated Data: Tracing Knowledge Cutoffs in Large Language Models**
  - 저자: Moonlight AI review
  - URL: https://www.themoonlight.io/ko/review/dated-data-tracing-knowledge-cutoffs-in-large-language-models
  - Raw: `docs/references/raw/academic/www-themoonlight-io-ko-review-dated-data-tracing-knowledge-c.md`
  - 요약: LLM의 지식 컷오프를 dated data로 추적하는 논문 리뷰. 시간별 사실을 사용해 모델이 어느 시점까지의 정보를 학습했는지 추정하는 문제를 다룬다. PolitiKAST는 최신 선거/여론조사 정보를 KG와 retrieval로 보강해야 한다.
  - PolitiKAST 활용 포인트: 배경/모델: knowledge cutoff와 temporal grounding 필요성.
  - Raw quotes: "Knowledge Cutoffs"

- **Knowledge Cutoff(지식 컷오프)란?**
  - 저자: inblog glossary
  - URL: https://inblog.ai/ko/glossary/knowledge-cutoff
  - Raw: `docs/references/raw/academic/inblog-ai-ko-glossary-knowledge-cutoff.md`
  - 요약: 지식 컷오프의 의미를 한국어로 설명하는 글. 모델이 훈련 데이터의 마지막 시점 이후 사건을 모를 수 있으므로 최신 정보가 필요한 작업에서는 검색/RAG가 필요하다는 일반 배경으로 활용한다.
  - PolitiKAST 활용 포인트: 서론/배경: 최신 한국 지방선거 맥락에 retrieval이 필요한 이유.
  - Raw quotes: "지식 컷오프"

## Voter behavior / opinion dynamics

- **Mebane working paper mw18A**
  - 저자: Walter R. Mebane Jr.
  - URL: http://websites.umich.edu/~wmebane/mw18A.pdf
  - Raw: `docs/references/raw/academic/websites-umich-edu-~wmebane-mw18A-pdf.md`
  - 요약: Michigan의 Walter Mebane 선거/투표행태 관련 PDF로 접근은 성공했으나 도구 출력에서 제목 세부를 확인하지 못했다. 선거자료 통계와 이상탐지/투표행태 분석 맥락의 참고문헌으로 분류한다.
  - PolitiKAST 활용 포인트: 실험: 선거 데이터 통계 진단 보조.
  - Raw quotes: "mw18A"

- **CCA_Hill0424 working paper**
  - 저자: HEC Hill
  - URL: https://people.hec.edu/hill/wp-content/uploads/sites/25/2023/05/CCA_Hill0424.pdf
  - Raw: `docs/references/raw/academic/people-hec-edu-hill-wp-content-uploads-sites-25-2023-05-CCA_.md`
  - 요약: HEC의 Hill PDF는 접근 성공했으나 제목 세부를 도구 출력에서 확인하지 못했다. URL상 2024년판 working paper이며 voter behavior/choice aggregation 범주 보조 문헌으로 보관한다.
  - PolitiKAST 활용 포인트: 배경: voter choice/collective choice 관련 추가 확인 필요 문헌.
  - Raw quotes: "CCA_Hill0424"

- **ACM DOI 10.5555/3545946.3599059**
  - 저자: unknown
  - URL: https://dl.acm.org/doi/10.5555/3545946.3599059
  - Raw: `docs/references/raw/academic/dl-acm-org-doi-10-5555-3545946-3599059.md`
  - 요약: ACM DOI 페이지가 웹 fetch에서 Internal Error를 반환했다.
  - PolitiKAST 활용 포인트: 접근 실패.
  - Raw quotes: 원문 미확보로 직접 인용 불가.

- **ACM DOI abs 10.5555/3545946.3599059**
  - 저자: unknown
  - URL: https://dl.acm.org/doi/abs/10.5555/3545946.3599059
  - Raw: `docs/references/raw/academic/dl-acm-org-doi-abs-10-5555-3545946-3599059.md`
  - 요약: ACM abstract URL도 접근 실패로 분류했다.
  - PolitiKAST 활용 포인트: 접근 실패.
  - Raw quotes: 원문 미확보로 직접 인용 불가.

- **University of Stirling Technical Report TR168**
  - 저자: Ken Turner / Stirling technical report series
  - URL: https://www.cs.stir.ac.uk/~kjt/techreps/pdf/TR168.pdf
  - Raw: `docs/references/raw/academic/www-cs-stir-ac-uk-~kjt-techreps-pdf-TR168-pdf.md`
  - 요약: TR168 PDF가 웹 fetch에서 Internal Error를 반환했다.
  - PolitiKAST 활용 포인트: 접근 실패.
  - Raw quotes: 원문 미확보로 직접 인용 불가.

- **University of Stirling Technical Report TR169**
  - 저자: Ken Turner / Stirling technical report series
  - URL: https://www.cs.stir.ac.uk/~kjt/techreps/pdf/TR169.pdf
  - Raw: `docs/references/raw/academic/www-cs-stir-ac-uk-~kjt-techreps-pdf-TR169-pdf.md`
  - 요약: TR169 PDF 접근 성공. 도구 출력상 Microsoft Word 변환 PDF이며, multi-agent/social simulation 또는 voting protocol 관련 기술보고서로 분류된다. 세부 제목은 후속 수동 확인이 필요하다.
  - PolitiKAST 활용 포인트: 모델: agent protocol/voting process 참고 후보.
  - Raw quotes: "TR169"

- **DI FC UL workshop file**
  - 저자: unknown
  - URL: https://www.di.fc.ul.pt/~fjmc/files/workshop
  - Raw: `docs/references/raw/academic/www-di-fc-ul-pt-~fjmc-files-workshop.md`
  - 요약: 웹 도구 호출 한도와 로컬 DNS 제한 때문에 원문 확인 실패.
  - PolitiKAST 활용 포인트: 접근 실패.
  - Raw quotes: 원문 미확보로 직접 인용 불가.

- **Moreira 2011 power PDF**
  - 저자: Silvio Amir / Moreira
  - URL: https://www.silvioamir.com/assets/pdf/moreira2011power.pdf
  - Raw: `docs/references/raw/academic/www-silvioamir-com-assets-pdf-moreira2011power-pdf.md`
  - 요약: moreira2011power.pdf 접근 성공. 파일명상 power/voting 관련 논문으로 보이며, 도구 출력에서 제목 세부는 확인하지 못했다. voter behavior/collective choice 후보 문헌으로 보관한다.
  - PolitiKAST 활용 포인트: 배경: power index 또는 collective decision 관련 보조 문헌 확인 후보.
  - Raw quotes: "power"

- **CEU 2025 thesis draft**
  - 저자: Ghadena Hgaig
  - URL: https://www.etd.ceu.edu/2025/hgaig_ghadena.pdf
  - Raw: `docs/references/raw/academic/www-etd-ceu-edu-2025-hgaig_ghadena-pdf.md`
  - 요약: CEU 2025 PDF 접근 성공. 5쪽 분량의 draft로 확인되며, voter behavior/turnout 관련 학위논문 초안 또는 연구노트로 분류된다. 세부 제목은 후속 확인 필요.
  - PolitiKAST 활용 포인트: 배경: 최신 voter behavior 논의 후보 문헌.
  - Raw quotes: "draft"

- **The Greek Semantic Parliament portal PDF**
  - 저자: unknown
  - URL: https://cdn6.f-cdn.com/files/download/287157208/thegreeksemanticparliamentport.pdf
  - Raw: `docs/references/raw/academic/cdn6-f-cdn-com-files-download-287157208-thegreeksemanticparl.md`
  - 요약: CDN PDF가 웹 fetch에서 Internal Error를 반환했다.
  - PolitiKAST 활용 포인트: 접근 실패.
  - Raw quotes: 원문 미확보로 직접 인용 불가.

## 접근 실패

- http://webhotel4.ruc.dk/~henning/publications/PoliticalContext.pdf — 웹 fetch에서 Internal Error. URL 제목상 정치적 맥락 관련 PDF로 보이나 원문을 확인하지 못했다.
- https://accesson.kisti.re.kr/archive/pdfDown.do?arti_id=ATN0004015411 — KISTI AccessON PDF 다운로드 URL이 웹 fetch에서 Internal Error를 반환했다.
- https://cdn6.f-cdn.com/files/download/287157208/thegreeksemanticparliamentport.pdf — CDN PDF가 웹 fetch에서 Internal Error를 반환했다.
- https://ceur-ws.org/Vol-3977/SemGenAge-6.pdf — curl error 6: curl: (6) Could not resolve host: ceur-ws.org
- https://dl.acm.org/doi/10.5555/3545946.3599059 — ACM DOI 페이지가 웹 fetch에서 Internal Error를 반환했다.
- https://dl.acm.org/doi/abs/10.5555/3545946.3599059 — ACM abstract URL도 접근 실패로 분류했다.
- https://eee.inha.ac.kr/bbs/eee/3919/122958/download.do — Inha download URL이 웹 fetch에서 Internal Error를 반환했다.
- https://faculty.haas.berkeley.edu/rjmorgan/Information — curl error 6: curl: (6) Could not resolve host: faculty.haas.berkeley.edu
- https://github.com/amazingljy1206/ElectionSim — curl error 6: curl: (6) Could not resolve host: github.com
- https://hal.science/hal-04862262v1/file/226.pdf — HAL이 Anubis Access Denied를 반환했다. 원문 제목과 내용을 확인하지 못했다.
- https://kiss.kstudy.com/Detail/Ar?key=10903 — curl error 6: curl: (6) Could not resolve host: kiss.kstudy.com
- https://openreview.net/pdf?id=i4Jcu0p87D — curl error 6: curl: (6) Could not resolve host: openreview.net
- https://pmc.ncbi.nlm.nih.gov/articles/PMC9246136/ — PMC 페이지가 reCAPTCHA/브라우저 확인으로 막혔다. 동일 DOI의 PLOS 원문과 printable PDF에서 필요한 정보를 확보했다.
- https://pmc.ncbi.nlm.nih.gov/articles/PMC9912226/ — PMC가 reCAPTCHA/브라우저 확인으로 막혔다. 원문 내용을 확인하지 못했다.
- https://s-space.snu.ac.kr/bitstream/10371/90256/1/2 — S-Space bitstream이 웹 fetch에서 Internal Error를 반환했다.
- https://s-space.snu.ac.kr/bitstream/10371/96444/1/7.Institutional-Interaction-and-Strategic-Voting-in-Koreas-New-Mixed-Electoral-System-JungugChoi.pdf — curl error 6: curl: (6) Could not resolve host: s-space.snu.ac.kr
- https://scholarworks.bwise.kr/hanyang/bitstream/2021.sw.hanyang/197001/1/Valence — Hanyang scholarworks bitstream이 웹 fetch에서 Internal Error를 반환했다. URL상 valence voting 관련 논문으로 보이나 원문 확인 실패.
- https://ui.adsabs.harvard.edu/abs/2022PLoSO..1770194G/abstract — NASA ADS 상세 레코드는 웹 fetch에서 Internal Error가 발생했다. 동일 논문의 PLOS 원문과 PDF는 접근 가능하므로 학술 메타데이터 보조 출처로만 취급한다.
- https://www.aeaweb.org/conference/2020/preliminary/paper/i4a3Qy36 — curl error 6: curl: (6) Could not resolve host: www.aeaweb.org
- https://www.cs.stir.ac.uk/~kjt/techreps/pdf/TR168.pdf — TR168 PDF가 웹 fetch에서 Internal Error를 반환했다.
- https://www.dbpia.co.kr/journal/articleDetail?nodeId=NODE02245487 — curl error 6: curl: (6) Could not resolve host: www.dbpia.co.kr
- https://www.dbpia.co.kr/journal/articleDetail?nodeId=NODE09355965 — curl error 6: curl: (6) Could not resolve host: www.dbpia.co.kr
- https://www.dbpia.co.kr/journal/articleDetail?nodeId=NODE11724875 — curl error 6: curl: (6) Could not resolve host: www.dbpia.co.kr
- https://www.dbpia.co.kr/journal/articleDetail?nodeId=NODE12025121 — curl error 6: curl: (6) Could not resolve host: www.dbpia.co.kr
- https://www.di.fc.ul.pt/~fjmc/files/workshop — 웹 도구 호출 한도와 로컬 DNS 제한 때문에 원문 확인 실패.
- https://www.marcelgarz.com/wp-content/uploads/Political-Scandals-Apr2019-web.pdf — curl error 6: curl: (6) Could not resolve host: www.marcelgarz.com
