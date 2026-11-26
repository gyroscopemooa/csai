# CS AI 개발 사이트 설정 한 장 요약 — 2026-11-26

대상: `feat/product-functions` 기능 브랜치, CS AI 전용 Supabase 프로젝트, `csai.jeonmeensoo.workers.dev` 개발 Worker. 기존 서비스의 프로젝트·DB·키를 재사용하지 않습니다. 아래 값은 저장소에 입력하지 말고 로컬 비공개 환경 또는 Cloudflare Worker secrets/variables에만 등록합니다.

## 1. Supabase SQL

CS AI 전용 프로젝트인지 먼저 확인한 뒤 SQL Editor에서 아래 SQL을 **한 번** 실행합니다. `001_foundation_DRAFT.sql`은 실행하지 않습니다. 이 스키마를 Supabase Data API의 노출 스키마 목록에 추가하지 않습니다.

```sql
BEGIN;
CREATE SCHEMA IF NOT EXISTS csai_private;
REVOKE ALL ON SCHEMA csai_private FROM PUBLIC, anon, authenticated;
REVOKE ALL ON ALL TABLES IN SCHEMA csai_private FROM PUBLIC, anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA csai_private FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA csai_private REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA csai_private REVOKE ALL ON SEQUENCES FROM PUBLIC, anon, authenticated;
COMMIT;
```

동일한 원본 파일: `supabase/migrations/002_private_runtime_bootstrap.sql`. 이후 서버가 private schema에 테이블을 초기화합니다. 기존 SQLite 이전은 별도 백업과 빈 테스트 DB에서 dry-run을 통과한 뒤 진행합니다.

## 2. 필수 비공개 설정

| 영역 | 변수 | 값 또는 확인 사항 |
|---|---|---|
| 실행 | `DEMO_MODE`, `SHARED_TEST_MODE`, `CANONICAL_APP_URL` | 개발 사이트는 각각 `1`, `1`, `https://csai.jeonmeensoo.workers.dev` |
| DB | `CSAI_DB_BACKEND`, `DATABASE_URL` | SQL 적용·실연결 검증 후 `postgres`, CS AI 전용 SSL PostgreSQL **session pooler** URL. URL을 채팅·GitHub에 게시하지 않음 |
| 운영자 | `OPERATOR_OWNERS`, `OPERATOR_EMAILS` | 검증된 Google ID/이메일만. 현재 설정의 기존 운영자 값을 보존 |
| Google | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | CS AI OAuth 클라이언트 값. 기존 값 보존 |
| AI | `OPENAI_API_KEY`, `TRAIN_MODEL`, `CHAT_MODEL` | 실제 키, `gpt-6.2-sol`, `gpt-6-luna`; 계정별 모델 접근 확인 후 실제 호출 |
| AI 원가 | `TRAIN_INPUT_USD_PER_M`, `TRAIN_OUTPUT_USD_PER_M`, `TRAIN_CACHED_USD_PER_M` | 공식 Standard USD/100만 토큰: `1.00`, `5.00`, `0.05` (2026-11-26 확인) |
| AI 원가 | `CHAT_INPUT_USD_PER_M`, `CHAT_OUTPUT_USD_PER_M`, `CHAT_CACHED_USD_PER_M` | `0.05`, `0.25`, `0.005` (2026-11-26 확인) |
| AI 추론 | `TRAIN_EFFORT`, `CHAT_EFFORT`, `BOOKING_EFFORT` | 현재 예시 `low`, `none`, `low`; 실제 모델 지원 확인 |
| 암호화 | `INTEGRATION_ENCRYPTION_KEY` | 기존 값 유지. 변경 시 기존 암호화된 연결정보를 읽지 못할 수 있음 |

로컬 테스트에는 `APP_URL=http://127.0.0.1:3000`, `DATA_DIR=./data/gui-test`, `CSAI_DB_BACKEND=sqlite`, `DEMO_MODE=1`, `SHARED_TEST_MODE=0`을 사용합니다. 로컬 운영자 테스트만 `LOCAL_OPERATOR_TOKEN`을 비공개 설정합니다. 실제 API 키·DB URL은 격리 테스트에 넣지 않습니다.

## 3. OAuth 등록 URI

- 승인된 JavaScript 원본: `https://csai.jeonmeensoo.workers.dev`, 로컬 OAuth 테스트 시 `http://127.0.0.1:3000`
- 승인된 리디렉션 URI: `https://csai.jeonmeensoo.workers.dev/auth/google/callback`, `https://csai.jeonmeensoo.workers.dev/auth/calendar/callback`
- 로컬 OAuth 테스트 시 추가: `http://127.0.0.1:3000/auth/google/callback`, `http://127.0.0.1:3000/auth/calendar/callback`

## 4. 선택 기능과 활성화 조건

| 기능 | 변수 | 활성화 전 확인 |
|---|---|---|
| Resend | `RESEND_API_KEY`, `RESEND_FROM`, `ENABLE_AUTO_EMAIL`, `ENABLE_LIVE_EMAIL` | 발신 도메인/수신자 검증 후 live `1` |
| 캘린더·리포트 | `ENABLE_BACKGROUND_WORKER`, `ENABLE_AUTO_CALENDAR`, `ENABLE_AUTO_REPORTS` | DB당 워커 1개, 컨테이너 sleep 영향 확인 |
| 웹 푸시 | `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`, `ENABLE_AUTO_PUSH`, `ENABLE_LIVE_PUSH` | HTTPS, 기기 권한, 실발송 테스트 |
| 채널 | `ENABLE_CHANNEL_WEBHOOKS`, `KAKAO_CALLBACK_HOSTS` | 네이버·카카오 채널 승인, 정확한 콜백 호스트 |
| 문자 | `SOLAPI_API_KEY`, `SOLAPI_API_SECRET`, `SOLAPI_SENDER`, `SOLAPI_ALIMTALK_PFID`, `SOLAPI_ALIMTALK_TEMPLATE_ID`, `ENABLE_AUTO_MESSAGES`, `ENABLE_LIVE_MESSAGES` | 발신번호·템플릿·수신 동의 검증 |
| 도메인 | `CUSTOM_DOMAIN_TARGET`, `CLOUDFLARE_ZONE_ID`, `CLOUDFLARE_API_TOKEN`, `ENABLE_CUSTOM_DOMAINS`, `ENABLE_AUTO_DOMAINS` | Cloudflare for SaaS·TLS·라우팅 검증 |
| 보관 | `BASE_HISTORY_DAYS`, `EXTENDED_HISTORY_DAYS` | 현재 기본 90일/확장 1825일 조회 정책; 자동 삭제 없음 |
| 실제 PG | PG 공급자, MID, 결제·웹훅·빌링 키 | 공급자/계약 미확정. 모의 결제만 사용하며 실제 청구 비활성화 |

모든 `ENABLE_LIVE_*`, `ENABLE_CHANNEL_WEBHOOKS`, `ENABLE_CUSTOM_DOMAINS`는 검증 전 `0`으로 둡니다. `.env.example`은 공개 예시이며 실제 키를 넣지 않습니다.

## 5. 현재 연결 확인 결과

- 로컬 Supabase 커넥터에는 `transtream`만 보여 CS AI 전용 프로젝트 SQL을 실행하지 않았습니다. CS AI 프로젝트가 같은 계정에 연결된 뒤 위 SQL을 적용해야 합니다.
- Wrangler는 `jeonmeensoo@gmail.com` 계정의 `csai` Worker를 확인했습니다. 현재 PC에 Docker CLI가 없어 Container 배포 dry-run이 실패했습니다. Docker 빌드 환경이 필요합니다.
- PostgreSQL 실제 연결·재시작 후 데이터 유지, 외부 실발송, 실 PG 결제·환불·정기 갱신은 아직 검증되지 않았습니다.
