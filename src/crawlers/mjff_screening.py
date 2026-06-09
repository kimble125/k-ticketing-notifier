"""
무주산골영화제 — 실내상영 영화 예매 가능 감지

페이지 구조 (https://ticket.dtidea.kr/mjff/html/01/01.php?s_date=YYYY-MM-DD):
  - 같은 날짜의 모든 상영작이 한 페이지에 표 형태로 나옴
  - 각 행: 시간 / 영화 / 등급 / 예매 상태(버튼 또는 텍스트)
  - "예매하기" = 가능, "온라인매진" = 불가

설정 예시:
  - name: "무주산골 실내상영 06/06"
    type: "mjff_screening"
    enabled: true
    interval_minutes: 5
    settings:
      date: "2026-06-06"
      target_url: "https://ticket.dtidea.kr/mjff/html/01/01.php?s_date=2026-06-06"
      sold_out_keyword: "온라인매진"
      available_keyword: "예매하기"
      targets:
        - movie: "별과 모래"
          time: "10:30"
        - movie: "산양들"
          time: "16:30"
        # ...
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from .mjff_auth_base import MJFFAuthBase

logger = logging.getLogger(__name__)


class MJFFScreeningCrawler(MJFFAuthBase):
    def __init__(self, settings: dict):
        super().__init__(settings)
        self.date = settings.get("date", "")
        self.target_url = settings.get("target_url", "")
        if not self.target_url and self.date:
            self.target_url = (
                f"https://ticket.dtidea.kr/mjff/html/01/01.php?s_date={self.date}"
            )
        self.sold_out_keyword = settings.get("sold_out_keyword", "온라인매진")
        self.available_keyword = settings.get("available_keyword", "예매하기")
        self.targets: list[dict] = settings.get("targets", [])
        self._session_name = settings.get(
            "session_name", f"mjff-screening-{self.date or 'unknown'}"
        )

    def check(self) -> dict:
        html = self.fetch_html(self.target_url)
        if html is None:
            return {"items": [], "raw_data": "", "click_url": self.target_url}

        items, raw = self._parse_screening_html(html)
        return {
            "items": items,
            "raw_data": raw,
            "click_url": self.target_url,
        }

    # ── HTML 파싱 ────────────────────────────────────────

    def _parse_screening_html(self, html: str) -> tuple[list[dict], str]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        items: list[dict] = []
        raw_parts: list[str] = []

        # 모든 행을 순회하며 영화 제목 + 시간 매칭
        rows = soup.find_all("tr")

        for target in self.targets:
            movie = target["movie"].strip()
            time_str = target.get("time", "").strip()

            status_text = "(미발견)"
            available = False

            for tr in rows:
                tr_text = tr.get_text(" ", strip=True)
                # 영화 제목과 시간이 모두 포함되는 행을 찾음
                if movie not in tr_text:
                    continue
                if time_str and not self._time_matches(tr_text, time_str):
                    continue

                # 행 내에서 상태 추출
                # 1) 예매하기 / 온라인매진 텍스트
                if self.available_keyword in tr_text:
                    status_text = self.available_keyword
                    available = True
                elif self.sold_out_keyword in tr_text:
                    status_text = self.sold_out_keyword
                    available = False
                else:
                    # 셀별로 마지막 셀의 텍스트를 상태로 추정
                    cells = tr.find_all(["td", "th"])
                    if cells:
                        status_text = cells[-1].get_text(strip=True)[:30]
                break

            items.append({
                "date": self.date,
                "movie": movie,
                "time": time_str,
                "status": status_text,
                "available": available,
            })
            raw_parts.append(f"{movie}@{time_str}::{status_text}")

        return items, "\n".join(raw_parts)

    @staticmethod
    def _time_matches(text: str, expected: str) -> bool:
        """텍스트 안에서 expected 시간(HH:MM)이 등장하는지 확인"""
        # expected 의 콜론 양옆 공백 가능성도 허용
        pattern = re.escape(expected).replace(r"\:", r"\s*:\s*")
        return bool(re.search(pattern, text))

    # ── 알림 메시지 포맷팅 ───────────────────────────────

    def format_alert(self, items: list[dict]) -> Optional[str]:
        avail = [i for i in items if i["available"]]
        if not avail:
            return None
        lines = [f"🎬 무주산골 실내상영 예매 오픈! ({self.date})"]
        for it in avail:
            lines.append(f"  • {it['time']} {it['movie']} — {it['status']}")
        lines.append("\n👉 즉시 예매 페이지로!")
        return "\n".join(lines)
