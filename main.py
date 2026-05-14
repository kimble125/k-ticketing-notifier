#!/usr/bin/env python3
"""
ticket-notifier — 메인 엔트리포인트

사용법:
  python main.py                   # 활성 watcher 1회 체크 → 알림 발송
  python main.py --check           # 동일 (명시적)
  python main.py --test-alert      # 알림 채널만 테스트 (사이트 접속 X)
  python main.py --config PATH     # 다른 설정 파일 사용

GitHub Actions cron으로 5분마다 호출되는 것을 전제로 함.
sleep/while 루프를 쓰지 않고 "한 번 실행" 모드로 동작.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime

from src.config import load_config, get_enabled_watchers
from src.crawlers import get_crawler
from src.notifiers import build_from_config
from src.notifiers.base import Priority
from src.scheduler import should_run_now, apply_human_pause
from src.state import StateManager


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def run_check(config: dict) -> int:
    """모든 활성 watcher 를 1회 체크. 반환값은 변경 감지된 항목 수."""
    advanced = config.get("advanced", {})
    state_mgr = StateManager(advanced.get("state_dir", "./data/state"))
    notifier = build_from_config(config)

    watchers = get_enabled_watchers(config)
    if not watchers:
        logging.warning("활성화된 watcher 가 없습니다. config.yaml 을 확인하세요.")
        return 0

    logging.info(f"=== 체크 시작: {len(watchers)}개 watcher ===")
    changes = 0

    for w in watchers:
        name = w["name"]
        wtype = w.get("type", "webpage")
        base_interval = w.get("interval_minutes")

        # 시간대별 스케줄: 지금 돌릴 차례인가?
        should_run, priority = should_run_now(name, state_mgr, base_interval)
        if not should_run:
            logging.info(f"[{name}] 스킵 (아직 간격 미충족)")
            continue

        logging.info(f"[{name}] 체크 중... (priority={priority.name})")

        try:
            crawler = get_crawler(w)
            result = crawler.check()
        except Exception as e:
            logging.exception(f"[{name}] 크롤러 실패: {e}")
            # 에러도 알림 (단, 같은 에러 반복 알림은 쿨다운으로 제한)
            if not state_mgr.in_cooldown(f"{name}::error", 60):
                notifier.send(
                    title="⚠️ 모니터링 오류",
                    message=f"{name} 체크 실패: {str(e)[:200]}",
                    priority=Priority.DEFAULT,
                )
                state_mgr.mark_alert_sent(f"{name}::error")
            continue

        raw = result.get("raw_data", "")
        items = result.get("items", [])
        click_url = result.get("click_url", "")

        # 변경 감지
        changed = state_mgr.has_changed(name, raw) if raw else False
        state_mgr.update_hash(name, raw)  # 항상 last_check 업데이트

        if not changed:
            logging.info(f"[{name}] 변경 없음")
            continue

        # 변경된 경우 → 알림 메시지 생성
        msg = None
        title = name

        # 크롤러가 자체 포맷터를 가지면 우선 사용
        if hasattr(crawler, "format_alert"):
            msg = crawler.format_alert(items)

        # 포맷터가 None 을 반환했다면 (예: 예약 불가만 변경된 경우) 알림 보내지 않음
        if not msg:
            logging.info(f"[{name}] 변경되었지만 알림 조건 미충족")
            continue

        # 쿨다운 (같은 watcher 의 알림이 너무 자주 반복되는 것 방지)
        cooldown = w.get("cooldown_minutes", config.get("advanced", {}).get("cooldown_minutes", 30))
        if state_mgr.in_cooldown(name, cooldown):
            logging.info(f"[{name}] 쿨다운 중 (마지막 알림 {cooldown}분 이내)")
            continue

        # 핵심 알림 전송!
        logging.info(f"[{name}] 🔔 변경 감지! 알림 전송")
        notifier.send(
            title=f"🎟 {title}",
            message=msg,
            priority=priority,
            click_url=click_url or None,
        )
        state_mgr.mark_alert_sent(name)
        changes += 1

        apply_human_pause()  # 다음 watcher 전 잠깐 쉬기

    logging.info(f"=== 체크 완료: 변경 감지 {changes}건 ===")
    return changes


def run_test_alert(config: dict) -> None:
    """알림 채널만 테스트 (사이트 접속 없음)"""
    notifier = build_from_config(config)
    if not notifier:
        logging.error("활성화된 알림 채널이 없습니다.")
        sys.exit(1)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results = notifier.send(
        title="🧪 ticket-notifier 테스트 알림",
        message=(
            f"이 메시지가 보이면 알림 채널이 정상 작동합니다.\n"
            f"시간: {now}\n"
            f"활성 채널: {', '.join(c.name for c in notifier.channels)}"
        ),
        priority=Priority.DEFAULT,
    )
    print("결과:", results)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ticket-notifier — 예매 오픈 감지 알림 봇"
    )
    parser.add_argument("--config", default=None, help="설정 파일 경로 (기본: config.yaml)")
    parser.add_argument("--check", action="store_true", help="1회 체크 실행 (기본 동작)")
    parser.add_argument("--test-alert", action="store_true", help="알림 채널만 테스트")
    args = parser.parse_args()

    config = load_config(args.config)
    setup_logging(config.get("advanced", {}).get("log_level", "INFO"))

    if args.test_alert:
        run_test_alert(config)
        return

    # 기본은 --check 와 동일
    changes = run_check(config)
    sys.exit(0 if changes >= 0 else 1)


if __name__ == "__main__":
    main()
