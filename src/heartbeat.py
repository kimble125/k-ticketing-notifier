"""
Daily heartbeat — "봇이 살아있어요" 알림 (옵션)

main.py 가 매 체크마다 maybe_send_heartbeat() 를 호출하고,
하루에 한 번 (설정한 시각 이후 첫 실행) 만 실제로 발송한다.

설정 (config.yaml 의 heartbeat 섹션):
  heartbeat:
    enabled: true
    hour: 12          # 발송 기준 시각 (이 시각 이후 첫 체크에서 발송)
    minute: 0
    priority: "low"
    title: "🟢 살아있어요"
    message: "오늘 모니터링 정상 가동 중입니다."

환경변수 HEARTBEAT_ENABLED=true 로도 켤 수 있다 (GitHub Secrets 편의).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from .notifiers.base import Priority

logger = logging.getLogger(__name__)

# state.py 에 저장되는 heartbeat 추적용 키
_STATE_KEY = "_heartbeat"


def _is_enabled(hb: dict) -> bool:
    """config 의 enabled 또는 환경변수 HEARTBEAT_ENABLED 중 하나라도 참이면 켬"""
    env = os.environ.get("HEARTBEAT_ENABLED", "").strip().lower()
    if env in ("1", "true", "yes", "on"):
        return True
    return bool(hb.get("enabled", False))


def maybe_send_heartbeat(config: dict, state_mgr, notifier) -> bool:
    """
    조건이 맞으면 heartbeat 알림을 1회 발송하고 True 를 반환.

    발송 조건 (모두 충족):
      1) heartbeat.enabled (또는 HEARTBEAT_ENABLED 환경변수) 가 참
      2) 오늘 아직 heartbeat 를 보낸 적이 없음
      3) 현재 시각이 설정한 hour:minute 이후
    """
    hb = config.get("heartbeat", {}) or {}
    if not _is_enabled(hb):
        return False

    if notifier is None or not notifier:
        logger.debug("heartbeat: 활성 알림 채널이 없어 건너뜀")
        return False

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    state = state_mgr.get(_STATE_KEY)
    if state.get("last_date") == today:
        return False  # 오늘 이미 발송

    # 설정 시각 이후인가?
    hour = int(hb.get("hour", 12))
    minute = int(hb.get("minute", 0))
    scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now < scheduled:
        return False  # 아직 발송 시각 전

    priority = Priority.from_str(str(hb.get("priority", "low")))
    title = hb.get("title", "🟢 ticket-notifier 살아있어요")
    message = hb.get(
        "message",
        f"오늘 모니터링 정상 가동 중입니다. ({now.strftime('%Y-%m-%d %H:%M')})",
    )

    try:
        notifier.send(title=title, message=message, priority=priority)
    except Exception as e:  # 알림 실패가 전체 체크를 막지 않도록
        logger.warning(f"heartbeat 발송 실패: {e}")
        return False

    state_mgr.save(_STATE_KEY, {"last_date": today, "last_sent": now.isoformat(timespec="seconds")})
    logger.info(f"heartbeat 발송 완료 ({today})")
    return True
