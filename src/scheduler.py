"""
시간대별 동적 스케줄링 + 우선순위 결정

원리:
  - 평소(낮): 5분 주기
  - 오픈 임박(자정 ±30분): 1~2분 주기
  - 야간: 알림 priority 가 URGENT 로 자동 격상 → Pushover Emergency 발동
  - 매번 ±jitter 초 무작위 지연으로 "사람스러움" 유지

이 모듈은 GitHub Actions cron(5분마다) + 한 번 호출 시 한 번 체크 패턴에 최적화.
즉 스케줄러 자체가 sleep 하지 않고, "지금 이 watcher 를 돌릴 차례인가?" 만 판별.
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime, time as dtime
from typing import Optional

from .notifiers.base import Priority

logger = logging.getLogger(__name__)


@dataclass
class WindowRule:
    """시간 구간별 간격/우선순위 규칙"""
    start: dtime
    end: dtime
    interval_minutes: float
    priority: Priority = Priority.HIGH

    def contains(self, t: dtime) -> bool:
        # 자정을 가로지르는 윈도우 지원 (예: 22:00 ~ 02:00)
        if self.start <= self.end:
            return self.start <= t < self.end
        return t >= self.start or t < self.end


# 사용자가 답변한 추천 스케줄을 그대로 코드로:
#   06:00 ~ 23:30 : 5분 주기 / HIGH
#   23:30 ~ 00:00 : 2분 주기 / HIGH
#   00:00 ~ 00:30 : 1분 주기 / URGENT (수면모드 무력화)
#   00:30 ~ 06:00 : 15분 주기 / URGENT
DEFAULT_RULES: list[WindowRule] = [
    WindowRule(dtime(6, 0),  dtime(23, 30), 5.0,  Priority.HIGH),
    WindowRule(dtime(23, 30), dtime(0, 0),  2.0,  Priority.HIGH),
    WindowRule(dtime(0, 0),  dtime(0, 30),  1.0,  Priority.URGENT),
    WindowRule(dtime(0, 30), dtime(6, 0),  15.0, Priority.URGENT),
]


def current_rule(now: Optional[datetime] = None, rules: list[WindowRule] | None = None) -> WindowRule:
    """현재 시각에 해당하는 WindowRule 반환"""
    now = now or datetime.now()
    rules = rules or DEFAULT_RULES
    t = now.time()
    for r in rules:
        if r.contains(t):
            return r
    # 매칭 실패 → 기본 5분
    return WindowRule(dtime(0, 0), dtime(23, 59), 5.0, Priority.DEFAULT)


def should_run_now(
    watcher_name: str,
    state_mgr,
    base_interval_minutes: float | None = None,
    now: Optional[datetime] = None,
    jitter_seconds: int = 15,
) -> tuple[bool, Priority]:
    """
    지금 이 watcher 를 실행해야 하는지 결정.

    Returns:
        (실행 여부, 알림 우선순위)
    """
    now = now or datetime.now()
    rule = current_rule(now)
    interval_min = base_interval_minutes if base_interval_minutes is not None else rule.interval_minutes

    state = state_mgr.get(watcher_name)
    last = state.get("last_check", "")
    if not last:
        return True, rule.priority

    try:
        last_dt = datetime.fromisoformat(last)
    except ValueError:
        return True, rule.priority

    elapsed = (now - last_dt).total_seconds()
    # 인간적인 무작위 지연 추가: 기준 - jitter ~ 기준 + jitter
    jitter = random.uniform(-jitter_seconds, jitter_seconds)
    threshold = interval_min * 60 + jitter
    return elapsed >= threshold, rule.priority


def apply_human_pause(seconds_min: float = 1.0, seconds_max: float = 3.0) -> None:
    """크롤러 사이의 인간적인 짧은 대기 — 봇 판정 회피"""
    time.sleep(random.uniform(seconds_min, seconds_max))
