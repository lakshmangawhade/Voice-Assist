"""
Unit tests for golden query templates.

Run with:
    cd backend
    python -m pytest tests/test_query_templates.py -v
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.query_templates import (
    build_count_appointments,
    build_list_appointments,
    build_provider_schedule,
    build_patient_upcoming,
    build_availability,
    build_patient_lookup,
    get_template,
)
from app.utils.time_normalizer import TimeRange


def _today_range() -> TimeRange:
    dt = datetime(2025, 4, 30, 0, 0, 0)
    return TimeRange(dt, dt.replace(hour=23, minute=59, second=59), "today")


class TestCountAppointments:
    def test_basic(self):
        sql, params = build_count_appointments({}, _today_range())
        assert "COUNT(*)" in sql
        assert "appointment" in sql.lower()
        assert len(params) >= 2  # start_dt, end_dt

    def test_with_provider(self):
        slots = {"provider": {"name": None, "id": "5"}}
        sql, params = build_count_appointments(slots, _today_range())
        assert "ProvNum" in sql
        assert 5 in params

    def test_with_status(self):
        slots = {"status": "scheduled"}
        sql, params = build_count_appointments(slots, _today_range())
        assert "AptStatus" in sql


class TestListAppointments:
    def test_has_limit(self):
        sql, params = build_list_appointments({}, _today_range())
        assert "LIMIT" in sql
        assert params[-1] == 20  # DEFAULT_RESULT_LIMIT

    def test_has_patient_name(self):
        sql, _ = build_list_appointments({}, _today_range())
        assert "PatientName" in sql

    def test_ordered_by_datetime(self):
        sql, _ = build_list_appointments({}, _today_range())
        assert "ORDER BY" in sql
        assert "AptDateTime" in sql


class TestProviderSchedule:
    def test_with_provider_name(self):
        slots = {"provider": {"name": "Smith", "id": None}}
        sql, params = build_provider_schedule(slots, _today_range())
        assert "LIKE" in sql
        assert any("%Smith%" in str(p) for p in params)


class TestPatientUpcoming:
    def test_with_patient_id(self):
        slots = {"patient": {"name": None, "id": "123"}}
        sql, params = build_patient_upcoming(slots)
        assert "PatNum" in sql
        assert 123 in params

    def test_with_patient_name(self):
        slots = {"patient": {"name": "John Doe", "id": None}}
        sql, params = build_patient_upcoming(slots)
        assert "FName" in sql
        assert "LName" in sql

    def test_defaults_to_future(self):
        slots = {"patient": {"name": "Test", "id": None}}
        sql, params = build_patient_upcoming(slots, time_range=None)
        assert "AptDateTime" in sql  # should have a >= now filter


class TestAvailability:
    def test_only_active_statuses(self):
        slots = {"provider": {"name": None, "id": "1"}}
        sql, _ = build_availability(slots, _today_range())
        assert "AptStatus" in sql
        assert "IN (1, 4)" in sql


class TestPatientLookup:
    def test_by_name(self):
        slots = {"patient": {"name": "Jane Smith", "id": None}}
        sql, params = build_patient_lookup(slots)
        assert "FName" in sql
        assert "LName" in sql
        assert any("Jane" in str(p) for p in params)

    def test_by_id(self):
        slots = {"patient": {"name": None, "id": "42"}}
        sql, params = build_patient_lookup(slots)
        assert "PatNum" in sql
        assert 42 in params


class TestTemplateRegistry:
    def test_count_registered(self):
        fn = get_template("COUNT_APPOINTMENTS")
        assert fn is not None

    def test_unknown_returns_none(self):
        fn = get_template("NONEXISTENT_INTENT")
        assert fn is None

    def test_all_intents_registered(self):
        for intent in [
            "COUNT_APPOINTMENTS", "LIST_APPOINTMENTS",
            "PROVIDER_SCHEDULE", "PATIENT_UPCOMING",
            "AVAILABILITY", "PATIENT_LOOKUP",
        ]:
            assert get_template(intent) is not None, f"{intent} not registered"


class TestSQLSafety:
    """Ensure template output is safe."""

    def test_no_select_star(self):
        for intent in [
            "COUNT_APPOINTMENTS", "LIST_APPOINTMENTS",
            "PROVIDER_SCHEDULE", "PATIENT_UPCOMING",
            "AVAILABILITY", "PATIENT_LOOKUP",
        ]:
            fn = get_template(intent)
            sql, _ = fn({}, _today_range())
            # SELECT * should not appear (COUNT(*) is OK)
            lines = sql.split("\n")
            for line in lines:
                stripped = line.strip().upper()
                if stripped.startswith("SELECT") and "COUNT(*)" not in stripped:
                    assert "SELECT *" not in stripped, f"{intent} uses SELECT *"

    def test_always_has_limit(self):
        for intent in [
            "LIST_APPOINTMENTS", "PROVIDER_SCHEDULE",
            "PATIENT_UPCOMING", "AVAILABILITY", "PATIENT_LOOKUP",
        ]:
            fn = get_template(intent)
            sql, _ = fn({}, _today_range())
            assert "LIMIT" in sql.upper(), f"{intent} missing LIMIT"

