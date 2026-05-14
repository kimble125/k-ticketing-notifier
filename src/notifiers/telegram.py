"""
텔레그램 알림 (선택 채널 — 양방향 기능 없이 발신만)

기존 movie-club-ticket-notifier-main의 bot 모듈과 달리, 여기서는
명령어 인터페이스를 제거하고 단순 발신 함수만 둠. 봇 폴링 비용 절감.

설정 예시:
  notifiers:
    telegram:
      enabled: true
      bot_token: "${TELEGRAM_BOT_TOKEN}"
      chat_ids: "${TELEGRAM_CHAT_IDS}"  # 쉼표로 구분된 ID들
"""

from __future__ import annotations

import logging
from typing import Optional

import requests

from .base import Notifier, Priority

logger = logging.getLogger(__name__)


class TelegramNotifier(Notifier):
    name = "telegram"

    def __init__(self, settings: dict):
        self.token = settings.get("bot_token", "").strip()
        raw_ids = settings.get("chat_ids", "")
        if isinstance(raw_ids, list):
            self.chat_ids = [str(x).strip() for x in raw_ids if str(x).strip()]
        else:
            self.chat_ids = [c.strip() for c in str(raw_ids).split(",") if c.strip()]

        if not self.token or not self.chat_ids:
            logger.warning(
                "Telegram 설정이 비어있습니다. "
                "TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_IDS 환경변수를 확인하세요."
            )

    def send(
        self,
        title: str,
        message: str,
        priority: Priority = Priority.DEFAULT,
        click_url: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> bool:
        if not self.token or not self.chat_ids:
            return False

        text = f"<b>{_esc(title)}</b>\n\n{_esc(message)}"
        if click_url:
            text += f'\n\n👉 <a href="{click_url}">지금 예매하기</a>'

        # priority 가 URGENT 이상이면 알림음 강제
        disable_notification = priority == Priority.LOW

        ok_all = True
        for chat_id in self.chat_ids:
            try:
                resp = requests.post(
                    f"https://api.telegram.org/bot{self.token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                        "disable_notification": disable_notification,
                    },
                    timeout=10,
                )
                if resp.status_code != 200:
                    logger.error(f"[telegram] 실패 ({chat_id}): {resp.text[:200]}")
                    ok_all = False
            except requests.RequestException as e:
                logger.error(f"[telegram] 전송 실패 ({chat_id}): {e}")
                ok_all = False

        return ok_all


def _esc(text: str) -> str:
    """텔레그램 HTML 모드용 최소 이스케이프"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
