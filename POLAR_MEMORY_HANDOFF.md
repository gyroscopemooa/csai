# Polar 결제와 외부 AI 기억 이전

## 설정 및 확인

- 기존 상품과 금액은 `catalog.json`과 `billing.quote` 사용. 사용자 금액은 Checkout에 반영하지 않는다.
- Polar Sandbox 조직에서 월 정기결제 상품과 일회 결제 상품을 만들고 각 ID를 `POLAR_SANDBOX_MONTHLY_PRODUCT_ID`, `POLAR_SANDBOX_ONE_TIME_PRODUCT_ID`에 지정한다. Checkout 생성 권한이 있는 샌드박스 조직 토큰을 `POLAR_SANDBOX_TOKEN`에 비밀로 저장한다.
- `POLAR_SANDBOX_CHECKOUT_ENABLED=1`이면 운영자 인증으로 `POST /api/operator/polar/sandbox-checkout`에 기존 서버 견적 요청과 같은 JSON을 보낼 수 있다. 예: `{"kind":"subscription","plan":"lite","addons":["all"]}`. URL은 샌드박스 확인용이고 CS AI 권한을 지급하지 않는다.
- 실제 테스트는 첫 결제, 다음 청구서 동일 KRW 금액, 차기 적용과 일할계산, 해지와 환불을 확인해야 한다. Checkout 공식 문서는 `prices`의 ad-hoc 금액을 지원하지만 이 작업에서 자동 갱신은 검증하지 못했다. 구독 변경 문서는 `product_id` 교체와 `invoice`, `prorate`, `next_period`를 지원한다. 동일 금액의 구성을 하나의 고정 가격 Polar 상품으로 재사용하는 방식은 후보이며, 구성 및 적용 시점은 CS AI 원장에 별도 보관해야 한다.
- 실제 연동 전 Webhook 엔드포인트와 서명 검증, 주문·구독·환불 멱등 처리, 잔액 회수와 감사 화면을 구현해야 한다. 예정 이벤트는 `order.paid`, `order.refunded`, `subscription.updated`, `subscription.revoked`이며 실제 엔드포인트가 완성된 뒤 Polar에서 설정한다. 운영 키와 상품 ID는 별도 환경으로 관리한다.
- [Checkout 공식 문서](https://polar.sh/docs/api-reference/checkouts/create-session) · [구독 변경 공식 문서](https://polar.sh/docs/api-reference/subscriptions/update)

## 기억 이전과 저장소

- 교육 메뉴의 외부 AI 기억 이전은 ZIP 또는 JSON의 대화 목록과 날짜, 같은 파일 내 중복 및 선택 후보의 추정 토큰을 확인한다. 원본은 요청 처리 동안만 메모리에 존재하며 DB, 모델, 고객 상담 데이터에 저장되지 않는다. 현재 ZIP 내 단일 conversations.json과 최대 25MB 파일을 지원한다.
- 이번 변경의 Supabase 신규 SQL은 없다. 이후 이전 이력과 크레딧 예약·정산, 구간 진행 상태, 결제 원장은 기존 전용 스키마에 추가해야 한다. 이전 수수료 기본값 9,900원, 관리자 설정, 별도 수수료 결제, 사용자 확인을 거친 교육 반영 및 데이터 재시도는 아직 제공하지 않는다.
