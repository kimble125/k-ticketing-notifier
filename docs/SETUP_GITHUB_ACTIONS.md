# GitHub Actions 설정 가이드 — 컴퓨터 안 켜도 24/7 동작

## 왜 GitHub Actions 인가?

- **무료** (Public 레포 사용 시 사실상 무제한, Private는 월 2,000분)
- **24/7 가동** (본인 노트북 끄고 자도 동작)
- **시크릿 안전 보관** (GitHub 가 암호화 저장 + 코드/로그에 절대 노출 X)
- **로그 자동 보관** (Actions 탭에서 매 실행 로그 확인)

---

## ⚠️ 시작 전 절대 규칙

**아래 표의 값들은 모두 가짜 예시입니다. 절대 그대로 복사하지 말고 본인 정보를 입력하세요.**

이 문서에 본인 실제 값을 적어두는 것도 금지입니다. 실제 값은 오직
GitHub Secrets 의 입력 폼에만 직접 타이핑하세요. 한 번 저장된 Secret 은
GitHub 도 다시 보여주지 않으니, 코드나 문서에 남길 이유가 전혀 없습니다.

---

## 설정 단계 (초보자용, 약 10분)

### 1. 이 코드를 GitHub 에 올리기

GitHub Desktop 앱을 추천 (터미널 없이 GUI 로 push 가능):

1. https://desktop.github.com 에서 다운로드 → 설치 → 로그인
2. File → Add Local Repository → `ticket-notifier` 폴더 선택
3. Publish repository → 이름 `ticket-notifier`, **Public** 선택, Publish

> **중요**: `.env` 파일은 절대 커밋되지 않아요 (`.gitignore` 가 차단).
> `config.yaml` 도 마찬가지. 베이스 코드와 `config.example.yaml` 만 올라갑니다.

### 2. Secrets 등록

레포 페이지 → **Settings** (톱니바퀴) → 왼쪽 메뉴 **Secrets and variables** → **Actions**
→ **New repository secret** 으로 다음 항목을 하나씩 등록.

**아래 Value 열은 모두 가짜 예시이며, 실제 본인 값을 입력해야 합니다.**

| Name | Value (예시 — 본인 값으로 교체) | 필수 |
|---|---|---|
| `MJFF_NAME` | `(본인 실명)` | ✅ |
| `MJFF_PHONE` | `(본인 휴대폰, 하이픈 없이)` | ✅ |
| `MJFF_PASS` | `(예매자 인증 비밀번호 — 보통 생년월일 5~6자리)` | ✅ |
| `NTFY_TOPIC` | `(짐작 불가능한 랜덤 문자열)` 예: `mjff-XXXXXX-watcher-2026` | ✅ |
| `NTFY_SERVER` | `https://ntfy.sh` | ⚪ 기본값 |
| `PUSHOVER_USER_KEY` | (Pushover 가이드 참고) | ⚪ |
| `PUSHOVER_APP_TOKEN` | (Pushover 가이드 참고) | ⚪ |
| `TELEGRAM_BOT_TOKEN` | (선택) | ⚪ |
| `TELEGRAM_CHAT_IDS` | (선택) | ⚪ |

⚠️ **Secrets 등록 후**: 위 표의 가짜 값을 본인이 입력한 실제 값으로 절대 갱신해서
README 나 이 문서에 적지 마세요. Public 레포에 push 되면 노출됩니다.

### 3. Actions 활성화

1. 레포 페이지 → **Actions** 탭
2. "I understand my workflows, go ahead and enable them" 클릭
3. 좌측 메뉴에서 **ticket-notifier** 워크플로 선택
4. 우측 상단 **Run workflow** → **수동 테스트** (Force test alert 체크박스 켜고 실행) → ntfy 알림이 도착하는지 확인

### 4. 결과 확인

- Actions 탭에서 매 5분마다 새 실행이 쌓임
- 클릭하면 로그를 볼 수 있음 (어느 watcher 가 변경 감지됐는지 등)
- 알림은 ntfy 앱 + Pushover 앱으로 자동 도착

---

## 🆘 실수로 개인정보를 push 해버렸다면

git history 에 한 번 들어간 비밀값은 force push 해도 GitHub 캐시·포크·검색엔진에 남을 수 있습니다. 그래서 **노출됐다면 노출된 값 자체를 무효화**하는 게 정답입니다.

### 즉시 할 일 (5분)

1. **무주산골 예매자 비밀번호 변경**
   - 무주산골 측은 예매자 비밀번호 변경 절차가 명확하지 않을 수 있음 → 운영 문의로 요청
   - 또는 본인이 사용 가능한 다른 비밀번호로 재예매자 등록
2. **이미 등록된 GitHub Secrets 도 즉시 새 값으로 업데이트**
3. **노출된 파일을 갱신해서 다시 push** (위에 안전한 더미로 교체된 버전)

### 추가 권장 (10분)

git history 에서 노출된 커밋 자체를 지우는 게 깔끔합니다. 가장 쉬운 방법:

- GitHub 레포를 **삭제** → 본인 PC 의 `.git` 폴더도 삭제 → 새 레포로 다시 시작
- 또는 BFG Repo-Cleaner / git filter-repo 같은 도구 사용 (조금 복잡)

휴대폰 번호는 변경이 어려우니, "노출 자체"보다 "비밀번호 무효화" 가 우선입니다.

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

- Public 레포: **사실상 무제한**
- Private 레포: 월 2,000분 무료. 5분 cron + 매 실행 30초 → 월 ~3시간 사용 → OK
- 무료 시간 초과 시: 그 달 잔여 cron 이 멈춤. 다음 달 1일에 자동 복구
