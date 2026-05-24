#!/usr/bin/env python3
"""
ticket-notifier — 메인 엔트리포인트

사용법:
  python main.py                   # 활성 watcher 1회 체크 → 알림 발송
  python main.py --check           # 동일 (명시적)
  python main.py --test-alert      # 알림 채널만 테스트 (사이트 접속 X)
  python main.py --heartbeat       # 강제 heartbeat 1회 발송 (테스트용)
  python main.py --config PATH     # 다른 설정 파일 사용

GitHub Actions cron 으로 5분마다 호출되는 것을 전제로 함.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime

from src.config import load_config, get_enabled_watchers
from src.crawlers import get_crawler
from src.heartbeat import maybe_send_heartbeat
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

    # ── 1) Daily heartbeat (조건 맞으면 1회 발송) ─────────
    if maybe_send_heartbeat(config, state_mgr, notifier):
        logging.info("heartbeat 발송 완료")

    # ── 2) 모니터링 ───────────────────────────────────────
    watchers = get_enabled_watchers(config)
    if not watchers:
        logging.warning("활성화된 watcher 가 없습니다. config.yaml 을 확인하세요.")
        return 0

    logging.info(f"=== 체크 시작: {len(watchers)}개 watcher ===")
    changes = 0

    for w in watchers:
        name = w["name"]
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

        changed = state_mgr.has_changed(name, raw) if raw else False
        state_mgr.update_hash(name, raw)

        if not changed:
            logging.info(f"[{name}] 변경 없음")
            continue

        msg = None
        if hasattr(crawler, "format_alert"):
            msg = crawler.format_alert(items)

        if not msg:
            logging.info(f"[{name}] 변경되었지만 알림 조건 미충족")
            continue

        cooldown = w.get("cooldown_minutes", config.get("advanced", {}).get("cooldown_minutes", 30))
        if state_mgr.in_cooldown(name, cooldown):
            logging.info(f"[{name}] 쿨다운 중 (마지막 알림 {cooldown}분 이내)")
            continue

        logging.info(f"[{name}] 🔔 변경 감지! 알림 전송")
        notifier.send(
            title=f"🎟 {name}",
            message=msg,
            priority=priority,
            click_url=click_url or None,
        )
        state_mgr.mark_alert_sent(name)
        changes += 1

        apply_human_pause()

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
    logging.info(f"테스트 결과: {results}")
    print("결과:", results)


def run_heartbeat(config: dict) -> None:
    """강제 heartbeat 발송 (테스트용 — 시각/날짜 조건 무시)"""
    advanced = config.get("advanced", {})
    state_mgr = StateManager(advanced.get("state_dir", "./data/state"))
    notifier = build_from_config(config)

    if not notifier:
        logging.error("활성화된 알림 채널이 없습니다.")
        sys.exit(1)

    # 강제로 last_date 비우고 재호출
    state_mgr.save("_heartbeat", {})
    # config.heartbeat.enabled 가 false 여도 강제 발송하려면 임시 활성화
    cfg2 = dict(config)
    hb = dict(cfg2.get("heartbeat", {}))
    hb["enabled"] = True
    hb["hour"] = 0
    hb["minute"] = 0
    cfg2["heartbeat"] = hb
    sent = maybe_send_heartbeat(cfg2, state_mgr, notifier)
    print(f"heartbeat 발송: {'성공' if sent else '실패'}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ticket-notifier — 예매 오픈 감지 알림 봇"
    )
    parser.add_argument("--config", default=None, help="설정 파일 경로 (기본: config.yaml)")
    parser.add_argument("--check", action="store_true", help="1회 체크 실행 (기본 동작)")
    parser.add_argument("--test-alert", action="store_true", help="알림 채널만 테스트")
    parser.add_argument("--heartbeat", action="store_true", help="강제 heartbeat 발송")
    args = parser.parse_args()

    config = load_config(args.config)
    setup_logging(config.get("advanced", {}).get("log_level", "INFO"))

    if args.test_alert:
        run_test_alert(config)
        return
    if args.heartbeat:
        run_heartbeat(config)
        return

    changes = run_check(config)
    sys.exit(0 if changes >= 0 else 1)


if __name__ == "__main__":
    main()
