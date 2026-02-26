"""
Unit tests for the time normaliser.

Run with:
    cd backend
    python -m pytest tests/test_time_normalizer.py -v
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ensure backend root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.time_normalizer import normalize_time, TimeRange


def _ref() -> datetime:
    """Fixed reference datetime for reproducible tests (Wednesday)."""
    return datetime(2025, 4, 30, 10, 30, 0)  # a Wednesday


class TestBasicDays:
    def test_today(self):
        tr = normalize_time("today", reference_dt=_ref())
        assert tr is not None
        assert tr.start_dt.date() == _ref().date()

    def test_tomorrow(self):
        tr = normalize_time("tomorrow", reference_dt=_ref())
        assert tr is not None
        assert tr.start_dt.date() == (_ref() + timedelta(days=1)).date()

    def test_yesterday(self):
        tr = normalize_time("yesterday", reference_dt=_ref())
        assert tr is not None
        assert tr.start_dt.date() == (_ref() - timedelta(days=1)).date()

    def test_day_after_tomorrow(self):
        tr = normalize_time("day after tomorrow", reference_dt=_ref())
        assert tr is not None
        assert tr.start_dt.date() == (_ref() + timedelta(days=2)).date()


class TestWeekday:
    def test_next_monday(self):
        tr = normalize_time("next Monday", reference_dt=_ref())
        assert tr is not None
        assert tr.start_dt.weekday() == 0  # Monday

    def test_this_friday(self):
        tr = normalize_time("this Friday", reference_dt=_ref())
        assert tr is not None
        assert tr.start_dt.weekday() == 4  # Friday


class TestTimeWindows:
    def test_tomorrow_morning(self):
        tr = normalize_time("tomorrow morning", reference_dt=_ref())
        assert tr is not None
        assert tr.start_dt.date() == (_ref() + timedelta(days=1)).date()
        assert tr.start_dt.hour == 7
        assert tr.end_dt.hour == 12

    def test_after_lunch(self):
        tr = normalize_time("after lunch", reference_dt=_ref())
        assert tr is not None
        assert tr.start_dt.hour == 13
        assert tr.end_dt.hour == 17

    def test_afternoon(self):
        tr = normalize_time("afternoon", reference_dt=_ref())
        assert tr is not None
        assert tr.start_dt.hour == 12

    def test_evening(self):
        tr = normalize_time("evening", reference_dt=_ref())
        assert tr is not None
        assert tr.start_dt.hour == 17


class TestBetweenAndFrom:
    def test_between_4_and_6(self):
        tr = normalize_time("between 4 and 6", reference_dt=_ref())
        assert tr is not None
        assert tr.start_dt.hour == 16  # 4 PM (adjusted)
        assert tr.end_dt.hour == 18

    def test_from_9_to_11(self):
        tr = normalize_time("from 9 to 11", reference_dt=_ref())
        assert tr is not None
        assert tr.start_dt.hour == 9
        assert tr.end_dt.hour == 11


class TestRelative:
    def test_in_2_hours(self):
        ref = _ref()
        tr = normalize_time("in 2 hours", reference_dt=ref)
        assert tr is not None
        assert tr.start_dt.hour == ref.hour + 2

    def test_this_week(self):
        tr = normalize_time("this week", reference_dt=_ref())
        assert tr is not None
        assert tr.start_dt.weekday() == 0  # Monday

    def test_next_week(self):
        ref = _ref()
        tr = normalize_time("next week", reference_dt=ref)
        assert tr is not None
        # Should start on next Monday
        assert tr.start_dt > ref


class TestExplicitDate:
    def test_explicit_date(self):
        tr = normalize_time("April 30 2009", reference_dt=_ref())
        assert tr is not None
        assert tr.start_dt.year == 2009
        assert tr.start_dt.month == 4
        assert tr.start_dt.day == 30

    def test_dd_mm_yyyy_numeric_date(self):
        tr = normalize_time("31-12-2019", reference_dt=_ref())
        assert tr is not None
        assert tr.start_dt.year == 2019
        assert tr.start_dt.month == 12
        assert tr.start_dt.day == 31


class TestSlots:
    def test_slot_date(self):
        tr = normalize_time("", slots={"date": "2024-03-15"}, reference_dt=_ref())
        assert tr is not None
        assert tr.start_dt.year == 2024
        assert tr.start_dt.month == 3

    def test_slot_date_range(self):
        tr = normalize_time(
            "",
            slots={
                "date_range": {"start": "2024-03-01", "end": "2024-03-07"}
            },
            reference_dt=_ref(),
        )
        assert tr is not None
        assert tr.start_dt.day == 1
        assert tr.end_dt.day == 7


class TestSqlParams:
    def test_to_sql_params(self):
        tr = normalize_time("tomorrow", reference_dt=_ref())
        assert tr is not None
        params = tr.to_sql_params()
        assert "start_dt" in params
        assert "end_dt" in params
        assert params["start_dt"].startswith("2025-05-01")


class TestNoMatch:
    def test_no_time_expression(self):
        tr = normalize_time("hello, how are you?", reference_dt=_ref())
        # This might or might not return None depending on fuzzy parser
        # The key is it doesn't crash
        assert tr is None or isinstance(tr, TimeRange)

