# Reference refetch toolkit

Codex가 작성한 `docs/references/raw/` 의 일부 raw 파일은 fetch 실패 로그 + 사전지식
요약입니다 (이 호스트의 DNS 차단 + pandoc/pdftotext 부재 때문). 이 스크립트는
DNS 정상 호스트에서 raw 파일을 다시 받아 갱신합니다.

## 빠른 사용법

```bash
# 1) 다른 호스트(DNS 정상)에서 레포 클론 후
cd cmux-hackathon-politicast

# 2) 기본 실행: 4개 카테고리 전체 재fetch + 리포트
python3 scripts/refs/refetch_references.py

# 3) 실패로 의심되는 raw 파일만 재fetch (작은 파일/실패 헤더 휴리스틱)
python3 scripts/refs/refetch_references.py --only-failed

# 4) 특정 카테고리만
python3 scripts/refs/refetch_references.py --category tooling
python3 scripts/refs/refetch_references.py --category academic --category tooling

# 5) 어떤 URL이 처리될지 미리 보기
python3 scripts/refs/refetch_references.py --only-failed --dry-run
```

## 의존성

스크립트가 없으면 자동으로 레포 루트의 `.venv`를 만들고 그 안에 `pip install` 한 뒤
해당 Python으로 재실행합니다. Homebrew Python처럼 PEP 668
`externally-managed-environment`가 걸린 호스트에서도 시스템 Python을 건드리지 않습니다.

- `requests` — HTTP fetch
- `markdownify` + `beautifulsoup4` — HTML → Markdown 변환
- `pypdf` — PDF 텍스트 추출

자동 설치를 막고 싶으면 `--no-install` 추가 후 직접:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install requests markdownify beautifulsoup4 pypdf
```

## 출력

- `docs/references/raw/<category>/<slug>.md` — URL별 raw 콘텐츠가 갱신됩니다.
  - 첫 줄: `# Source: <원본 URL>`
  - HTML이었으면 markdown 변환 결과
  - PDF였으면 텍스트 추출 결과
- `docs/references/refetch-report.md` — 카테고리별 성공/실패 요약 표 + 실패 URL 사유 목록.

## 동작

1. `docs/references/manifests/<category>.txt` 에서 URL 추출 (주석은 무시).
2. `--only-failed`면 기존 raw 파일이 다음 중 하나일 때만 재fetch:
   - 파일이 없거나
   - 파일 크기 < 800 bytes
   - `<!-- FETCH FAILED ... -->` / `Could not resolve host` / `# Source:` 만 있고 본문 비어있음
3. 도메인별로 1.5초 간격을 두고, 도메인 간은 병렬(최대 4개) fetch.
4. Content-Type 보고 변환:
   - `application/pdf` → `pypdf` 텍스트 추출
   - `text/html` / `application/xml` → `markdownify`
   - 그 외 → 원문 그대로
5. 변환 실패 시에도 raw에 `# Source` 헤더 + 에러 사유 기록.

## 한계

- 동적 페이지(JavaScript 필수)는 본문이 비어 보일 수 있음 — 그런 경우 KB의 *접근 실패* 섹션에 별도 메모.
- 일부 사이트(인스타그램, 페이스북 등)는 로그인 없이는 항상 빈 본문을 반환. manifest에서 이미 일부 제외했지만 남아있는 게 있다면 보고서에서 확인 후 수동 처리.
- 한국 뉴스 사이트(예: chosun, daum)는 봇 차단으로 403 발생 가능 — `User-Agent`는 일반 Chrome으로 설정했지만 IP 차단까진 못 우회.

## 검증 후 다음 단계

`docs/references/refetch-report.md` 를 보고:

- TOTAL OK 비율이 90% 이상이면 raw 자료가 신뢰할 수 있는 상태.
- 카테고리별 실패가 많으면 해당 KB(`docs/references/kb/<category>.md`) 의 "## 접근 실패" 섹션과 대조해 paper-writer 가 인용 여부 판단.
- raw 가 갱신된 후 KB 본문도 보강이 필요하면 `update-paper` 스킬 / paper-writer 에이전트로 패치.
