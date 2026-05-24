"""
무주산골영화제 — 숙박패키지 예매 가능 감지

지원 흐름:
  (A) target_url 직접 진입 → 호텔 행에서 상태 셀 확인 (단순 모드)
  (B) target_url → '예매하기' 버튼 클릭 → 일정 선택 화면 → 특정 날짜 클릭
      → 호텔 행에서 상태 셀 확인 (calendar 모드)

설정 예시 (calendar 모드 — 사용자가 요청한 6/6 가족호텔 골드):
  - name: "무주산골 숙박 6/6 가족호텔(골드)"
    type: "mjff_lodging"
    enabled: true
    interval_minutes: 5
    settings:
      target_url: "https://ticket.dtidea.kr/mjff/html/03/04.php"
      booking_button_text: "예매하기"
      select_date: "6. 6.(토)"      # ← 이게 있으면 calendar 모드
      session_name: "mjff-lodging-0606"
      targets:
        - name: "가족호텔(골드)"
          available_keyword: "예약 가능"   # 이 키워드로 바뀌면 알림
          unavailable_keyword: "예약 불가"  # 현재 상태 (참고용)
          status_cell_index: 4

단순 모드 예시:
      # select_date 생략 → 첫 페이지에서 바로 호텔 행 검색
"""

from __future__ import annotations

import logging
from typing import Optional

from .mjff_auth_base import MJFFAuthBase, AUTH_PATH_HINT

logger = logging.getLogger(__name__)


class MJFFLodgingCrawler(MJFFAuthBase):
    def __init__(self, settings: dict):
        super().__init__(settings)
        self.target_url = settings.get(
            "target_url", "https://ticket.dtidea.kr/mjff/html/03/04.php"
        )
        self.booking_button_text = settings.get("booking_button_text", "예매하기")
        self.select_date = settings.get("select_date", "").strip()
        self.targets: list[dict] = settings.get("targets", [])
        self._session_name = settings.get("session_name", "mjff-lodging")

    def check(self) -> dict:
        if self.select_date:
            html = self._fetch_calendar_mode()
        else:
            html = self.fetch_html(self.target_url)
            if not html or not self._find_any_target(html):
                # 버튼 클릭 후 다시 시도
                html = self._fetch_after_button_click()

        if html is None:
            return {"items": [], "raw_data": "", "click_url": self.target_url}

        items, raw = self._parse_lodging_html(html)
        return {"items": items, "raw_data": raw, "click_url": self.target_url}

    # ── Calendar 모드 ───────────────────────────────────

    def _fetch_calendar_mode(self) -> Optional[str]:
        """
        target_url 진입 → 예매하기 클릭 → 일정 선택 화면 → select_date 클릭 → HTML 반환
        """
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
                page.goto(self.target_url, timeout=30000, wait_until="domcontentloaded")
                self._human_pause()

                # 인증 처리
                if AUTH_PATH_HINT in page.url:
                    if not self._fill_auth_form(page):
                        return None
                    if AUTH_PATH_HINT in page.url:
                        page.goto(self.target_url, timeout=30000)
                        self._human_pause()

                # 예매하기 버튼
                btn = page.locator(f"text='{self.booking_button_text}'")
                if btn.count() > 0:
                    btn.first.click()
                    page.wait_for_load_state("networkidle", timeout=15000)
                    self._human_pause()

                # 일정 선택 — 날짜 텍스트 클릭
                date_loc = page.locator(f"text={self.select_date!r}")
                if date_loc.count() == 0:
                    # 정확히 매칭 안 되면 partial match
                    # 예: "6. 6.(토)" 가 "6.6.(토)" 또는 "06.06.(토)" 식일 수 있음
                    for variant in [
                        self.select_date.replace(" ", ""),
                        self.select_date.replace(".", ". "),
                        self.select_date.split("(")[0].strip(),
                    ]:
                        date_loc = page.locator(f"text={variant!r}")
                        if date_loc.count() > 0:
                            break

                if date_loc.count() > 0:
                    date_loc.first.click()
                    page.wait_for_load_state("networkidle", timeout=15000)
                    self._human_pause()
                else:
                    logger.warning(f"[lodging] '{self.select_date}' 날짜를 찾을 수 없음")

                html = page.content()
                try:
                    context.storage_state(path=str(self._state_path))
                except Exception:
                    pass
                return html

            except Exception as e:
                logger.exception(f"[lodging calendar] 실패: {e}")
                return None
            finally:
                browser.close()

    # ── 단순 모드 (기존) ────────────────────────────────

    def _find_any_target(self, html: str) -> bool:
        return any(t["name"] in html for t in self.targets)

    def _fetch_after_button_click(self) -> Optional[str]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
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
                page.goto(self.target_url, timeout=30000)
                self._human_pause()

                if AUTH_PATH_HINT in page.url:
                    if not self._fill_auth_form(page):
                        return None
                    if AUTH_PATH_HINT in page.url:
                        page.goto(self.target_url, timeout=30000)
                        self._human_pause()

                btn = page.locator(f"text='{self.booking_button_text}'")
                if btn.count() > 0:
                    btn.first.click()
                    page.wait_for_load_state("networkidle", timeout=15000)
                    self._human_pause()

                html = page.content()
                try:
                    context.storage_state(path=str(self._state_path))
                except Exception:
                    pass
                return html
            except Exception as e:
                logger.exception(f"[lodging] 버튼 클릭 흐름 실패: {e}")
                return None
            finally:
                browser.close()

    # ── HTML 파싱 ───────────────────────────────────────

    def _parse_lodging_html(self, html: str) -> tuple[list[dict], str]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        items: list[dict] = []
        raw_parts: list[str] = []

        for target in self.targets:
            name = target["name"]
            available_kw = target.get("available_keyword", "예약 가능")
            cell_idx = int(target.get("status_cell_index", 4))

            row_text = "(미발견)"
            status = "(미발견)"
            for tr in soup.find_all("tr"):
                tr_text = tr.get_text(" ", strip=True)
                if name in tr_text:
                    row_text = tr_text
                    cells = tr.find_all(["td", "th"])
                    if len(cells) > cell_idx:
                        status = cells[cell_idx].get_text(strip=True)
                    elif cells:
                        status = cells[-1].get_text(strip=True)
                    break

            available = available_kw in status
            items.append({
                "name": name,
                "status": status,
                "available": available,
                "row_text": row_text[:120],
            })
            raw_parts.append(f"{name}::{status}")

        if not items and self.targets:
            logger.warning("[lodging] 대상 행 미발견. 페이지 구조 변경 가능성.")

        return items, "\n".join(raw_parts)

    # ── 알림 메시지 ─────────────────────────────────────

    def format_alert(self, items: list[dict]) -> Optional[str]:
        available = [i for i in items if i["available"]]
        if not available:
            return None
        prefix = f" ({self.select_date})" if self.select_date else ""
        lines = [f"🏨 무주산골 숙박패키지 예약 가능!{prefix}"]
        for it in available:
            lines.append(f"  • {it['name']} — {it['status']}")
        lines.append("\n👉 지금 바로 예매 페이지로!")
        return "\n".join(lines)
