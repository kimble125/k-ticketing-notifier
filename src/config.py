"""
설정 로더 — YAML + .env 통합

우선순위 (높은 → 낮은):
  1. 환경변수 (Docker / GitHub Actions Secrets)
  2. .env 파일 (로컬 개발)
  3. config.yaml 파일 (구조적 설정)
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

import yaml

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = ROOT / "config.yaml"
EXAMPLE_CONFIG_PATH = ROOT / "config.example.yaml"
ENV_FILE = ROOT / ".env"


def _load_env() -> None:
    """.env 파일이 있으면 로드 (없어도 무시 — CI/CD 환경 지원)"""
    if load_dotenv and ENV_FILE.exists():
        load_dotenv(ENV_FILE)
        logger.debug(f".env 로드 완료: {ENV_FILE}")


def _interpolate_env(value: Any) -> Any:
    """
    문자열 값에 ${VAR_NAME} 패턴이 있으면 환경변수로 치환.
    예: "${MJFF_NAME}" → os.environ["MJFF_NAME"]
    """
    if isinstance(value, str):
        result = value
        # ${VAR} 와 ${VAR:default} 패턴 둘 다 지원
        import re

        def replacer(match: "re.Match[str]") -> str:
            expr = match.group(1)
            if ":" in expr:
                key, default = expr.split(":", 1)
                return os.environ.get(key.strip(), default)
            return os.environ.get(expr.strip(), "")

        result = re.sub(r"\$\{([^}]+)\}", replacer, result)
        return result
    if isinstance(value, dict):
        return {k: _interpolate_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_interpolate_env(v) for v in value]
    return value


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """YAML 설정 파일을 로드. 없으면 example로 자동 대체 시도."""
    _load_env()

    config_path = Path(
        path or os.environ.get("CONFIG_PATH", str(DEFAULT_CONFIG_PATH))
    )

    if not config_path.exists():
        # GitHub Actions나 CI에서 config.yaml 없이 .env+example 만으로 동작 허용
        if EXAMPLE_CONFIG_PATH.exists():
            logger.warning(
                f"{config_path} 가 없어 {EXAMPLE_CONFIG_PATH.name} 으로 대체합니다. "
                f"환경변수로 비밀값을 덮어쓰는지 확인하세요."
            )
            config_path = EXAMPLE_CONFIG_PATH
        else:
            logger.error(
                f"설정 파일을 찾을 수 없습니다: {config_path}\n"
                f"  cp config.example.yaml config.yaml 후 본인 정보로 수정하세요."
            )
            sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    # ${VAR} 치환
    config = _interpolate_env(raw)
    _validate(config)
    return config


def _validate(config: dict) -> None:
    """필수 키 존재 확인 + 친절한 에러 메시지"""
    watchers = config.get("watchers", [])
    if not watchers:
        logger.warning("watchers 가 비어있습니다. config.yaml 에 모니터링 대상을 추가하세요.")

    # 최소 하나의 알림 채널이 활성화돼야 함
    notifiers = config.get("notifiers", {})
    enabled = [k for k, v in notifiers.items() if isinstance(v, dict) and v.get("enabled")]
    if not enabled:
        logger.warning(
            "활성화된 알림 채널이 없습니다. "
            "config.yaml 의 notifiers 섹션에서 최소 하나는 enabled: true 로 설정하세요."
        )

    for i, w in enumerate(watchers):
        if "name" not in w:
            logger.error(f"watcher[{i}] 에 name 이 없습니다.")
            sys.exit(1)
        if "type" not in w:
            logger.error(f"watcher[{i}] '{w.get('name', '?')}' 에 type 이 없습니다.")
            sys.exit(1)


def get_enabled_watchers(config: dict) -> list[dict]:
    """활성화된 watcher 목록만 반환"""
    return [w for w in config.get("watchers", []) if w.get("enabled", True)]
