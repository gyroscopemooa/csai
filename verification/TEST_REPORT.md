# v0.3 기능 및 UI 검증 결과

- pytest: **37/37 통과** (v0.2의 32개 + 예약 복구/이메일 워커 4개 + 백업 1개)
- Python 컴파일 및 JavaScript 문법 확인: PASS
- Chromium UI + ASGI API 테스트 브리지: PASS, JS 페이지 오류 0개, 캡처 26개
- 예약 복구 발급 → 새 고객 세션 복구 → 원래 세션으로 재이전 → 기존 취소 및 승인 흐름을 브라우저에서 확인.
- 코드 재발급/만료/일회용/업체별 분리/기존 예약 변경 권한 제거/기존 상담 대화 미공개 검증.
- 이메일 워커: 데모 실제 발송 차단, 동일 이벤트 중복 처리 방지, 설정 OFF 존중. Resend 실계정 미검증.
- 로컬 SQLite 백업 무결성 및 덮어쓰기 금지 검증.
- UI: 기존 메뉴, 상담·교육·요금·예약·업무·채널·상담원·테스트 결제 기능을 유지. 흰 카드, 둥근 입력 및 모바일 입력창 개선. 390px 화면 가로 넘침 검사 포함.

테스트는 임시 SQLite DB와 외부 모의 응답만 사용합니다. 실제 PG 결제, OpenAI 호출, Google/네이버/카카오/Resend 실연동, 운영 Supabase 전환, 웹 푸시/SMS/알림톡 실발송 및 공개 배포는 완료되지 않았습니다. 직접 HTTP 브라우저 E2E는 별도 환경에서 확인해야 합니다. v0.2의 직접 HTTP smoke 검증은 과거 결과이며 이번 버전에는 아래 별도 smoke 결과를 기록합니다.
- v0.3 직접 HTTP smoke: PASS (홈, 데모 로그인, 잔액 조회, JS 정적 파일).

## v0.4 motion regression
- `node --check web/app.js`: PASS.
- `python -m pytest -q`: 37 passed.
- `python tests/browser_check.py`: PASS, 26 captures, no page errors (ASGI bridge).
- Live external integration and production deployment were not tested. Motion reference sites were consulted, but no external paid templates or MCP services were installed.

## v0.5 controlled trial and deployment regression (2026-11-25)
- `python -m pytest -q`: **39 passed**. Operator-only local access, invite trial allocation, invitation limit controls, credit deductions, model cost ledger, and container health checks are covered.
- `node --check web/app.js`: PASS.
- `python tests/browser_check.py`: PASS, 26 captures, no page errors. The 390px mobile viewport and booking prefill path were exercised through the ASGI test bridge.
- The Cloudflare Container project type check completed. Image deployment was not performed from this computer because Docker CLI/Desktop is not installed; production external integrations remain intentionally unverified.

## 채팅·메뉴 UI 재검증 (2026-11-26)
- 로컬 주소와 서버 허용 Origin을 모두 `http://127.0.0.1:3000`으로 맞춰 브라우저 채팅의 403 오류를 수정했습니다.
- `python -m pytest -q`: **40 passed**. `node --check web/app.js`: PASS.
- `python tests/browser_check.py`: PASS, 26개 화면, JavaScript 페이지 오류 0개.
- `python tests/live_ui_smoke.py`: 실제 localhost HTTP로 데스크톱 채팅 전송, 사이드바 이동, 채팅창 크기 변경, 390px 모바일 입력, 무료 계정의 업체 이미지 업로드·표시를 확인했습니다. 결과: `live_ui_smoke.json`.
- 다른 사이트의 Origin으로 보낸 변경 요청은 403, 허용 Origin의 미인증 요청은 401로 확인했습니다.
- 외부 OAuth 및 Cloudflare 배포 후의 로그인·AI 응답은 이 로컬 검증 범위에 포함되지 않습니다.
