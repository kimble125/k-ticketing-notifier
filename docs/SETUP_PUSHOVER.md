# Pushover 설정 가이드 — 새벽 알림이 수면모드도 뚫고 울리게

## 왜 Pushover 인가?

iOS 의 방해 금지(Do Not Disturb) / 수면 집중 모드는 ntfy·텔레그램·문자
어떤 알림도 막아버립니다. Pushover 의 **Emergency Priority** 는 Apple
공식 Critical Alerts 권한을 받아둔 몇 안 되는 푸시 서비스라서, 새벽 3시
방해 금지 상태에서도 사이렌 소리를 울려서 사용자를 깨울 수 있어요.

비용: 앱 1회 결제 **$5** (iOS / Android 동일). 평생 사용.

---

## 설치 단계

### 1. 앱 설치 + 계정 생성

1. App Store 또는 Google Play 에서 **Pushover** 검색 → 설치 ($5)
2. 앱 실행 → 이메일/비밀번호로 계정 생성
3. 앱 안에서 디바이스 이름 입력 (예: "iPhone")

### 2. User Key 확보

1. https://pushover.net 에 같은 계정으로 로그인
2. 메인 화면 우측에 **Your User Key** 가 30글자 정도로 표시됨 → 복사
3. `.env` 의 `PUSHOVER_USER_KEY=` 뒤에 붙여넣기

### 3. Application Token 발급

1. https://pushover.net/apps/build 접속
2. Name: `ticket-notifier` (아무거나 가능)
3. Type: `Application`
4. Description: 빈칸 OK
5. Create Application 클릭
6. 생성된 페이지의 **API Token/Key** 복사
7. `.env` 의 `PUSHOVER_APP_TOKEN=` 뒤에 붙여넣기

### 4. 활성화

`config.yaml` 또는 `config.example.yaml` 에서:

```yaml
notifiers:
  pushover:
    enabled: true    # ← false 였던 것을 true 로
```

### 5. iOS: Critical Alerts 권한 허용

알림이 한 번이라도 오면 아이폰에 권한 요청 팝업이 뜹니다:
- "Pushover 가 Critical Alerts 를 보낼 수 있게 하시겠어요?" → **허용**
- 안 떴다면: 설정 → 알림 → Pushover → "긴급 경고(Critical Alerts)" 켜기

### 6. 테스트

```bash
python main.py --test-alert
```

알림이 도착하면 OK. 새벽 시간대(00:00 ~ 06:00)에 예매 가능이 감지되면
자동으로 사이렌 사운드 + 방해 금지 무력화로 알람이 울립니다.

---

## 작동 원리 (한 줄)

`src/scheduler.py` 가 현재 시각이 야간(00:00 ~ 06:00) 이면 알림 우선순위를
`URGENT (=2)` 로 자동 격상 → Pushover 가 retry/expire 헤더로 사이렌 반복
재생 → 사용자가 앱에서 "Acknowledge" 누를 때까지 계속 울림.

---

## 대안 (Pushover 가 부담스러우면)

| 옵션 | 장단점 |
|---|---|
| **Bark (iOS 무료)** | 오픈소스 + 무료지만 Critical Alerts 지원이 들쭉날쭉. 자체 서버 호스팅 가능. |
| **Twilio 전화** | 가장 확실. 통화 = DND 무시. 통화당 ~$0.014. 발신번호 등록 절차 필요. |
| **스마트 스피커** | Alexa/Google Home/Nest 에 webhook 으로 announcement. 24/7 ON 가정. |

이 중 가장 가성비 좋은 건 Pushover 입니다. ($5 → 평생)
