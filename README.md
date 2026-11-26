# CS AI — 기능 우선 확장형 MVP v0.3

> **2026-11-26 최신 인계:** 이 브랜치의 다음 작업은 [HANDOFF_HOME.md](HANDOFF_HOME.md)를 먼저 읽고 진행하세요. [FEATURE_CHECKLIST.md](FEATURE_CHECKLIST.md) 및 [DEPLOY_DEV.md](DEPLOY_DEV.md)가 최신 기능·검수·배포 상태 기준입니다. 아래 README의 과거 버전 테스트 통과 기록과 미구현 목록은 현재 브랜치의 전체 테스트 결과가 아닙니다. 현재 전체 CI 실패 및 실제 PG/DB/외부 연동 검증 미완료, main 미병합 상태입니다.

이 프로젝트는 실제 FastAPI 서버 + SQLite DB + 모바일 대응 웹 UI를 실행할 수 있는 개발용 MVP입니다. **공개 운영 또는 실결제 가능한 완성품은 아닙니다.** 기존 34페이지 기획서, 가격, 19종 초기 디자인 및 이전 개발 명령을 `reference/`에 보존했습니다. 기능 우선으로 확장했으며 기존 디자인은 임의로 전면 개편하지 않았습니다.

## v0.5 개발 환경 변경

- 로컬 `http://127.0.0.1:3000`에서 `SEED_UI_SAMPLES=1`로 서버를 실행하면 새 로컬 테스트 계정에 가상 상담 8건이 자동 생성됩니다. 통합 상담함의 긴 대화·채널·상태·스크롤 검수용이며 상담 한도와 크레딧을 쓰지 않습니다. 기존 로컬 계정은 통합 상담함에서 **샘플 상담 8건 넣기**를 누르세요. **샘플만 지우기**로 가상 상담만 삭제할 수 있습니다. 공유 테스트 및 운영 주소에서는 이 기능을 사용할 수 없습니다.

- 랜딩은 CS AI와 기존 문구를 유지하면서 **나의 클론 상담사**를 표시합니다.
- 직접 지침, 모범 답변, 미학습 답변 교정, 업로드 자료는 모두 교육 견적 → 크레딧 예약 → 교육 실행 → 검토 → 승인 흐름을 사용합니다. 단순 업체 정보와 표현 옵션만 무료 설정입니다.
- 운영자 권한은 서버의 `OPERATOR_OWNERS=google:<검증된 Google sub>` 또는 `OPERATOR_EMAILS=<Google에서 검증된 이메일>`로만 부여합니다. URL 파라미터나 클라이언트 값으로 권한을 주지 않습니다. 로컬에서만 `local:operator`과 24자 이상 `LOCAL_OPERATOR_TOKEN`을 사용할 수 있습니다.
- 초청 체험은 운영자가 1회용 링크로 발급하며 기본 50회 상담/100C/14일(상담 100·300회, 교육 20~300C, 기간 1~30일 조절 가능), 예약 체험 10건을 제공합니다. 체험과 운영자 사용량은 일반 구독 지갑과 분리됩니다.
- 로컬 개발 서버에서는 사이드바의 `로컬 화면 비교`로 무료 가입, LITE 유료 구독 예시, 개발 검수를 전환할 수 있습니다. 세 상태는 별도 데모 작업공간이며 실제 결제나 운영자 권한이 아닙니다. 개발 검수에는 로컬 구현이 있는 추가 기능만 켭니다. 배포 주소에서는 이 전환 UI와 API가 비활성화됩니다.
- 교육은 `gpt-6.2-sol`, 상담은 `gpt-6-luna`를 기본 환경변수 값으로 두고, 모델 사용량·예상 원가를 운영자 전용으로 기록합니다. 실제 키·계정 가용성 및 청구 단가는 배포 전 별도 확인해야 합니다.

## Cloudflare dev 배포

`cloudflare/`에는 FastAPI를 Cloudflare Containers로 실행하는 **dev 전용** 구성이 있습니다. 일반 Pages 또는 일반 Worker Git 배포를 선택하면 Python API가 실행되지 않습니다. Containers는 beta이고 컨테이너 디스크가 재시작 시 초기화되므로, 이 구성은 SQLite 데이터를 보존하는 운영 배포에 사용하면 안 됩니다. 운영 전환은 Supabase Postgres와 RLS 이식 후 진행합니다.

`wrangler.jsonc`의 `keep_vars: true`는 대시보드에 등록한 Production OAuth 변수와 시크릿을 다음 GitHub 배포에도 유지합니다. 비밀값은 저장소에 넣지 말고 Worker Runtime variables and secrets에 등록합니다.

```bash
cd cloudflare
npm install
npx wrangler deploy
```

배포 후 실제 Worker URL로 `APP_URL`을 설정하고, `SHARED_TEST_MODE=1`, `DEMO_MODE=1`, Google OAuth 및 운영자 `google:<sub>` 값을 Cloudflare secret/environment variable로 넣어야 합니다. OpenAI, Supabase, Resend, 결제 관련 비밀값은 테스트 전까지 비워 둡니다.

Supabase는 다른 서비스와 공유하지 않고 `csai` 전용 개발 프로젝트를 생성합니다. 생성 후 `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`를 로컬 `.env`와 Cloudflare secret에 각각 넣습니다. 현 런타임은 SQLite이며, `supabase/migrations/001_foundation_DRAFT.sql`은 검토 전인 초안이므로 새 프로젝트에 자동 적용하지 않습니다.

## Windows에서 실행
1. ZIP 전체를 새 폴더(예: `C:\Projects\CSAI`)에 압축 해제합니다. `run.py`, `requirements.txt`, `web/`가 같은 폴더 안에 있어야 합니다. 기존 폴더에 덮어쓰기보다는 별도 폴더에서 테스트를 권장합니다.
2. Python 3.11~3.13 설치 후 `start_windows.bat` 더블클릭. 첫 실행에는 의존성 설치를 위한 인터넷이 필요합니다.
3. `http://127.0.0.1:3000`에서 **로컬 테스트로 들어가기** 클릭. 로그인, PG, 실제 AI 키 없이 작동을 확인할 수 있습니다. 이때 AI 답변은 규칙 기반 테스트입니다. 다른 포트로 실행할 때는 `APP_URL`도 같은 주소로 설정해야 브라우저 채팅 요청이 허용됩니다.
4. 업체 정보 및 말투 설정 → 교육 자료 등록 → 교육 비용 확인 → 교육 실행 → 결과 수정/승인 → 첫 상담 테스트.
5. 요금제에서 LITE(300회/9,900원) 및 필요한 유료 옵션을 선택 → 로컬 테스트용 구독 적용 → 테스트 결제 완료. 실제 돈은 결제되지 않습니다.
6. 채팅 미리보기에서 공개 설정을 켜고 같은 PC의 별도 브라우저 창에서 고객 상담 링크를 엽니다. QR 주소는 localhost이므로 휴대폰 등 다른 기기에서는 접근할 수 없습니다.
7. 일정표 옵션, 자동 예약 및 변경·취소 옵션을 선택한 후 맞춤 양식과 담당자를 설정해 예약 흐름을 확인합니다.

macOS/Linux: `sh start_mac_linux.sh`. 수동 실행: `python -m pip install -r requirements.txt`, `.env.example`을 `.env`로 복사(기존 `.env` 덮어쓰기 금지), `python run.py`.

## 구현 범위 및 상태

| 기능 | 상태 |
|---|---|
| 업체별 로그인 세션, DB 분리 | 로컬 검증; 실제 Google 로그인 코드 실계정 미검증 |
| 교육 업로드 TXT/CSV/MD/PDF/DOCX/XLSX/JPG/PNG/WebP | 파일당 5MB, PDF 30페이지, 한 교육 최대 60,000자·이미지 8장. HWP/URL 직접 수집 미구현 |
| 교육 자료 분할·중복 파일 방지·크레딧·검토·수정·승인·버전 복원 | 로컬 검증; 실제 AI 분석 호출은 모의 검증 |
| 실시간 상담·최근 대화 길이 제한·관련 FAQ/규칙 검색·사용량 차감 | 로컬 검증, 실제 모델 성능·원가 미검증. 모델 ID 환경변수화 |
| 첫 무료 답변 1회, 유료 사용량, 상담 기록·담당자 전환·미학습 질문 | 로컬 검증 |
| 비회원 상담, 공지, 판매처 안내, QR, iframe | 로컬 검증; 외부 HTTPS 위젯 검증 필요 |
| 로고, 테마, 지정 상담 주소, 브랜드 간소화 | 로컬 구현; AI 고지는 항상 유지 |
| 추가 AI 상담원 1명 | 별도 링크·말투·인사·개별 FAQ, 공통 교육 자료·예약·구독 사용량 공유 |
| 일정 양식, 날짜·시간 조회, 최종 고객 확인, 승인·결제 확인, 월간 일정 | 로컬 검증 |
| 담당자별 예약 충돌 검사 | 로컬 검증, 영업시간은 업체 공통. 개별 휴무·수용량·외부 일정 충돌 미구현 |
| 고객의 자체 예약 변경·취소 | 자동·수동 승인 및 일회용 복구 코드로 다른 기기 이전 가능. 전화번호 본인 인증은 미구현 |
| 고객 견적·민원·업무 요청 접수 | 대화에서 일부 명시적 키워드로 양식 제안, 고객 확인 후 저장. AI 자동 견적 산정/전송은 미구현 |
| 상담을 CRM·견적·업무·잠재고객·민원 기록으로 전환, 상태 수정·삭제 | 로컬 검증; 완전 자동 CRM/잠재고객 분류는 미구현 |
| 상담 통계·XLSX 내보내기 | 로컬 기본 구현 |
| 요금표, 기능표, 추가 옵션·패키지 | 기존 가격 유지. 패키지 중복 방지 및 서버 금액 계산 |
| 구독·교육·메시지 테스트 주문, 중복 결제 방지, 구독 기간/만료·해지 예약 | 로컬 검증. 실제 PG/자동 갱신/환불/세금/일할계산 미구현 |
| 네이버·카카오 메시지 통합 | 로컬 테스트 UI, 인증정보 암호화, 웹훅·영속 대기열·워커·전송 코드. 외부 API 모의 검증만 |
| Google Calendar | 별도 OAuth·암호화된 갱신 토큰·기본 캘린더 일정 조회 및 명시적 개별 예약 동기화, 외부 모의 검증. 자동 동기화/외부 일정 기반 중복 검사 미구현 |
| 알림 기록·읽음, Resend 이메일 | 로컬 기록·수동 전송 및 자동 워커, 중복 전송 차단. 실제 Resend 계정 미검증 |
| 알림톡·SMS | 테스트 충전/잔액만 구현. 실발송, 발송량 차감, 템플릿 승인 미구현 |
| 자체 도메인, 장기 보관 정책, Web Push, 자동 정기 리포트, 외부 업무 API | 미구현/준비 중 |

`catalog.json`은 판매 예정 가격의 단일 기준입니다. 준비 중 기능은 테스트 권한만 부여 가능하며 실제 판매 금지. 구독은 테스트 결제일 기준 월 단위이며, 같은 기간의 테스트 요금제 변경은 사용량을 유지합니다. 자동 갱신 및 일할 차액 결제는 구현되지 않았습니다. 기존 `/api/demo/billing`은 로컬 개발/회귀 테스트 호환 전용입니다.

## 실제 외부 연결 설정

비밀키는 `.env`에만 저장하고 Git에 올리지 마세요. 운영에서 이 프로젝트의 데모 설정을 그대로 사용하지 마세요. 실제 고객 정보/결제정보를 개발 환경에 넣지 마세요.

### OpenAI
- `OPENAI_API_KEY`, `TRAIN_MODEL`, `CHAT_MODEL` 설정 후 재시작.
- 기본 모델 ID는 이전 기획안(`gpt-6.2-sol`, `gpt-6-luna`)에서 이어받은 환경변수 기본값으로, 현재 계정에서 실제 사용 가능한 API 모델 ID인지 확인해야 합니다. 이 버전에서는 실제 모델 호출을 수행하지 않았습니다. 계정에서 승인된 적합한 모델로 설정하세요.
- 파일 분석 비용은 입력/출력 토큰 및 이미지에 따라 계산되는 교육 크레딧 가안입니다. 모델별 토큰 단가, 추론, 이미지 비용, 실패한 요청 비용을 실측한 후 판매할 것. 분할 분석은 모든 텍스트 구간을 순서대로 분석하고 중복 FAQ와 충돌을 검토합니다. 실제 AI 품질, 한글 문서/사진 분석, 민감정보 제거는 별도 검증 필요.

### Google 로그인 / Google Calendar
- Google Cloud OAuth 클라이언트에서 `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` 설정.
- 로그인 리디렉션 URI: `APP_URL/auth/google/callback`.
- Calendar API를 활성화하고 별도 OAuth 리디렉션 URI `APP_URL/auth/calendar/callback` 추가.
- `INTEGRATION_ENCRYPTION_KEY` 생성: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
- 키는 비밀로 보관하며 변경하면 기존 연결 정보를 복구할 수 없습니다. 관리자 채널 페이지에서 Google Calendar 권한 연결 후 일정 조회·개별 동기화 버튼으로 검증. 외부 이벤트의 제목/참석자를 서비스에 가져오지 않으며, 예약 날짜/시간과 일반 제목만 외부로 전송합니다. 본 앱이 등록한 일정만 수정/삭제. 연결 해제는 로컬 저장 토큰 제거이며 Google에서 권한 철회는 별도로 해야 합니다.
- 공식 문서: https://developers.google.com/workspace/calendar/api/guides/create-events / https://developers.google.com/identity/protocols/oauth2/web-server

### 네이버 톡톡 / 카카오톡 채널
- 공식 관리자센터 계정/채널 권한과 AI 챗봇 사용 조건을 먼저 확인합니다.
- HTTPS 환경 구축, `INTEGRATION_ENCRYPTION_KEY` 및 `APP_URL` 설정. `ENABLE_CHANNEL_WEBHOOKS=0`가 기본값입니다. 로컬에서는 활성화할 수 없습니다. **공개 운영 승인 전에는 켜지 마세요.**
- 네이버: 파트너 ID와 보내기 API Authorization을 등록. 발급된 비공개 URL을 네이버 파트너센터 개발자 도구의 Webhook URL에 입력하고 텍스트 send 이벤트를 등록. echo 이벤트는 무시됩니다.
- 카카오: 챗봇 관리자센터에서 봇 ID, 스킬 URL과 승인된 AI 콜백 설정. `KAKAO_CALLBACK_HOSTS`에는 공식 문서/실제 승인된 정확한 콜백 호스트만 설정. 임의 URL 또는 와일드카드 사용 금지.
- `python worker.py`는 승인된 배포 환경에서만 별도 프로세스로 실행합니다. 수신 요청은 대기열에 기록한 뒤 바로 응답하고 워커가 실제 상담 엔진을 호출합니다. 외부 채널 예약은 자체 상담 링크로 안내합니다. 상담원의 직접 답변을 외부 채널에 다시 전송하는 기능은 아직 미구현입니다. 네이버 이벤트에는 신뢰 가능한 고유 ID가 없는 경우가 있어 현재 짧은 시간 내 동일 메시지 중복 차단만 지원합니다. 외부 실패/응답 미확인시 자동 재발송하지 않습니다. 운영에서는 공급자 서명 또는 IP 제한 검증, 비공개 경로 로그 마스킹, 회전/재시도/장애 복구를 추가해야 합니다.
- 공식 문서: https://github.com/navertalk/chatbot-api / https://kakaobusiness.gitbook.io/main/tool/chatbot/skill_guide/ai_chatbot_callback_guide

### Resend
`RESEND_API_KEY`, `RESEND_FROM` 설정. 인증된 발신 도메인 필요. 관리자 알림 페이지에서 수신 주소와 관련 옵션(이메일 + 신규/미학습/예약 알림)을 설정한 뒤 대기 알림 보내기를 누르면 설정에 따라 모의 또는 실제 전송을 처리합니다. DEMO_MODE=1에서는 키가 있어도 `simulated`로 표시하며 실제 전송하지 않습니다. 실제 발송에는 DEMO_MODE=0, ENABLE_LIVE_EMAIL=1, 검증된 수신자 및 발신 도메인이 필요합니다. 승인 전 비활성 상태를 유지하세요. 이메일에는 고객 문의 본문 대신 알림 제목과 관리자 주소만 넣습니다.

## 테스트 / 개발자 인계
```bash
python -m pytest -q
python -m py_compile app.py ai.py store.py ops.py billing.py branding.py channel_live.py google_calendar.py worker.py
node --check web/app.js
```
브라우저 테스트: `pip install playwright`, `playwright install chromium`, `python tests/browser_check.py`. UI 테스트는 Chromium 화면 + 실제 ASGI API 테스트 브리지를 사용합니다. 실제 Uvicorn 로컬 HTTP 연결 smoke 테스트는 통과했습니다. 일반 브라우저 직접 HTTP E2E는 PC에서 추가 검증 필요.

`verification/TEST_REPORT.md`와 `verification/browser_result.json`을 참고하세요. ZIP에 기존 DB, 실제 고객정보, API 키, 테스트 캐시는 포함하지 않았습니다. `.env.example`만 있습니다.

## 출시 전 차단 사항
실제 PG 계약/결제/구독 관리, Supabase 운영 DB 마이그레이션/RLS/원자적 거래 RPC, API 모델 계정 연결, 외부 채널/Google/Resend 실계정 테스트, 전화번호 등 본인 인증 및 장기 세션 정책, 다중 사용자 및 권한, 데이터 저장·삭제·보관 정책, 외부 도메인/HTTPS, 파일 악성코드 검사, 서비스 약관, 요금 세금 처리, 자동 장애 복구 및 분산 보안은 필수입니다. 로컬 구독/크레딧 구매 우회 기능은 운영에서 완전히 비활성화할 것. `supabase/migrations/001_foundation_DRAFT.sql`은 이전 설계 초안이며 새 기능의 마이그레이션은 아직 아님. 공개 인터넷에 현재 앱을 그대로 노출하지 마세요.

실제 외부 가입, 결제, 이메일·톡 발송, 원격 GitHub 생성, 배포는 이 작업에서 수행하지 않았습니다.

## v0.3 추가 기능 및 검증
- 예약 복구: 고객의 내 예약에서 일회용 코드를 발급하고 동일 업체의 다른 기기 상담창에서 입력하면 그 예약에 한해 관리 권한이 이전됩니다. 원래 기기의 변경 권한은 제거되고 상담 대화는 공유되지 않습니다. 코드 재발급·사용·만료 시 이전 코드는 무효입니다. 예약 종료 전 발급, 최대 365일 또는 예약 종료+7일 중 빠른 시점까지 유효. 코드는 비밀이며 전화번호 소유 확인을 대체하지 않습니다.
- 이메일 워커: `.env`의 `ENABLE_AUTO_EMAIL=1`로 설정한 후 별도 터미널에서 `python worker.py` 실행. 관련 알림과 이메일 옵션, 수신 주소, 동의 설정을 확인하며 최근 24시간 이벤트를 처리합니다. 데모에서는 실제 발송하지 않습니다. 동일 이벤트 중복 처리 방지, 전송 결과가 모호하면 관리자 검토 상태로 남깁니다. 실제 사용 전 수신 주소 검증, 발송 한도 및 동의 절차를 구현해야 합니다.
- 백업: `python backup.py backups/local-2026-11-25.sqlite3`로 로컬 데이터베이스 일관성 백업 생성. 기존 파일 덮어쓰기 금지, 무결성 확인. 백업에는 개인정보가 포함될 수 있어 암호화된 저장소에 보관하고 Git에 올리지 마세요. 실제 운영 DB 백업/복원 자동화는 별도 구현 필요.
- 토스풍 UI 개선: 흰 카드, 연회색 배경, 파란색 버튼, 넉넉한 여백과 모바일 입력창 크기 개선. 실제 토스 서비스 복제는 아니며 최종 브랜드 디자인은 미확정입니다.
- 기능 테스트 37개 통과, Chromium 브라우저 ASGI 브리지 검증 26개 캡처 및 JS 오류 0개. 이전 테스트와 예약 복구 이전 흐름을 함께 확인했습니다. 외부 서비스 실계정 검증은 하지 않았습니다.

## v0.4 UI motion enhancement
See `MOTION_GUIDE.md` for the implemented effects, reference links and development constraints. Original CSS/JS only; no new runtime dependencies, no external premium assets. Existing business rules and backend preserved. Local tests: 37 passed; browser suite uses ASGI bridge, not a deployed service.
