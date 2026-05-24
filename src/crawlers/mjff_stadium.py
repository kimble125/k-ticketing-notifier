"""
무주등나무운동장 1일 입장권 — 날짜별 매진/예매 감지

흐름:
  /03/01.php 진입 → (인증) → '예매하기' 클릭 → 날짜 목록 표시
  → 특정 날짜('6. 6.(토)') 행/카드에서 '온라인매진' 또는 '예매하기' 상태 확인

설정 예시:
  - name: "무주등나무운동장 6/6"
    type: "mjff_stadium"
    enabled: true
    interval_minutes: 5
    settings:
      target_url: "https://ticket.dtidea.kr/mjff/html/03/01.php"
      booking_button_text: "예매하기"
      session_name: "mjff-stadium"
      targets:
        - date_label: "6. 6.(토)"            # 화면에 보이는 날짜 텍스트
          sold_out_keyword: "온라인매진"     # 현재 상태
          available_keyword: "예매하기"      # 이 키워드로 바뀌면 알림
        # 여러 날짜 동시 감시 가능
        # - date_label: "6. 7.(일)"
"""

from __future__ import annotations

import logging
from typing import Optional

from .mjff_auth_base import MJFFAuthBase, AUTH_PATH_HINT

logger = logging.getLogger(__name__)


class MJFFStadiumCrawler(MJFFAuthBase):
    def __init__(self, settings: dict):
        super().__init__(settings)
        self.target_url = settings.get(
            "target_url", "https://ticket.dtidea.kr/mjff/html/03/01.php"
        )
        self.booking_button_text = settings.get("booking_button_text", "예매하기")
        self.targets: list[dict] = settings.get("targets", [])
        self._session_name = settings.get("session_name", "mjff-stadium")

    def check(self) -> dict:
        html = self._fetch_with_button_click()
        if html is None:
            return {"items": [], "raw_data": "", "click_url": self.target_url}

        items, raw = self._parse(html)
        return {"items": items, "raw_data": raw, "click_url": self.target_url}

    # ── Playwright 로 페이지 가져오기 ───────────────────

    def _fetch_with_button_click(self) -> Optional[str]:
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
                else:
                    logger.warning(f"[stadium] '{self.booking_button_text}' 버튼 미발견 — 이미 목록일 수 있음")

                html = page.content()
                try:
                    context.storage_state(path=str(self._state_path))
                except Exception:
                    pass
                return html

            except Exception as e:
                logger.exception(f"[stadium] 페이지 로드 실패: {e}")
                return None
            finally:
                browser.close()

    # ── HTML 파싱 ───────────────────────────────────────

    def _parse(self, html: str) -> tuple[list[dict], str]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        items: list[dict] = []
        raw_parts: list[str] = []

        # 모든 요소(row/카드 등)를 순회하며 날짜 라벨 매칭
        all_blocks = soup.find_all(["tr", "li", "div"])

        for target in self.targets:
            date_label = target["date_label"]
            sold_out = target.get("sold_out_keyword", "온라인매진")
            available_kw = target.get("available_keyword", "예매하기")

            # 날짜 라벨 변형들 시도
            label_variants = [
                date_label,
                date_label.replace(" ", ""),
                date_label.replace(".", ". "),
                date_label.split("(")[0].strip(),
            ]

            status_text = "(미발견)"
            available = False
            block_text = "(미발견)"

            for block in all_blocks:
                txt = block.get_text(" ", strip=True)
                if not any(v in txt for v in label_variants):
                    continue
                block_text = txt[:200]

                # 같은 블록 내에서 상태 키워드 찾기
                if available_kw in txt and sold_out not in txt:
                    status_text = available_kw
                    available = True
                    break
                if sold_out in txt:
                    status_text = sold_out
                    available = False
                    break
                # 매칭 키워드 없으면 일단 블록의 일부를 상태로
                status_text = txt[:30]
                break

            items.append({
                "date_label": date_label,
                "status": status_text,
                "available": available,
                "block_text": block_text,
            })
            raw_parts.append(f"{date_label}::{status_text}")

        if not items and self.targets:
            logger.warning("[stadium] 타겟 날짜 미발견. 페이지 구조 변경?")

        return items, "\n".join(raw_parts)

    # ── 알림 메시지 ─────────────────────────────────────

    def format_alert(self, items: list[dict]) -> Optional[str]:
        avail = [i for i in items if i["available"]]
        if not avail:
            return None
        lines = ["⚽ 무주등나무운동장 1일 입장권 예매 가능!"]
        for it in avail:
            lines.append(f"  • {it['date_label']} — {it['status']}")
        lines.append("\n👉 즉시 예매!")
        return "\n".join(lines)
