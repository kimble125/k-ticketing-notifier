# 호연님께 — 이 패키지로 무엇을 하면 되나요?

## 한 줄 요약
이 zip 의 파일 4개를 본인 `ticket-notifier` 폴더에 덮어쓰고 GitHub 에 push 한 뒤,
**새 Opus 4.8 채팅을 열어서 `HANDOFF.md` 와 패치를 첨부**하면 됩니다.

## 단계별 (5분)

### 1. 본인 폴더에 패치 적용
1. zip 안의 파일들을 본인 `ticket-notifier` 폴더에 **같은 경로로** 복사:
   - `config.example.yaml` → 폴더 루트
   - `.github/workflows/notify.yml` → 같은 위치
   - `src/crawlers/__init__.py` → 같은 위치 (덮어쓰기)
   - `src/crawlers/seoul_outdoor_library.py` → 신규 추가
2. GitHub Desktop 으로 commit & push

### 2. 새 Opus 4.8 채팅 열기
1. Cowork 새 채팅 → 모델 Opus 4.8 선택
2. `HANDOFF.md` 와 `FIRST_MESSAGE_TEMPLATE.md` 를 첨부
3. `FIRST_MESSAGE_TEMPLATE.md` 안의 메시지를 그대로 복사해서 보내기

### 3. 새 채팅에 추가로 도와줄 일
새 채팅이 묻는 것 따라가시면 됩니다. 다음 정도가 예상돼요:
- 서울야외도서관 페이지를 한 번 본인이 브라우저에서 열어서 화면 캡처
- Actions Run failed 의 상세 로그 캡처
- firefly 필요 여부 (네이버 부계정 만들지 결정)

## 잊지 말 것
- **mjff 비활성화 됨** — 영화제 종료. 다음 시즌 시작 시 config 에서 `enabled: true` 로
- **서울야외도서관 5개 프로그램 알림이 본 패치의 주력**
- **HANDOFF.md 가 새 채팅의 핵심 컨텍스트** — 절대 빼먹지 마세요
