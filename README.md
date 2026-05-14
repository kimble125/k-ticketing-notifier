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

## 🎯 어떤 문제를 해결하나요?

무주산골영화제 같은 인기 영화제는 **숙박패키지**와 **실내상영 티켓**이 오픈
즉시 매진됩니다. 그런데 정확한 오픈 시각이 불확실하거나 자정에 오픈되는
경우가 많아서, 사용자가 직접 5분마다 새로고침해야 하는 답답한 상황이 생겨요.

이 봇은:
- **5분마다 자동으로 사이트를 체크** (인기 시간엔 1분 간격으로 가속)
- 상태가 "온라인매진" → "예매하기" 로 바뀌면 **즉시 알림**
- **새벽 3시라도 수면모드 무력화** (Pushover Emergency Priority)
- GitHub Actions 무료로 **24/7 가동** (본인 컴퓨터 꺼져 있어도 OK)
- 개인정보는 `.env` 로 분리 → **GitHub 공개해도 안전**

---

## ⚡ 한눈에 보는 구조

```
┌────────────────────────────────────────────────────────┐
│  GitHub Actions (5분 cron)                              │
│    │                                                    │
│    └─► python main.py --check                           │
│           │                                             │
│           ├─► scheduler.py (지금 돌릴 시간인가? + 지터) │
│           │                                             │
│           ├─► crawlers/                                 │
│           │     ├─ mjff_lodging.py    (숙박패키지)     │
│           │     ├─ mjff_screening.py  (실내상영)       │
│           │     └─ webpage.py         (일반 공지)      │
│           │                                             │
│           ├─► state.py (변경 감지 + 쿨다운)            │
│           │                                             │
│           └─► notifiers/                                │
│                 ├─ ntfy.py     (메인, 무료)            │
│                 ├─ pushover.py (새벽 수면모드 무력화)  │
│                 └─ telegram.py (선택)                   │
└────────────────────────────────────────────────────────┘
```

---

## 🚀 5분 만에 시작하기 (초보자용)

> 터미널 안 써본 분도 따라할 수 있게 작성. 더 자세한 가이드는 [docs/](docs/) 참고.

### 1단계 — 알림 받을 채널 준비 (ntfy, 가입 X)

1. 휴대폰에 **ntfy** 앱 설치 (App Store / Play Store)
2. 앱 실행 → "+" 버튼 → 토픽 이름 입력
   - 예: `mjff-7a3f9b2c-watcher-2026` ← 짐작 불가능한 랜덤 조합 권장
   - 이 토픽 이름이 곧 **본인 전용 알림 채널** 입니다
3. 토픽 이름을 기억해두세요 (다음 단계에 입력)

### 2단계 — 레포 fork (GitHub 가입 필요)

1. https://github.com/kimble125/ticket-notifier (이 레포) 페이지 우상단 **Fork** 클릭
2. 본인 GitHub 계정 아래에 사본이 생김

### 3단계 — Secrets 등록 (개인정보를 안전하게 GitHub 에 저장)

본인 fork 레포 → **Settings** → **Secrets and variables** → **Actions** →
**New repository secret** 으로 다음 5개를 등록:

| Name | Value | 비고 |
|---|---|---|
| `MJFF_NAME` | 본인 실명 (예매자 정보) | |
| `MJFF_PHONE` | 휴대폰 (- 없이) | |
| `MJFF_PASS` | 비밀번호 (보통 생년월일) | |
| `NTFY_TOPIC` | 1단계의 토픽 이름 | |
| `NTFY_SERVER` | `https://ntfy.sh` | 생략 가능 |

상세: [docs/SETUP_GITHUB_ACTIONS.md](docs/SETUP_GITHUB_ACTIONS.md)

### 4단계 — Actions 활성화

레포 페이지 → **Actions** 탭 → "I understand..." 클릭 → 활성화 완료.

5분 안에 첫 체크가 자동 실행됩니다. 본인 ntfy 앱에 알림이 오면 정상 작동.

### 5단계 (선택) — 새벽 알람용 Pushover

자정에 예매가 열리면 ntfy 알림이 iOS 방해 금지 모드에 막힐 수 있어요.
**Pushover** 를 추가하면 사이렌으로 강제 기상시켜줍니다.

설정: [docs/SETUP_PUSHOVER.md](docs/SETUP_PUSHOVER.md) (앱 $5 결제, 약 5분 소요)

---

## 🔧 본인 환경에 맞게 수정하기

### 모니터링 대상 변경

`config.example.yaml` 의 `watchers:` 섹션을 수정. 예시:

```yaml
- name: "무주산골 실내상영 6/6"
  type: "mjff_screening"
  enabled: true
  interval_minutes: 5
  settings:
    date: "2026-06-06"
    targets:
      - movie: "별과 모래"
        time: "10:30"
      # 원하는 영화 추가
```

### 다른 영화제 / 다른 사이트에 응용

이 봇은 **무주산골 + dtidea.kr 솔루션 전용**으로 설계됐지만,
일반 웹페이지 변경 감지에는 `type: "webpage"` 워처를 사용 가능:

```yaml
- name: "메가박스 코엑스 돌비"
  type: "webpage"
  settings:
    url: "https://www.megabox.co.kr/theater/time"
    selector: ".theater-schedule"
    encoding: "utf-8"
    keywords: ["돌비"]
```

dtidea 가 아닌 다른 인증 사이트(인터파크티켓·멜론티켓 등)는
`src/crawlers/mjff_auth_base.py` 를 본떠서 `interpark_auth_base.py` 같은
새 크롤러를 추가하면 됨. 핵심 로직(`fetch_html`)만 갈아끼우면 나머지는
재사용 가능.

---

## ⏰ 시간대별 자동 스케줄링 (`src/scheduler.py`)

| 시간대 | 체크 간격 | 알림 우선순위 | 의도 |
|---|---|---|---|
| 06:00 ~ 23:30 | 5분 | HIGH | 평시: 봇 의심 받지 않게 일반 사용자 수준 |
| 23:30 ~ 00:00 | 2분 | HIGH | 오픈 직전 가속 |
| 00:00 ~ 00:30 | 1분 | **URGENT** | 오픈 추정 시점 — 즉각 반응 |
| 00:30 ~ 06:00 | 15분 | URGENT | 심야: 네트워크/전력 절약, 단 변화 있으면 강제 알람 |

매 요청마다 ±15초 랜덤 지터가 들어가서 "사람 같은" 패턴이 유지됩니다.
규칙을 바꾸려면 `src/scheduler.py` 의 `DEFAULT_RULES` 수정.

---

## ⚠️ 사용 시 주의사항 / 권장사항

### ✅ 권장

- **본인 예매 목적으로만 사용하세요** — 자동 예매·재판매 X
- **체크 간격은 5분 이상 유지** — 사이트 부담 + 봇 판정 회피
- **개인정보는 절대 코드에 박지 마세요** — `.env` 또는 GitHub Secrets 사용
- **레포 공개 시 fork 패턴 안내**: README 의 "5분 만에 시작하기" 처럼
  다른 사람이 본인 정보로 채우는 방식을 권장

### ⚠️ 주의

- **무주산골 측 요청 시 즉시 코드를 비공개 전환** 합니다 (분쟁 시 정상참작 요소)
- **사이트 약관 확인 의무는 사용자에게 있습니다** — 자동화된 접근을 명시적으로
  금지하는 약관이 추가되면 사용 중단
- **봇 탐지 회피 라이브러리(`playwright_stealth`) 는 기본 비활성** —
  탐지 회피 = 자동화 의도 은폐로 해석될 수 있어서 약관 회색지대
- **무주산골은 "계정" 개념이 없어 계정 잠금은 발생하지 않지만** IP 차단 / CAPTCHA
  추가 / 예매자 정보 블랙리스트 같은 위험은 이론상 존재. 5분 주기를 지키면 거의 없음.

### 📋 법적/윤리적 디스클레이머

이 코드는 학습 및 개인 사용 목적으로 공개됩니다. 본 코드를 사용함으로써
발생하는 모든 결과(예매 실패, 사이트 차단, 약관 위반에 따른 제재 등)에 대한
책임은 사용자 본인에게 있습니다.

본 코드는 무주산골영화제 운영사와 무관하며, 코드의 유효성·정확성은 사이트
구조 변경에 따라 언제든 깨질 수 있습니다.

---

## 🧪 로컬에서 테스트하기 (선택)

GitHub Actions 만 쓸 거면 이 섹션은 건너뛰어도 됨. 본인 컴퓨터에서 한 번
시험해보고 싶다면:

```bash
# 1. 클론
git clone https://github.com/본인아이디/ticket-notifier.git
cd ticket-notifier

# 2. 가상환경 + 의존성
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium

# 3. 비밀값 설정
cp .env.example .env
# .env 를 열어 본인 정보 입력

# 4. 알림 채널만 테스트
python main.py --test-alert

# 5. 실제 사이트 체크 (1회)
python main.py --check
```

---

## 📁 프로젝트 구조

```
ticket-notifier/
├── main.py                          # 엔트리포인트 (1회 체크 모드)
├── requirements.txt
├── config.example.yaml              # 설정 템플릿
├── .env.example                     # 환경변수 템플릿
├── .gitignore                       # .env, config.yaml, state/*.json 제외
├── .github/workflows/notify.yml     # 5분 cron + secrets 주입
├── docs/
│   ├── SETUP_GITHUB_ACTIONS.md      # 초보자용 배포 가이드
│   └── SETUP_PUSHOVER.md            # 새벽 알람 설정
├── src/
│   ├── config.py                    # YAML + .env 통합 로더
│   ├── state.py                     # 변경 감지 + 쿨다운
│   ├── scheduler.py                 # 시간대별 간격 + 지터
│   ├── crawlers/
│   │   ├── __init__.py              # type → 크롤러 라우팅
│   │   ├── mjff_auth_base.py        # dtidea.kr 인증 공통
│   │   ├── mjff_lodging.py          # 숙박패키지
│   │   ├── mjff_screening.py        # 실내상영
│   │   └── webpage.py               # 일반 웹페이지
│   └── notifiers/
│       ├── __init__.py
│       ├── base.py                  # Notifier ABC + Priority enum
│       ├── ntfy.py                  # 메인 채널 (무료)
│       ├── pushover.py              # Critical Alerts (새벽용)
│       ├── telegram.py              # 선택
│       └── multi.py                 # 여러 채널 동시 발송
└── data/state/                      # 해시·세션·last_check (자동 생성)
```

---

## 🤝 비슷한 프로젝트들

| 프로젝트 | 차이 |
|---|---|
| [Sumaid/Movie-Ticket-Notifier](https://github.com/Sumaid/Movie-Ticket-Notifier) | BookMyShow(인도) 전용. 한국 사이트 미지원 |
| [abinpaul1/BookMyShow-ticket-notifier-telegram-bot](https://github.com/abinpaul1/BookMyShow-ticket-notifier-telegram-bot) | 텔레그램 전용. 새벽 critical alerts X |
| [kimble125/movie-club-ticket-notifier](https://github.com/kimble125/movie-club-ticket-notifier) | 본 프로젝트의 기반. CGV 특화. 인증 페이지 미지원 |

→ 한국 영화제/공연 인증 페이지 + 새벽 수면모드 무력화까지 한 번에 다루는
   레포는 알려진 한 이 프로젝트가 처음입니다.

---

## 📄 License

MIT — 개인 학습 목적의 사용을 권장합니다.

본 코드를 사용한 자동 예매·재판매·상업 이용은 [공연법 개정안(2026.02 시행)](https://www.law.go.kr/) 위반 소지가 있습니다.
