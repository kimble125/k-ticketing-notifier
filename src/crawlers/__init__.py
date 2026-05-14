"""크롤러 모듈 — watcher type 에 따라 적절한 크롤러를 반환"""

from typing import Any


def get_crawler(watcher: dict) -> Any:
    """watcher type 에 맞는 크롤러 인스턴스 반환"""
    wtype = watcher.get("type", "webpage")
    settings = watcher.get("settings", {})

    if wtype == "mjff_lodging":
        from .mjff_lodging import MJFFLodgingCrawler
        return MJFFLodgingCrawler(settings)
    if wtype == "mjff_screening":
        from .mjff_screening import MJFFScreeningCrawler
        return MJFFScreeningCrawler(settings)
    if wtype == "webpage":
        from .webpage import WebpageCrawler
        return WebpageCrawler(settings)

    raise ValueError(f"알 수 없는 watcher type: {wtype}")
