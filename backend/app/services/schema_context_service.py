"""
Schema Context Service
======================
Provides compact, relevant schema context to the LLM for SQL generation.

Primary source: ``schema_descriptions.FIELD_DESCRIPTIONS`` (auto-generated
from the SQL dump via ``generate_schema_docs.py``).

Fallback: live introspection via ``DatabaseService.get_table_schema()``.

The service selects only the 2-6 most relevant tables for a given query,
keeping the context window small and focused.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from app.config import SCHEDULING_TABLES

# Import the auto-generated schema docs
try:
    from app.services.schema_descriptions import FIELD_DESCRIPTIONS
except ImportError:
    FIELD_DESCRIPTIONS: dict = {}


# ---------------------------------------------------------------------------
# Keyword-to-table relevance mapping
# ---------------------------------------------------------------------------
_TABLE_KEYWORDS: dict[str, list[str]] = {
    "appointment":     ["appointment", "schedule", "booking", "apt", "visit"],
    "patient":         ["patient", "person", "name", "client", "demographics"],
    "provider":        ["provider", "doctor", "dentist", "hygienist", "dr"],
    "operatory":       ["operatory", "room", "chair", "op"],
    "appointmenttype": ["appointment type", "type", "category"],
    "clinic":          ["clinic", "location", "office", "site"],
    "procedurelog":    ["procedure log", "procedure", "treatment", "completed"],
    "procedurecode":   ["procedure code", "ada code", "cdt code", "code"],
    "schedule":        ["schedule", "block", "blockout", "time block"],
    "scheduleop":      ["schedule op", "schedule operatory"],
    "claim":           ["claim", "insurance claim", "billing claim"],
    "claimproc":       ["claim proc", "claim procedure"],
    "payment":         ["payment", "pay", "transaction"],
    "icd9":            ["icd9", "icd-9", "diagnosis", "diagnostic code"],
    "allergy":         ["allergy", "allergies", "reaction"],
    "disease":         ["disease", "condition", "medical history"],
    "medication":      ["medication", "medicine", "drug", "rx"],
    "adjustment":      ["adjustment", "write-off", "discount"],
    "recall":          ["recall", "recare", "hygiene recall"],
}

# Intent-to-tables shortlist
_INTENT_TABLES: dict[str, list[str]] = {
    "COUNT_APPOINTMENTS": ["appointment", "patient", "provider"],
    "LIST_APPOINTMENTS":  ["appointment", "patient", "provider", "operatory"],
    "PROVIDER_SCHEDULE":  ["appointment", "provider", "patient", "operatory"],
    "PATIENT_UPCOMING":   ["appointment", "patient", "provider"],
    "AVAILABILITY":       ["appointment", "provider", "operatory", "schedule", "scheduleop"],
    "PATIENT_LOOKUP":     ["patient"],
    "RESCHEDULE_APPOINTMENT": ["appointment", "patient", "provider"],
    "CANCEL_APPOINTMENT":     ["appointment", "patient"],
    "CREATE_APPOINTMENT":     ["appointment", "patient", "provider", "operatory"],
}

# Key columns per table (only include the most useful ones for compact context)
_KEY_COLUMNS: dict[str, list[str]] = {
    "appointment": [
        "AptNum", "PatNum", "ProvNum", "ClinicNum", "AptStatus",
        "AptDateTime", "ProcDescript", "Note", "Confirmed",
        "IsNewPatient", "IsHygiene", "Op", "AppointmentTypeNum",
        "Pattern",
    ],
    "patient": [
        "PatNum", "LName", "FName", "MiddleI", "Preferred",
        "PatStatus", "Birthdate", "HmPhone", "WirelessPhone",
        "Email", "PriProv", "ClinicNum", "Address", "City", "State",
    ],
    "provider": [
        "ProvNum", "Abbr", "LName", "FName", "IsHidden",
        "Specialty", "ProvColor", "IsSecondary",
    ],
    "operatory": [
        "OperatoryNum", "OpName", "Abbrev", "IsHidden",
        "ProvDentist", "ProvHygienist", "IsHygiene", "ClinicNum",
    ],
    "clinic": [
        "ClinicNum", "Description", "Abbr", "Phone", "Address",
        "City", "State",
    ],
    "procedurecode": [
        "CodeNum", "ProcCode", "Descript", "AbbrDesc", "ProcCat",
    ],
    "icd9": [
        "ICD9Num", "ICD9Code", "Description",
    ],
}


class SchemaContextService:
    """
    Provide compact schema context for SQL generation.

    Usage::

        svc = SchemaContextService(db_service)
        context_text = svc.get_relevant_schema(
            nl_query="how many appointments tomorrow?",
            intent="COUNT_APPOINTMENTS",
            slots={"date": "2024-04-30"},
        )
    """

    def __init__(self, db_service=None):
        """
        Parameters
        ----------
        db_service : DatabaseService, optional
            Used for live introspection fallback.  If ``None``, the service
            relies entirely on ``FIELD_DESCRIPTIONS``.
        """
        self.db_service = db_service
        self._live_tables: Optional[Set[str]] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_relevant_schema(
        self,
        nl_query: str = "",
        intent: str = "",
        slots: Optional[dict] = None,
    ) -> str:
        """
        Return a compact text block describing only the relevant tables and
        columns for the given query / intent.

        Format::

            Table: appointment
             - AptNum (bigint): Unique appointment identifier
             - PatNum (bigint): Patient number - FK to patient
             ...

        Parameters
        ----------
        nl_query : str
            Original natural-language query.
        intent : str
            Detected intent name (e.g., ``COUNT_APPOINTMENTS``).
        slots : dict, optional
            Extracted slots from intent service.

        Returns
        -------
        str
            Compact schema context for LLM prompt injection.
        """
        tables = self._select_tables(nl_query, intent, slots)

        parts: list[str] = []
        for tbl in tables:
            block = self._format_table(tbl)
            if block:
                parts.append(block)

        if not parts:
            return ""

        return "=== RELEVANT DATABASE SCHEMA ===\n\n" + "\n\n".join(parts) + "\n"

    def get_all_table_names(self) -> List[str]:
        """Return all known table names (from schema docs or live DB)."""
        names: set[str] = set(FIELD_DESCRIPTIONS.keys())
        if self.db_service:
            try:
                live = self.db_service.get_tables()
                names.update(t.lower() for t in live)
            except Exception:
                pass
        return sorted(names)

    # ------------------------------------------------------------------
    # Table selection
    # ------------------------------------------------------------------

    def _select_tables(
        self,
        nl_query: str,
        intent: str,
        slots: Optional[dict],
    ) -> list[str]:
        """Pick 2-6 relevant tables based on intent + keyword matching."""
        selected: list[str] = []

        # 1. Intent-based shortlist
        if intent in _INTENT_TABLES:
            selected.extend(_INTENT_TABLES[intent])

        # 2. Keyword matching from the query
        query_lower = nl_query.lower()
        for tbl, keywords in _TABLE_KEYWORDS.items():
            if tbl in selected:
                continue
            if any(kw in query_lower for kw in keywords):
                selected.append(tbl)

        # 3. raw_query_target from slots
        if slots and slots.get("raw_query_target"):
            target = slots["raw_query_target"].lower().strip()
            if target and target not in selected:
                selected.append(target)

        # 4. Ensure we have at least appointment + patient for scheduling intents
        if intent and intent != "GENERAL_QUERY":
            for must in ("appointment", "patient"):
                if must not in selected:
                    selected.insert(0, must)

        # 5. Filter to only tables that actually exist
        available = self._available_tables()
        selected = [t for t in selected if t in available]

        # 6. Cap at 6
        return selected[:6]

    def _available_tables(self) -> Set[str]:
        """Tables known from schema docs + live DB."""
        if self._live_tables is not None:
            return self._live_tables

        tables = set(FIELD_DESCRIPTIONS.keys())
        if self.db_service:
            try:
                live = self.db_service.get_tables()
                tables.update(t.lower() for t in live)
            except Exception:
                pass
        self._live_tables = tables
        return tables

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def _format_table(self, table_name: str) -> str:
        """Format a single table's schema compactly."""
        table_lower = table_name.lower()

        # Determine which columns to show
        key_cols = _KEY_COLUMNS.get(table_lower)
        descriptions = FIELD_DESCRIPTIONS.get(table_lower, {})

        if not descriptions:
            # Live introspection fallback
            if self.db_service:
                try:
                    schema = self.db_service.get_table_schema(table_name)
                    if schema:
                        lines = [f"Table: {table_name}"]
                        for col, dtype in list(schema.items())[:15]:
                            lines.append(f"  - {col} ({dtype})")
                        return "\n".join(lines)
                except Exception:
                    pass
            return ""

        lines = [f"Table: {table_name}"]

        if key_cols:
            # Show only key columns
            for col in key_cols:
                desc = descriptions.get(col)
                if desc:
                    lines.append(f"  - {col}: {desc}")
        else:
            # Show first 12 columns
            for i, (col, desc) in enumerate(descriptions.items()):
                if i >= 12:
                    lines.append(f"  ... ({len(descriptions) - 12} more columns)")
                    break
                lines.append(f"  - {col}: {desc}")

        return "\n".join(lines)

