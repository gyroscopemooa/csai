# CS AI 개발 브랜치 전용 검증 및 Cloudflare 배포 절차

이 문서는 아직 배포하지 않은 feat/product-functions 브랜치의 실행 절차입니다.
기존 main과 사용자가 작업한 디자인을 덮어쓰거나 자동 병합하지 않습니다.

## PC에서

1. 기존 미커밋 변경을 먼저 확인하고 별도로 보존합니다. 현재 저장소를 강제로 reset 하지 않습니다.
2. 개발 브랜치를 최신 상태로 받습니다. 충돌이 있다면 자동 해결하지 말고 검토합니다.

```sh
git fetch origin
git switch feat/product-functions
git pull --ff-only origin feat/product-functions
```

3. 격리된 테스트 환경에서 전체 테스트를 통과시킵니다.

```sh
python -m pip install -r requirements.txt
python -m compileall -q app.py store.py ai.py billing.py postgres_store.py
node --check web/app.js
node --check web/widget.js
node --check web/push-sw.js
python -m pytest -q
```

실제 DB URL, 실제 API 키 또는 고객 데이터로 테스트하지 않습니다. 기존 .env를 덮어쓰지 않습니다.
테스트 실패 시 중단하고 먼저 원인을 해결합니다.

4. Cloudflare CLI에 로그인한 PC에서 개발용 Worker 설정을 확인합니다.
   wrangler.jsonc의 Worker 이름이 csai인지, 대상 계정과 기존 저장소 환경변수가 맞는지 확인합니다.
   현재 개발 Worker의 DEMO_MODE=1 및 SHARED_TEST_MODE=1을 유지합니다.
   기존 실제 데이터가 있는 컨테이너는 임시 저장소일 수 있으므로 필요한 경우 먼저 백업합니다.

```sh
cd cloudflare
npm ci
npx wrangler whoami
npx wrangler deploy
```

5. CLI가 실제 출력한 URL과 새 버전의 /health를 확인합니다. 예상 개발 URL은
   https://csai.jeonmeensoo.workers.dev 입니다. 랜딩 하단 01~04 장점 카드 및 로그인/채팅/사이드바를 확인합니다.
   main 병합은 별도 검증 뒤 진행합니다.

## 현재 제한

- 모바일 채팅에서는 Cloudflare 인증된 CLI/계정 또는 연결된 PC 브라우저 제어가 불가능합니다.
- GitHub 직접 복제는 현재 실행 환경 DNS 문제로 실패했습니다.
- 자동 테스트는 실패 또는 미확인 상태이므로 테스트 성공을 확인하기 전 배포하지 않습니다.
- Supabase 실제 연결과 실제 PG, 외부 발송은 별도 설정 및 검증이 필요합니다.


## 기존 SQLite 자료를 Supabase로 이전하는 경우

기존 환경의 모든 쓰기를 멈추고 SQLite 공식 backup 기능으로 별도 백업을 만듭니다.
백업 파일과 기존 설정(.env, OAuth 설정, 암호화 키)을 안전한 위치에 보존합니다.
운영 자료나 키를 GitHub에 커밋하지 않습니다.
새 Supabase DB의 private schema를 초기화한 후 현재 브랜치로 스키마를 먼저 생성합니다.
DATABASE_URL은 해당 전용 DB의 비공개 환경변수로 설정합니다.

저장소 루트에서 (PYTHONPATH에 저장소 루트 포함):

```sh
python -m scripts.import_sqlite --source /path/to/offline-backup.sqlite3
```

기본은 읽기 전용 dry-run입니다. 기존 대상 데이터가 있거나 스키마/무결성 문제가 있으면 중단합니다.
검토한 백업으로 빈 대상 DB에 실제 이전하기로 결정한 경우에만 `--apply --confirmed-offline-backup`을 추가합니다.
이 도구는 실제 PostgreSQL 이전 테스트를 아직 통과하지 않았습니다. 반드시 복제된 테스트 데이터에서 검증합니다.
이전이 실패하더라도 기존 SQLite 백업을 삭제하지 않습니다. 두 DB에서 동시에 서비스를 쓰지 않습니다.
