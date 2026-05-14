"""
상태 관리 — 각 watcher의 이전 상태를 저장/비교하여 변경을 감지.

같은 알림이 5분마다 반복되지 않도록 해시 비교 + 쿨다운을 둠.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StateManager:
    """파일 기반 상태 관리자 (JSON)"""

    def __init__(self, state_dir: str | Path = "./data/state"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        return self.state_dir / f"{safe}.json"

    def get(self, name: str) -> dict[str, Any]:
        p = self._path(name)
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"상태 파일 읽기 실패 ({name}): {e}")
        return {}

    def save(self, name: str, state: dict[str, Any]) -> None:
        try:
            self._path(name).write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except IOError as e:
            logger.error(f"상태 파일 저장 실패 ({name}): {e}")

    # ── 해시 기반 변경 감지 ──────────────────────────────

    @staticmethod
    def hash_of(data: Any) -> str:
        content = data if isinstance(data, str) else json.dumps(
            data, sort_keys=True, ensure_ascii=False
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def has_changed(self, name: str, new_data: Any) -> bool:
        old = self.get(name).get("hash", "")
        return old != self.hash_of(new_data)

    def update_hash(self, name: str, data: Any, extra: dict | None = None) -> None:
        s = self.get(name)
        s["hash"] = self.hash_of(data)
        s["last_check"] = datetime.now().isoformat(timespec="seconds")
        if extra:
            s.update(extra)
        self.save(name, s)

    # ── 쿨다운 (중복 알림 방지) ──────────────────────────

    def in_cooldown(self, name: str, minutes: int) -> bool:
        """직전 알림 시각으로부터 minutes 이내라면 True (=쏘지 말 것)"""
        last = self.get(name).get("last_alert", "")
        if not last:
            return False
        try:
            last_dt = datetime.fromisoformat(last)
        except ValueError:
            return False
        return datetime.now() - last_dt < timedelta(minutes=minutes)

    def mark_alert_sent(self, name: str) -> None:
        s = self.get(name)
        s["last_alert"] = datetime.now().isoformat(timespec="seconds")
        self.save(name, s)
