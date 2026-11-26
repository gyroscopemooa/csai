# CS AI 개발 인수인계

실제 코드 기준: v0.4. 최신 요구사항: v0.5(초청 체험 포함).

이 ZIP은 v0.4 전체 소스, 기존 34페이지 기획서, 스크린샷 및 테스트 기록과 v0.5 인수인계 문서를 합친 것입니다. v0.5 전체 소스는 현재 확보되지 않았으므로 최신 기능이 이 ZIP에서 실행된다고 가정하지 마세요. GUI에서 누락된 변경을 실제로 구현·테스트해야 합니다.

## Windows 시작
1. C:\Projects\CSAI 폴더에 압축 해제. app.py가 폴더 바로 아래에 있어야 합니다.
2. GUI/Codex에서 이 폴더를 열고 GUI_FINAL_COMMAND.md의 내용을 전달합니다.
3. Python 3.11+가 있다면 start_windows.bat을 실행하고 http://127.0.0.1:3000 에서 로컬 확인. test_windows.bat으로 테스트.
4. Google OAuth/OpenAI/Supabase/배포 서비스 등 연결은 GUI와 함께 진행. 실제 키는 채팅이나 Git에 기록하지 말 것.

## 자료
- GUI_FINAL_COMMAND.md: 최우선 실행 명령
- handoff/HANDOFF_GUI_v05.md, handoff/README_v05.md: 최신 상세 지침
- reference/CS_AI_개발기획_명령서.docx: 원본 34페이지 기획서 (직접 교육 무료 등 일부 과거 정책은 최신 지침으로 대체)
- verification/: v0.4 과거 테스트 및 화면 캡처
- README.md: v0.4 실제 소스 사용 설명

공개 인터넷에 로컬 데모 서버를 그대로 노출하지 마세요.
