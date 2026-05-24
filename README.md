<div align="center">

# 🎟 ticket-notifier

**예매 오픈을 절대 놓치지 않는 알림 봇 — 무주산골영화제 전용 + 다른 사이트 응용 가이드**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![ntfy](https://img.shields.io/badge/ntfy-supported-brightgreen)](https://ntfy.sh)
[![Pushover](https://img.shields.io/badge/Pushover-Critical%20Alerts-orange)](https://pushover.net)
[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Free%2024%2F7-2088FF?logo=githubactions&logoColor=white)](https://docs.github.com/en/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## ⚠️ 보안 경고 — 가장 먼저 읽어주세요

- **이 레포지토리의 어떤 문서·코드 파일에도 본인 개인정보(실명, 휴대폰, 비밀번호, 토큰)를 절대 적지 마세요.**
- 실제 값은 **오직 두 곳에만** 입력합니다:
  1. 본인 컴퓨터의 `.env` 파일 (`.gitignore` 가 차단 → GitHub 에 안 올라감)
  2. GitHub 레포 **Settings → Secrets and variables → Actions** 의 입력 폼 (암호화 저장)
- 실수로 한 번 push 된 비밀번호는 git history·GitHub 캐시·검색엔진에 남을 수 있습니다.
  실수가 있었다면 **비밀번호를 변경**하고 [복구 가이드](docs/SETUP_GITHUB_ACTIONS.md#실수로-개인정보를-push-해버렸다면)를 따라주세요.

---

## 🎯 어떤 문제를 해결하나요?

무주산골영화제 같은 인기 영화제는 **숙박패키지**와 **실내상영 티켓**이 오픈
즉시 매진됩니다. 정확한 오픈 시각이 불확실하거나 자정에 오픈되는 경우가 많아서,
사용자가 직접 5분마다 새로고침해야 하는 답답한 상황이 생겨요.

이 봇은:
- **5분마다 자동으로 사이트를 체크** (인기 시간엔 1분 간격으로 가속)
- 상태가 "온라인매진" → "예매하기" 로 바뀌면 **즉시 알림**
- **새벽 3시라도 수면모드 무력화** (Pushover Emergency Priority)
- GitHub Actions 무료로 **24/7 가동** (본인 컴퓨터 꺼져 있어도 OK)
- 개인정보는 `.env` 로 분리 → **GitHub 공개해도 안전**
- 매일 1회 "살아있어요" heartbeat 알림 (선택)

---

## 🚀 5분 만에 시작하기 (초보자용)

### 1단계 — 알림 받을 채널 준비 (ntfy, 가입 X)

1. 휴대폰에 **ntfy** 앱 설치 (App Store / Play Store)
2. 앱 실행 → "+" 버튼 → 토픽 이름 입력
   - 예: `mjff-7a3f9b2c-watcher-2026` ← 짐작 불가능한 랜덤 조합 권장
   - 이 토픽 이름이 곧 **본인 전용 알림 채널** 입니다 (URL 형태로 공개되므로 추측 어렵게)
3. 토픽 이름을 기억해두세요 (다음 단계에 입력)

### 2단계 — 레포 fork (GitHub 가입 필요)

본인 GitHub 계정에서 이 레포 fork. GitHub Desktop 앱을 추천 (터미널 없이 GUI):
1. https://desktop.github.com 다운로드 + 로그인
2. File → Add Local Repository → `ticket-notifier` 폴더 선택
3. Publish repository → Public 선택 + Publish

### 3단계 — Secrets 등록 (개인정보를 안전하게 GitHub 에 저장)

본인 fork 레포 → **Settings** → **Secrets and variables** → **Actions** →
**New repository secret** 으로 다음 5개를 등록.

**⚠️ Name 은 그대로 적되, Value 는 본인 실제 값을 입력하세요. 이 README 나 docs 에 절대 본인 값을 적어두지 마세요.**

- `MJFF_NAME` : 본인 실명
- `MJFF_PHONE` : 본인 휴대폰 번호 (하이픈 없이)
- `MJFF_PASS` : 예매자 인증 비밀번호 (보통 생년월일 5~6자리)
- `NTFY_TOPIC` : 1단계의 토픽 이름
- `NTFY_SERVER` : `https://ntfy.sh` (생략 가능)

상세: [docs/SETUP_GITHUB_ACTIONS.md](docs/SETUP_GITHUB_ACTIONS.md)

### 4단계 — Actions 활성화 + 즉시 테스트

레포 페이지 → **Actions** 탭 → "I understand..." 클릭 → 활성화.

**테스트 알림을 강제로 보내려면 (변경 감지 조건 무시):**
1. Actions 탭 → 왼쪽 메뉴에서 **ticket-notifier** 선택
2. 오른쪽 위 **Run workflow** 버튼 클릭
3. **`Force test alert` 체크박스를 켜고** Run 클릭
4. 약 30초~1분 후 ntfy 앱에 테스트 알림이 도착하면 정상

### 5단계 (선택) — 새벽 알람용 Pushover

자정에 예매가 열리면 ntfy 알림이 iOS 방해 금지 모드에 막힐 수 있어요.
**Pushover** 를 추가하면 사이렌으로 강제 기상시켜줍니다.

설정: [docs/SETUP_PUSHOVER.md](docs/SETUP_PUSHOVER.md) (앱 $5 결제, 약 5분)

---

## 🧪 알림이 안 올 때 — 즉시 테스트하는 3가지 방법

> 변경 감지 조건이 안 맞으면 알림이 안 오는 게 정상입니다. 채널 자체가
> 작동하는지 검증하려면 아래 방법으로 강제로 알림을 발생시키세요.

### 방법 A — GitHub Actions 의 Force test alert (가장 권장)
위 4단계 마지막 항목 그대로. 환경변수 → main.py → ntfy → 휴대폰까지 전 경로 검증됩니다.

### 방법 B — 브라우저로 ntfy 토픽에 직접 발송 (가장 빠름)
모바일 또는 PC 브라우저 주소창에 다음을 입력 + 엔터:

```
https://ntfy.sh/본인의토픽이름?title=test&message=hello
```

GET 요청만으로 알림이 전송됩니다. 1초 안에 ntfy 앱에 도착하면 채널은 정상.

### 방법 C — 로컬에서 (Python 환경이 있다면)
```bash
python main.py --test-alert    # 알림 채널만 검증
python main.py --heartbeat      # heartbeat 강제 발송
```

---

## 🟢 Daily heartbeat — 매일 1회 "살아있어요" 알림 (선택)

### 켜기

`config.example.yaml` 의 `heartbeat` 섹션에서:
```yaml
heartbeat:
  enabled: true        # ← 기본 false 였던 것을 true 로
  hour: 12             # 매일 정오에 발송
  minute: 0
  priority: "low"      # 조용한 알림 (방해 금지)
```

→ GitHub 에 push 하면 다음 정오부터 매일 자동 발송.

### 끄기 (3가지 중 어느 것이든 한 줄)

| 방법 | 설명 |
|---|---|
| ① `enabled: false` | `config.example.yaml` 의 heartbeat 섹션에서 토글만 변경 |
| ② 섹션 통째 주석 | `heartbeat:` 부터 끝까지 모든 줄 앞에 `#` |
| ③ Secrets 에서 끄기 | GitHub Secrets 에 `HEARTBEAT_ENABLED` = `false` 추가 → config 무시 |

→ 어느 방법이든 push 하면 즉시 적용. ③번은 코드 수정 없이 GitHub 웹에서 끄고 켤 수 있어서 가장 편함.

### 작동 원리

5분 cron 으로 호출되더라도 `src/heartbeat.py` 가 "오늘 보냈는지" 를 상태
파일로 추적해서 **하루에 정확히 1번** 만 발송합니다. 발송 시각 이후 첫
cron 호출에서만 발동.

---

## 🔧 모니터링 대상 변경 / 다른 사이트 응용

`config.example.yaml` 의 `watchers:` 섹션을 수정. 예시 — 다른 영화 추가:

```yaml
- name: "무주산골 실내상영 6/6"
  type: "mjff_screening"
  settings:
    date: "2026-06-06"
    targets:
      - movie: "별과 모래"
        time: "10:30"
      # 원하는 영화 + 시간 추가
```

dtidea 가 아닌 다른 사이트는 일반 변경 감지로:
```yaml
- name: "메가박스 코엑스 돌비"
  type: "webpage"
  settings:
    url: "https://www.megabox.co.kr/theater/time"
    selector: ".theater-schedule"
    encoding: "utf-8"
    keywords: ["돌비"]
```

---

## ⏰ 시간대별 자동 스케줄링 (`src/scheduler.py`)

| 시간대 | 체크 간격 | 알림 우선순위 | 의도 |
|---|---|---|---|
| 06:00 ~ 23:30 | 5분 | HIGH | 평시 |
| 23:30 ~ 00:00 | 2분 | HIGH | 오픈 직전 가속 |
| 00:00 ~ 00:30 | 1분 | **URGENT** | 오픈 추정 시점 — 즉각 반응 |
| 00:30 ~ 06:00 | 15분 | URGENT | 심야: 변화 있으면 강제 알람 |

매 요청마다 ±15초 랜덤 지터로 "사람 같은" 패턴 유지.
규칙 변경: `src/scheduler.py` 의 `DEFAULT_RULES`.

---

## ⚠️ 사용 시 주의사항

### ✅ 권장
- 본인 예매 목적으로만 사용
- 체크 간격은 5분 이상 유지
- 개인정보는 `.env` 또는 Secrets 에만
- 레포 공개 시 fork 패턴 안내 (본인이 직접 쓰는 게 아니라 다른 사람도 자기 정보로 쓰게)

### ⚠️ 주의
- 무주산골 측 요청 시 즉시 비공개 전환
- 사이트 약관 확인 의무는 사용자에게 있음
- 봇 탐지 회피 라이브러리(`playwright_stealth`)는 기본 비활성
- 무주산골은 "계정" 개념 없음 → 계정 잠금 X, 다만 IP 차단·CAPTCHA 추가 위험은 이론상 존재

### 📋 디스클레이머
이 코드는 학습 및 개인 사용 목적으로 공개됩니다. 사용으로 발생하는 모든 결과(예매 실패,
사이트 차단, 약관 위반 제재 등)에 대한 책임은 사용자 본인에게 있습니다.

---

## 📁 프로젝트 구조

```
ticket-notifier/
├── main.py                          # 엔트리포인트
├── requirements.txt
├── config.example.yaml              # 설정 템플릿 (heartbeat 포함)
├── .env.example                     # 환경변수 템플릿
├── .gitignore                       # .env, config.yaml, state 제외
├── .github/workflows/notify.yml     # 5분 cron + Force test alert 입력
├── docs/
│   ├── SETUP_GITHUB_ACTIONS.md
│   └── SETUP_PUSHOVER.md
├── src/
│   ├── config.py                    # YAML + .env 통합 로더
│   ├── state.py                     # 변경 감지 + 쿨다운
│   ├── scheduler.py                 # 시간대별 간격 + 지터
│   ├── heartbeat.py                 # ★ 매일 1회 살아있어요
│   ├── crawlers/
│   │   ├── mjff_auth_base.py        # dtidea.kr 인증 공통
│   │   ├── mjff_lodging.py          # 숙박패키지
│   │   ├── mjff_screening.py        # 실내상영
│   │   └── webpage.py               # 일반 웹페이지
│   └── notifiers/
│       ├── base.py                  # Priority enum
│       ├── ntfy.py                  # 메인 채널 (무료)
│       ├── pushover.py              # Critical Alerts (새벽용)
│       ├── telegram.py              # 선택
│       └── multi.py                 # 여러 채널 동시 발송
└── data/state/                      # 해시·세션·heartbeat 기록 (자동 생성)
```

---

## 📄 License

MIT — 개인 학습 목적의 사용을 권장합니다.

본 코드를 사용한 자동 예매·재판매·상업 이용은 [공연법 개정안(2026.02 시행)](https://www.law.go.kr/) 위반 소지가 있습니다.
