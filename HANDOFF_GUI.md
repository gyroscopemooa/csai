# GUI / Codex 이어서 개발 명령 — v0.3

현재 폴더는 CS AI 기능 우선 확장형 MVP입니다. `README.md`, `catalog.json`, `verification/TEST_REPORT.md`, `reference/`의 34페이지 개발 기획서와 19종 UI 캡처를 먼저 읽으세요. 현재 코드 기준은 `app.py`, `store.py`, `ai.py`, `ops.py`, `billing.py`, `branding.py`, `google_calendar.py`, `channel_live.py`, `worker.py`, `web/`입니다. 참고용 HTML은 현재 앱이 아닙니다. 이미 작동하는 기능과 가격을 보존하고 초기화 또는 재작성하지 마세요. 디자인은 추후 수정 예정이므로 기능/보안/사용 편의성을 먼저 완성하세요.

## 실행과 검증
1. Python 의존성을 설치하고 `python -m pytest -q` 실행. 현재 37개 테스트 기준. 로컬에서 `python run.py` 실행 후 실제 일반 브라우저에서 로그인, 교육, 미학습 질문, 첫 무료 테스트, 구독/충전, 상담, 예약, 고객 변경·취소, CRM/견적, 외부 채널 설정, 추가 상담원과 버튼을 모두 클릭 검증하세요. 이전 브라우저 캡처와 비교하세요.
2. 사용자의 실제 외부 계정 연결은 기존 계정을 재사용합니다. 비밀키는 `.env` 또는 시크릿 저장소에만 저장하고 로그/채팅/커밋에 노출 금지. 실제 PG/유료 구매/도메인 구매/약관 수락/외부 발송은 필요한 승인과 검증 없이는 하지 마세요.
3. Google OAuth/OpenAI 실제 연결: 공식 모델 가용성 및 단가 확인, 교육 분할·이미지 입력·토큰 견적 실측, 실패 및 부분 처리 비용, 자료 개인정보 제거, 버전 복원, 긴 대화, 상담 품질 테스트. 입력이 긴 경우에도 관련 정보만 전달. 교육은 고성능, 상담은 저비용 모델을 유지하고 임의 가격 변경 금지.
4. 운영 DB 전환: 현재 로컬 FastAPI + SQLite를 유지하면서 저장 계층을 Postgres/Supabase로 이전. 기존 SQL은 초안임을 주의하고 이번 v0.3의 주문·구독·메시지 잔액, 추가 상담원, 지정 주소, 예약 변경 요청, 이벤트, 발송 기록, 채널 큐, 암호화 연동 테이블까지 포함해 신규 마이그레이션을 검증. 업체별 RLS, 원자적 사용량/교육 크레딧/예약 및 구독 검증, 키 보관, 백업을 설계. Next.js로 전환할 필요가 있더라도 동작 보존 후 단계적으로 진행.
5. 실제 PG 연결: 사용자의 사업자 계약에 맞는 공식 PG를 확인하고 제공자 서버 검증, webhook 서명, 결제 금액·상품·주문 ID 일치, 멱등성, 구독 자동 갱신 및 만료/해지/환불/일할 계산/세금, 판매 가능한 SKU만 활성화. `/api/demo/billing` 및 sandbox confirm은 운영 비활성화. 교육·메시지 충전과 월 구독을 분리. 실제 결제 없이 가짜 결제 완료 표시 금지.
6. 예약: 현재 업체 양식·담당자별 예약·고객 확정·수동 승인·외부 결제 확인·일정표·변경/취소 요청을 유지. 고객이 다른 기기 또는 세션에서도 본인 확인 후 예약을 조회·변경하도록 현재 일회용 복구 코드 유지 및 전화번호 본인 인증 수단 추가. 담당자별 영업시간, 휴무, 버퍼, 수용량 및 외부 일정의 실시간 충돌 확인과 예약 변경 동기화 추가. 외부 상품 결제/취소는 판매처 링크 안내만 하고 실제 환불로 오인시키지 말 것.
7. 외부 채널: 새 웹훅/큐/워커 코드를 공급자 실계정에서 검증하고 상용 조건·권한 확인. 네이버 sender API 오류코드와 중복 이벤트 정책, 카카오 승인된 콜백 호스트와 유효시간, 인증 및 메시지 실패 처리, 다중 워커 동시성, 로그 비밀정보 보호, 예약 링크 연결 및 관리자 직접 답변의 외부 전송을 완성. 실제 승인 전 `ENABLE_CHANNEL_WEBHOOKS=0` 유지. Google Calendar 외부 일정과 충돌 검증 및 자동 동기화. 기존 Resend 자동 발송 워커 및 중복 방지 유지, 실발송 및 수신자 인증 검증, 승인된 알림톡 템플릿/SMS 공급자 API, 충전량 원자 차감 및 실패 복구, 웹 푸시/PWA 설치, 자동 리포트 추가.
8. 추가 기능: 고객 CRM/견적/잠재고객의 AI 분류와 업체 맞춤 업무 양식, 장기 보관 정책과 데이터 삭제, 외부 업무 API 및 권한, 자체 도메인(검증된 DNS/HTTPS), 별도 상담원 추가 수량과 독립 교육 범위 등을 완성. 기존 가격 및 기능표는 사용자 확인 없이 임의 변경하지 마세요. 미구현 상품은 실제 판매 차단. 기본 포함 및 추가 유료 기능을 명확히 노출.
9. 보안 및 운영: 실제 고객정보 사용 전 개인정보 정책/처리 동의, 파일 비공개 저장/악성 검사/민감정보 제거, 비회원 봇 방지, 분산 속도 제한, CSRF/세션/인증, 장애 중복 처리, 개인정보 보관 및 삭제, 로그/알림 최소화, API 비용 제한, 자동 백업, 모니터링, E2E/부하 테스트. 현재 localhost 데모는 공개 운영 금지. 실제 배포 전에 검증된 기능만 활성화.
10. GitHub가 없으면 로컬 Git init 후 초기 커밋. 원격 저장소는 연결 가능한 기존 계정 또는 사용자가 승인한 새 저장소에 생성. `.env`, `data/`, 테스트 고객정보, 개인 파일을 제외하고 커밋. 모든 테스트 및 실제 연동 결과를 기록하고, 배포 권한이 확보되면 검증 후 커밋·푸시·배포.

외부 인증과 비용/권한이 실제로 필요한 지점에서만 사용자 확인을 요청하고, 그 전까지는 가능한 작업을 순서대로 진행하세요. 모의 테스트와 실계정 검증을 구분하고, 코드만 있는 기능을 실사용 완료로 보고하지 마세요.

추가된 `recovery.py`, `notifications.py`, `backup.py`와 테스트를 유지하세요. 예약 복구 코드는 본인 인증을 대체하지 않습니다. 브라우저 디자인은 v0.3 캡처를 기준으로 토스풍을 유지하되 브랜드 디자인은 추후 사용자와 확정합니다. 현재 외부 계정/PG 승인 없이 공개 출시하지 마세요.

## v0.4 Motion handoff
Read `MOTION_GUIDE.md` before adjusting design. Keep the existing Toss-inspired visual language; use MotionSites, Motion AI Kit, Motion Primitives, 21st, React Bits, Aceternity and Magic UI as references only when compatible with the current stack. Do not introduce a framework migration just for motion. Preserve all business functionality, reduced-motion behavior, pending/error state, and existing pricing. No paid template or MCP account has been installed.
