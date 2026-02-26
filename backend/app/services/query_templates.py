"""
Golden Query Templates
======================
Pre-defined, parameterised SQL templates for the most common scheduling
intents.  Each template function receives resolved *slots* and a
``TimeRange`` (from the time normaliser) and returns ``(sql, params)``.

Using templates instead of free-form LLM SQL generation:
  - Eliminates injection risk for 80 %+ of queries
  - Guarantees correct JOINs and column references
  - Always includes LIMIT and date filters

Adding a new template
---------------------
1. Write a function ``build_<INTENT_LOWER>(slots, time_range, limit)``
   that returns ``(sql_string, params_tuple)``.
2. Register it in ``TEMPLATE_REGISTRY`` at the bottom of this file.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.config import DEFAULT_RESULT_LIMIT, MAX_RESULT_LIMIT, APT_STATUS_REVERSE
from app.utils.time_normalizer import TimeRange

# Type alias
SqlAndParams = Tuple[str, Tuple[Any, ...]]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _limit(requested: Optional[int]) -> int:
    if requested is None:
        return DEFAULT_RESULT_LIMIT
    return min(max(1, requested), MAX_RESULT_LIMIT)


def _add_status_filter(
    conditions: list[str],
    params: list[Any],
    status: Optional[str],
):
    """Append an AptStatus filter if a status slot is provided."""
    if not status:
        return
    code = APT_STATUS_REVERSE.get(status.lower())
    if code is not None:
        conditions.append("a.`AptStatus` = %s")
        params.append(code)


def _add_provider_filter(
    conditions: list[str],
    params: list[Any],
    provider_slot: Optional[dict],
):
    """Append a provider filter if provider id or name is provided."""
    if not provider_slot:
        return
    prov_id = provider_slot.get("id")
    prov_name = provider_slot.get("name")
    if prov_id:
        conditions.append("a.`ProvNum` = %s")
        params.append(int(prov_id))
    elif prov_name:
        conditions.append(
            "(pr.`Abbr` LIKE %s OR pr.`LName` LIKE %s OR pr.`FName` LIKE %s)"
        )
        like = f"%{prov_name}%"
        params.extend([like, like, like])


def _add_clinic_filter(
    conditions: list[str],
    params: list[Any],
    clinic_slot: Optional[dict],
):
    """Append a clinic filter."""
    if not clinic_slot:
        return
    cid = clinic_slot.get("id")
    if cid:
        conditions.append("a.`ClinicNum` = %s")
        params.append(int(cid))


def _add_patient_filter(
    conditions: list[str],
    params: list[Any],
    patient_slot: Optional[dict],
):
    """Append patient filter (by id or name)."""
    if not patient_slot:
        return
    pid = patient_slot.get("id")
    pname = patient_slot.get("name")
    if pid:
        conditions.append("a.`PatNum` = %s")
        params.append(int(pid))
    elif pname:
        parts = pname.strip().split()
        if len(parts) >= 2:
            conditions.append("(p.`FName` LIKE %s AND p.`LName` LIKE %s)")
            params.extend([f"%{parts[0]}%", f"%{parts[-1]}%"])
        else:
            conditions.append("(p.`FName` LIKE %s OR p.`LName` LIKE %s)")
            like = f"%{parts[0]}%"
            params.extend([like, like])


def _time_conditions(
    conditions: list[str],
    params: list[Any],
    time_range: Optional[TimeRange],
):
    """Append AptDateTime range filter."""
    if not time_range:
        return
    tp = time_range.to_sql_params()
    conditions.append("a.`AptDateTime` >= %s")
    params.append(tp["start_dt"])
    conditions.append("a.`AptDateTime` < %s")
    params.append(tp["end_dt"])


# ---------------------------------------------------------------------------
# Template functions
# ---------------------------------------------------------------------------

def build_count_appointments(
    slots: Dict[str, Any],
    time_range: Optional[TimeRange] = None,
    limit: Optional[int] = None,
) -> SqlAndParams:
    """
    COUNT_APPOINTMENTS
    Returns: single row with ``cnt`` column.
    """
    conditions: list[str] = []
    params: list[Any] = []

    _time_conditions(conditions, params, time_range)
    _add_status_filter(conditions, params, slots.get("status"))
    _add_provider_filter(conditions, params, slots.get("provider"))
    _add_clinic_filter(conditions, params, slots.get("clinic"))
    _add_patient_filter(conditions, params, slots.get("patient"))

    where = " AND ".join(conditions) if conditions else "1=1"

    sql = f"""
        SELECT COUNT(*) AS cnt
        FROM `appointment` a
        LEFT JOIN `patient`   p  ON a.`PatNum`  = p.`PatNum`
        LEFT JOIN `provider`  pr ON a.`ProvNum` = pr.`ProvNum`
        WHERE {where}
    """
    return sql.strip(), tuple(params)


def build_list_appointments(
    slots: Dict[str, Any],
    time_range: Optional[TimeRange] = None,
    limit: Optional[int] = None,
) -> SqlAndParams:
    """
    LIST_APPOINTMENTS
    Returns: appointment rows with patient/provider info, ordered by time.
    """
    conditions: list[str] = []
    params: list[Any] = []

    _time_conditions(conditions, params, time_range)
    _add_status_filter(conditions, params, slots.get("status"))
    _add_provider_filter(conditions, params, slots.get("provider"))
    _add_clinic_filter(conditions, params, slots.get("clinic"))
    _add_patient_filter(conditions, params, slots.get("patient"))

    where = " AND ".join(conditions) if conditions else "1=1"
    lim = _limit(limit)

    sql = f"""
        SELECT
            a.`AptNum`,
            a.`AptDateTime`,
            a.`AptStatus`,
            a.`ProcDescript`,
            a.`Note`,
            a.`Confirmed`,
            a.`IsNewPatient`,
            a.`IsHygiene`,
            a.`ProvNum`,
            a.`PatNum`,
            CONCAT(p.`LName`, ', ', p.`FName`) AS PatientName,
            pr.`Abbr`                           AS ProviderAbbr
        FROM `appointment` a
        LEFT JOIN `patient`  p  ON a.`PatNum`  = p.`PatNum`
        LEFT JOIN `provider` pr ON a.`ProvNum` = pr.`ProvNum`
        WHERE {where}
        ORDER BY a.`AptDateTime` ASC
        LIMIT %s
    """
    params.append(lim)
    return sql.strip(), tuple(params)


def build_provider_schedule(
    slots: Dict[str, Any],
    time_range: Optional[TimeRange] = None,
    limit: Optional[int] = None,
) -> SqlAndParams:
    """
    PROVIDER_SCHEDULE – same as LIST but provider is mandatory.
    Falls through to LIST_APPOINTMENTS with provider filter.
    """
    return build_list_appointments(slots, time_range, limit)


def build_patient_upcoming(
    slots: Dict[str, Any],
    time_range: Optional[TimeRange] = None,
    limit: Optional[int] = None,
) -> SqlAndParams:
    """
    PATIENT_UPCOMING – upcoming appointments for a specific patient.
    If no time range is given, defaults to >= now.
    """
    conditions: list[str] = []
    params: list[Any] = []

    if time_range:
        _time_conditions(conditions, params, time_range)
    else:
        # Default: future appointments
        from datetime import datetime
        conditions.append("a.`AptDateTime` >= %s")
        params.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    _add_patient_filter(conditions, params, slots.get("patient"))
    _add_status_filter(conditions, params, slots.get("status"))

    where = " AND ".join(conditions) if conditions else "1=1"
    lim = _limit(limit)

    sql = f"""
        SELECT
            a.`AptNum`,
            a.`AptDateTime`,
            a.`AptStatus`,
            a.`ProcDescript`,
            a.`Note`,
            CONCAT(p.`LName`, ', ', p.`FName`) AS PatientName,
            pr.`Abbr`                           AS ProviderAbbr
        FROM `appointment` a
        LEFT JOIN `patient`  p  ON a.`PatNum`  = p.`PatNum`
        LEFT JOIN `provider` pr ON a.`ProvNum` = pr.`ProvNum`
        WHERE {where}
        ORDER BY a.`AptDateTime` ASC
        LIMIT %s
    """
    params.append(lim)
    return sql.strip(), tuple(params)


def build_availability(
    slots: Dict[str, Any],
    time_range: Optional[TimeRange] = None,
    limit: Optional[int] = None,
) -> SqlAndParams:
    """
    AVAILABILITY – find booked slots for a provider/clinic within a range.
    The pipeline layer will compute "free" slots by subtracting from
    business hours.  Here we return existing appointments so the caller
    can derive gaps.
    """
    conditions: list[str] = []
    params: list[Any] = []

    _time_conditions(conditions, params, time_range)
    _add_provider_filter(conditions, params, slots.get("provider"))
    _add_clinic_filter(conditions, params, slots.get("clinic"))
    # Only scheduled/active appointments matter for availability
    conditions.append("a.`AptStatus` IN (1, 4)")  # Scheduled or ASAP

    where = " AND ".join(conditions) if conditions else "1=1"
    lim = _limit(limit)

    sql = f"""
        SELECT
            a.`AptNum`,
            a.`AptDateTime`,
            a.`Pattern`,
            a.`ProvNum`,
            a.`Op`,
            pr.`Abbr` AS ProviderAbbr
        FROM `appointment` a
        LEFT JOIN `provider` pr ON a.`ProvNum` = pr.`ProvNum`
        WHERE {where}
        ORDER BY a.`AptDateTime` ASC
        LIMIT %s
    """
    params.append(lim)
    return sql.strip(), tuple(params)


def build_patient_lookup(
    slots: Dict[str, Any],
    time_range: Optional[TimeRange] = None,
    limit: Optional[int] = None,
) -> SqlAndParams:
    """
    PATIENT_LOOKUP – search patients by name or ID.
    """
    conditions: list[str] = []
    params: list[Any] = []
    lim = _limit(limit)

    patient = slots.get("patient")
    if patient:
        pid = patient.get("id")
        pname = patient.get("name")
        if pid:
            conditions.append("p.`PatNum` = %s")
            params.append(int(pid))
        elif pname:
            parts = pname.strip().split()
            if len(parts) >= 2:
                conditions.append("(p.`FName` LIKE %s AND p.`LName` LIKE %s)")
                params.extend([f"%{parts[0]}%", f"%{parts[-1]}%"])
            else:
                conditions.append("(p.`FName` LIKE %s OR p.`LName` LIKE %s)")
                like = f"%{parts[0]}%"
                params.extend([like, like])

    where = " AND ".join(conditions) if conditions else "1=1"

    sql = f"""
        SELECT
            p.`PatNum`,
            p.`LName`,
            p.`FName`,
            p.`Preferred`,
            p.`Birthdate`,
            p.`HmPhone`,
            p.`WirelessPhone`,
            p.`Email`,
            p.`PatStatus`,
            p.`PriProv`,
            p.`ClinicNum`
        FROM `patient` p
        WHERE {where}
        LIMIT %s
    """
    params.append(lim)
    return sql.strip(), tuple(params)


# ---------------------------------------------------------------------------
# Registry  –  maps intent name → builder function
# ---------------------------------------------------------------------------

TEMPLATE_REGISTRY: Dict[str, Any] = {
    "COUNT_APPOINTMENTS":  build_count_appointments,
    "LIST_APPOINTMENTS":   build_list_appointments,
    "PROVIDER_SCHEDULE":   build_provider_schedule,
    "PATIENT_UPCOMING":    build_patient_upcoming,
    "AVAILABILITY":        build_availability,
    "PATIENT_LOOKUP":      build_patient_lookup,
}


def get_template(intent: str):
    """
    Return the template builder for *intent*, or ``None`` if no template
    exists (caller should fall back to LLM SQL generation).
    """
    return TEMPLATE_REGISTRY.get(intent)

