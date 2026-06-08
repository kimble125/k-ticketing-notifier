# 새 Opus 4.8 채팅 시작 시 첫 메시지 템플릿

호연님이 새 채팅 열고 다음 메시지를 그대로 보내시면 됩니다 (별표 부분만 본인 상황에 맞게 채워주세요):

---

```
안녕! k-ticketing-notifier 프로젝트의 후속 작업을 시작합니다.
첨부한 HANDOFF.md 를 가장 먼저 읽어주세요. 본 프로젝트에 대한 컨텍스트,
이전 채팅의 결정·실패 이력·호연님 선호도·미해결 이슈가 다 정리돼 있어요.

## 첨부 파일
- HANDOFF.md (가장 먼저 정독)
- 패치 4종:
  - src/crawlers/seoul_outdoor_library.py
  - src/crawlers/__init__.py
  - config.example.yaml
  - .github/workflows/notify.yml

## 본 채팅의 목표
1. 위 패치를 본인 ticket-notifier 폴더에 적용 + GitHub push
2. 서울야외도서관 힙독클럽 5개 프로그램 알림이 실제로 동작하도록 _parse 메서드 보강
3. GitHub Actions "Run failed" 이슈 진단·해결
4. (선택) HANDOFF.md §7 의 고도화 항목 중 우선순위 결정

## 본 채팅에서 가장 먼저 해주실 일
- HANDOFF.md 정독 (특히 §5 미해결 이슈, §8 주의사항)
- 본인 폴더에 패치 적용 가이드 안내
- 폴더 경로: /Users/kimble/Library/CloudStorage/GoogleDrive-hoykim125@gmail.com/내 드라이브/Git/ticket-notifier

호연님 GitHub: https://github.com/kimble125/k-ticketing-notifier
```

---

## 첨부 시 주의

- **HANDOFF.md 와 패치 zip 을 같이 첨부** (또는 패치 폴더 전체를 마운트)
- 새 채팅 시작 직후 호연님께 "git clone 으로 코드 전체를 받아도 될까요?" 라고 묻기 권장
- 새 채팅의 첫 응답에서 HANDOFF.md 의 §1·§2·§5·§8 을 자기 말로 요약해줘서 컨텍스트 흡수 검증
