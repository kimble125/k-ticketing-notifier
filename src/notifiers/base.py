"""
알림 채널 공통 인터페이스

Priority:
  - LOW    : 일상 변경 (조용히)
  - DEFAULT: 일반 알림
  - HIGH   : 예매 가능 등 중요 알림
  - URGENT : 새벽이라도 깨워야 하는 알림 (Pushover Emergency, ntfy max)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional


class Priority(int, Enum):
    LOW = 1
    DEFAULT = 3
    HIGH = 4
    URGENT = 5

    @classmethod
    def from_str(cls, s: str) -> "Priority":
        return {
            "low": cls.LOW,
            "default": cls.DEFAULT,
            "normal": cls.DEFAULT,
            "high": cls.HIGH,
            "urgent": cls.URGENT,
            "critical": cls.URGENT,
            "emergency": cls.URGENT,
        }.get(s.lower(), cls.DEFAULT)


class Notifier(ABC):
    """알림 채널 공통 인터페이스"""

    name: str = "base"

    @abstractmethod
    def send(
        self,
        title: str,
        message: str,
        priority: Priority = Priority.DEFAULT,
        click_url: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> bool:
        """알림 전송. 성공 시 True."""
        ...
