"""
알림 채널 모듈

여러 채널을 동시에 묶어서 보낼 수 있는 MultiNotifier 가 핵심.
설정의 notifiers 섹션에 따라 어떤 채널을 켤지 결정됨.
"""

from .base import Notifier, Priority
from .multi import MultiNotifier

__all__ = ["Notifier", "Priority", "MultiNotifier", "build_from_config"]


def build_from_config(config: dict) -> "MultiNotifier":
    """config['notifiers'] 에서 활성 채널들을 모아 MultiNotifier 생성"""
    notif_cfg = config.get("notifiers", {})
    channels: list[Notifier] = []

    if notif_cfg.get("ntfy", {}).get("enabled"):
        from .ntfy import NtfyNotifier
        channels.append(NtfyNotifier(notif_cfg["ntfy"]))

    if notif_cfg.get("pushover", {}).get("enabled"):
        from .pushover import PushoverNotifier
        channels.append(PushoverNotifier(notif_cfg["pushover"]))

    if notif_cfg.get("telegram", {}).get("enabled"):
        from .telegram import TelegramNotifier
        channels.append(TelegramNotifier(notif_cfg["telegram"]))

    return MultiNotifier(channels)
