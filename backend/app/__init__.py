"""PolitiKAST FastAPI backend.

3 router groups:
  - public/   : 인증 없음, slowapi rate limit. 시청자/연구자용 read-only API.
  - admin/    : JWT bearer. frontend stream 이 핸들러 작성.
  - internal/ : 정적 service token. 외부 시뮬레이터가 결과 업로드.

도메인 로직은 `src/` 의 SoT 를 그대로 호출. 본 패키지는 dispatch + DTO 변환만.
"""
