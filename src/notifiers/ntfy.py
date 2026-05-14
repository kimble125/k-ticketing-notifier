"""
ntfy 알림 (메인 채널 — 무료, 가입 불필요)

설정 예시:
  notifiers:
    ntfy:
      enabled: true
      topic: "${NTFY_TOPIC}"     # .env 에서 로드
      server: "${NTFY_SERVER:https://ntfy.sh}"
"""

from __future__ import annotations

import logging
from typing import Optional

import requests

from .base import Notifier, Priority

logger = logging.getLogger(__name__)

# ntfy priority 매핑 (1=min, 5=max)
PRIORITY_MAP = {
    Priority.LOW: "2",
    Priority.DEFAULT: "3",
    Priority.HIGH: "4",
    Priority.URGENT: "5",
}


class NtfyNotifier(Notifier):
    name = "ntfy"

    def __init__(self, settings: dict):
        self.topic = settings.get("topic", "").strip()
        self.server = settings.get("server", "https://ntfy.sh").rstrip("/")
        self.default_tags = settings.get("tags", ["ticket", "loudspeaker"])
        # Bearer 토큰 (자체 호스팅 + 인증된 토픽일 때만)
        self.token = settings.get("token", "").strip()

        if not self.topic or "CHANGE-ME" in self.topic:
            logger.warning(
                "ntfy topic이 설정되지 않았거나 기본값입니다. "
                ".env의 NTFY_TOPIC을 짐작 불가능한 랜덤 문자열로 변경하세요."
            )

    @property
    def url(self) -> str:
        return f"{self.server}/{self.topic}"

    def send(
        self,
        title: str,
        message: str,
        priority: Priority = Priority.DEFAULT,
        click_url: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> bool:
        if not self.topic:
            logger.error("ntfy topic이 없습니다.")
            return False

        # ntfy 헤더는 ISO-8859-1 인코딩만 안전 → 한글 제목은 RFC 2047 인코딩
        from email.header import Header
        safe_title = Header(title, "utf-8").encode()

        headers = {
            "Title": safe_title,
            "Priority": PRIORITY_MAP.get(priority, "3"),
            "Tags": ",".join(tags or self.default_tags),
        }
        if click_url:
            headers["Click"] = click_url
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            resp = requests.post(
                self.url,
                data=message.encode("utf-8"),
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()
            logger.info(f"[ntfy] 전송 완료: {title[:40]}")
            return True
        except requests.RequestException as e:
            logger.error(f"[ntfy] 전송 실패: {e}")
            return False
