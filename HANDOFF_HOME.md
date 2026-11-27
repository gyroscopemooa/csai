# CS AI 최종 인계 — 2026-11-26

## 1. 반드시 이 버전에서 이어서 작업

- 저장소: https://github.com/gyroscopemooa/csai
- 개발 브랜치: feat/pricing-increase-1127
- 기존 main: 3e7a11f736a2dfedc28489ba162b0cc12a216558 (기존 디자인 및 로그인 보존)
- PR: https://github.com/gyroscopemooa/csai/pull/1 (draft, 미병합)
- 인계 최신 작업: 현재 브랜치 HEAD 확인 (이 문서의 과거 커밋 수 및 PR은 참고만)
- 최신 main 대비 상태는 git rev-list --left-right --count origin/main...HEAD 로 확인.
- 기존 dev 주소: https://csai.jeonmeensoo.workers.dev (최신 브랜치 배포 미확인)
- 최신 소스는 반드시 GitHub 브랜치에서 가져온다. 과거 ZIP을 풀어 덮어쓰지 않는다.
- 최신 검수표 FEATURE_CHECKLIST.md, 배포/이전 절차 DEPLOY_DEV.md, 설정 기준 .env.example.
- README의 이전 버전 테스트 결과 및 미구현 목록은 현재 브랜치의 검증 결과가 아니다.

## 2. PC GUI에 붙여 넣을 명령문

> CS AI 저장소 gyroscopemooa/csai의 feat/pricing-increase-1127 브랜치에 모바일에서 개발한 최신 코드가 저장돼 있다. 처음부터 재개발하지 말고 현재 로컬 작업 및 미커밋 변경을 먼저 확인하여 보존하고, 최신 브랜치를 받아 기존 UI/기능을 유지한 채 이어서 개발해라. HANDOFF_HOME.md, FEATURE_CHECKLIST.md, DEPLOY_DEV.md, .env.example부터 읽어라.
>
> 기존 main을 강제 reset하거나 덮어쓰지 말고 별도 개발 브랜치에서 수정해라. 상단 랜딩, 로그인, 사이드바 및 기존 style.css를 유지하고, 새 하단 01~04 장점 카드가 제대로 보이는지 확인해라. 웹앱에 반짝이·이모지·AI 장식 아이콘은 넣지 마라. 로컬은 3000 포트로 열고 GUI 브라우저로 PC/모바일을 확인해라.
>
> 먼저 격리된 SQLite 테스트 환경에서 Python 전체 컴파일, JS 구문 검사, pytest 전체 실행 및 실제 브라우저 테스트를 진행해라. 실패를 숨기거나 테스트를 삭제하지 말고 원인을 고쳐라. 전체 기능·권한·사용량·크레딧·예약 충돌·결제 실패 및 환불 회수·업체별 데이터 분리를 검증해라. 실제 API 모델 ID와 단가는 공식 문서 및 계정 가용성으로 확인해라.
>
> 그다음 CS AI 전용 Supabase 프로젝트에만 SQL과 DATABASE_URL을 설정하고 PostgreSQL 실제 연결 및 재시작 후 데이터 유지, 기존 데이터 이전 필요 여부를 검증해라. 다른 프로젝트를 수정하지 마라. 필요한 환경변수와 OAuth URI를 한 번에 목록으로 보고하고 누락값은 비공개 설정에서만 등록해라. 외부 서비스 및 실결제는 제공자 승인과 테스트를 마치기 전까지 비활성화해라. PG는 실제 공급자 확정 후 결제 승인/실패/웹훅/중복 지급 방지/환불/구독 갱신/해지까지 개발해라.
>
> 전체 검증이 성공하면 개발 브랜치에서 커밋·푸시하고 Cloudflare Containers dev Worker 배포를 진행해라. 기존 DB와 환경변수를 보존하고 실제 배포 결과 URL, /health, 로그인, 랜딩 하단까지 확인해라. 실패하면 원인과 필요한 설정을 명확히 보고하고 main 병합이나 운영 배포는 검증 후에만 진행해라. 각 단계마다 개발/테스트 체크표를 갱신하고 실제 수행한 작업만 완료로 표시해라.

## 3. 실행 순서

### A. 기존 작업 보존 및 소스 준비
저장소 루트에서 git status, git remote -v를 먼저 확인한다.
미커밋 작업은 별도로 보존한다. 기존 브랜치를 변경할 때 충돌 위험이 있으면 새 worktree를 사용한다.
```sh
git fetch origin
git switch feat/pricing-increase-1127
git pull --ff-only origin feat/pricing-increase-1127
git log -1 --oneline
```
로컬에 브랜치가 없으면 git switch --track origin/feat/pricing-increase-1127.
강제 reset, force push, 기존 작업 삭제 금지.

### B. 로컬 실행 및 테스트
기존 .env를 덮어쓰지 말고 테스트 전용 DATA_DIR 및 환경을 준비한다.
Windows PowerShell에서 Python 가상환경 설치 후:
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:DEMO_MODE="1"
$env:SHARED_TEST_MODE="0"
$env:CSAI_DB_BACKEND="sqlite"
$env:DATA_DIR="./data/gui-test"
$env:APP_URL="http://127.0.0.1:3000"
$env:OPENAI_API_KEY=""
$env:DATABASE_URL=""
$env:ENABLE_BACKGROUND_WORKER="0"
$env:ENABLE_CHANNEL_WEBHOOKS="0"
$env:ENABLE_LIVE_EMAIL="0"
$env:ENABLE_LIVE_PUSH="0"
$env:ENABLE_LIVE_MESSAGES="0"
$env:ENABLE_CUSTOM_DOMAINS="0"
.\.venv\Scripts\python.exe -m compileall -q app.py store.py ai.py billing.py postgres_store.py
node --check web/app.js
node --check web/widget.js
node --check web/push-sw.js
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 3000
```
실제 발송/외부 자동 워커를 모두 끈 별도 환경에서만 실행한다. 기존 .env의 값이 테스트에 흘러들지 않도록 확인한다.
브라우저: http://127.0.0.1:3000
포트 사용 중이면 3001로 바꾸고 APP_URL도 같은 포트로 맞춘다.
검증은 mock 및 테스트 DB부터. 실제 API 키 연결은 별도 단계다.
GitHub Actions 최신 전체 테스트는 실패 상태이고 실행 단계/로그가 조회되지 않았다.
브라우저 JS 구문 검사는 통과했지만 전체 Python/실제 브라우저/실제 DB 테스트 완료는 아니다.

### C. Supabase
전용 프로젝트 확인 → DB/백업 확인 → SQL Editor에서 supabase/migrations/002_private_runtime_bootstrap.sql 검토 후 적용 → 서버 스키마 초기화 → DATABASE_URL(SSL 연결) 및 CSAI_DB_BACKEND=postgres 설정.
001_foundation_DRAFT.sql은 적용하지 않는다. private schema를 외부 Data API에 노출하지 않는다.
현 백엔드는 직접 PostgreSQL 연결이므로 SUPABASE_URL/ANON_KEY/SERVICE_ROLE_KEY만 등록한다고 DB가 연결되지는 않는다.
먼저 별도 테스트 DB에서 scripts/postgres_smoke.py 및 기능 회귀 테스트를 검증한다. 해당 스크립트는 localhost의 csai_ci 전용이다. 실제 Supabase에서는 별도 테스트 계획 사용.
기존 SQLite 데이터는 삭제하지 않는다. 기존 데이터 이전이 필요한 경우 backup.py 및 scripts/import_sqlite.py를 검토하고, 쓰기를 중지한 백업과 빈 대상 DB에서 dry-run을 먼저 한다. 실제 이전은 별도 승인 및 검증 후. 이 이전 도구 자체도 실제 DB 검증 미완료.

### D. 환경변수 한 번에 준비
실제 값은 로컬 .env 또는 Cloudflare secrets에만 등록. 기존 암호화 키와 OAuth 값은 유지. 값 자체를 채팅이나 GitHub에 출력하지 않는다.

| 구분 | 환경변수 및 설정 | 상태 |
|---|---|---|
| 공통/개발 | DEMO_MODE=1, SHARED_TEST_MODE=1(공유 dev), APP_URL(로컬), CANONICAL_APP_URL(Cloudflare) | 공유 dev 유지 |
| DB | CSAI_DB_BACKEND, DATABASE_URL | 전용 Postgres 연결 검증 필요 |
| 운영자 | OPERATOR_OWNERS, OPERATOR_EMAILS; LOCAL_OPERATOR_TOKEN(로컬 전용) | Google 검증 계정만 |
| Google | GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET | 로그인 OAuth, Calendar API 및 URI 검증 |
| AI | OPENAI_API_KEY, TRAIN_MODEL, CHAT_MODEL, TRAIN_EFFORT, CHAT_EFFORT, BOOKING_EFFORT, TRAIN/CHAT_*_USD_PER_M | 기본 모델명 및 단가 실제 확인 |
| 암호화 | INTEGRATION_ENCRYPTION_KEY | 기존 값 유지 |
| 이메일 | RESEND_API_KEY, RESEND_FROM, ENABLE_AUTO_EMAIL, ENABLE_LIVE_EMAIL | 실제 발송은 확인된 계정 주소 및 도메인 |
| 워커 | ENABLE_BACKGROUND_WORKER, ENABLE_AUTO_CALENDAR, ENABLE_AUTO_REPORTS | 한 DB에 워커 하나, 컨테이너 sleep 검토 |
| 푸시 | VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_SUBJECT, ENABLE_AUTO_PUSH, ENABLE_LIVE_PUSH | HTTPS, 기기 권한 및 실발송 검증 |
| 채널 | ENABLE_CHANNEL_WEBHOOKS, KAKAO_CALLBACK_HOSTS | 네이버/카카오 관리자 연결 및 승인 |
| 문자 | SOLAPI_API_KEY, SOLAPI_API_SECRET, SOLAPI_SENDER, SOLAPI_ALIMTALK_PFID, SOLAPI_ALIMTALK_TEMPLATE_ID, ENABLE_AUTO_MESSAGES, ENABLE_LIVE_MESSAGES | SOLAPI 후보, 발신번호·템플릿 및 수신 동의 |
| 도메인 | CUSTOM_DOMAIN_TARGET, CLOUDFLARE_ZONE_ID, CLOUDFLARE_API_TOKEN, ENABLE_CUSTOM_DOMAINS, ENABLE_AUTO_DOMAINS | Cloudflare for SaaS 및 TLS |
| 보관 | BASE_HISTORY_DAYS, EXTENDED_HISTORY_DAYS | 기본 90일/1825일 임시 조회 정책; 삭제 금지 |
| 결제 | PG 공급자, MID, 결제/웹훅 키 등 | 공급자 확정 및 실제 개발 필요 |

OAuth 콜백: https://csai.jeonmeensoo.workers.dev/auth/google/callback 및 /auth/calendar/callback.
로컬 테스트 시 필요하면 실제 APP_URL의 콜백도 등록한다. 모든 live 플래그는 승인/검증까지 0으로 유지한다.
Cloudflare 코드가 실제 전달하는 환경변수는 cloudflare/src/index.ts로 대조한다. 누락된 전달 항목이 있으면 수정하고 테스트한다.
기본 모델 ID gpt-6.2-sol, gpt-6-luna는 실제 API 사용 가능 여부 미검증이며 그대로 사용 가능하다고 가정하지 않는다.

### E. 최종 검수
- [ ] 기존 상단 랜딩, Google 로그인, 모바일 레이아웃, 하단 01~04 장점/CTA.
- [ ] 무료 1회, 유료 요금제, 운영자 한도, 초청 체험 만료 및 취소, 결제/환불 시 잔액.
- [ ] 교육 견적/차감/실패 복구/승인/버전, URL·문서 업로드, 개별 상담원.
- [ ] 일반 상담, 미학습, 수동 상담, QR/위젯, 다국어, 디자인.
- [ ] 예약 충돌, 변경/취소, 관리자 등록, 복구, Google 동기화.
- [ ] CRM, 잠재 고객, 견적 단가·수량 검토, 민원/업무.
- [ ] 통계·엑셀·자동 리포트, 장기 조회, API 키와 업체별 데이터 분리.
- [ ] 이메일·푸시·문자·채널·도메인: 모의 테스트와 실제 연동 분리.
- [ ] PostgreSQL 연결/재시작/백업 복구, 실제 데이터 이전.
- [ ] 실제 PG 결제/구독 갱신/해지/환불/웹훅 검증.
- [ ] 전체 테스트 통과 및 PC·모바일 브라우저 검수.

### F. Cloudflare dev 배포
현재 프로젝트는 일반 Pages/정적 Worker와 달리 Python FastAPI Container(Dockerfile) 기반.
PC에서 Cloudflare 인증, Docker/빌드 환경 및 기존 Worker csai의 정확한 계정 확인 후:
```sh
cd cloudflare
npm ci
npx wrangler whoami
npx wrangler deploy
```
기존 환경변수 보존(keep_vars=true) 및 SQLite 임시 저장 데이터 백업. 새 버전의 테스트가 실패하면 기존 dev를 덮어쓰지 않는다.
CLI 출력 URL 및 /health 확인. dev 사이트 랜딩 하단과 로그인 실제 검증.
현재 모바일 환경에서는 GitHub DNS 오류, Cloudflare 인증/CLI/PC 브라우저 미연결로 deploy 실행 불가. 현재 dev는 최신 기능 미배포 상태로 취급한다.
검증 전 main 병합 및 실결제/운영 활성화 금지.

## 4. 완료 기준
코드 작성과 검증을 분리한다. 기능별 개발 여부는 FEATURE_CHECKLIST.md를 기준으로 하고, 테스트 실제 통과만 검증 체크한다. 전체 실행 검증 및 PG는 아직 미완료다. 나머지 코드에도 실제 테스트에서 오류가 나올 수 있으므로 숫자만 100%로 올리지 않는다. 마지막에 실제 커밋 SHA, 테스트 결과(성공/실패 수), 수정 파일, 설정 누락, 배포 버전과 URL을 보고한다.

2026-11-27 추가: NEXT_PHASE_1127.md와 MOTION_HANDOFF_1127.md 및 각 phase 문서를 확인. ENABLE_NAVER_STAFF_SEND=0 유지, 공식 실계정 발송 검증 후만 활성화. 카카오 상담톡 계약/권한 별도 필요. 최신 브랜치에서 통합 상담함, 수동 모드, 발송 상태·중복 방지, DB 마이그레이션 전체 테스트 필요.
