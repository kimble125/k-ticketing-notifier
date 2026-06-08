"""
서울야외도서관(힙독클럽) 프로그램 상태 감시

⚠️ 이 파일은 **스켈레톤(설계 초안)** 입니다.
   실제 페이지 HTML 구조 분석은 새 채팅(Opus 4.8)에서 수행 필요.

대상 URL:
  https://seouloutdoorlibrary.kr/user/program/selectPageListProgram.do?area_id=hipdok&flag=program_list

감시 대상 (호연님 요청):
  1. 노마드리딩 ③ : 커피향 바다독서 in 강릉
  2. [리딩몹] 최애책 재독단 #4. 소장하고 싶은 그 책
  3. [리딩몹] 챕터 퍼즐 리딩 #1. 기록하기로 했습니다.
  4. [힙독클럽 X 서울도서관] 작가힙톡_하주원 작가
  5. [힙독클럽 X 서울도서관] 작가힙톡_하지현 작가

감지 조건 (둘 중 더 안정적인 신호 채택 — 새 채팅에서 검증):
  (A) 상태 표시가 "정원 마감" → "신청중" 등으로 변경
  (B) 모집 정원/현재 신청자 수 숫자가 감소 (취소표 발생)

권장 구현 단계 (새 채팅에서):
  1. Playwright 로 페이지 직접 접속 → 첫 HTML 캡처 → 구조 파악
     - .program-list, .program-item 같은 CSS 셀렉터 찾기
     - 각 프로그램 카드의 제목 / 상태 / 정원 / 신청자수 위치
  2. SSR 인지 SPA(JS 렌더) 인지 확인:
     - requests 로 받아본 HTML 에 프로그램 제목이 보이면 SSR (cheaper)
     - 안 보이면 Playwright 필요
  3. 인증 필요한가? 회원가입 후 신청만 가능하지만 "목록 조회"는 비인증 가능할 수 있음
  4. 페이지네이션? 한 페이지에 5개 다 보이는가, 스크롤·페이지 이동 필요한가
  5. 가장 안정적인 신호 결정 (상태 텍스트 vs 숫자 변화)
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class SeoulOutdoorLibraryCrawler:
    """힙독클럽 프로그램 목록 감시 — 스켈레톤"""

    def __init__(self, settings: dict):
        self.target_url = settings.get(
            "target_url",
            "https://seouloutdoorlibrary.kr/user/program/selectPageListProgram.do?area_id=hipdok&flag=program_list",
        )
        # 감지 모드: "status_change" (정원마감→신청중) 또는 "count_change" (정원 숫자)
        self.detection_mode = settings.get("detection_mode", "status_change")
        self.headless = bool(settings.get("headless", True))
        self.use_playwright = bool(settings.get("use_playwright", True))
        # 감시 대상 프로그램 목록
        self.targets: list[dict] = settings.get("targets", [])
        # 상태 키워드 (사이트 구조 파악 후 조정 필요)
        self.full_keyword = settings.get("full_keyword", "정원 마감")
        self.open_keyword = settings.get("open_keyword", "신청중")

    def check(self) -> dict:
        if self.use_playwright:
            html = self._fetch_with_playwright()
        else:
            html = self._fetch_with_requests()

        if not html:
            return {"items": [], "raw_data": "", "click_url": self.target_url}

        items, raw = self._parse(html)
        return {
            "items": items,
            "raw_data": raw,
            "click_url": self.target_url,
        }

    # ── 페이지 가져오기 ─────────────────────────────────

    def _fetch_with_requests(self) -> Optional[str]:
        """SSR 사이트라면 이게 가장 가벼움"""
        import requests
        try:
            resp = requests.get(
                self.target_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept-Language": "ko-KR,ko;q=0.9",
                },
                timeout=15,
            )
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            logger.error(f"[seoul_lib] requests 실패: {e}")
            return None

    def _fetch_with_playwright(self) -> Optional[str]:
        """JS 렌더링 필요한 SPA용"""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("[seoul_lib] playwright 미설치")
            return None

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            try:
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    locale="ko-KR",
                )
                page = context.new_page()
                page.goto(self.target_url, timeout=30000, wait_until="networkidle")
                # TODO: 필요시 페이지네이션·스크롤 처리
                return page.content()
            except Exception as e:
                logger.exception(f"[seoul_lib] playwright 실패: {e}")
                return None
            finally:
                browser.close()

    # ── HTML 파싱 (구조 파악 후 새 채팅에서 보강) ──────

    def _parse(self, html: str) -> tuple[list[dict], str]:
        """
        TODO (새 채팅에서):
          - 실제 페이지 HTML inspect 후 CSS 셀렉터 확정
          - 프로그램 카드 컨테이너 (예: ".program-item") 식별
          - 카드 안에서 제목 / 상태 / 정원 / 현재 신청자수 위치 결정
          - 사용자의 감시 대상 5개 프로그램 제목과 매칭
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        items: list[dict] = []
        raw_parts: list[str] = []

        for target in self.targets:
            name = target["name"]
            status_text = "(미발견)"
            available = False

            # 임시 휴리스틱: 프로그램 이름이 들어있는 컨테이너를 찾고 그 근처 텍스트 확인
            # 실제 구조 파악 후 정확한 셀렉터로 교체
            for element in soup.find_all(["div", "li", "article", "section"]):
                text = element.get_text(" ", strip=True)
                if name not in text or len(text) > 1000:
                    continue
                # 한 카드 안에 상태 키워드가 있는지
                if self.open_keyword in text and self.full_keyword not in text:
                    status_text = self.open_keyword
                    available = True
                    break
                if self.full_keyword in text:
                    status_text = self.full_keyword
                    available = False
                    break

            items.append({
                "name": name,
                "status": status_text,
                "available": available,
            })
            raw_parts.append(f"{name[:40]}::{status_text}")

        return items, "\n".join(raw_parts)

    def format_alert(self, items: list[dict]) -> Optional[str]:
        avail = [i for i in items if i["available"]]
        if not avail:
            return None
        lines = ["📚 힙독클럽 프로그램 신청 가능!"]
        for it in avail:
            lines.append(f"  • {it['name'][:50]} — {it['status']}")
        lines.append("\n👉 즉시 신청 페이지로!")
        return "\n".join(lines)
