# GitHub Actions 설정 가이드 — 컴퓨터 안 켜도 24/7 동작

## 왜 GitHub Actions 인가?

- **무료** (퍼블릭 레포 + Public 사용자: 월 2,000분 / 5분 cron 기준 충분)
- **24/7 가동** (본인 노트북 끄고 자도 동작)
- **시크릿 안전 보관** (비밀번호/토큰을 GitHub 가 암호화 저장)
- **로그 자동 보관** (Actions 탭에서 매 실행 로그 확인)

---

## 설정 단계 (초보자용, 약 10분)

### 1. 이 코드를 GitHub 에 올리기

이미 `kimble125/movie-club-ticket-notifier` 에 비슷한 게 있다면 그 레포를 업데이트하면 됨.
새로 만들 거라면:

1. github.com → New repository
2. 이름: `ticket-notifier` (또는 원하는 이름)
3. **Public** 선택 (Actions 무료 시간이 더 많음)
4. README 체크 해제 (이미 있음)
5. Create repository

로컬에서:
```bash
cd ticket-notifier
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/본인아이디/ticket-notifier.git
git push -u origin main
```

> **중요**: `.env` 파일은 절대 커밋되지 않아요 (`.gitignore` 가 차단).
> `config.yaml` 도 마찬가지. 베이스 코드와 `config.example.yaml` 만 올라갑니다.

### 2. Secrets 등록

레포 페이지 → **Settings** (톱니바퀴) → 왼쪽 메뉴 **Secrets and variables** → **Actions**
→ **New repository secret** 으로 다음 항목을 하나씩 등록:

| Name | Value | 필수 |
|---|---|---|
| `MJFF_NAME` | 홍길동 | ✅ |
| `MJFF_PHONE` | 01084437243 | ✅ |
| `MJFF_PASS` | 910125 | ✅ |
| `NTFY_TOPIC` | mjff-7a3f9b2c-watcher-2026 | ✅ |
| `NTFY_SERVER` | https://ntfy.sh | ⚪ (생략 시 기본값) |
| `PUSHOVER_USER_KEY` | (Pushover 가이드 참고) | ⚪ |
| `PUSHOVER_APP_TOKEN` | (Pushover 가이드 참고) | ⚪ |
| `TELEGRAM_BOT_TOKEN` | (선택) | ⚪ |
| `TELEGRAM_CHAT_IDS` | (선택) | ⚪ |

### 3. Actions 활성화

1. 레포 페이지 → **Actions** 탭
2. "I understand my workflows, go ahead and enable them" 클릭
3. 좌측 메뉴에서 **ticket-notifier** 워크플로 선택
4. 우측 상단 **Run workflow** → 한 번 수동 실행해서 정상 동작 확인

### 4. 결과 확인

- Actions 탭에서 매 5분마다 새 실행이 쌓임
- 클릭하면 로그를 볼 수 있음 (어느 watcher 가 변경 감지됐는지 등)
- 알림은 ntfy 앱 + Pushover 앱으로 자동 도착

---

## 문제 해결

### "secrets not set" 같은 에러
→ Settings → Secrets and variables 에 값이 잘 들어갔는지 확인.
   값은 한 번 저장 후 다시 볼 수 없으니, 잊으면 새로 만들어야 함.

### "Playwright timeout" 에러
→ GitHub Actions 의 인프라가 일시적으로 느릴 때 발생. 다음 5분 cron 에서 재시도됨.
   같은 에러가 연속 3번 이상이면 무주산골 사이트가 진짜 다운됐을 가능성.

### state 파일이 계속 커밋되는 게 부담스럽다
→ `.github/workflows/notify.yml` 의 "Persist state" 스텝을 제거하면 됨.
   대신 매 실행이 "처음 본 페이지"로 인식돼서 매번 알림이 발송될 수 있음.

### 5분보다 더 자주 돌리고 싶다
→ GitHub Actions cron 의 최소 간격이 5분이라 불가. 더 빠르게 하려면
   본인 PC + cron 또는 Raspberry Pi 가 필요.

---

## 비용/한도 요약

- Public 레포: **사실상 무제한** (GitHub 정책상 한도 명시 X)
- Private 레포: 월 2,000분 무료. 5분 cron + 매 실행 30초 → 월 ~3시간 사용 → OK
- 무료 시간 초과 시: 그 달 잔여 cron 이 멈춤. 다음 달 1일에 자동 복구

> 본 프로젝트는 영화제 기간 (보통 2~4주) 동안만 돌리면 되므로 Public/Private 둘 다 무료 한도 안에서 운영 가능.
