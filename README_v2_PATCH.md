# ─── v2 변경사항 (이 섹션을 기존 README.md 의 적절한 위치에 추가하세요) ───

## 🆕 v2 추가 사이트 (총 4개 추가)

| 사이트 | type | 시크릿 추가 | 주기 |
|---|---|---|---|
| 무주등나무운동장 1일 입장권 | `mjff_stadium` | 기존 MJFF_* 재사용 | 5분 |
| 숙박 일정 선택 (6/6 가족호텔 골드) | `mjff_lodging` + `select_date` | 기존 재사용 | 5분 |
| 운문산 반딧불이 신비탐사 | `firefly` | `NAVER_ID`, `NAVER_PW` ★ | 10분 |
| CGV 매진 빈자리 (너바나 GV) | `cgv` | 추가 X | 15분 (기본 비활성) |

자세한 설정/시크릿 등록은 [docs/SETUP_NEW_SITES.md](docs/SETUP_NEW_SITES.md) 참고.

### v2 적용 방법

1. outputs 폴더의 변경된 파일들을 본인 `ticket-notifier` 폴더에 덮어쓰기
2. GitHub Secrets 에 `NAVER_ID`, `NAVER_PW` 신규 등록 (firefly 사용 시)
3. `config.example.yaml` 의 새 watchers 검토 + 본인 환경에 맞게 수정
4. CGV watcher 는 기본 `enabled: false` — 필요할 때만 켜기
5. GitHub Desktop 으로 commit & push
