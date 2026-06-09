"""
무주산골영화제 — 숙박패키지 예매 가능 감지

원본 monitor_mjff.py 의 흐름을 그대로 옮기되:
  - 인증 정보를 .env 로 분리
  - 여러 호텔/객실을 한 번에 감시 (targets 리스트)
  - 세션 재사용으로 재로그인 빈도 ↓
  - HTML 파싱은 BeautifulSoup 으로 안정화

설정 예시:
  - name: "무주산골 숙박패키지"
    type: "mjff_lodging"
    enabled: true
    interval_minutes: 5
    settings:
      target_url: "https://ticket.dtidea.kr/mjff/html/03/04.php"
      booking_button_text: "예매하기"     # 페이지 진입 후 클릭할 버튼
      targets:
        - name: "가족호텔(골드)"
          available_keyword: "예약 가능"
          status_cell_index: 4            # 0-based, 5번째 셀
        - name: "가족호텔(실버)"
          available_keyword: "예약 가능"
          status_cell_index: 4
"""

from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urljoin

from .mjff_auth_base import MJFFAuthBase

logger = logging.getLogger(__name__)


class MJFFLodgingCrawler(MJFFAuthBase):
    def __init__(self, settings: dict):
        super().__init__(settings)
        self.target_url = settings.get(
            "target_url", "https://ticket.dtidea.kr/mjff/html/03/04.php"
        )
        self.booking_button_text = settings.get("booking_button_text", "예매하기")
        self.targets: list[dict] = settings.get("targets", [])
        # 이 watcher 의 세션 파일 이름
        self._session_name = settings.get("session_name", "mjff-lodging")

    def check(self) -> dict:
        """
        Returns:
            {
                "items": [
                    {"name": "가족호텔(골드)", "status": "예약 가능", "available": True, ...},
                    ...
                ],
                "raw_data": str,    # 변경 감지용 (모든 대상의 상태 직렬화)
                "click_url": str,   # 알림에서 바로 열 URL
            }
        """
        html = self.fetch_html(self.target_url)
        if html is None:
            return {"items": [], "raw_data": "", "click_url": self.target_url}

        # 첫 진입 페이지가 예매 목록이 아니라 안내 페이지일 수 있음 → 예매하기 버튼 추적
        # 페이지에 이미 호텔 목록이 있을 수도, 또는 버튼 클릭 후 다른 페이지로 가야 할 수도 있음
        # Playwright 안에서 클릭하는 게 가장 안전하므로 base의 fetch_html 흐름을 한 번 더 호출
        # → 이번엔 booking 페이지로 직접 이동 시도

        # 사이트 구조상 dtidea.kr/03/04.php 가 이미 예매 목록일 가능성이 높지만,
        # 만약 버튼 클릭이 필요하면 별도 메서드로 처리
        items, raw = self._parse_lodging_html(html)
        if not items:
            # 버튼 클릭 후 다시 시도
            html2 = self._fetch_after_button_click()
            if html2:
                items, raw = self._parse_lodging_html(html2)

        return {
            "items": items,
            "raw_data": raw,
            "click_url": self.target_url,
        }

    # ── 예매하기 버튼이 별도 페이지일 때 처리 ────────────

    def _fetch_after_button_click(self) -> Optional[str]:
        """target_url 진입 후 예매하기 버튼을 클릭한 다음의 HTML 을 반환"""
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
                page.goto(self.target_url, timeout=30000, wait_until="domcontentloaded")
                self._human_pause()

                # 인증 페이지 처리
                from .mjff_auth_base import AUTH_PATH_HINT
                if AUTH_PATH_HINT in page.url:
                    if not self._fill_auth_form(page):
                        return None
                    if AUTH_PATH_HINT in page.url:
                        page.goto(self.target_url, timeout=30000)
                        self._human_pause()

                # 예매하기 버튼 클릭
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

    # ── HTML 파싱 ────────────────────────────────────────

    def _parse_lodging_html(self, html: str) -> tuple[list[dict], str]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        items: list[dict] = []
        raw_parts: list[str] = []

        for target in self.targets:
            name = target["name"]
            available_kw = target.get("available_keyword", "예약 가능")
            cell_idx = int(target.get("status_cell_index", 4))

            # 호텔 이름이 포함된 행 찾기
            row_text = "(미발견)"
            status = "(미발견)"
            for tr in soup.find_all("tr"):
                tr_text = tr.get_text(" ", strip=True)
                if name in tr_text:
                    row_text = tr_text
                    cells = tr.find_all(["td", "th"])
                    if len(cells) > cell_idx:
                        status = cells[cell_idx].get_text(strip=True)
                    break

            available = available_kw in status
            items.append({
                "name": name,
                "status": status,
                "available": available,
                "row_text": row_text[:120],
            })
            # 변경 감지용: 이름:상태 의 튜플들
            raw_parts.append(f"{name}::{status}")

        if not items and self.targets:
            logger.warning("[lodging] 대상 행을 하나도 찾지 못함. 페이지 구조 변경 가능성.")

        return items, "\n".join(raw_parts)

    # ── 알림 메시지 포맷팅 ───────────────────────────────

    def format_alert(self, items: list[dict]) -> Optional[str]:
        """예약 가능 항목이 하나라도 있으면 메시지 생성, 없으면 None"""
        available = [i for i in items if i["available"]]
        if not available:
            return None
        lines = ["🏨 무주산골 숙박패키지 예약 가능!"]
        for it in available:
            lines.append(f"  • {it['name']} — {it['status']}")
        lines.append("\n👉 지금 바로 예매 페이지로 이동하세요!")
        return "\n".join(lines)
