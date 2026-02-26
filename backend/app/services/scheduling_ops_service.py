"""
Scheduling Operations Service  (WRITE intents)
================================================
Deterministic, safe backend operations for appointment mutation:
  - find_appointments
  - check_conflicts
  - reschedule_appointment
  - cancel_appointment
  - create_appointment

**None of these methods execute unless the caller supplies
``confirmed=True``.**  The LLM never generates SQL for writes – instead it
produces an *action plan* JSON, which the pipeline validates and runs through
these deterministic functions.

All DB operations use parameterised queries via ``DatabaseService``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.config import APT_STATUS, APT_STATUS_REVERSE


class SchedulingOpsService:
    """
    Encapsulates safe WRITE operations on the appointment table.

    Parameters
    ----------
    db_service : DatabaseService
        An initialised database service for executing queries.
    """

    def __init__(self, db_service):
        self.db = db_service

    # ------------------------------------------------------------------
    # READ helpers (used internally before writes)
    # ------------------------------------------------------------------

    def find_appointments(
        self,
        apt_id: Optional[int] = None,
        patient_id: Optional[int] = None,
        patient_name: Optional[str] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        provider_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find appointments matching the given criteria."""
        conditions: list[str] = []
        params: list[Any] = []

        if apt_id:
            conditions.append("`AptNum` = %s")
            params.append(apt_id)
        if patient_id:
            conditions.append("`PatNum` = %s")
            params.append(patient_id)
        if date_start:
            conditions.append("`AptDateTime` >= %s")
            params.append(date_start)
        if date_end:
            conditions.append("`AptDateTime` < %s")
            params.append(date_end)
        if provider_id:
            conditions.append("`ProvNum` = %s")
            params.append(provider_id)

        where = " AND ".join(conditions) if conditions else "1=1"

        sql = f"""
            SELECT `AptNum`, `PatNum`, `ProvNum`, `AptDateTime`,
                   `AptStatus`, `ProcDescript`, `Note`, `Op`
            FROM `appointment`
            WHERE {where}
            ORDER BY `AptDateTime` ASC
            LIMIT %s
        """
        params.append(limit)

        try:
            results = self.db.execute_query(sql, tuple(params))
            return results if results else []
        except Exception as e:
            print(f"[SchedulingOps] find_appointments error: {e}")
            return []

    def check_conflicts(
        self,
        provider_id: int,
        new_datetime: str,
        duration_minutes: int = 30,
        exclude_apt_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Check if a provider has conflicting appointments around a proposed time.

        Returns list of conflicting appointments (empty = no conflict).
        """
        conditions = [
            "`ProvNum` = %s",
            "`AptStatus` IN (1, 4)",  # Scheduled or ASAP
            "`AptDateTime` >= %s",
            "`AptDateTime` < %s",
        ]
        # Check ± duration around the proposed time
        try:
            proposed_dt = datetime.strptime(new_datetime, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            proposed_dt = datetime.strptime(new_datetime, "%Y-%m-%d %H:%M")

        from datetime import timedelta
        range_start = (proposed_dt - timedelta(minutes=duration_minutes)).strftime("%Y-%m-%d %H:%M:%S")
        range_end = (proposed_dt + timedelta(minutes=duration_minutes)).strftime("%Y-%m-%d %H:%M:%S")

        params: list[Any] = [provider_id, range_start, range_end]

        if exclude_apt_id:
            conditions.append("`AptNum` != %s")
            params.append(exclude_apt_id)

        where = " AND ".join(conditions)
        sql = f"""
            SELECT `AptNum`, `PatNum`, `AptDateTime`, `ProcDescript`
            FROM `appointment`
            WHERE {where}
            LIMIT 10
        """

        try:
            results = self.db.execute_query(sql, tuple(params))
            return results if results else []
        except Exception as e:
            print(f"[SchedulingOps] check_conflicts error: {e}")
            return []

    # ------------------------------------------------------------------
    # WRITE operations  (require confirmed=True)
    # ------------------------------------------------------------------

    def reschedule_appointment(
        self,
        apt_id: int,
        new_datetime: str,
        confirmed: bool = False,
    ) -> Dict[str, Any]:
        """
        Move an existing appointment to a new date/time.

        Does NOT execute unless ``confirmed=True``.
        """
        if not confirmed:
            return {
                "success": False,
                "action": "RESCHEDULE_APPOINTMENT",
                "apt_id": apt_id,
                "new_datetime": new_datetime,
                "status": "AWAITING_CONFIRMATION",
                "message": f"Please confirm: reschedule appointment #{apt_id} to {new_datetime}?",
            }

        # Verify appointment exists
        existing = self.find_appointments(apt_id=apt_id)
        if not existing:
            return {
                "success": False,
                "action": "RESCHEDULE_APPOINTMENT",
                "error": f"Appointment #{apt_id} not found",
            }

        apt = existing[0]
        provider_id = apt.get("ProvNum")

        # Check for conflicts
        if provider_id:
            conflicts = self.check_conflicts(provider_id, new_datetime, exclude_apt_id=apt_id)
            if conflicts:
                return {
                    "success": False,
                    "action": "RESCHEDULE_APPOINTMENT",
                    "error": "Time conflict exists",
                    "conflicts": conflicts,
                }

        # Execute update
        sql = "UPDATE `appointment` SET `AptDateTime` = %s WHERE `AptNum` = %s"
        try:
            self.db.execute_query(sql, (new_datetime, apt_id))
            return {
                "success": True,
                "action": "RESCHEDULE_APPOINTMENT",
                "apt_id": apt_id,
                "new_datetime": new_datetime,
                "message": f"Appointment #{apt_id} rescheduled to {new_datetime}",
            }
        except Exception as e:
            return {
                "success": False,
                "action": "RESCHEDULE_APPOINTMENT",
                "error": str(e),
            }

    def cancel_appointment(
        self,
        apt_id: int,
        confirmed: bool = False,
    ) -> Dict[str, Any]:
        """
        Cancel (mark as Broken) an existing appointment.

        Does NOT execute unless ``confirmed=True``.
        """
        if not confirmed:
            return {
                "success": False,
                "action": "CANCEL_APPOINTMENT",
                "apt_id": apt_id,
                "status": "AWAITING_CONFIRMATION",
                "message": f"Please confirm: cancel appointment #{apt_id}?",
            }

        existing = self.find_appointments(apt_id=apt_id)
        if not existing:
            return {
                "success": False,
                "action": "CANCEL_APPOINTMENT",
                "error": f"Appointment #{apt_id} not found",
            }

        # Set status to Broken (5)
        sql = "UPDATE `appointment` SET `AptStatus` = %s WHERE `AptNum` = %s"
        try:
            self.db.execute_query(sql, (5, apt_id))
            return {
                "success": True,
                "action": "CANCEL_APPOINTMENT",
                "apt_id": apt_id,
                "message": f"Appointment #{apt_id} has been cancelled",
            }
        except Exception as e:
            return {
                "success": False,
                "action": "CANCEL_APPOINTMENT",
                "error": str(e),
            }

    def create_appointment(
        self,
        patient_id: int,
        provider_id: int,
        apt_datetime: str,
        proc_descript: str = "",
        operatory: int = 0,
        confirmed: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a new appointment.

        Does NOT execute unless ``confirmed=True``.
        """
        if not confirmed:
            return {
                "success": False,
                "action": "CREATE_APPOINTMENT",
                "status": "AWAITING_CONFIRMATION",
                "details": {
                    "patient_id": patient_id,
                    "provider_id": provider_id,
                    "datetime": apt_datetime,
                    "procedure": proc_descript,
                },
                "message": (
                    f"Please confirm: create appointment for patient #{patient_id} "
                    f"with provider #{provider_id} at {apt_datetime}?"
                ),
            }

        # Check conflicts
        conflicts = self.check_conflicts(provider_id, apt_datetime)
        if conflicts:
            return {
                "success": False,
                "action": "CREATE_APPOINTMENT",
                "error": "Time conflict exists with provider",
                "conflicts": conflicts,
            }

        sql = """
            INSERT INTO `appointment`
                (`PatNum`, `ProvNum`, `AptDateTime`, `AptStatus`, `ProcDescript`, `Op`)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        try:
            self.db.execute_query(sql, (
                patient_id, provider_id, apt_datetime,
                1,  # Scheduled
                proc_descript,
                operatory,
            ))
            return {
                "success": True,
                "action": "CREATE_APPOINTMENT",
                "message": f"Appointment created for patient #{patient_id} at {apt_datetime}",
            }
        except Exception as e:
            return {
                "success": False,
                "action": "CREATE_APPOINTMENT",
                "error": str(e),
            }

    # ------------------------------------------------------------------
    # Action plan execution
    # ------------------------------------------------------------------

    def execute_action_plan(
        self,
        plan: Dict[str, Any],
        confirmed: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute a WRITE action plan produced by the intent layer.

        The plan has the shape::

            {
                "intent": "RESCHEDULE_APPOINTMENT",
                "steps": [...],
                "confidence": 0.8,
                "needs_clarification": [...]
            }

        Returns a result dict with ``success``, ``message``, and optional
        ``needs_clarification``.
        """
        intent = plan.get("intent", "")
        steps = plan.get("steps", [])
        needs = plan.get("needs_clarification", [])

        # If clarification is needed, return that immediately
        if needs:
            return {
                "success": False,
                "status": "NEEDS_CLARIFICATION",
                "needs_clarification": needs,
                "message": "I need a bit more information before I can proceed.",
            }

        if intent == "RESCHEDULE_APPOINTMENT":
            return self._execute_reschedule_plan(steps, confirmed)
        elif intent == "CANCEL_APPOINTMENT":
            return self._execute_cancel_plan(steps, confirmed)
        elif intent == "CREATE_APPOINTMENT":
            return self._execute_create_plan(steps, confirmed)
        else:
            return {
                "success": False,
                "error": f"Unknown write intent: {intent}",
            }

    def _execute_reschedule_plan(
        self,
        steps: List[Dict],
        confirmed: bool,
    ) -> Dict[str, Any]:
        """Process reschedule steps."""
        apt_id = None
        new_time = None

        for step in steps:
            op = step.get("op", "")
            if op == "FIND_APPOINTMENT":
                by = step.get("by", {})
                apt_id = by.get("apt_id")
            elif op == "CHECK_CONFLICTS":
                new_time = step.get("new_time")
            elif op == "REQUIRE_CONFIRMATION":
                pass  # handled by confirmed flag

        if not apt_id:
            return {"success": False, "error": "No appointment ID specified"}
        if not new_time:
            return {"success": False, "error": "No new time specified"}

        return self.reschedule_appointment(int(apt_id), new_time, confirmed=confirmed)

    def _execute_cancel_plan(
        self,
        steps: List[Dict],
        confirmed: bool,
    ) -> Dict[str, Any]:
        """Process cancel steps."""
        apt_id = None
        for step in steps:
            op = step.get("op", "")
            if op == "FIND_APPOINTMENT":
                by = step.get("by", {})
                apt_id = by.get("apt_id")

        if not apt_id:
            return {"success": False, "error": "No appointment ID specified"}

        return self.cancel_appointment(int(apt_id), confirmed=confirmed)

    def _execute_create_plan(
        self,
        steps: List[Dict],
        confirmed: bool,
    ) -> Dict[str, Any]:
        """Process create steps."""
        patient_id = None
        provider_id = None
        apt_datetime = None
        proc_descript = ""

        for step in steps:
            op = step.get("op", "")
            if op == "SET_PATIENT":
                patient_id = step.get("patient_id")
            elif op == "SET_PROVIDER":
                provider_id = step.get("provider_id")
            elif op == "SET_TIME":
                apt_datetime = step.get("datetime")
            elif op == "SET_PROCEDURE":
                proc_descript = step.get("description", "")

        if not all([patient_id, provider_id, apt_datetime]):
            return {
                "success": False,
                "error": "Missing required fields: patient, provider, and datetime",
            }

        return self.create_appointment(
            int(patient_id), int(provider_id), apt_datetime,
            proc_descript=proc_descript, confirmed=confirmed,
        )

