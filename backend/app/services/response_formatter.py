"""
Voice-Friendly Response Formatter
==================================
Converts raw query results + intent information into concise spoken output
with an optional structured payload for UI rendering.

Return shape::

    {
        "speech": "You have 12 appointments on April 30.",
        "data": {...},                      # structured for UI
        "follow_up_question": "..." | None  # optional follow-up
    }

Adding new formatters
---------------------
1. Write a ``_fmt_<INTENT_LOWER>(rows, slots, time_range)`` function.
2. Register it in ``_FORMATTER_REGISTRY`` at the bottom.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config import APT_STATUS, DEFAULT_RESULT_LIMIT
from app.utils.time_normalizer import TimeRange


def format_response(
    intent: str,
    rows: List[Dict[str, Any]],
    slots: Dict[str, Any],
    time_range: Optional[TimeRange] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Entry point: choose the right formatter based on *intent*.

    Parameters
    ----------
    intent : str
        Detected intent name.
    rows : list[dict]
        Query result rows from the database.
    slots : dict
        Extracted slots.
    time_range : TimeRange, optional
        Resolved time range.
    extra : dict, optional
        Any extra context (e.g., write-operation results).

    Returns
    -------
    dict  with ``speech``, ``data``, ``follow_up_question``.
    """
    formatter = _FORMATTER_REGISTRY.get(intent, _fmt_general)
    return formatter(rows, slots, time_range, extra)


# ---------------------------------------------------------------------------
# Individual formatters
# ---------------------------------------------------------------------------

def _fmt_count_appointments(
    rows: List[Dict], slots: Dict, time_range: Optional[TimeRange],
    extra: Optional[Dict] = None,
) -> Dict[str, Any]:
    """COUNT_APPOINTMENTS"""
    cnt = 0
    if rows and isinstance(rows[0], dict):
        cnt = rows[0].get("cnt", 0)
    elif rows and isinstance(rows[0], (tuple, list)):
        cnt = rows[0][0]

    period = _describe_period(time_range)
    provider = _describe_provider(slots)

    speech = f"You have {cnt} appointment{'s' if cnt != 1 else ''}"
    if period:
        speech += f" {period}"
    if provider:
        speech += f" with {provider}"
    speech += "."

    if cnt == 0:
        speech = f"There are no appointments{' ' + period if period else ''}."

    return {
        "speech": speech,
        "data": {"count": cnt, "period": period, "provider": provider},
        "follow_up_question": None,
    }


def _fmt_list_appointments(
    rows: List[Dict], slots: Dict, time_range: Optional[TimeRange],
    extra: Optional[Dict] = None,
) -> Dict[str, Any]:
    """LIST_APPOINTMENTS / PROVIDER_SCHEDULE"""
    if not rows:
        period = _describe_period(time_range)
        return {
            "speech": f"There are no appointments{' ' + period if period else ''}.",
            "data": {"appointments": []},
            "follow_up_question": None,
        }

    total = len(rows)
    show = min(total, 10)  # show up to 10 in speech; enough for most questions
    period = _describe_period(time_range)

    lines = []
    for r in rows[:show]:
        lines.append(_format_single_apt(r))

    speech = f"You have {total} appointment{'s' if total != 1 else ''}{' ' + period if period else ''}. "
    speech += " ".join(lines)
    if total > show:
        speech += f" There are {total - show} more. I can list them if you'd like."

    follow_up = f"Would you like to hear the rest of the {total} appointments?" if total > show else None

    return {
        "speech": speech,
        "data": {"appointments": rows, "total": total, "shown": show},
        "follow_up_question": follow_up,
    }


def _fmt_provider_schedule(
    rows: List[Dict], slots: Dict, time_range: Optional[TimeRange],
    extra: Optional[Dict] = None,
) -> Dict[str, Any]:
    """PROVIDER_SCHEDULE – delegates to list formatter."""
    return _fmt_list_appointments(rows, slots, time_range, extra)


def _fmt_patient_upcoming(
    rows: List[Dict], slots: Dict, time_range: Optional[TimeRange],
    extra: Optional[Dict] = None,
) -> Dict[str, Any]:
    """PATIENT_UPCOMING"""
    patient_name = ""
    if slots.get("patient") and slots["patient"].get("name"):
        patient_name = slots["patient"]["name"]

    if not rows:
        if patient_name:
            speech = f"There are no upcoming appointments for {patient_name}."
        else:
            speech = "There are no upcoming appointments for this patient."
        return {
            "speech": speech,
            "data": {"appointments": []},
            "follow_up_question": None,
        }

    total = len(rows)
    show = min(total, 3)

    lines = [_format_single_apt(r) for r in rows[:show]]

    if patient_name:
        speech = f"{patient_name} has {total} upcoming appointment{'s' if total != 1 else ''}. "
    else:
        speech = f"This patient has {total} upcoming appointment{'s' if total != 1 else ''}. "
    speech += " ".join(lines)

    return {
        "speech": speech,
        "data": {"appointments": rows, "total": total},
        "follow_up_question": None,
    }


def _fmt_availability(
    rows: List[Dict], slots: Dict, time_range: Optional[TimeRange],
    extra: Optional[Dict] = None,
) -> Dict[str, Any]:
    """AVAILABILITY – report booked slots and suggest gaps."""
    period = _describe_period(time_range)
    provider = _describe_provider(slots)

    if not rows:
        speech = f"{provider + ' is' if provider else 'The provider is'} completely free{' ' + period if period else ''}."
        return {
            "speech": speech,
            "data": {"booked_slots": [], "provider": provider},
            "follow_up_question": "Would you like to book an appointment?",
        }

    total = len(rows)
    speech = (
        f"{provider + ' has' if provider else 'There are'} "
        f"{total} booked slot{'s' if total != 1 else ''}{' ' + period if period else ''}. "
    )

    # Show first few booked times
    times = []
    for r in rows[:5]:
        apt_dt = r.get("AptDateTime", "")
        if apt_dt:
            try:
                dt = datetime.strptime(str(apt_dt), "%Y-%m-%d %H:%M:%S")
                times.append(dt.strftime("%I:%M %p"))
            except (ValueError, TypeError):
                times.append(str(apt_dt))

    if times:
        speech += f"Booked times include: {', '.join(times)}. "

    return {
        "speech": speech,
        "data": {"booked_slots": rows, "total": total},
        "follow_up_question": "Would you like to find a free slot?",
    }


def _fmt_patient_lookup(
    rows: List[Dict], slots: Dict, time_range: Optional[TimeRange],
    extra: Optional[Dict] = None,
) -> Dict[str, Any]:
    """PATIENT_LOOKUP"""
    if not rows:
        name = ""
        if slots.get("patient") and slots["patient"].get("name"):
            name = slots["patient"]["name"]
        return {
            "speech": f"No patients found{' matching ' + name if name else ''}.",
            "data": {"patients": []},
            "follow_up_question": None,
        }

    total = len(rows)
    if total == 1:
        p = rows[0]
        name = f"{p.get('FName', '')} {p.get('LName', '')}".strip()
        speech = f"I found patient {name}"
        phone = p.get("WirelessPhone") or p.get("HmPhone")
        if phone:
            speech += f", phone: {phone}"
        speech += "."
    else:
        speech = f"I found {total} patients matching that name. "
        for p in rows[:3]:
            name = f"{p.get('FName', '')} {p.get('LName', '')}".strip()
            speech += f"{name}. "

    return {
        "speech": speech,
        "data": {"patients": rows, "total": total},
        "follow_up_question": None,
    }


def _fmt_write_result(
    rows: List[Dict], slots: Dict, time_range: Optional[TimeRange],
    extra: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Format write operation results."""
    extra = extra or {}
    status = extra.get("status", "")
    message = extra.get("message", "")

    if status == "AWAITING_CONFIRMATION":
        return {
            "speech": message,
            "data": extra,
            "follow_up_question": message,
        }

    if extra.get("success"):
        return {
            "speech": message or "The operation was completed successfully.",
            "data": extra,
            "follow_up_question": None,
        }

    error = extra.get("error", "An error occurred")
    return {
        "speech": f"I couldn't complete that operation: {error}",
        "data": extra,
        "follow_up_question": "Would you like to try something else?",
    }


def _fmt_general(
    rows: List[Dict], slots: Dict, time_range: Optional[TimeRange],
    extra: Optional[Dict] = None,
) -> Dict[str, Any]:
    """GENERAL_QUERY – pass data through for LLM to compose response."""
    if not rows:
        return {
            "speech": "",  # empty = let LLM handle
            "data": {"rows": [], "raw_text": "No information found in the database."},
            "follow_up_question": None,
        }

    # Build a readable summary
    text_lines = []
    for i, r in enumerate(rows[:20]):
        if isinstance(r, dict):
            vals = ", ".join(f"{k}: {v}" for k, v in r.items() if v is not None and str(v).strip())
            text_lines.append(vals)
        else:
            text_lines.append(str(r))

    raw_text = "\n".join(text_lines)
    total = len(rows)

    return {
        "speech": "",  # Let LLM compose voice response from data
        "data": {"rows": rows, "total": total, "raw_text": raw_text},
        "follow_up_question": None,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _describe_period(time_range: Optional[TimeRange]) -> str:
    """Produce a human-friendly period description."""
    if not time_range:
        return ""
    desc = time_range.description
    if desc:
        # Avoid "for on ..." – if desc already starts with a preposition, use it as-is
        if desc.startswith(("for ", "on ", "from ", "between ")):
            return desc
        return f"for {desc}"
    start = time_range.start_dt
    end = time_range.end_dt
    if start.date() == end.date():
        return f"on {start.strftime('%B %d, %Y')}"
    return f"from {start.strftime('%B %d')} to {end.strftime('%B %d, %Y')}"


def _describe_provider(slots: Dict) -> str:
    prov = slots.get("provider")
    if prov and prov.get("name"):
        return f"Dr. {prov['name']}"
    return ""


def _format_single_apt(r: Dict) -> str:
    """Format a single appointment row into a spoken sentence.

    Always includes PatNum so compound queries ("what are their patient
    numbers?") are answered directly from this speech — no LLM needed.
    """
    parts = []

    # Time
    apt_dt = r.get("AptDateTime", "")
    if apt_dt:
        try:
            dt = datetime.strptime(str(apt_dt), "%Y-%m-%d %H:%M:%S")
            parts.append(f"at {dt.strftime('%I:%M %p')}")
        except (ValueError, TypeError):
            parts.append(f"at {apt_dt}")

    # Patient name + number (always include PatNum for accuracy)
    pat_name = r.get("PatientName", "")
    pat_num = r.get("PatNum")
    if pat_name and pat_num:
        parts.append(f"with {pat_name} (patient {pat_num})")
    elif pat_name:
        parts.append(f"with {pat_name}")
    elif pat_num:
        parts.append(f"patient {pat_num}")

    # Provider
    prov = r.get("ProviderAbbr", "")
    if prov:
        parts.append(f"(provider: {prov})")

    # Procedure
    proc = r.get("ProcDescript", "")
    if proc:
        parts.append(f"for {proc}")

    # Status
    status_code = r.get("AptStatus")
    if status_code is not None:
        status_label = APT_STATUS.get(int(status_code), "")
        if status_label and status_label.lower() != "scheduled":
            parts.append(f"[{status_label}]")

    return " ".join(parts) + "."


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_FORMATTER_REGISTRY: Dict[str, Any] = {
    "COUNT_APPOINTMENTS":  _fmt_count_appointments,
    "LIST_APPOINTMENTS":   _fmt_list_appointments,
    "PROVIDER_SCHEDULE":   _fmt_provider_schedule,
    "PATIENT_UPCOMING":    _fmt_patient_upcoming,
    "AVAILABILITY":        _fmt_availability,
    "PATIENT_LOOKUP":      _fmt_patient_lookup,
    "RESCHEDULE_APPOINTMENT": _fmt_write_result,
    "CANCEL_APPOINTMENT":     _fmt_write_result,
    "CREATE_APPOINTMENT":     _fmt_write_result,
}

