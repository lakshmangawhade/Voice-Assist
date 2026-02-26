"""
Time Normalization Layer
========================
Converts natural-language time expressions (voice-friendly) into canonical
datetime ranges that can be used directly in SQL WHERE clauses:

    AptDateTime >= :start_dt AND AptDateTime < :end_dt

Supports:
  - "today", "tomorrow", "yesterday"
  - "next Monday", "this Friday"
  - "morning", "afternoon", "evening", "after lunch"
  - "between 4 and 6", "from 9 to 11"
  - "in 2 hours", "in 30 minutes"
  - "next week", "this week"
  - Explicit dates: "April 30 2009", "2024-03-15"

Uses ``python-dateutil`` for robust relative-date parsing with fallback
heuristics for dental-scheduling vocabulary.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, time as dtime
from typing import Optional, Tuple

from dateutil import parser as dateutil_parser
from dateutil.relativedelta import relativedelta, MO, TU, WE, TH, FR, SA, SU

from app.config import DEFAULT_TIMEZONE

# ---------------------------------------------------------------------------
# Named time windows (half-open: [start, end) )
# ---------------------------------------------------------------------------
_TIME_WINDOWS: dict[str, Tuple[dtime, dtime]] = {
    # More-specific entries MUST come before their substrings so that the
    # first-match loop in _parse_natural_language picks the right window.
    "early_morning": (dtime(6, 0), dtime(9, 0)),
    "late_morning":  (dtime(10, 0), dtime(12, 0)),
    "morning":       (dtime(7, 0), dtime(12, 0)),
    "after_lunch":   (dtime(13, 0), dtime(17, 0)),
    "lunch":         (dtime(12, 0), dtime(13, 0)),
    "afternoon":     (dtime(12, 0), dtime(17, 0)),
    "evening":       (dtime(17, 0), dtime(21, 0)),
    "night":         (dtime(20, 0), dtime(23, 59)),
}

_DAY_MAP = {
    "monday": MO, "tuesday": TU, "wednesday": WE,
    "thursday": TH, "friday": FR, "saturday": SA, "sunday": SU,
    # abbreviations
    "mon": MO, "tue": TU, "tues": TU, "wed": WE,
    "thu": TH, "thur": TH, "thurs": TH,
    "fri": FR, "sat": SA, "sun": SU,
}


class TimeRange:
    """Immutable container for a resolved datetime range."""

    __slots__ = ("start_dt", "end_dt", "description")

    def __init__(self, start_dt: datetime, end_dt: datetime, description: str = ""):
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.description = description

    def __repr__(self) -> str:
        return (
            f"TimeRange(start={self.start_dt.isoformat()}, "
            f"end={self.end_dt.isoformat()}, desc='{self.description}')"
        )

    def to_sql_params(self) -> dict:
        """Return params dict suitable for parameterised SQL."""
        return {
            "start_dt": self.start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "end_dt":   self.end_dt.strftime("%Y-%m-%d %H:%M:%S"),
        }


def _now() -> datetime:
    """Return current local datetime (no tzinfo – matches MySQL DATETIME)."""
    return datetime.now()


def _start_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _end_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize_time(
    raw_text: str,
    slots: Optional[dict] = None,
    reference_dt: Optional[datetime] = None,
) -> Optional[TimeRange]:
    """
    Parse *raw_text* (and optional structured slots) into a canonical
    ``TimeRange``.

    Priority order:
      1. Explicit ``date`` or ``date_range`` slot  (ISO strings)
      2. Explicit ``time_window`` slot
      3. Natural-language heuristics on *raw_text*

    Parameters
    ----------
    raw_text : str
        Original user utterance (lowercased internally).
    slots : dict, optional
        Structured slots from the intent layer.
    reference_dt : datetime, optional
        Anchor "now"; defaults to ``datetime.now()``.

    Returns
    -------
    TimeRange or None
        ``None`` only when no temporal expression is detected at all.
    """
    now = reference_dt or _now()
    today_start = _start_of_day(now)
    text = raw_text.lower().strip()
    slots = slots or {}

    # ----- 1. Explicit slot: date_range ----------------------------------
    date_range = slots.get("date_range")
    if date_range and isinstance(date_range, dict):
        start_str = date_range.get("start")
        end_str = date_range.get("end")
        if start_str and end_str:
            try:
                s = dateutil_parser.parse(start_str)
                e = dateutil_parser.parse(end_str)
                # Ensure the end covers the full day (23:59:59)
                return TimeRange(
                    _start_of_day(s),
                    _end_of_day(e),
                    f"{start_str} to {end_str}",
                )
            except (ValueError, TypeError):
                pass

    # ----- 2. Explicit slot: date ----------------------------------------
    slot_date = slots.get("date")
    if slot_date:
        try:
            dt = dateutil_parser.parse(slot_date)
            return _apply_time_window(dt, slots, text, "on " + slot_date)
        except (ValueError, TypeError):
            pass

    # ----- 3. Natural-language parsing -----------------------------------
    return _parse_natural_language(text, now, today_start, slots)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _apply_time_window(
    base_date: datetime,
    slots: dict,
    text: str,
    desc: str,
) -> TimeRange:
    """
    Narrow a whole-day range to a time window if one is specified in
    *slots* (``time_window``) or detected in *text*.
    """
    tw = slots.get("time_window")
    if tw and isinstance(tw, dict):
        st = tw.get("start_time")
        et = tw.get("end_time")
        if st and et:
            try:
                sh, sm = map(int, st.split(":"))
                eh, em = map(int, et.split(":"))
                return TimeRange(
                    base_date.replace(hour=sh, minute=sm, second=0, microsecond=0),
                    base_date.replace(hour=eh, minute=em, second=0, microsecond=0),
                    desc,
                )
            except (ValueError, TypeError):
                pass

    # Try named windows from text
    for name, (ws, we) in _TIME_WINDOWS.items():
        if name.replace("_", " ") in text or name.replace("_", "") in text:
            return TimeRange(
                base_date.replace(hour=ws.hour, minute=ws.minute, second=0, microsecond=0),
                base_date.replace(hour=we.hour, minute=we.minute, second=0, microsecond=0),
                f"{desc} ({name})",
            )

    # Default: whole day
    return TimeRange(_start_of_day(base_date), _end_of_day(base_date), desc)


def _parse_natural_language(
    text: str,
    now: datetime,
    today_start: datetime,
    slots: dict,
) -> Optional[TimeRange]:
    """Heuristic NL parser for common scheduling phrases."""

    # -- "day after tomorrow" (must be tested BEFORE "tomorrow") --
    if "day after tomorrow" in text:
        dat = today_start + timedelta(days=2)
        return _apply_time_window(dat, slots, text, "day after tomorrow")

    # -- "today" --
    if re.search(r'\btoday\b', text):
        return _apply_time_window(today_start, slots, text, "today")

    # -- "tomorrow" --
    if re.search(r'\btomorrow\b', text):
        tmr = today_start + timedelta(days=1)
        return _apply_time_window(tmr, slots, text, "tomorrow")

    # -- "yesterday" --
    if re.search(r'\byesterday\b', text):
        yst = today_start - timedelta(days=1)
        return _apply_time_window(yst, slots, text, "yesterday")

    # -- "next <weekday>" / "this <weekday>" --
    for day_name, rd_day in _DAY_MAP.items():
        if re.search(rf'\bnext\s+{day_name}\b', text):
            target = now + relativedelta(weekday=rd_day(+2))  # +2 = next occurrence after this week
            return _apply_time_window(_start_of_day(target), slots, text, f"next {day_name}")
        if re.search(rf'\bthis\s+{day_name}\b', text):
            target = now + relativedelta(weekday=rd_day(+1))  # +1 = this week
            return _apply_time_window(_start_of_day(target), slots, text, f"this {day_name}")
        # bare weekday
        if re.search(rf'\bon\s+{day_name}\b', text) or re.search(rf'\b{day_name}\b', text):
            # Only match standalone weekday names (length > 3 to avoid false positives)
            if len(day_name) > 3 or re.search(rf'\bon\s+{day_name}\b', text):
                target = now + relativedelta(weekday=rd_day(+1))
                return _apply_time_window(_start_of_day(target), slots, text, day_name)

    # -- "this week" --
    if re.search(r'\bthis\s+week\b', text):
        # Monday through Friday of current week
        monday = today_start - timedelta(days=today_start.weekday())
        friday = monday + timedelta(days=4)
        return TimeRange(monday, _end_of_day(friday), "this week")

    # -- "next week" --
    if re.search(r'\bnext\s+week\b', text):
        monday = today_start - timedelta(days=today_start.weekday()) + timedelta(weeks=1)
        friday = monday + timedelta(days=4)
        return TimeRange(monday, _end_of_day(friday), "next week")

    # -- "in N hours / minutes" --
    m = re.search(r'\bin\s+(\d+)\s+(hour|minute|hr|min)s?\b', text)
    if m:
        amount = int(m.group(1))
        unit = m.group(2)
        if unit.startswith("hour") or unit.startswith("hr"):
            delta = timedelta(hours=amount)
        else:
            delta = timedelta(minutes=amount)
        start = now + delta
        end = start + timedelta(hours=1)
        return TimeRange(start, end, f"in {amount} {unit}(s)")

    # -- "between <H> and <H>" --
    m = re.search(r'\bbetween\s+(\d{1,2})\s*(?:and|to|-)\s*(\d{1,2})\b', text)
    if m:
        h1, h2 = int(m.group(1)), int(m.group(2))
        # Assume PM if values look like afternoon
        if h1 < 7:
            h1 += 12
        if h2 < 7:
            h2 += 12
        if h2 <= h1:
            h2 = h1 + 1
        base = today_start
        return TimeRange(
            base.replace(hour=h1, minute=0, second=0),
            base.replace(hour=h2, minute=0, second=0),
            f"between {h1}:00 and {h2}:00",
        )

    # -- "from <H> to <H>" --
    m = re.search(r'\bfrom\s+(\d{1,2})\s*(?:to|-)\s*(\d{1,2})\b', text)
    if m:
        h1, h2 = int(m.group(1)), int(m.group(2))
        if h1 < 7:
            h1 += 12
        if h2 < 7:
            h2 += 12
        if h2 <= h1:
            h2 = h1 + 1
        base = today_start
        return TimeRange(
            base.replace(hour=h1, minute=0, second=0),
            base.replace(hour=h2, minute=0, second=0),
            f"from {h1}:00 to {h2}:00",
        )

    # -- named time windows without explicit date → assume today --
    for name, (ws, we) in _TIME_WINDOWS.items():
        pattern = name.replace("_", r"[\s_]?")
        if re.search(rf'\b{pattern}\b', text):
            return TimeRange(
                today_start.replace(hour=ws.hour, minute=ws.minute),
                today_start.replace(hour=we.hour, minute=we.minute),
                f"today ({name})",
            )

    # -- Explicit numeric date formats (DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD, etc.) --
    # These are tried BEFORE the fuzzy parser so they get the right day-first
    # interpretation for formats like 31-12-2019 or 25/02/2026.
    date_match = re.search(
        r'\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b'   # DD-MM-YYYY or MM-DD-YYYY
        r'|'
        r'\b(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})\b',  # YYYY-MM-DD
        text,
    )
    if date_match:
        try:
            if date_match.group(1) is not None:
                # DD-MM-YYYY or MM-DD-YYYY – try day-first, then month-first
                raw_date_str = date_match.group(0)
                try:
                    parsed = dateutil_parser.parse(raw_date_str, dayfirst=True)
                except (ValueError, TypeError):
                    parsed = dateutil_parser.parse(raw_date_str, dayfirst=False)
            else:
                # YYYY-MM-DD
                raw_date_str = date_match.group(0)
                parsed = dateutil_parser.parse(raw_date_str)

            return _apply_time_window(
                _start_of_day(parsed), slots, text, parsed.strftime("%Y-%m-%d"),
            )
        except (ValueError, TypeError, OverflowError):
            pass

    # -- Fallback: try dateutil parser for explicit dates like "April 30 2009" --
    # Try dayfirst=True first (common outside the US), then dayfirst=False.
    for dayfirst in (True, False):
        try:
            parsed = dateutil_parser.parse(text, fuzzy=True, dayfirst=dayfirst)
            # Only accept if the parsed date differs from now (i.e., it found a real date)
            if parsed.date() != now.date() or "today" in text:
                return _apply_time_window(
                    _start_of_day(parsed), slots, text, parsed.strftime("%Y-%m-%d"),
                )
        except (ValueError, TypeError, OverflowError):
            continue

    return None

