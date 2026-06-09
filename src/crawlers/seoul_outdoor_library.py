"""
서울야외도서관(힙독클럽) 프로그램 상태 감시 크롤러

■ 실제 페이지 분석 결과 (2026-06-09, 화면 직접 확인 + 호연님 확인)
  - JS 렌더링(SPA 성격) → requests 만으로는 본문이 비어 옴 → **Playwright 필수**
  - 프로그램은 카드 그리드 + **페이지네이션(1·2·3·4…)**
  - 각 카드는 **두 가지 상태 신호**를 동시에 노출한다:

    (A) 상태 배지 (카드 썸네일 우상단의 짧은 라벨)
        가능한 값: 정원 마감 / 신청 예정 / 신청중 / 대기 신청 중 / 신청 마감 / 종료
        ★ 호연님이 노리는 핵심 전이:  정원 마감·신청 예정  →  신청중

    (B) 모집 정원 숫자 (현재 신청자 수 / 총 정원)
        예) 200 / 200 (= 정원 마감),  183 / 200 (= 빈자리 17)
        ★ 취소표 포착:  200/200  →  199/200  (배지가 늦게 바뀌어도 숫자는 먼저 움직임)

  - 고정 한글 라벨: 행사 일시 / 신청 기간 / 모집 정원

■ 감지 전략 (기본: 두 신호 모두 = 가장 안전)
  - raw_data 스냅샷에 (상태 배지 + 현재/총) 를 함께 담아 hash → 상태·숫자 어떤 변화든 감지
  - 알림 트리거(설정 가능, 기본 둘 다):
      "status_open" : 상태가 신청중/대기 신청 중 등 '신청 가능' 상태로 바뀜  (의미적으로 정확)
      "spot_freed"  : 현재 < 총  (취소표/빈자리 — 배지가 늦어도 잡음; 종료·신청 마감은 제외)
  - 둘 중 하나만 쓰고 싶으면 config 의 settings.alert_triggers 로 조절

■ 클래스명 비의존 파싱
  - 카드 컨테이너 클래스가 아니라 **고정 한글 라벨의 순서 관계**로 파싱.
  - 카드 기준점 = "행사 일시" (모든 카드에 1개). 그 앞줄=제목, 그 위=상태 배지,
    뒤쪽=신청 기간/모집 정원. 라벨/값이 줄이 갈려도 앞쪽으로 탐색해 안전하게 수집.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_URL = (
    "https://seouloutdoorlibrary.kr/user/program/"
    "selectPageListProgram.do?area_id=hipdok&flag=program_list"
)

# 사이트의 상태 배지 값들 (호연님 확인). 공백 무시하고 매칭.
KNOWN_STATUSES = ["정원 마감", "신청 예정", "대기 신청 중", "신청중", "신청 마감", "종료"]
# '신청 가능' 으로 간주하는 상태 (status_open 트리거)
DEFAULT_OPEN_STATUSES = ["신청중", "대기 신청 중"]
# 빈자리가 생겨도 신청 불가/무의미한 상태 (spot_freed 트리거에서 제외)
#  - 종료/신청 마감: 이미 끝남,  신청 예정: 아직 신청 시작 전(→신청중 전이는 status_open이 잡음)
DEFAULT_CLOSED_STATUSES = ["종료", "신청 마감", "신청 예정"]

# 제목으로 오인하면 안 되는 '태그/배지' 류 토큰 (제목 탐색 시 건너뜀)
_TAG_TOKENS = (
    "무료", "유료", "전용 프로그램", "적립대상", "활동후기", "주제 도서", "강독",
)

_LABEL_EVENT = ("행사 일시", "행사일시")
_LABEL_PERIOD = ("신청 기간", "신청기간")
_LABEL_QUOTA = ("모집 정원", "모집정원")


def _nospace(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


def _norm(s: str) -> str:
    """제목 비교용 정규화: 유니코드 정규화(③→3 등) + 공백/문장부호 제거 + 소문자."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    circled = {"①": "1", "②": "2", "③": "3", "④": "4", "⑤": "5",
               "⑥": "6", "⑦": "7", "⑧": "8", "⑨": "9", "⑩": "10"}
    for k, v in circled.items():
        s = s.replace(k, v)
    s = s.lower()
    s = re.sub(r"[\s\W_]+", "", s, flags=re.UNICODE)
    return s


class SeoulOutdoorLibraryCrawler:
    """힙독클럽 프로그램 목록 감시 (상태 배지 + 모집정원 숫자 병행)"""

    def __init__(self, settings: dict):
        self.target_url = settings.get("target_url", DEFAULT_URL)
        self.headless = bool(settings.get("headless", True))
        self.use_playwright = bool(settings.get("use_playwright", True))
        self.max_pages = int(settings.get("max_pages", 10))
        self.nav_timeout_ms = int(settings.get("nav_timeout_ms", 30000))
        self.targets: list[dict] = settings.get("targets", [])
        # 알림 트리거: 기본 둘 다. ["status_open"], ["spot_freed"], 또는 둘 다.
        self.alert_triggers = list(settings.get("alert_triggers", ["status_open", "spot_freed"]))
        self.open_statuses = list(settings.get("open_statuses", DEFAULT_OPEN_STATUSES))
        self.closed_statuses = list(settings.get("closed_statuses", DEFAULT_CLOSED_STATUSES))
        # ── 사전 알림(리드타임 리마인더) + 신규 프로그램 감지 ──
        self.reminders_enabled = bool(settings.get("reminders_enabled", True))
        self.detect_new_programs = bool(settings.get("detect_new_programs", True))
        # 신청 시작 몇 분 전에 알릴지 (기본 1일=1440 / 1시간=60 / 10분)
        self.reminder_offsets_minutes = list(settings.get("reminder_offsets_minutes", [1440, 60, 10]))
        # 리마인더 대상: "all"(모든 힙독클럽 프로그램) 또는 "targets"(내 지정 목록만)
        self.reminder_scope = settings.get("reminder_scope", "all")
        self.state_dir = settings.get("state_dir", "./data/state")

    # ──────────────────────────────────────────────────────────
    #  엔트리포인트
    # ──────────────────────────────────────────────────────────
    def check(self) -> dict:
        htmls = self._fetch_all_pages()
        if not htmls:
            logger.warning("[seoul_lib] 페이지를 가져오지 못함")
            return {"items": [], "raw_data": "", "click_url": self.target_url}

        found: dict[str, dict] = {}
        for html in htmls:
            for rec in self._extract(html):
                key = _norm(rec["name_raw"])
                if key and key not in found:
                    found[key] = rec

        logger.info(f"[seoul_lib] 전체 {len(found)}개 프로그램 발견 (대상 {len(self.targets)}개와 매칭)")

        items = self._match_targets(list(found.values()))

        for it in items:
            if it["found"]:
                logger.info(
                    f"[seoul_lib] ✓ '{it['name'][:26]}' → 상태='{it['status'] or '?'}' "
                    f"정원={it['current']}/{it['total']} "
                    f"{'[알림대상]' if it['alert'] else ''}"
                )
            else:
                logger.warning(f"[seoul_lib] ✗ 대상 미발견: '{it['name'][:40]}'")

        extra = self._compute_extra_alerts(found, items)
        if extra:
            logger.info(f"[seoul_lib] 추가 알림 {len(extra)}건 (신규/사전 리마인더)")

        return {
            "items": items,
            "raw_data": self._raw_snapshot(items),
            "click_url": self.target_url,
            "extra_alerts": extra,
        }

    # ──────────────────────────────────────────────────────────
    #  페이지 가져오기 (페이지네이션 포함)
    # ──────────────────────────────────────────────────────────
    def _fetch_all_pages(self) -> list[str]:
        if self.use_playwright:
            htmls = self._fetch_with_playwright()
            if htmls:
                return htmls
            logger.warning("[seoul_lib] playwright 실패 → requests 폴백")
        html = self._fetch_with_requests()
        return [html] if html else []

    def _fetch_with_requests(self) -> Optional[str]:
        import requests
        try:
            resp = requests.get(
                self.target_url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                    ),
                    "Accept-Language": "ko-KR,ko;q=0.9",
                },
                timeout=15,
            )
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            logger.error(f"[seoul_lib] requests 실패: {e}")
            return None

    def _fetch_with_playwright(self) -> list[str]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("[seoul_lib] playwright 미설치")
            return []

        htmls: list[str] = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            try:
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                    ),
                    locale="ko-KR",
                )
                page = context.new_page()
                page.set_default_timeout(self.nav_timeout_ms)
                page.goto(self.target_url, wait_until="networkidle")
                self._wait_for_cards(page)
                htmls.append(page.content())
                for pageno in range(2, self.max_pages + 1):
                    if not self._goto_page_number(page, pageno):
                        break
                    self._wait_for_cards(page)
                    htmls.append(page.content())
                return htmls
            except Exception as e:
                logger.exception(f"[seoul_lib] playwright 실패: {e}")
                return htmls
            finally:
                browser.close()

    def _wait_for_cards(self, page) -> None:
        try:
            page.wait_for_function(
                "() => document.body && document.body.innerText.includes('모집 정원')",
                timeout=self.nav_timeout_ms,
            )
        except Exception:
            logger.debug("[seoul_lib] '모집 정원' 대기 타임아웃 (그래도 진행)")

    def _goto_page_number(self, page, pageno: int) -> bool:
        before = page.content()
        selectors = [
            f"xpath=//a[normalize-space(.)='{pageno}']",
            f"xpath=//button[normalize-space(.)='{pageno}']",
            f"xpath=//*[@onclick and normalize-space(.)='{pageno}']",
        ]
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if loc.count() == 0:
                    continue
                loc.click(timeout=5000)
                page.wait_for_load_state("networkidle", timeout=self.nav_timeout_ms)
                if page.content() != before:
                    return True
            except Exception:
                continue
        return False

    # ──────────────────────────────────────────────────────────
    #  파싱 (행사 일시 기준 카드 분할 — 라벨/값 줄 분리에도 안전)
    # ──────────────────────────────────────────────────────────
    def _extract(self, html: str) -> list[dict]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        lines = [ln.strip() for ln in soup.get_text("\n", strip=True).split("\n") if ln.strip()]

        event_idxs = [i for i, ln in enumerate(lines)
                      if any(lab in ln for lab in _LABEL_EVENT)]
        records: list[dict] = []
        for k, e in enumerate(event_idxs):
            start = (event_idxs[k - 1] + 1) if k > 0 else 0
            end = event_idxs[k + 1] if k + 1 < len(event_idxs) else len(lines)
            title = self._title_before(lines, e, start)
            quota = self._grab_quota(lines, e, end)
            if not (title and quota):
                continue
            cur, tot = quota
            records.append({
                "name_raw": title,
                "current": cur,
                "total": tot,
                "period": self._grab_period(lines, e, end),
                "status": self._find_status(lines, start, e),
            })
        return records

    @staticmethod
    def _title_before(lines: list[str], event_idx: int, low: int) -> Optional[str]:
        j = event_idx - 1
        while j >= low:
            cand = lines[j]
            if any(tok in cand for tok in _TAG_TOKENS) or len(cand) < 3 \
               or any(lab in cand for lab in _LABEL_EVENT + _LABEL_PERIOD + _LABEL_QUOTA) \
               or _nospace(cand) in {_nospace(s) for s in KNOWN_STATUSES}:
                j -= 1
                continue
            return cand
        return None

    @staticmethod
    def _find_status(lines: list[str], low: int, high: int) -> Optional[str]:
        """카드 상단(제목 위) 구간에서 상태 배지 라벨을 찾음. 가장 가까운 것."""
        norm_map = {_nospace(s): s for s in KNOWN_STATUSES}
        result = None
        for i in range(low, high):
            ln = lines[i]
            if len(ln) > 12:
                continue
            key = _nospace(ln)
            if key in norm_map:
                result = norm_map[key]  # 마지막(=제목에 가장 가까운) 것 채택
        return result

    @staticmethod
    def _grab_period(lines: list[str], lo: int, hi: int) -> Optional[str]:
        for i in range(lo, hi):
            if any(lab in lines[i] for lab in _LABEL_PERIOD):
                blob = " ".join(lines[i:i + 3])
                m = re.search(r"(\d{4}\.\d{1,2}\.\d{1,2}.*?~.*?\d{1,2}:\d{2})", blob)
                if m:
                    return re.sub(r"\s+", " ", m.group(1)).strip()
        return None

    @staticmethod
    def _grab_quota(lines: list[str], lo: int, hi: int) -> Optional[tuple[int, int]]:
        """[lo,hi) 안에서 모집 정원 (현재/총). 라벨과 값이 다른 줄이어도 OK."""
        for i in range(lo, hi):
            if any(lab in lines[i] for lab in _LABEL_QUOTA):
                blob = " ".join(lines[i:i + 4])
                m = re.search(r"모집\s*정원\D*?(\d[\d,]*)\s*/\s*(\d[\d,]*)", blob)
                if not m:
                    m = re.search(r"(\d[\d,]*)\s*/\s*(\d[\d,]*)", blob)
                if m:
                    try:
                        return int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))
                    except ValueError:
                        return None
        return None

    # ──────────────────────────────────────────────────────────
    #  대상 매칭 / 트리거 판정 / 스냅샷 / 알림
    # ──────────────────────────────────────────────────────────
    def _is_alert(self, status: Optional[str], cur: Optional[int], tot: Optional[int]) -> tuple[bool, list[str]]:
        reasons = []
        if "status_open" in self.alert_triggers and status and status in self.open_statuses:
            reasons.append(f"상태='{status}'")
        if "spot_freed" in self.alert_triggers and cur is not None and tot is not None \
           and cur < tot and (status not in self.closed_statuses):
            reasons.append(f"빈자리 {tot - cur}")
        return (len(reasons) > 0), reasons

    def _match_targets(self, records: list[dict]) -> list[dict]:
        items: list[dict] = []
        for target in self.targets:
            name = target["name"]
            # 'match' 가 있으면 그 문자열로 매칭(한자·긴 제목 회피용). 없으면 name 사용.
            nt = _norm(target.get("match") or name)
            match = next((r for r in records if nt and (nt in _norm(r["name_raw"]) or _norm(r["name_raw"]) in nt)), None)
            if match:
                cur, tot = match["current"], match["total"]
                alert, reasons = self._is_alert(match.get("status"), cur, tot)
                items.append({
                    "name": name, "found": True,
                    "status": match.get("status"),
                    "current": cur, "total": tot,
                    "remaining": max(tot - cur, 0) if (cur is not None and tot is not None) else None,
                    "alert": alert, "reasons": reasons,
                    "period": match.get("period"),
                    "matched_title": match["name_raw"],
                })
            else:
                items.append({
                    "name": name, "found": False, "status": None,
                    "current": None, "total": None, "remaining": None,
                    "alert": False, "reasons": [], "period": None, "matched_title": None,
                })
        return items

    @staticmethod
    def _raw_snapshot(items: list[dict]) -> str:
        """변경 감지용 안정 스냅샷: 상태 배지 + 현재/총 (둘 중 무엇이 바뀌어도 감지)."""
        parts = []
        for it in items:
            if it["found"]:
                parts.append(f"{it['name']}|{it.get('status') or '-'}|{it['current']}/{it['total']}")
            else:
                parts.append(f"{it['name']}|MISSING")
        return "\n".join(parts)

    # ──────────────────────────────────────────────────────────
    #  추가 알림: 신규 프로그램 감지 + 신청 시작 사전 리마인더
    # ──────────────────────────────────────────────────────────
    def _compute_extra_alerts(self, found: dict, items: list[dict]) -> list[dict]:
        if not (self.reminders_enabled or self.detect_new_programs):
            return []
        from datetime import datetime, timedelta
        try:
            from ..state import StateManager
        except Exception:
            return []
        sm = StateManager(self.state_dir)
        now = datetime.now()
        alerts: list[dict] = []

        # 리마인더 대상 레코드
        if self.reminder_scope == "targets":
            wanted = {_norm(it["matched_title"]) for it in items if it.get("found")}
            recs = [r for r in found.values() if _norm(r["name_raw"]) in wanted]
        else:
            recs = list(found.values())

        # (1) 신규 프로그램 감지 (첫 실행은 베이스라인만 저장 → 폭주 방지)
        if self.detect_new_programs:
            seen = set(sm.get("_hipdok_seen").get("titles", []))
            current = {_norm(r["name_raw"]) for r in found.values()}
            if not seen:
                sm.save("_hipdok_seen", {"titles": sorted(current)})
            else:
                new_keys = current - seen
                for r in found.values():
                    if _norm(r["name_raw"]) in new_keys:
                        alerts.append({
                            "title": "🆕 힙독클럽 새 프로그램",
                            "message": self._new_prog_message(r),
                            "priority": "high",
                        })
                if new_keys:
                    sm.save("_hipdok_seen", {"titles": sorted(seen | current)})

        # (2) 신청 시작 사전 리마인더 (각 임계값 1회만)
        if self.reminders_enabled:
            for r in recs:
                start = self._parse_start_dt(r.get("period"))
                if not start or now >= start:
                    continue
                for off in self.reminder_offsets_minutes:
                    fire_from = start - timedelta(minutes=off)
                    if not (fire_from <= now < start):
                        continue
                    key = f"_remind::{_norm(r['name_raw'])}::{off}"
                    if sm.get(key).get("sent"):
                        continue
                    alerts.append({
                        "title": f"⏰ 신청 {self._fmt_offset(off)} 전 — {r['name_raw'][:24]}",
                        "message": self._reminder_message(r, off, start),
                        "priority": "urgent" if off <= 10 else "high",
                    })
                    sm.save(key, {"sent": True, "at": now.isoformat(timespec="seconds")})
        return alerts

    @staticmethod
    def _parse_start_dt(period):
        if not period:
            return None
        m = re.search(r"(\d{4})\.(\d{1,2})\.(\d{1,2})\s+(\d{1,2}):(\d{2})", period)
        if not m:
            return None
        from datetime import datetime
        y, mo, d, h, mi = map(int, m.groups())
        try:
            return datetime(y, mo, d, h, mi)
        except ValueError:
            return None

    @staticmethod
    def _fmt_offset(minutes: int) -> str:
        if minutes % 1440 == 0:
            return f"{minutes // 1440}일"
        if minutes % 60 == 0:
            return f"{minutes // 60}시간"
        return f"{minutes}분"

    def _reminder_message(self, r: dict, off: int, start) -> str:
        return (
            f"📚 {r['name_raw'][:50]}\n"
            f"신청 시작: {start.strftime('%m/%d %H:%M')} ({self._fmt_offset(off)} 후)\n"
            f"신청기간: {r.get('period') or '?'}\n"
            f"모집정원: {r['current']}/{r['total']}  상태: {r.get('status') or '?'}\n"
            f"👉 시작 시간에 바로 신청 준비!"
        )

    def _new_prog_message(self, r: dict) -> str:
        return (
            f"📚 {r['name_raw'][:50]}\n"
            f"신청기간: {r.get('period') or '?'}\n"
            f"모집정원: {r['current']}/{r['total']}  상태: {r.get('status') or '?'}\n"
            f"👉 힙독클럽에 새 프로그램이 올라왔어요!"
        )

    def format_alert(self, items: list[dict]) -> Optional[str]:
        hot = [i for i in items if i.get("alert")]
        if not hot:
            return None
        lines = ["📚 힙독클럽 — 신청 가능/빈자리 감지!"]
        for it in hot:
            tag = " · ".join(it["reasons"])
            seat = f"{it['current']}/{it['total']}" if it["current"] is not None else "?"
            lines.append(f"  • {it['name'][:44]}")
            lines.append(f"     {tag}  (모집 {seat}, 상태 {it.get('status') or '?'})")
            if it.get("period"):
                lines.append(f"     신청기간: {it['period']}")
        lines.append("\n👉 지금 신청 페이지로!")
        return "\n".join(lines)
