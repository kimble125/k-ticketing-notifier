"""
여러 알림 채널을 묶어서 동시에 보내는 어그리게이터.

- 하나가 실패해도 다른 채널은 계속 시도
- 결과는 dict {채널이름: 성공여부}
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional

from .base import Notifier, Priority

logger = logging.getLogger(__name__)


class MultiNotifier:
    def __init__(self, channels: Iterable[Notifier]):
        self.channels = list(channels)
        if not self.channels:
            logger.warning("활성화된 알림 채널이 없습니다. 알림이 전송되지 않습니다.")

    def send(
        self,
        title: str,
        message: str,
        priority: Priority = Priority.DEFAULT,
        click_url: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> dict[str, bool]:
        results: dict[str, bool] = {}
        for ch in self.channels:
            try:
                results[ch.name] = ch.send(title, message, priority, click_url, tags)
            except Exception as e:
                logger.exception(f"[{ch.name}] 예상치 못한 오류: {e}")
                results[ch.name] = False
        return results

    def __len__(self) -> int:
        return len(self.channels)

    def __bool__(self) -> bool:
        return bool(self.channels)
