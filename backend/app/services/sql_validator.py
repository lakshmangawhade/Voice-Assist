"""
SQL Validator
=============
Programmatically validates LLM-generated (or template-generated) SQL before
execution.  Uses ``sqlglot`` for AST inspection so we don't rely on fragile
regex checks.

Rules enforced
--------------
* Only SELECT statements allowed (for READ intents).
* No ``SELECT *`` – columns must be explicit.
* LIMIT clause required for list/table-shaped outputs.
* All referenced tables must be in the allowed set.
* All referenced columns must exist in those tables.
* Required filters for the intent must be present
  (e.g., a date filter for COUNT_APPOINTMENTS).
* No dangerous DDL / DML keywords.
"""

from __future__ import annotations

import re
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

try:
    import sqlglot
    from sqlglot import exp as sqlglot_exp
    HAS_SQLGLOT = True
except ImportError:
    HAS_SQLGLOT = False

from app.services.schema_descriptions import FIELD_DESCRIPTIONS


def _sql_for_sqlglot_parse(sql: str) -> str:
    """
    sqlglot does not understand DB-API `%s` placeholders used by
    `mysql-connector-python`. It interprets `%` as modulo and fails to parse:

        WHERE col >= %s AND col < %s

    For validation we only need the AST for table/column inspection, so we
    replace placeholders with harmless literals *for parsing only*.
    """
    # Positional placeholders: %s
    sql = re.sub(r"%s\b", "1", sql)
    # Named pyformat placeholders: %(name)s (not used by our templates, but safe)
    sql = re.sub(r"%\([a-zA-Z_][a-zA-Z0-9_]*\)s\b", "1", sql)
    return sql


class ValidationError:
    """One issue found during validation."""

    __slots__ = ("code", "message")

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message

    def __repr__(self):
        return f"ValidationError({self.code}: {self.message})"

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message}


# ---------------------------------------------------------------------------
# Dangerous patterns  (checked even without sqlglot)
# ---------------------------------------------------------------------------
_DANGEROUS_KEYWORDS = re.compile(
    r'\b(DROP|DELETE|UPDATE|INSERT|TRUNCATE|CREATE|ALTER|'
    r'EXEC|EXECUTE|GRANT|REVOKE|CALL|LOAD|REPLACE)\b',
    re.IGNORECASE,
)


def validate(
    sql: str,
    params: Optional[dict | tuple] = None,
    allowed_tables: Optional[Set[str]] = None,
    allowed_columns: Optional[Dict[str, Set[str]]] = None,
    intent: str = "",
    expected_shape: str = "table",
) -> Tuple[bool, List[ValidationError]]:
    """
    Validate a SQL string.

    Parameters
    ----------
    sql : str
        The SQL to validate.
    params : dict or tuple, optional
        Parameterised values (not inspected, just logged for context).
    allowed_tables : set of str, optional
        Lowercase table names that may appear.  Defaults to all tables
        in ``FIELD_DESCRIPTIONS``.
    allowed_columns : dict, optional
        ``{table_lower: set_of_column_names}``.  Defaults to all columns
        in ``FIELD_DESCRIPTIONS``.
    intent : str
        The detected intent (used for required-filter checks).
    expected_shape : str
        ``"scalar"`` | ``"list"`` | ``"table"``  – governs LIMIT
        requirement.

    Returns
    -------
    (ok, errors)
        ``ok`` is True when no errors are found.
    """
    errors: list[ValidationError] = []

    if not sql or not sql.strip():
        errors.append(ValidationError("EMPTY_SQL", "SQL string is empty"))
        return False, errors

    sql_stripped = sql.strip()

    # -- 1. Must start with SELECT -------------------------------------------
    if not sql_stripped.upper().startswith("SELECT"):
        errors.append(ValidationError("NOT_SELECT", "Only SELECT queries are allowed for READ intents"))

    # -- 2. Dangerous keywords ------------------------------------------------
    m = _DANGEROUS_KEYWORDS.search(sql_stripped)
    if m:
        errors.append(ValidationError("DANGEROUS_KEYWORD", f"SQL contains forbidden keyword: {m.group(0)}"))

    # -- 3. No SELECT * -------------------------------------------------------
    if re.search(r'\bSELECT\s+\*\s', sql_stripped, re.IGNORECASE):
        # Allow COUNT(*) but not bare SELECT *
        if not re.search(r'\bCOUNT\s*\(\s*\*\s*\)', sql_stripped, re.IGNORECASE):
            errors.append(ValidationError("SELECT_STAR", "SELECT * is not allowed; list columns explicitly"))

    # -- 4. LIMIT required for list/table outputs -----------------------------
    if expected_shape in ("list", "table"):
        if not re.search(r'\bLIMIT\b', sql_stripped, re.IGNORECASE):
            errors.append(ValidationError("MISSING_LIMIT", "LIMIT clause is required for list/table outputs"))

    # -- 5. sqlglot-based deep checks ----------------------------------------
    if HAS_SQLGLOT:
        _sqlglot_checks(sql_stripped, errors, allowed_tables, allowed_columns)
    else:
        # Fallback: simple regex checks for table names
        _regex_table_check(sql_stripped, errors, allowed_tables)

    # -- 6. Intent-specific required filters ----------------------------------
    _check_intent_filters(sql_stripped, errors, intent)

    ok = len(errors) == 0
    return ok, errors


# ---------------------------------------------------------------------------
# sqlglot-based AST inspection
# ---------------------------------------------------------------------------

def _sqlglot_checks(
    sql: str,
    errors: list[ValidationError],
    allowed_tables: Optional[Set[str]],
    allowed_columns: Optional[Dict[str, Set[str]]],
):
    """Parse SQL with sqlglot and inspect tables/columns."""
    if allowed_tables is None:
        allowed_tables = {t.lower() for t in FIELD_DESCRIPTIONS.keys()}
    if allowed_columns is None:
        allowed_columns = {
            t.lower(): set(cols.keys())
            for t, cols in FIELD_DESCRIPTIONS.items()
        }

    sql_to_parse = _sql_for_sqlglot_parse(sql)

    try:
        parsed = sqlglot.parse(sql_to_parse, dialect="mysql")
    except Exception as e:
        errors.append(ValidationError("PARSE_ERROR", f"SQL parse error: {e}"))
        return

    if not parsed:
        errors.append(ValidationError("PARSE_ERROR", "sqlglot returned no statements"))
        return

    for statement in parsed:
        if statement is None:
            continue

        # Check statement type
        if not isinstance(statement, sqlglot_exp.Select):
            errors.append(ValidationError(
                "NOT_SELECT", f"Statement is {type(statement).__name__}, not SELECT"
            ))
            continue

        # Extract tables
        referenced_tables: set[str] = set()
        for table in statement.find_all(sqlglot_exp.Table):
            tname = table.name.lower().strip("`").strip('"').strip("'")
            if tname and tname != "dual":
                referenced_tables.add(tname)

        # Validate tables (skip information_schema)
        for tbl in referenced_tables:
            if tbl.startswith("information_schema"):
                continue
            if tbl not in allowed_tables:
                errors.append(ValidationError(
                    "UNKNOWN_TABLE",
                    f"Table `{tbl}` is not in the allowed schema"
                ))

        # Extract columns and validate
        for col_node in statement.find_all(sqlglot_exp.Column):
            col_name = col_node.name.strip("`").strip('"').strip("'")
            col_table = (col_node.table or "").strip("`").strip('"').strip("'").lower()

            if not col_name or col_name == "*":
                continue

            # If column has a table qualifier, validate against that table
            if col_table and col_table in allowed_columns:
                valid_cols = allowed_columns[col_table]
                if col_name not in valid_cols:
                    # Case-insensitive fallback
                    if col_name.lower() not in {c.lower() for c in valid_cols}:
                        errors.append(ValidationError(
                            "UNKNOWN_COLUMN",
                            f"Column `{col_name}` not found in table `{col_table}`"
                        ))
            elif not col_table:
                # Unqualified column – check if it exists in any referenced table
                found = False
                for tbl in referenced_tables:
                    tcols = allowed_columns.get(tbl, set())
                    if col_name in tcols or col_name.lower() in {c.lower() for c in tcols}:
                        found = True
                        break
                # Don't flag aliases (e.g., cnt, PatientName) – they're fine
                # We only flag if we're fairly sure it's not an alias
                # Heuristic: if it looks like a CamelCase field, flag it
                if not found and re.match(r'^[A-Z][a-zA-Z]+$', col_name):
                    errors.append(ValidationError(
                        "UNKNOWN_COLUMN",
                        f"Column `{col_name}` not found in any referenced table"
                    ))


def _regex_table_check(
    sql: str,
    errors: list[ValidationError],
    allowed_tables: Optional[Set[str]],
):
    """Fallback table validation without sqlglot."""
    if allowed_tables is None:
        allowed_tables = {t.lower() for t in FIELD_DESCRIPTIONS.keys()}

    # Rough extraction: FROM / JOIN followed by table name
    for m in re.finditer(r'(?:FROM|JOIN)\s+`?(\w+)`?', sql, re.IGNORECASE):
        tbl = m.group(1).lower()
        if tbl not in allowed_tables and not tbl.startswith("information_schema"):
            errors.append(ValidationError(
                "UNKNOWN_TABLE",
                f"Table `{tbl}` is not in the allowed schema"
            ))


# ---------------------------------------------------------------------------
# Intent-specific filter checks
# ---------------------------------------------------------------------------

def _check_intent_filters(
    sql: str,
    errors: list[ValidationError],
    intent: str,
):
    """Ensure required filters are present for certain intents."""
    sql_upper = sql.upper()

    date_intents = {
        "COUNT_APPOINTMENTS", "LIST_APPOINTMENTS",
        "PROVIDER_SCHEDULE", "AVAILABILITY",
    }

    if intent in date_intents:
        # Should have a date/datetime filter
        has_date = any(kw in sql_upper for kw in [
            "APTDATETIME", "APT_DATE_TIME", "CURDATE", "DATE(",
        ])
        if not has_date:
            errors.append(ValidationError(
                "MISSING_DATE_FILTER",
                f"Intent {intent} requires a date/datetime filter on AptDateTime"
            ))

    if intent == "PROVIDER_SCHEDULE":
        if "PROVNUM" not in sql_upper and "ABBR" not in sql_upper:
            errors.append(ValidationError(
                "MISSING_PROVIDER_FILTER",
                "PROVIDER_SCHEDULE requires a provider filter"
            ))

    if intent == "PATIENT_UPCOMING":
        if "PATNUM" not in sql_upper and "FNAME" not in sql_upper and "LNAME" not in sql_upper:
            errors.append(ValidationError(
                "MISSING_PATIENT_FILTER",
                "PATIENT_UPCOMING requires a patient filter"
            ))

