"""
무주산골영화제 dtidea.kr 인증 공통 흐름 (Playwright 동기 API)

원리:
  1. 목표 페이지로 직접 GET
  2. /09/01.php (인증 폼) 로 리다이렉트되면 환경변수의 정보로 자동 입력
  3. 인증 후 다시 목표 페이지로 이동
  4. HTML 을 추출해 자식 클래스에 넘김

세션 재사용:
  - storage_state JSON 으로 쿠키 저장
  - 다음 실행 시 재로그인 없이 바로 접근 → 사이트 부담 감소
"""

from __future__ import annotations

import logging
import os
import random
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

AUTH_PATH_HINT = "09/01.php"


class MJFFAuthBase:
    """Playwright 기반 dtidea.kr 인증 공통 기능"""

    def __init__(self, settings: dict):
        # 인증 정보는 .env (환경변수) 에서만 읽음 — 코드/설정 파일에 절대 안 박힘
        self.user_info = {
            "name": os.getenv("MJFF_NAME", "").strip(),
            "hp": os.getenv("MJFF_PHONE", "").strip().replace("-", ""),
            "pass": os.getenv("MJFF_PASS", "").strip(),
        }
        self.headless = bool(settings.get("headless", True))
        self.use_stealth = bool(settings.get("use_stealth", False))
        self.viewport = settings.get("viewport", {"width": 1280, "height": 1024})
        self.user_agent = settings.get(
            "user_agent",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36",
        )

        # 세션 재사용 (재로그인 빈도 감소 → 사이트 부담 ↓)
        sess_dir = Path(settings.get("session_dir", "./data/state/cookies"))
        sess_dir.mkdir(parents=True, exist_ok=True)
        # watcher 이름이 settings 에 없으니, 호출 측에서 set_session_name 사용
        self._session_dir = sess_dir
        self._session_name = settings.get("session_name", "mjff-default")

        # 페이지 로드 후 인간적인 지연(jitter) — 사이트 부담 감소 + 봇 판정 회피
        self.min_pause_ms = int(settings.get("min_pause_ms", 1500))
        self.max_pause_ms = int(settings.get("max_pause_ms", 3500))

        # 인증 정보 검증
        if not all(self.user_info.values()):
            logger.error(
                "MJFF 인증 정보가 누락되었습니다. .env 파일에 "
                "MJFF_NAME / MJFF_PHONE / MJFF_PASS 를 설정하세요."
            )

    # ── 세션 상태 파일 경로 ──────────────────────────────

    @property
    def _state_path(self) -> Path:
        return self._session_dir / f"{self._session_name}.json"

    def _human_pause(self) -> None:
        """인간적인 랜덤 대기 — 매번 정확히 같은 간격이면 봇으로 의심받음"""
        ms = random.randint(self.min_pause_ms, self.max_pause_ms)
        time.sleep(ms / 1000.0)

    # ── 공통: 목표 URL 페이지 HTML 가져오기 ───────────────

    def fetch_html(self, target_url: str) -> Optional[str]:
        """
        목표 URL 의 HTML 을 반환. 인증 페이지로 리다이렉트되면 자동 처리.
        실패 시 None.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error(
                "playwright 가 설치되지 않았습니다. "
                "pip install playwright && playwright install chromium 실행 필요."
            )
            return None

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
            try:
                context = browser.new_context(
                    user_agent=self.user_agent,
                    viewport=self.viewport,
                    locale="ko-KR",
                    storage_state=str(self._state_path) if self._state_path.exists() else None,
                )

                if self.use_stealth:
                    try:
                        from playwright_stealth import Stealth
                        Stealth().apply_stealth_sync(context)
                    except ImportError:
                        logger.debug("playwright_stealth 미설치 — stealth 모드 건너뜀")

                page = context.new_page()

                # 1차 시도: 목표 URL 로 직접 이동
                logger.info(f"[mjff] {target_url} 접속 시도")
                page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
                self._human_pause()

                # 인증 페이지로 리다이렉트됐는지 확인
                if AUTH_PATH_HINT in page.url:
                    logger.info("[mjff] 인증 페이지 감지 → 폼 자동 입력")
                    if not self._fill_auth_form(page):
                        logger.error("[mjff] 인증 실패")
                        return None
                    # 인증 후 다시 목표 페이지로 이동 (보통 자동 리다이렉트되지만 보험)
                    if AUTH_PATH_HINT in page.url:
                        page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
                        self._human_pause()

                html = page.content()

                # 인증 성공한 케이스에 한해 세션 저장 → 다음 실행 시 재로그인 생략
                try:
                    context.storage_state(path=str(self._state_path))
                except Exception:
                    pass

                return html

            except Exception as e:
                logger.exception(f"[mjff] 페이지 로드 실패: {e}")
                return None
            finally:
                browser.close()

    # ── 인증 폼 자동 입력 ────────────────────────────────

    def _fill_auth_form(self, page) -> bool:
        """09/01.php 인증 페이지에서 이름/휴대폰/비밀번호 입력 후 제출"""
        if not all(self.user_info.values()):
            return False

        try:
            page.fill("#u_name", self.user_info["name"])
            page.fill("#u_hp", self.user_info["hp"])
            page.fill("#u_pass", self.user_info["pass"])
            # 약간의 인간적인 지연
            self._human_pause()
            # 제출 버튼 ('사용자 인증' value)
            page.click("input[value='사용자 인증']")
            page.wait_for_load_state("networkidle", timeout=15000)
            self._human_pause()
            # 여전히 인증 페이지에 있으면 실패
            return AUTH_PATH_HINT not in page.url
        except Exception as e:
            logger.error(f"[mjff] 인증 폼 입력 실패: {e}")
            return False
