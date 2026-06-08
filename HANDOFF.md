# HANDOFF — k-ticketing-notifier 새 채팅 컨텍스트 인수인계

> 이 문서는 **새 Opus 4.8 채팅에 가장 먼저 첨부할 컨텍스트** 입니다.
> 새 채팅은 이 문서만 읽으면 호연님의 프로젝트·결정·실패·선호도를 모두 파악할 수 있어야 합니다.

---

## 0. 새 채팅이 가장 먼저 해야 할 일

1. 이 HANDOFF.md 전체를 정독
2. 호연님 GitHub 레포 https://github.com/kimble125/k-ticketing-notifier 를 `git clone` 으로 로컬 작업 폴더에 받기
3. 함께 첨부된 **patch 파일들**(`src/crawlers/seoul_outdoor_library.py`, 새 `crawlers/__init__.py`, 새 `config.example.yaml`, 새 `.github/workflows/notify.yml`) 을 레포에 덮어쓰기
4. 본격 작업 시작 전 README + 본 HANDOFF 의 모든 "주의" 마크를 확인

---

## 1. 프로젝트 한 줄 요약

**한국 예매/모집 사이트 자동 모니터링 봇.** 사용자가 fork 해서 본인 정보 채우면 GitHub Actions 5분 cron 으로 무료 24/7 동작. 상태 변경 시 ntfy/Pushover/Telegram 으로 알림.

- GitHub: https://github.com/kimble125/k-ticketing-notifier
- 로컬 작업 폴더: `/Users/kimble/Library/CloudStorage/GoogleDrive-hoykim125@gmail.com/내 드라이브/Git/ticket-notifier`
  - ⚠️ **Google Drive 동기화 락 빈발** — 자세한 건 §6 참고

---

## 2. 사용자(호연님) 프로필

| 항목 | 정보 |
|---|---|
| 직업 | 데이터 엔지니어링/분석/사이언스 분야 입문자 |
| 코딩 경험 | Python 기초 단계. 터미널 사용 가능하지만 익숙치 않음 |
| 선호 응답 언어 | **한국어** |
| 응답 스타일 | 단계별·구체적·초보자 친화. 전문가 수준 깊이는 유지하되 산출물은 쉬워야 함 |
| 의사결정 방식 | 선택지 제시·트레이드오프 비교를 좋아함. AskUserQuestion 활용 권장 |
| 자주 쓰는 도구 | GitHub Desktop (터미널 대안), ntfy 앱 (iOS), Mac |

> 호연님은 **단계별 가이드를 매우 자세히** 원합니다. "GitHub Secrets 등록" 같은 동작도 클릭 위치까지 분해해서 설명해야 함. 추상적 안내(예: "쿠키 export 하세요")는 거의 못 따라옴.

---

## 3. 현재 시스템 아키텍처

```
GitHub Actions (5분 cron, Node.js 24)
   │
   └─► python main.py --check
          │
          ├─► src/scheduler.py        시간대별 간격 + 지터 + URGENT 격상
          ├─► src/heartbeat.py        매일 1회 살아있어요 알림 (옵션)
          ├─► src/state.py            해시 변경감지 + 쿨다운
          ├─► src/crawlers/           ★ watcher type 별 분기
          │     ├─ mjff_*             (영화제 — 종료, 비활성)
          │     ├─ firefly            (네이버 로그인 필요)
          │     ├─ seoul_outdoor_library  ★ 신규, 스켈레톤만 있음
          │     └─ webpage            (일반 변경감지)
          └─► src/notifiers/          ★ 알림 채널 다중화
                ├─ ntfy.py            (메인, 무료)
                ├─ pushover.py        (새벽 Critical Alert)
                ├─ telegram.py        (선택)
                └─ multi.py           (어그리게이터)
```

### 핵심 설계 결정 (변경하지 말 것)

1. **YAML + .env 통합**: 비밀값은 `${VAR}` 패턴으로 환경변수 치환. `src/config.py` 의 `_interpolate_env`.
2. **세션 재사용**: dtidea/firefly 인증 후 `data/state/cookies/*.json` 으로 storage_state 저장. 재로그인 빈도 ↓ → 사이트 부담 ↓.
3. **지터 + 시간대별 간격**: `src/scheduler.py` 의 `DEFAULT_RULES`. 평시 5분 / 자정 ±30분 1분 / 새벽 15분. 매번 ±15초 랜덤.
4. **URGENT priority 자동 격상**: 새벽엔 ntfy max + Pushover Emergency. iOS DND 무력화.
5. **쿨다운**: 같은 알림이 5분마다 반복되지 않도록 `cooldown_minutes` 옵션. `src/state.py` 의 `in_cooldown`.

---

## 4. 현재 작업해야 할 새 요구사항 — 서울야외도서관 힙독클럽

### 4.1 감시 대상 (호연님 직접 지정)

URL: https://seouloutdoorlibrary.kr/user/program/selectPageListProgram.do?area_id=hipdok&flag=program_list

다음 5개 프로그램의 상태 변경 시 알림:
1. 노마드리딩 ③ : 커피향 바다독서 in 강릉
2. [리딩몹] 최애책 재독단 #4. 소장하고 싶은 그 책
3. [리딩몹] 챕터 퍼즐 리딩 #1. 기록하기로 했습니다.
4. [힙독클럽 X 서울도서관] 작가힙톡_하주원 작가 : 운동하면 좋은 걸 누가 모르냐고요
5. [힙독클럽 X 서울도서관] 작가힙톡_하지현 작가 : 스트레스는 나를 어떻게 바꾸는가

### 4.2 감지 조건 (호연님 표현)

"'정원 마감' 이 '신청중'(혹은 기타 다른 표시)으로 바뀌거나, **혹은** 모집 정원이 바뀔 때 — **둘 중 더 원활하고 효과적인 일에 알림**"

→ 새 채팅은 다음을 먼저 검증한 뒤 더 신뢰성 있는 신호 채택:
   - (A) 상태 텍스트 변경: 정원 마감 → 신청중 (사이트 정책이 바뀌지 않는 한 안정적)
   - (B) 신청자 수/정원 숫자 변경: 취소표 발생 감지 가능. 다만 카운트 표시가 없을 가능성도 ↑

### 4.3 권장 첫 단계 (새 채팅에서)

1. **로컬에서 페이지 직접 fetch + HTML inspect** (Playwright headless=false 권장)
   - 사이트가 SSR 인지 SPA 인지 결정 → `use_playwright` 옵션 토글
   - 프로그램 카드의 CSS 셀렉터 확정
   - "정원 마감" / "신청중" 같은 정확한 텍스트 표현 확인
2. **스켈레톤 (`src/crawlers/seoul_outdoor_library.py`) 의 `_parse` 메서드 보강**
3. **5개 프로그램 모두 매칭되는지 테스트** (`python main.py --check` 으로 dry-run)
4. **푸시 검증**: ntfy 앱에서 알림 도착 확인
5. **GitHub Actions 에 배포** → 5분 cron 으로 진짜 감시 시작

---

## 5. 미해결 이슈 — 새 채팅이 디버깅해야 할 것들

### 🚨 이슈 1: GitHub Actions Run failed (exit 1) 반복

**증상**:
- 이메일로 "Run failed" 알림 계속 옴
- 최근 run: https://github.com/kimble125/k-ticketing-notifier/actions/runs/27048562329
- Annotations: `Process completed with exit code 1` + `Node.js 20 actions are deprecated` warning

**원인 후보** (확률 순):
1. **MJFF/firefly watcher 실패 → main.py 가 exit 1** ← v4 patch 에서 mjff 모두 비활성화로 해결 가능. 새 채팅이 먼저 패치 적용 후 다시 run 해서 검증
2. **playwright install 단계 timeout** — 12분 timeout 늘림 + chromium 캐시 활용
3. **config.example.yaml 파싱 실패** — v4 patch 에서 YAML 검증됨
4. **state 파일 git push 권한 부족** — `permissions: contents: write` + `git push || echo warning` 으로 완화
5. **Secrets 미설정 / 오타** — Actions 로그의 `[ERROR]` 줄 직접 확인 필요

**진단 절차**:
1. 새 patch 적용 후 Actions 탭에서 다음 run 트리거 (workflow_dispatch → `debug: true`)
2. "Run check" step 의 로그를 위에서 아래로 정독 → 어느 watcher 에서 끊겼는지 확인
3. 실패 watcher 의 `Traceback` 또는 `[ERROR]` 메시지로 좁히기
4. 단일 watcher 만 활성화한 채로 재실행하여 격리

### 🚨 이슈 2: Node.js 20 deprecation

v4 patch 에서 해결:
- `actions/checkout@v4` → `@v5`
- `actions/setup-python@v5` → `@v6`
- env `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"` 설정

이건 **에러가 아닌 경고**였으므로 진짜 실패 원인은 따로. 위 §1 참고.

### 🚨 이슈 3: 서울야외도서관 페이지 구조 미파악

본 세션에서는 web_fetch 로 페이지를 받지 못했고 (SPA 가능성), 직접 페이지를 inspect 할 수단이 없었음. **새 채팅은 본인 PC 에서 Playwright headless=false 로 1회 페이지를 띄워보고 구조를 파악하는 게 필수**.

### 🚨 이슈 4: firefly 네이버 2FA

- 운문산 반딧불이가 활성화될 경우 네이버 2FA 가 GitHub Actions runner 에서 막을 수 있음
- 해결책 (3가지) 은 `docs/SETUP_NEW_SITES.md` 의 옵션 A/B/C 참고
- **호연님 진행 상태**: 옵션 A(부계정 만들기) 또는 옵션 C(쿠키 export) 중 본인이 선택할 예정. 확인 필요

### 🚨 이슈 5: Google Drive 동기화 락 (개발 환경)

- 로컬 작업 폴더가 Google Drive 안에 있음
- Drive 클라이언트가 파일을 잠가서 cp/edit 실패 빈발 (`Resource deadlock avoided`)
- **해결책**:
  - 본 세션에서는 sandbox `/tmp` 또는 outputs 폴더에 새 파일 작성 후 zip 으로 묶어 사용자에게 전달 (이 패키지 방식)
  - 또는 GitHub Desktop 으로 commit & push 한 뒤 새 채팅이 git pull 로 받기

### ⚠️ 이슈 6: 호연님 개인정보 노출 이력

본 세션 초기에 **두 차례 실수**가 있었음:
1. 호연님이 첫 메시지에 무주산골 비밀번호 `910125` 노출 → SETUP_GITHUB_ACTIONS.md 에 예시값으로 그대로 옮김 → 이후 더미값으로 교체
2. 호연님이 firefly 용 네이버 비밀번호 `Getathesis8282!!` 를 채팅에 직접 입력

**새 채팅이 지킬 규칙**:
- 호연님이 코드/문서/채팅에 비밀값을 **절대 적지 말도록** 안내. 실수 시 즉시 변경 권장
- 작성하는 모든 문서·코드·예시에 자리표시자(`(본인 값으로 교체)`)만 쓰기. 호연님의 실제 메시지를 그대로 따와서 복사 X
- 노출 발견 시 즉시 알리고 비밀번호 변경 권장

---

## 6. 새 채팅의 권장 작업 흐름 (체크리스트)

- [ ] 본 HANDOFF 정독
- [ ] 패치 4종 (config / workflow / crawlers/__init__.py / seoul_outdoor_library.py) 확인
- [ ] 호연님께 git clone 시켜서 새 채팅이 코드 전체를 읽을 수 있는 상태로 만들기
- [ ] 패치 적용 + commit & push → Actions 첫 run 결과 확인
- [ ] Actions 실패 시 `inputs.debug=true` 로 재실행 → 정확한 실패 원인 파악
- [ ] 서울야외도서관 페이지를 headless=false 로 띄워서 HTML 구조 inspect
- [ ] seoul_outdoor_library.py 의 `_parse` 정확한 셀렉터로 보강
- [ ] 5개 프로그램 매칭 검증 (한 번 dry-run)
- [ ] 첫 알림 도착 확인 (테스트로 `enabled` 토글, 또는 force_test_alert)
- [ ] heartbeat 활성 권장 (`HEARTBEAT_ENABLED=true` Secret 또는 config)

---

## 7. 알림봇 고도화·효율화 권장사항 (장기)

새 채팅이 본격 작업 후 여유 있을 때 검토할 만한 개선점:

### 7.1 단일 watcher 실패 격리
현재 main.py 는 한 watcher 가 실패해도 다른 watcher 는 계속 진행하지만, 마지막에 exit code 결정 로직이 모든 watcher 의 결과를 종합하지 않음. → 부분 실패 시에도 0 으로 종료하도록 (또는 별도 metrics 알림)

### 7.2 watcher 별 로그 라인 prefix 통일
현재 `logger.info(f"[{name}] ...")` 패턴인데, `name` 이 한글이라 로그 grep 이 어려움. 영문 `slug` 옵션 추가 권장.

### 7.3 Playwright 캐시 영속화
GitHub Actions cache 로 `~/.cache/ms-playwright` 캐싱 → 매 run 마다 chromium 재다운로드 안 해도 됨. 8분 timeout 여유 ↑

### 7.4 Daily run summary 알림 (heartbeat 의 발전형)
하루 1회 24시간 동안의:
- 총 run 횟수, 성공/실패 비율
- watcher 별 변경 감지 횟수
- 평균 소요 시간
- 다음 24시간 예측 (예: 자정 오픈 임박이면 cron 가속 안내)

### 7.5 multi-region ntfy fallback
ntfy.sh 단일 장애 대비. 자체 호스팅 ntfy 인스턴스를 백업으로.

### 7.6 사용자가 알림에서 "5분 mute" 버튼 누를 수 있게
ntfy action button 으로 webhook 호출 → 해당 watcher 일시 비활성. iOS 한정으로는 Pushover 의 callback url.

### 7.7 watcher 검증 단계 (Dry-run)
실제 알림 발송 없이 "지금 알림이 갈 조건인가" 만 출력하는 모드. 개발 중 유용.

### 7.8 CGV 재시도 (선택)
v3 에서 제거했지만, 만약 호연님이 다시 필요해지면:
- CGV 가 새 사이트 SPA 로 전환된 게 핵심 차단 원인
- 레거시 URL (`iframeTheater.aspx`) 이 일부 살아있을 가능성 재검토
- 약관 회색지대 + Cloudflare 봇 탐지 위험은 그대로

---

## 8. 개발 도중 절대 잊지 말 주의사항

1. **🚨 비밀값은 절대 코드/문서/채팅 본문에 적지 않는다.** 자리표시자만 사용
2. **🚨 호연님 메시지에 비밀번호가 보이면 즉시 알리고 변경 권장**
3. **호연님은 터미널 안 익숙 — GitHub Desktop 우선 안내**
4. **모든 단계는 "클릭 위치"까지 분해** (예: "오른쪽 위 ⚙️ Settings → 왼쪽 사이드바 Security 헤더 아래 Secrets and variables → Actions 클릭")
5. **테스트 알림은 항상 force_test_alert 또는 브라우저 `https://ntfy.sh/TOPIC?title=test&message=hi` 로**
6. **Google Drive 락 발생 시** sandbox /tmp 또는 outputs 폴더 활용 + zip 으로 묶어 전달
7. **mjff 는 비활성화 상태 유지** — 2026.06 종료. 차년도 시작 시 호연님 확인 후 재활성
8. **새 사이트 추가 시 항상**:
   - .env.example 에 시크릿 추가
   - .github/workflows/notify.yml 에 `env:` 주입 추가
   - GitHub Secrets 등록 안내
   - SETUP_NEW_SITES.md 에 옵션 단계 추가
9. **firefly 같은 인증 사이트는 storage_state 세션 재사용을 적극 활용**
10. **AskUserQuestion 도구를 적극 활용** — 호연님이 트레이드오프 비교를 좋아함

---

## 9. 새 채팅에 첨부할 파일 목록 (체크리스트)

본 zip(`k-ticketing-notifier-handoff.zip`) 에 포함:

```
HANDOFF.md                                ★ 새 채팅 첫 입력으로 첨부
src/crawlers/seoul_outdoor_library.py     스켈레톤
src/crawlers/__init__.py                  seoul 라우팅 추가
config.example.yaml                       mjff 비활성, seoul 활성
.github/workflows/notify.yml              Node 24 호환 + 디버그 입력
```

추가로 새 채팅에서 **호연님께 요청해서** 받아야 할 것:
- (선택) `https://github.com/kimble125/k-ticketing-notifier` git clone → 전체 코드 컨텍스트 확보
- (필요시) 최근 Actions run 실패 로그 캡처 → 정확한 디버깅
- (필요시) 서울야외도서관 페이지의 실제 HTML 일부 (Chrome DevTools → Elements → 프로그램 카드 inspect → outerHTML 복사)

---

## 10. 빠른 명령어 모음 (참고)

```bash
# 본인 PC 에서 한 번 dry-run
cd ~/Library/CloudStorage/GoogleDrive-*/Git/ticket-notifier
python3 main.py --test-alert      # 알림 채널만 검증
python3 main.py --heartbeat        # 강제 heartbeat 발송
python3 main.py --check            # 전체 watcher 1회 실행

# GitHub Actions 수동 테스트
# → 레포 페이지 → Actions 탭 → k-ticketing-notifier → Run workflow
#    → Force test alert 또는 Debug 체크박스 활용

# 브라우저로 ntfy 즉시 발송 (10초 검증)
# https://ntfy.sh/본인토픽?title=test&message=hello
```

---

## 11. 본 세션의 작업 이력 요약

| Phase | 산출물 |
|---|---|
| v1 | monitor_mjff.py 단일 스크립트 → 정식 프로젝트 구조 변환. mjff 인증 크롤러 + ntfy + Pushover + GitHub Actions 5분 cron |
| v2 | mjff_stadium (등나무운동장), firefly, cgv, mjff_lodging 일정선택 모드 추가. SETUP_NEW_SITES.md 초보자 가이드 |
| v3 | CGV 제거 (CGV 가 SPA 로 리뉴얼 → URL 직접 진입 불가 + 약관 회색지대) |
| **v4 (현재)** | **mjff 시즌 종료 → 모두 비활성. 서울야외도서관 신규 + Node.js 24 호환 + 에러 로깅 강화** |

---

끝. 새 채팅이 본격 진행할 때 막히는 부분 있으면 본 문서로 돌아와서 §5 / §8 다시 확인.
