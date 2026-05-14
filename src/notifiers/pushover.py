"""
Pushover 알림 (선택 채널 — 수면모드 무력화용)

Critical Alert (Emergency Priority = 2) 는 iOS의 방해 금지 모드를
무시하고 강제로 알람음을 울립니다. 새벽 예매 오픈 시 필수.

설정 예시:
  notifiers:
    pushover:
      enabled: true
      user_key: "${PUSHOVER_USER_KEY}"
      app_token: "${PUSHOVER_APP_TOKEN}"
      # 야간 강제 알람 사운드 (Pushover 내장 사운드 중 가장 시끄러운 것들)
      urgent_sound: "siren"   # alien / climb / persistent / siren 등
      # Emergency 재전송 간격(초)과 만료(초). 본인이 알람 끄지 않으면 계속 울림.
      retry_seconds: 60
      expire_seconds: 1800

설치 가이드: docs/SETUP_PUSHOVER.md
"""

from __future__ import annotations

import logging
from typing import Optional

import requests

from .base import Notifier, Priority

logger = logging.getLogger(__name__)

API_URL = "https://api.pushover.net/1/messages.json"

PRIORITY_MAP = {
    Priority.LOW: -1,
    Priority.DEFAULT: 0,
    Priority.HIGH: 1,
    Priority.URGENT: 2,   # ← Emergency (방해 금지 모드 무력화)
}


class PushoverNotifier(Notifier):
    name = "pushover"

    def __init__(self, settings: dict):
        self.user_key = settings.get("user_key", "").strip()
        self.app_token = settings.get("app_token", "").strip()
        self.urgent_sound = settings.get("urgent_sound", "siren")
        self.normal_sound = settings.get("normal_sound", "magic")
        self.retry_seconds = int(settings.get("retry_seconds", 60))
        self.expire_seconds = int(settings.get("expire_seconds", 1800))

        if not self.user_key or not self.app_token:
            logger.warning(
                "Pushover 키가 비어있습니다. .env의 PUSHOVER_USER_KEY/APP_TOKEN을 확인하세요."
            )

    def send(
        self,
        title: str,
        message: str,
        priority: Priority = Priority.DEFAULT,
        click_url: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> bool:
        if not self.user_key or not self.app_token:
            return False

        p = PRIORITY_MAP.get(priority, 0)
        data = {
            "token": self.app_token,
            "user": self.user_key,
            "title": title,
            "message": message,
            "priority": p,
            "sound": self.urgent_sound if priority == Priority.URGENT else self.normal_sound,
        }

        # Emergency priority 는 retry/expire 필수
        if p == 2:
            data["retry"] = self.retry_seconds
            data["expire"] = self.expire_seconds

        if click_url:
            data["url"] = click_url
            data["url_title"] = "지금 예매하기"

        try:
            resp = requests.post(API_URL, data=data, timeout=10)
            if resp.status_code == 200:
                logger.info(f"[pushover] 전송 완료: {title[:40]} (priority={p})")
                return True
            logger.error(f"[pushover] 실패: {resp.status_code} {resp.text[:200]}")
            return False
        except requests.RequestException as e:
            logger.error(f"[pushover] 전송 실패: {e}")
            return False
