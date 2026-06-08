"""크롤러 모듈 — watcher type 에 따라 적절한 크롤러를 반환"""

from typing import Any


def get_crawler(watcher: dict) -> Any:
    wtype = watcher.get("type", "webpage")
    settings = watcher.get("settings", {})

    if wtype == "mjff_lodging":
        from .mjff_lodging import MJFFLodgingCrawler
        return MJFFLodgingCrawler(settings)
    if wtype == "mjff_screening":
        from .mjff_screening import MJFFScreeningCrawler
        return MJFFScreeningCrawler(settings)
    if wtype == "mjff_stadium":
        from .mjff_stadium import MJFFStadiumCrawler
        return MJFFStadiumCrawler(settings)
    if wtype == "firefly":
        from .firefly import FireflyCrawler
        return FireflyCrawler(settings)
    if wtype == "seoul_outdoor_library":
        from .seoul_outdoor_library import SeoulOutdoorLibraryCrawler
        return SeoulOutdoorLibraryCrawler(settings)
    if wtype == "webpage":
        from .webpage import WebpageCrawler
        return WebpageCrawler(settings)

    raise ValueError(
        f"알 수 없는 watcher type: {wtype}. "
        f"지원: mjff_lodging, mjff_screening, mjff_stadium, firefly, "
        f"seoul_outdoor_library, webpage"
    )
