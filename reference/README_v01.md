# CS AI — 실행형 로컬 개발 프로젝트 v0.1

**실제 서버/DB가 연결된 로컬 MVP입니다. 아직 운영 출시 가능한 완성품은 아닙니다.**
기존 34페이지 기획서와 19개 UI 원본은 `reference/`에 보존했습니다. 기존 가격은 `catalog.json`이 단일 기준입니다. UI는 토스풍 반응형 HTML/CSS/JS를 사용하고 백엔드는 FastAPI + SQLite로 구현했습니다. 제안했던 Next.js/Supabase가 아닌 이유는 로컬에서 API, DB 동시성, 파일 파싱을 실제로 실행·검증하기 위해서입니다. Supabase 대상 SQL 초안을 함께 넣었으나 이 DB는 아직 연결되지 않았습니다.

## 집에서 실행하기 (Windows)
1. ZIP을 내려받아 `C:\Projects\CSAI` 등 원하는 폴더에 압축을 풉니다. `run.py`, `web/`, `requirements.txt`가 동일 폴더 안에 있어야 합니다.
2. Python 3.11~3.13이 설치되어 있는지 확인합니다. 처음 설치 시 인터넷이 필요합니다.
3. `start_windows.bat`를 더블클릭합니다. 처음에는 가상환경/의존성을 설치합니다. 실행 후 `http://127.0.0.1:8000`으로 접속합니다. 브라우저가 먼저 열리면 서버 준비 후 새로고침하세요.
4. **로컬 개발용 체험 시작** → 업체 정보/말투 등록 → 교육 자료 입력 → 교육 비용 확인 → 교육 결과 승인 → AI 상담 테스트.
5. 요금제 페이지에서 LITE(300회/9,900원), 필요 추가 기능을 선택하고 **로컬 테스트용 구독 적용**. 실결제 없음. 공개 링크 활성화 후 별도 브라우저에서 비회원 상담 테스트.
6. 일정표 옵션 + 자동 예약 옵션을 테스트용으로 적용하고 맞춤 양식, 영업시간/휴무, 자동·수동 모드를 설정합니다.

직접 명령 실행:
```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe run.py
```
(기존 `.env`가 있으면 덮어쓰지 마세요.) macOS/Linux: `sh start_mac_linux.sh`.

## API 연결
`.env`는 Git에 올리지 말 것. 외부 키가 없어도 로컬 규칙 기반 데모로 사용 가능합니다. 실제 API 교육/상담을 시험할 때만 `OPENAI_API_KEY`, `TRAIN_MODEL=gpt-6.2-sol`, `CHAT_MODEL=gpt-6-luna`를 설정하고 서버 재시작. API 비용 발생. 공식 모델 문서에서 계정의 가용성/단가를 재확인하세요. 실제 API 호출은 이 환경에서 수행하지 않았습니다. 응답 형식 및 크레딧 산정도 실측이 필요합니다.

Google 로그인: Google Cloud OAuth 클라이언트를 생성하고 리디렉션 URI `http://127.0.0.1:8000/auth/google/callback` 등록, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` 설정. 실제 Google OAuth 흐름은 미검증입니다. 네이버/카카오 로그인 버튼은 준비 중입니다.

로컬 QR은 localhost 주소를 포함하므로 다른 기기의 카메라로 접근할 수 없습니다. 실제 공유용 QR은 HTTPS 도메인 배포 및 검증 후 가능합니다. 데모 모드의 데이터는 테스트용이며 개인 고객 정보를 입력하지 마세요. 서버는 127.0.0.1에만 바인딩합니다.

## 구현/검증 범위
- 업체별 세션/DB 분리, 직접 프롬프트, 업체 정보, 판매처 링크, 말투, FAQ.
- 사진/텍스트/PDF/DOCX/XLSX/CSV 파싱·중복 제거; 교육 견적, 크레딧 예약, 실제 사용량 정산, 승인 후 반영. 실 API 연결 전 이미지 의미 분석은 데모입니다. HWP 변환·URL 크롤링은 미구현. DOCX 내 그림 및 텍스트가 충분한 PDF의 삽화는 별도 추출하지 않습니다.
- 무료 테스트 한 번, 이후 차단, 유료 테스트 사용량, 실패 복구, 요청 중복 처리, 공개 링크/QR, 비회원 세션, 상담 기록, 미학습 질문 및 직접 답변.
- 정적 공지와 링크는 AI 호출 없이 표시. 현 로컬 상담 엔진은 실제 AI 답변 및 규칙 기반 채팅 답변을 동일하게 한 회 차감합니다. 운영에서 별도 무과금 FAQ 버튼을 확장할 수 있습니다.
- 예약 양식 추가/삭제/순서/필수/형식, 시간 조회, 대화 내용 추출, 고객 요약 확인, 자동/수동 승인, 외부 결제 확인, 일정표, 중복 예약 차단, 관리자 변경/취소. 단일 리소스 및 월간 달력 기준. 고객 본인확인 기반의 외부 채널 예약 변경·취소는 미구현.
- 전체 요금표, 비교표, 개별 추가 기능/패키지/교육 크레딧/메시지 가격. 로컬 권한 부여 및 차감. 결제 프로바이더 연동 및 실제 구독 만료/갱신/환불 미구현.
- 간단한 고객·견적·업무·민원 수동 기록 및 상태, 통계, XLSX 내보내기, 유료 iframe 위젯. AI 기반 CRM/견적 완전자동화는 미구현. 외부 위젯 HTTPS/브라우저 호환 검증 필요.
- 네이버/카카오 메시지 포맷 어댑터 초안은 `integrations/`에 있으며 외부 webhook은 열지 않았습니다. 구글 캘린더, Resend, 알림톡, SMS, Web Push, 디자인/도메인 및 다중 상담원은 준비 중. 미구현 상품 실제 판매 금지.

## 검증 명령
```bash
python -m py_compile app.py ai.py store.py
node --check web/app.js
python -m pytest -q
```
`tests/browser_check.py`는 Playwright + Chromium으로 렌더링 코드를 실제 ASGI API에 테스트 브리지로 연결합니다. 이 환경 Chromium 정책이 로컬 HTTP 탐색을 차단해서 사용한 검증 방식입니다. 일반 브라우저 직접 HTTP 탐색은 집에서 추가 확인하세요. `verification/`에는 검증 캡처와 결과 JSON이 있습니다. 재실행하려면 `pip install playwright` 및 Chromium 설치가 필요합니다.

## 폴더 구조
- `app.py`: API/auth/교육/상담/예약/권한/업무/내보내기
- `ai.py`: 파일 파싱, OpenAI Responses API 호출, 교육 및 상담, 예약 정보 추출
- `store.py`: SQLite 스키마 및 트랜잭션, 권한/차감
- `catalog.json`: 모든 요금제와 추가 기능
- `web/`: 반응형 화면
- `tests/`: API와 브라우저 검증
- `supabase/migrations/`: 운영 DB 설계 초안(실행하지 않음)
- `reference/`: 기존 기획서/UI와 캡처
- `verification/`: 새 실행형 UI 테스트 캡처
- `HANDOFF_GUI.md`: 집에서 GUI/Codex에 전달할 개발 명령

## 운영 출시 전 필수 사항
Supabase/Postgres RLS 및 원자적 RPC로 이전, 실제 Google/OpenAI 키 검증, 결제 PG의 공식 webhook 서명/구독 상태/환불/세금/가격 확정, 파일 비공개 저장과 악성 검사·개인정보 보관/삭제, 접근권한·로그 마스킹, 분산 rate limiting/CAPTCHA, 크레딧/사용량 예약분 crash recovery, 고객 인증 및 예약 변경·취소, 외부 채널 계약 및 실제 콜백 검증, 장애 복구 및 백업, 보안 테스트, HTTPS/배포. 공개 운영에 `DEMO_MODE=1`을 사용하면 안 됩니다.

외부 서비스 가입, PG, GitHub 생성 및 배포는 이번 작업에서 실행하지 않았습니다.
