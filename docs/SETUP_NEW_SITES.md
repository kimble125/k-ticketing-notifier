# v2 신규 사이트 추가 가이드 (초보자용)

이 가이드는 **컴퓨터 기본 조작은 되지만 Python·터미널은 처음**인 분도 따라 할 수 있게 분 단위로 분해했어요. 천천히 한 줄씩 읽고 그대로 따라하세요.

🎯 **이 문서로 할 일**: v2에서 새로 추가된 3개 사이트(등나무운동장, 숙박 일정선택, 운문산 반딧불이)를 본인 GitHub에 셋업.

> 📌 **시작 전 확인**: 본인 GitHub 레포 `ticket-notifier`에 v2 zip 파일을 압축 풀어서 commit & push 이미 완료된 상태여야 합니다.

> ⚠️ **이전 버전에서 CGV watcher 제거됨**: 이전 v2 zip을 이미 풀었다면, `src/crawlers/cgv.py` 파일이 본인 `ticket-notifier/src/crawlers/` 폴더에 남아있을 수 있어요. **수동으로 삭제하세요**. (자세한 이유는 문서 마지막 "CGV 제거 사유" 참고)

---

## 0️⃣ 모든 사이트에 공통 — GitHub Secrets 등록 방법

새 사이트 중 운문산 반딧불이는 **네이버 시크릿 2개를 추가로** 등록해야 해요. 처음이신 분도 따라할 수 있게 클릭 단위로 설명합니다.

### 단계 1 — 본인 레포 페이지 열기

1. PC 브라우저(Chrome 권장)에서 https://github.com 접속 + 로그인
2. 화면 오른쪽 위 본인 프로필 아이콘 클릭 → **Your repositories** 클릭
3. 목록에서 **ticket-notifier** 클릭

### 단계 2 — Settings 메뉴로 이동

1. 레포 페이지 상단의 가로 메뉴를 보세요. 왼쪽부터 `<> Code`, `Issues`, `Pull requests`, ..., **`⚙️ Settings`**
2. **⚙️ Settings** 클릭 (가장 오른쪽 즈음에 있음)

> ⚠️ **`⚙️ Settings`가 안 보인다면**: 본인 레포의 소유자(owner)가 아니라 fork만 한 경우 권한이 없을 수 있어요. 본인 계정 이름이 레포 경로(`본인아이디/ticket-notifier`) 앞쪽에 들어있는지 확인하세요.

### 단계 3 — Secrets and variables 펼치기

1. Settings 페이지의 **왼쪽 사이드바**를 스크롤해서 내려가세요
2. `Security` 라는 회색 헤더 아래에 **`Secrets and variables`** 항목이 있어요 (▶ 화살표 모양)
3. 클릭하면 펼쳐지면서 3개 하위 항목이 나옵니다:
   - **Actions** ← 이걸 클릭
   - Codespaces
   - Dependabot

### 단계 4 — 첫 번째 Secret 추가 (NAVER_ID)

1. 화면 오른쪽 위 초록색 **`New repository secret`** 버튼 클릭
2. 새로운 페이지로 이동하면 두 칸이 보입니다:
   - **Name** 칸 (한 줄짜리)
   - **Secret** 칸 (여러 줄짜리)
3. **Name** 칸에 정확히 입력: `NAVER_ID` ← 대문자, 언더바, 띄어쓰기 없이
4. **Secret** 칸에 본인 네이버 ID 입력 (예: `naver_xxxx...`). 비밀번호 아님 ID만.
5. 화면 아래 초록색 **`Add secret`** 클릭
6. 목록 페이지로 돌아가면 `NAVER_ID • Updated now` 같은 줄이 보여야 정상

### 단계 5 — 두 번째 Secret 추가 (NAVER_PW)

1. 다시 **`New repository secret`** 클릭
2. **Name**: `NAVER_PW`
3. **Secret**: 본인 네이버 비밀번호 입력
4. **`Add secret`** 클릭
5. 목록에 `NAVER_ID`, `NAVER_PW` 두 개가 나란히 보이면 끝

> 💡 **저장 후 다시 볼 수 없어요**: GitHub은 보안 때문에 한 번 저장된 Secret 값을 다시는 보여주지 않습니다. 잊으면 새로 만들어야 함. 그래서 본인 PC에도 `.env` 파일로 같이 저장해두는 게 좋아요.

---

## 1️⃣ 무주등나무운동장 1일 입장권 (가장 쉬움)

### 별도 시크릿 추가 필요?
❌ 없음. 기존 `MJFF_NAME`, `MJFF_PHONE`, `MJFF_PASS` 그대로 사용.

### 추가 설정 필요?
❌ 없음. v2 zip의 `config.example.yaml` 안에 이미 watcher가 들어있어요. 그대로 동작.

### 다른 날짜를 감시하고 싶다면

`config.example.yaml` 파일을 (메모장이나 VSCode 같은 텍스트 에디터로) 열고 `무주등나무운동장 6/6` 부분을 찾으세요:

```yaml
targets:
  - date_label: "6. 6.(토)"     # ← 이 줄을 본인이 원하는 날짜로
    sold_out_keyword: "온라인매진"
    available_keyword: "예매하기"
```

- 6/7도 감시하려면 그 아래에 `- date_label: "6. 7.(일)"` 같은 줄을 추가 (들여쓰기 똑같이 맞춰주세요)
- 수정 후 GitHub Desktop에서 commit & push

---

## 2️⃣ 무주산골 숙박 — 일정 선택 흐름 (자동화됨)

### 별도 시크릿 추가 필요?
❌ 없음. 기존 MJFF 시크릿 재사용.

### 어떤 흐름인가요?
자동으로 다음을 합니다:
1. 숙박 페이지 진입 → 인증
2. '예매하기' 버튼 클릭
3. 일정 선택 화면에서 **'6. 6.(토)' 자동 클릭** ← v2 신기능
4. 가족호텔(골드) 행에서 상태 확인
5. "예약 가능"으로 바뀌면 알림

### 다른 호텔도 추가하려면

`config.example.yaml`의 `무주산골 숙박 6/6 가족호텔(골드)` 부분에서:

```yaml
targets:
  - name: "가족호텔(골드)"
    available_keyword: "예약 가능"
    status_cell_index: 4
  # ← 이 아래에 추가
  - name: "가족호텔(실버)"      # 정확한 객실 이름 (사이트 화면 그대로)
    available_keyword: "예약 가능"
    status_cell_index: 4
```

---

## 3️⃣ 운문산 반딧불이 (가장 까다로움 — 네이버 로그인)

이 사이트는 네이버 로그인이 필요해서, 네이버의 **2단계 인증(2FA)** 이 GitHub Actions 환경에서 막을 수 있어요. 3가지 옵션 중 본인 상황에 맞는 것 하나만 따라하세요.

### 🎯 어떤 옵션을 고를지 (요약)

| 옵션 | 난이도 | 보안 | 추천 |
|---|---|---|---|
| **A) 네이버 부계정 만들기** | ★★ | ★★★★★ | ⭐ 가장 권장 |
| **B) 기존 계정의 2단계 인증 끄기** | ★ | ★★ | 메인 계정 X |
| **C) 본인 PC에서 1회 로그인 후 쿠키 commit** | ★★★★ | ★★★★ | Python 익숙한 분만 |

### 옵션 A — 네이버 부계정 만들기 ⭐ 권장

**왜 추천**: 메인 계정과 완전히 분리. 노출되어도 메인 계정 안전. firefly 사이트는 처음 가입만 본인 인증 필요할 뿐 누가 예약하든 상관없음.

**단계**:
1. 평소 쓰는 네이버 계정을 **로그아웃** (오른쪽 위 프로필 → 로그아웃)
2. https://nid.naver.com/user2/V2Join.nhn 에서 새 계정 생성
3. 새 계정으로 https://www.firefly.or.kr 에 한 번 로그인해서 회원가입 완료 (예약하기 한 번 눌러보면 회원가입 유도됨)
4. 새 계정의 **2단계 인증을 끄기**:
   - https://nid.naver.com/user2/help/myInfo 접속
   - "2단계 인증" 항목 → "사용 안 함" 으로 설정
   - (부계정이라 메인 계정의 보안에 영향 없음)
5. 이 부계정의 ID/PW를 GitHub Secrets에 등록 (위 0️⃣ 단계 참고)
6. 끝. 본인 PC에서 추가 작업 없음.

### 옵션 B — 기존 계정의 2단계 인증 끄기

⚠️ **주의**: 본인 메인 네이버 계정에 2FA 끄는 건 비추. 만약 firefly 전용 계정으로 이미 분리했고, 그 계정의 2FA만 끄는 거라면 OK.

**단계**:
1. https://nid.naver.com/user2/help/myInfo 접속 + 본인 계정으로 로그인
2. "2단계 인증" 또는 "OTP 인증" 항목 찾기
3. "사용 안 함" 으로 변경
4. firefly 계정 ID/PW를 GitHub Secrets에 등록

### 옵션 C — 본인 PC에서 1회 수동 로그인 → 쿠키 commit

**언제 필요한가**: 2FA를 켜 두고 싶을 때. 한 번만 본인이 직접 로그인하면, 그 쿠키(=로그인 토큰)를 GitHub에 올려서 그 후엔 자동 로그인 없이 쿠키 재사용으로 동작.

**필요한 것**:
- Mac/Windows PC (호연님은 Mac)
- Python 3.11 이상 (없으면 설치 필요)
- Git (이미 GitHub Desktop으로 설치돼 있음)

#### Step C-1: Python 설치 (이미 있으면 건너뛰기)

1. Mac: 터미널 열고 `python3 --version` 실행 → `3.11.x` 같은 게 나오면 OK
2. 없거나 3.10 이하면: https://www.python.org/downloads/ 에서 최신 Python 다운로드 + 설치 (그냥 Next/Continue 계속 누르면 됨)

#### Step C-2: GitHub Desktop으로 본인 레포 클론 (이미 했으면 건너뛰기)

1. GitHub Desktop 열기
2. File → Clone Repository → 본인 ticket-notifier 선택 → Clone

#### Step C-3: 본인 PC에 .env 파일 만들기

1. Finder에서 ticket-notifier 폴더 열기
2. 그 안에 `.env.example` 파일이 있을 거예요. 이걸 같은 폴더에 **복사 → 이름을 `.env` 로 변경**
3. `.env` 파일을 텍스트 에디터(메모장/VSCode/Sublime 등)로 열기
4. `NAVER_ID=` 뒤에 본인 네이버 ID 입력
5. `NAVER_PW=` 뒤에 본인 네이버 비밀번호 입력
6. 저장

> 💡 `.env`는 `.gitignore`가 차단해서 GitHub에 절대 안 올라감. 본인 PC에만 남음.

#### Step C-4: 의존성 설치

1. **터미널** 앱 열기 (Spotlight: Command+Space → "터미널" 입력 → 엔터)
2. 다음 명령 한 줄씩 입력 (Cmd+C로 복사해서 Cmd+V로 붙여넣기 → 엔터):

```bash
cd "/Users/kimble/Library/CloudStorage/GoogleDrive-hoykim125@gmail.com/내 드라이브/Git/ticket-notifier"
```
(폴더 경로는 호연님 실제 폴더 위치)

```bash
pip3 install -r requirements.txt
```
(2~3분 걸림. "Successfully installed..." 메시지 나오면 OK)

```bash
python3 -m playwright install chromium
```
(브라우저 설치. 5분 정도. "chromium downloaded" 같은 메시지 나오면 OK)

#### Step C-5: firefly watcher 임시로 headless 끄기

1. 텍스트 에디터로 `config.example.yaml` 열기
2. "운문산 반딧불이 6/6" 부분 찾아서:
   ```yaml
   settings:
     target_url: "https://www.firefly.or.kr/content/index.sgk?gubun=f0202&dname=F02"
     headless: true        # ← 이 줄을 false 로 변경
     session_name: "firefly-naver"
   ```
3. `headless: false` 로 바꾸고 저장

#### Step C-6: 수동 실행 + 네이버 로그인

1. 터미널에 다시 입력:
```bash
python3 main.py --check
```

2. 잠시 후 **자동으로 브라우저 창이 열립니다** (Chromium)
3. 브라우저가 firefly.or.kr 페이지를 거쳐 네이버 로그인 화면을 띄울 거예요
4. **본인이 직접** ID/PW 입력하고 로그인 (필요시 2FA도 진행)
5. firefly.or.kr 로 돌아오면 자동으로 진행됨
6. 터미널에 "체크 완료" 같은 메시지 나오면 성공
7. 브라우저는 자동으로 닫힘

#### Step C-7: 생성된 쿠키 파일 확인

1. Finder에서 ticket-notifier → data → state → cookies 폴더 열기
2. `firefly-naver.json` 파일이 새로 생겼는지 확인 (있으면 성공)

#### Step C-8: 쿠키를 GitHub에 commit

1. `config.example.yaml` 의 `headless: false` → **`headless: true` 로 다시 변경** (잊지 마세요)
2. GitHub Desktop 열기 → ticket-notifier 선택
3. 왼쪽에 변경된 파일 목록에 `data/state/cookies/firefly-naver.json` 이 보여야 함
4. 아래 Summary 칸에 `add firefly naver cookie` 같이 입력
5. **Commit to main** 버튼 클릭
6. 오른쪽 위 **Push origin** 클릭
7. 끝

이제 GitHub Actions가 이 쿠키를 재사용해서 자동 로그인 → 캘린더 감시.

> ⚠️ **쿠키 만료**: 보통 1~3개월 후 만료됨. 알림이 안 오기 시작하면 위 단계를 다시 한 번 반복하세요.

---

## ❌ CGV — 제거됨 (자동화 불가능)

### 왜 제거했나요?

CGV는 2024년경 React/Next.js 기반 SPA(Single Page Application)로 리뉴얼하면서, **URL이 화면 상태와 무관**해졌어요. 예를 들어:

- 영화 검색 → 클릭 → 극장 선택 → 날짜 선택 → 시간표 페이지에 가도 주소창엔 항상 `https://cgv.co.kr/cnm/movieBook/movie` 같은 일반 URL만 표시
- 즉 "직접 URL 진입"이 불가능하고, 매번 검색→클릭 자동화를 해야 하는데 단계가 많아 깨지기 쉬움
- CGV 이용약관 제11조 자동화 금지 + Cloudflare 봇 탐지 → 차단 위험까지 큼

→ 결론적으로 **안정적으로 자동화가 불가능**하다고 판단해서 v2에서 완전 제거.

### 대안 — CGV 빈자리 모니터링이 정말 필요하다면

1. **CGV 앱 자체 알림**
   - CGV 앱 → 영화 검색 → 상세 페이지 → "관심 영화" 또는 "알림 신청"
   - 일부 인기 영화/GV는 매진 풀림 알림 공식 지원
   - 이게 가장 합법적이고 안전한 방법

2. **GV 주최측에 문의**
   - 너바나 더 밴드 같은 GV는 영화 배급사·제작사가 추가 회차를 열거나 별도 안내 가능
   - 영화사 인스타그램·트위터·뉴스레터 구독 권장

3. **수동 새로고침 효율화** (자동화 X)
   - Mac 키보드 단축키: 페이지 펼친 채 Cmd+R
   - 알람 앱으로 매 5분 알림 설정 → 수동 새로고침
   - 본인이 직접 새로고침하는 거라 약관·기술적 문제 없음

### 이미 첫 v2 zip을 풀어서 cgv.py가 있다면

`ticket-notifier/src/crawlers/cgv.py` 파일을 수동 삭제하세요:
1. Finder에서 ticket-notifier → src → crawlers 폴더 열기
2. `cgv.py` 파일을 휴지통으로 드래그
3. GitHub Desktop에서 변경사항 확인 (cgv.py 가 빨간색으로 deleted 표시)
4. commit & push

---

## 🔍 트러블슈팅 — 자주 묻는 질문

### Q. firefly에서 "NAVER_ID 환경변수 미설정" 에러
**A.** GitHub Secrets 등록을 안 했거나 이름 오타. `NAVER_ID`, `NAVER_PW` (대문자, 언더바)가 정확한지 확인.

### Q. firefly에서 "2단계 인증 / CAPTCHA 발생" 에러
**A.** 위의 옵션 A(부계정 만들기) 또는 옵션 C(쿠키 export) 중 하나 실행.

### Q. 알림이 너무 자주 와요
**A.** `config.example.yaml`의 해당 watcher의 `cooldown_minutes` 를 늘리세요 (예: 15 → 60). 한 번 알림 보낸 뒤 60분 동안 재발송 안 함.

### Q. GitHub Actions 로그를 어디서 볼 수 있나요?
**A.** 레포 페이지 → 상단 메뉴의 **Actions** 탭 → 최근 실행 목록 → 시간 클릭 → check 작업 클릭 → 단계별 로그 펼쳐서 확인.

### Q. 잠시 모든 알림을 끄고 싶어요
**A.** Actions 탭 → 왼쪽 사이드바 `ticket-notifier` 클릭 → 오른쪽 위 **`···`** → **Disable workflow**. 다시 켤 때는 같은 자리에 **Enable workflow** 가 보임.

### Q. v2 zip을 어떻게 압축 해제하나요?
**A.**
1. Finder에서 zip 파일 더블클릭 → 자동으로 폴더 생성
2. 그 폴더 안의 모든 파일/폴더를 선택 (Cmd+A)
3. 본인 `ticket-notifier` 폴더로 드래그
4. "교체하시겠습니까?" 라고 물으면 **교체** 클릭
5. GitHub Desktop에서 변경사항 확인 후 commit & push

---

## 📋 전체 시크릿 체크리스트 (v2 기준)

GitHub 레포의 Settings → Secrets and variables → Actions 에 다음이 있어야 함:

| Secret | 필수? | 어디서 얻나 |
|---|---|---|
| `MJFF_NAME` | ✅ | 본인 실명 |
| `MJFF_PHONE` | ✅ | 본인 휴대폰 (하이픈 없이) |
| `MJFF_PASS` | ✅ | 무주산골 예매자 비밀번호 |
| `NTFY_TOPIC` | ✅ | 본인이 정한 ntfy 토픽 이름 |
| `NTFY_SERVER` | ⚪ | 비워두면 `https://ntfy.sh` 기본 |
| `NAVER_ID` | firefly 사용 시 ✅ | 네이버 ID |
| `NAVER_PW` | firefly 사용 시 ✅ | 네이버 비밀번호 |
| `PUSHOVER_USER_KEY` | ⚪ | Pushover 가이드 참고 |
| `PUSHOVER_APP_TOKEN` | ⚪ | Pushover 가이드 참고 |

위 체크리스트의 ✅ 항목이 다 들어가 있고, fork 한 레포의 Actions 가 활성화돼 있으면 끝.
