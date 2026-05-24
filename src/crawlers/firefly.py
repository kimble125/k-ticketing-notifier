"""
운문산 반딧불이 신비탐사 예약 — 네이버 로그인 + 캘린더 감시

흐름:
  1. https://www.firefly.or.kr/content/index.sgk?gubun=f0202&dname=F02 진입
  2. '예약하기' 클릭 → "로그인 후 사용 가능" 팝업 → 확인
  3. 로그인 페이지 → '네이버 로그인' 선택
  4. 네이버 ID/PW 자동 입력 (또는 저장된 쿠키 재사용)
  5. firefly 사이트로 복귀 → 2026.06 캘린더 표시
  6. 특정 날짜('06' 토요일)의 상태가 "예약마감" → "예약가능" 으로 바뀌면 알림

보안:
  - 네이버 ID/PW는 .env (또는 GitHub Secrets)에서만 로드
  - 로그인 성공 후 storage_state.json 으로 세션 저장 → 다음 실행 시 재사용
  - 본인 메인 네이버 계정과 분리된 부계정 권장

설정 예시:
  - name: "운문산 반딧불이 6/6"
    type: "firefly"
    enabled: true
    interval_minutes: 10
    settings:
      target_url: "https://www.firefly.or.kr/content/index.sgk?gubun=f0202&dname=F02"
      session_name: "firefly-naver"
      headless: true
      targets:
        - day_label: "06"               # 캘린더에 표시되는 숫자
          weekday_hint: "토"             # 같은 행/주에 토요일이 들어있어야 매칭
          sold_out_keyword: "예약마감"
          available_keyword: "예약가능"
"""

from __future__ import annotations

import logging
import os
import random
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class FireflyCrawler:
    def __init__(self, settings: dict):
        self.target_url = settings.get(
            "target_url",
            "https://www.firefly.or.kr/content/index.sgk?gubun=f0202&dname=F02",
        )
        self.headless = bool(settings.get("headless", True))
        self.viewport = settings.get("viewport", {"width": 1280, "height": 1024})
        self.user_agent = settings.get(
            "user_agent",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36",
        )
        self.targets: list[dict] = settings.get("targets", [])

        # 세션 저장 위치
        sess_dir = Path(settings.get("session_dir", "./data/state/cookies"))
        sess_dir.mkdir(parents=True, exist_ok=True)
        self._session_name = settings.get("session_name", "firefly-naver")
        self._state_path = sess_dir / f"{self._session_name}.json"

        # 네이버 자격 — 환경변수에서만
        self.naver_id = os.getenv("NAVER_ID", "").strip()
        self.naver_pw = os.getenv("NAVER_PW", "").strip()

        self.min_pause_ms = int(settings.get("min_pause_ms", 1500))
        self.max_pause_ms = int(settings.get("max_pause_ms", 3500))

    def _human_pause(self) -> None:
        time.sleep(random.randint(self.min_pause_ms, self.max_pause_ms) / 1000.0)

    def check(self) -> dict:
        html = self._fetch_calendar_html()
        if html is None:
            return {"items": [], "raw_data": "", "click_url": self.target_url}

        items, raw = self._parse(html)
        return {"items": items, "raw_data": raw, "click_url": self.target_url}

    # ── 메인 흐름 ────────────────────────────────────────

    def _fetch_calendar_html(self) -> Optional[str]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("playwright 미설치")
            return None

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )
            try:
                context = browser.new_context(
                    user_agent=self.user_agent,
                    viewport=self.viewport,
                    locale="ko-KR",
                    storage_state=str(self._state_path) if self._state_path.exists() else None,
                )
                page = context.new_page()

                # 다이얼로그(팝업) 자동 처리
                page.on("dialog", lambda d: d.accept())

                logger.info(f"[firefly] {self.target_url} 접속")
                page.goto(self.target_url, timeout=30000, wait_until="domcontentloaded")
                self._human_pause()

                # '예약하기' 클릭
                reserve_loc = page.locator("text='예약하기'")
                if reserve_loc.count() > 0:
                    reserve_loc.first.click()
                    self._human_pause()
                else:
                    # 영문 또는 다른 라벨 시도
                    for alt in ["예약 하기", "예약신청", "예약"]:
                        loc = page.locator(f"text='{alt}'")
                        if loc.count() > 0:
                            loc.first.click()
                            self._human_pause()
                            break

                # 로그인 페이지로 이동했는지 확인 (URL/페이지 텍스트 둘 다 체크)
                if self._is_login_page(page):
                    logger.info("[firefly] 로그인 필요 → 네이버 로그인 시도")
                    if not self._naver_login(page):
                        logger.error("[firefly] 네이버 로그인 실패")
                        return None

                # firefly 사이트로 복귀했는지 확인하고 캘린더가 있는 페이지로 이동
                if "firefly.or.kr" not in page.url:
                    page.goto(self.target_url, timeout=30000)
                    self._human_pause()

                # '예약하기' 한 번 더 (로그인 후 다시 캘린더 진입이 필요한 경우)
                reserve_loc = page.locator("text='예약하기'")
                if reserve_loc.count() > 0:
                    try:
                        reserve_loc.first.click()
                        page.wait_for_load_state("networkidle", timeout=15000)
                        self._human_pause()
                    except Exception:
                        pass

                html = page.content()
                try:
                    context.storage_state(path=str(self._state_path))
                except Exception:
                    pass
                return html

            except Exception as e:
                logger.exception(f"[firefly] 페이지 로드 실패: {e}")
                return None
            finally:
                browser.close()

    # ── 네이버 로그인 ────────────────────────────────────

    def _is_login_page(self, page) -> bool:
        url = (page.url or "").lower()
        if "login" in url or "auth" in url or "member" in url:
            return True
        try:
            body = page.locator("body").inner_text()
            return "로그인 후" in body or "로그인이 필요" in body
        except Exception:
            return False

    def _naver_login(self, page) -> bool:
        if not self.naver_id or not self.naver_pw:
            logger.error("[firefly] NAVER_ID / NAVER_PW 환경변수 미설정")
            return False

        from playwright.sync_api import TimeoutError as PWTimeout

        # '네이버 로그인' 버튼 클릭
        naver_btn_selectors = [
            "text='네이버 로그인'",
            "text='네이버'",
            "a[href*='naver']",
            "img[alt*='네이버']",
            ".btn-naver, .naver-login, [class*='naver']",
        ]
        clicked = False
        for sel in naver_btn_selectors:
            try:
                loc = page.locator(sel)
                if loc.count() > 0:
                    loc.first.click()
                    clicked = True
                    logger.info(f"[firefly] 네이버 버튼 클릭: {sel}")
                    self._human_pause()
                    break
            except Exception:
                continue

        if not clicked:
            logger.error("[firefly] 네이버 로그인 버튼 미발견")
            return False

        # 네이버 도메인으로 이동 대기
        try:
            page.wait_for_url("**/naver.com/**", timeout=15000)
        except PWTimeout:
            pass

        # 이미 로그인된 상태(쿠키 재사용) → 동의 화면이 뜸
        # 아직 미로그인 → ID/PW 입력 필요
        try:
            if page.locator("#id").count() > 0:
                page.fill("#id", self.naver_id)
                self._human_pause()
                page.fill("#pw", self.naver_pw)
                self._human_pause()
                # 로그인 버튼
                for sel in ["button.btn_login", "input.btn_login", "button[type='submit']"]:
                    if page.locator(sel).count() > 0:
                        page.locator(sel).first.click()
                        break
                page.wait_for_load_state("networkidle", timeout=20000)
                self._human_pause()
        except Exception as e:
            logger.warning(f"[firefly] 네이버 ID/PW 입력 단계 예외: {e}")

        # 2FA / 추가 인증 감지
        cur = page.url.lower()
        if "captcha" in cur or "deviceconfirm" in cur or "twostep" in cur:
            logger.error(
                "[firefly] 네이버 2단계 인증 / CAPTCHA 발생. "
                "한 번 headless=false 로 수동 로그인 후 쿠키 저장이 필요합니다."
            )
            return False

        # 동의 버튼 처리
        for sel in ["button.btn_agree", "#btnAgree", "a.btn_agree"]:
            try:
                if page.locator(sel).count() > 0:
                    page.locator(sel).first.click()
                    page.wait_for_load_state("networkidle", timeout=15000)
                    break
            except Exception:
                continue

        # firefly 도메인으로 돌아왔는가
        for _ in range(10):
            if "firefly.or.kr" in page.url:
                return True
            time.sleep(1)
        return "firefly.or.kr" in page.url

    # ── 캘린더 파싱 ──────────────────────────────────────

    def _parse(self, html: str) -> tuple[list[dict], str]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        items: list[dict] = []
        raw_parts: list[str] = []

        # 캘린더 셀 모두 수집 — td, li, div 중 day 가 보이는 것
        cells = soup.find_all(["td", "li", "div", "a"])

        for target in self.targets:
            day_label = str(target["day_label"]).strip()
            sold_out = target.get("sold_out_keyword", "예약마감")
            available_kw = target.get("available_keyword", "예약가능")

            status_text = "(미발견)"
            available = False

            # day_label 이 정확히 포함된 짧은 셀을 우선 선택
            for c in cells:
                t = c.get_text(" ", strip=True)
                if not t:
                    continue
                # 너무 긴 블록은 false positive 가능
                if len(t) > 200:
                    continue
                if day_label not in t:
                    continue

                if available_kw in t and sold_out not in t:
                    status_text = available_kw
                    available = True
                    break
                if sold_out in t:
                    status_text = sold_out
                    available = False
                    break

            items.append({
                "day_label": day_label,
                "status": status_text,
                "available": available,
            })
            raw_parts.append(f"day{day_label}::{status_text}")

        return items, "\n".join(raw_parts)

    def format_alert(self, items: list[dict]) -> Optional[str]:
        avail = [i for i in items if i["available"]]
        if not avail:
            return None
        lines = ["🪲 운문산 반딧불이 신비탐사 예약 가능!"]
        for it in avail:
            lines.append(f"  • {it['day_label']}일 — {it['status']}")
        lines.append("\n👉 firefly.or.kr 으로 즉시!")
        return "\n".join(lines)
