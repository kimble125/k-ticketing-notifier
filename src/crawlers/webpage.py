"""
범용 웹페이지 변경 감지 크롤러 (인증 불필요한 페이지용)

원본 movie-club-ticket-notifier-main 의 webpage.py 를 그대로 가져옴.
무주산골영화제 공지사항 같은 곳에 사용.
"""

from __future__ import annotations

import logging
import re
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


class WebpageCrawler:
    """CSS 선택자 기반 웹페이지 변경 감지"""

    def __init__(self, settings: dict):
        self.url = settings.get("url", "")
        self.selector = settings.get("selector", "body")
        self.encoding = settings.get("encoding", "utf-8")
        self.keywords = [kw.upper() for kw in settings.get("keywords", [])]
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def check(self) -> dict:
        try:
            resp = self.session.get(self.url, timeout=15)
            resp.encoding = self.encoding
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"[webpage] 조회 실패 ({self.url}): {e}")
            return {"items": [], "raw_data": "", "click_url": self.url}

        soup = BeautifulSoup(resp.text, "html.parser")
        elements = soup.select(self.selector)
        if not elements:
            logger.warning(f"[webpage] 선택자 '{self.selector}' 매칭 0건: {self.url}")
            return {"items": [], "raw_data": "", "click_url": self.url}

        items, raw_parts = [], []
        for el in elements:
            text = el.get_text(strip=True)
            if not text:
                continue
            raw_parts.append(text)

            if self.keywords and not any(kw in text.upper() for kw in self.keywords):
                continue

            link_el = el.find("a") if el.name != "a" else el
            link = ""
            if link_el and link_el.get("href"):
                href = link_el["href"]
                js_match = re.search(r"OnReadArticle\('(\d+)'\)", href)
                if js_match:
                    seq = js_match.group(1)
                    board_match = re.search(r"strBoardID=([^&]+)", self.url)
                    board_id = board_match.group(1) if board_match else ""
                    link = (
                        f"https://mjff.or.kr/kor/artyboard/mboard.asp"
                        f"?Action=view&strBoardID={board_id}&intSeq={seq}"
                    )
                elif href.startswith("http"):
                    link = href
                elif href.startswith("/"):
                    link = urljoin(self.url, href)

            items.append({"title": text[:200], "link": link})

        return {
            "items": items,
            "raw_data": "\n".join(raw_parts),
            "click_url": items[0]["link"] if items else self.url,
        }

    def format_alert(self, items: list[dict]) -> Optional[str]:
        if not items:
            return None
        lines = [f"📢 새 공지 {len(items)}건 감지!"]
        for it in items[:10]:
            lines.append(f"  • {it['title'][:80]}")
        if len(items) > 10:
            lines.append(f"  ... 외 {len(items) - 10}건")
        return "\n".join(lines)
