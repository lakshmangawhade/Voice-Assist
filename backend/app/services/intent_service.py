"""
Intent + Slots Service
======================
Takes raw user text (often from voice) and returns a **strict JSON**
envelope describing the detected intent, extracted slots, and any
clarification needs.

Supported intents are defined in ``app.config.SUPPORTED_INTENTS``.

Adding a new intent
-------------------
1. Add the intent name to ``READ_INTENTS`` or ``WRITE_INTENTS`` in
   ``app/config.py``.
2. Update ``_INTENT_PROMPT`` below to describe the new intent and its
   required / optional slots.
3. If it's a READ intent, add a template in ``query_templates.py``.
   If it's a WRITE intent, add an operation handler in
   ``scheduling_ops_service.py``.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

import httpx
import os
from dotenv import load_dotenv
from pathlib import Path

from app.config import SUPPORTED_INTENTS, READ_INTENTS, WRITE_INTENTS, APT_STATUS_REVERSE

backend_dir = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=backend_dir / ".env")

# ---------------------------------------------------------------------------
# System prompt for intent extraction  (JSON-only output)
# ---------------------------------------------------------------------------
_INTENT_PROMPT = """You are an intent-extraction engine for a dental practice scheduling assistant.

TASK: Given a user message, return ONLY a JSON object (no markdown, no prose, no explanation).

SUPPORTED INTENTS:
- COUNT_APPOINTMENTS: User wants a count/number of appointments (e.g., "how many appointments today?")
- LIST_APPOINTMENTS: User wants a list of appointments (e.g., "show my appointments")
- PROVIDER_SCHEDULE: User asks about a specific provider/doctor schedule
- PATIENT_UPCOMING: User asks about a specific patient's upcoming visits
- PATIENT_LOOKUP: User wants to find a patient by name/ID
- AVAILABILITY: User asks about open/available slots for a provider
- RESCHEDULE_APPOINTMENT: User wants to move an existing appointment
- CANCEL_APPOINTMENT: User wants to cancel an appointment
- CREATE_APPOINTMENT: User wants to create/book a new appointment
- GENERAL_QUERY: Any other data question about the dental practice database (procedures, claims, ICD codes, billing, etc.)

OUTPUT JSON SCHEMA (return EXACTLY this structure):
{
  "intent": "<one of the intents above>",
  "slots": {
    "date": "YYYY-MM-DD or null",
    "date_range": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"} or null,
    "time_window": {"start_time": "HH:MM", "end_time": "HH:MM"} or null,
    "provider": {"name": "<name or abbreviation>", "id": "<ProvNum if known>"} or null,
    "clinic": {"name": "<name>", "id": "<ClinicNum if known>"} or null,
    "patient": {"name": "<name>", "id": "<PatNum if known>"} or null,
    "status": "<scheduled|completed|cancelled|broken|planned|unschedlist>" or null,
    "appointment_type": "<type description>" or null,
    "appointment_identifier": {"apt_id": "<AptNum>"} or null,
    "raw_time_expression": "<original time phrase from user, verbatim>" or null,
    "raw_query_target": "<table or topic the user is asking about>" or null
  },
  "needs_clarification": [
    {"field": "<slot name>", "reason": "<short reason>"}
  ],
  "assumptions": ["<any assumption you made>"],
  "confidence": 0.0 to 1.0
}

RULES:
- Return ONLY valid JSON, nothing else.
- Set null for any slot not mentioned or inferable.
- For time expressions like "tomorrow morning", "next Monday", "after lunch", put the verbatim phrase in raw_time_expression. Try to also fill date/time_window if you can.
- If the user references "today", set date to today's date if you know it, otherwise set raw_time_expression to "today".
- For GENERAL_QUERY, put the table or topic name in raw_query_target.
- confidence should reflect how certain you are about the intent (0.0-1.0).
- If intent is ambiguous, pick the most likely one and add others to assumptions.
- For WRITE intents (RESCHEDULE, CANCEL, CREATE), be conservative and add clarification needs.
"""


class IntentService:
    """
    Extract structured intent + slots from natural-language user input
    using the Groq LLM with strict JSON output.

    Falls back to rule-based extraction when the LLM is unavailable or
    returns unparseable output.
    """

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.1-8b-instant"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def extract(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyse *user_message* and return a strict intent+slots JSON dict.

        Parameters
        ----------
        user_message : str
            Raw text from the user / voice transcript.
        context : dict, optional
            Extra context such as ``{"default_provider_id": 1, "clinic_id": 2}``.

        Returns
        -------
        dict  (schema described in ``_INTENT_PROMPT``)
        """
        context = context or {}

        # Try LLM extraction first
        result = await self._llm_extract(user_message, context)

        if result is None:
            # Fallback: rule-based
            result = self._rule_based_extract(user_message, context)

        # Post-process
        result = self._post_process(result, user_message, context)
        return result

    # ------------------------------------------------------------------
    # LLM-based extraction
    # ------------------------------------------------------------------

    async def _llm_extract(
        self,
        user_message: str,
        context: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Call Groq LLM to extract intent+slots.  Returns None on failure."""
        if not self.api_key:
            return None

        system = _INTENT_PROMPT
        if context:
            system += f"\n\nADDITIONAL CONTEXT:\n{json.dumps(context, default=str)}"

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 512,
            "top_p": 1,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        for attempt in range(2):  # one retry
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(self.api_url, json=payload, headers=headers)
                    resp.raise_for_status()

                raw = resp.json()["choices"][0]["message"]["content"].strip()
                parsed = self._parse_json_response(raw)
                if parsed is not None:
                    return parsed

                # If first attempt failed to parse, retry with stricter prompt
                if attempt == 0:
                    messages.append({"role": "assistant", "content": raw})
                    messages.append({
                        "role": "user",
                        "content": (
                            "Your previous response was not valid JSON. "
                            "Return ONLY a JSON object with keys: intent, slots, "
                            "needs_clarification, assumptions, confidence. "
                            "No markdown, no code fences, no prose."
                        ),
                    })
                    payload["messages"] = messages
                    continue
            except Exception as e:
                print(f"[IntentService] LLM extraction error (attempt {attempt+1}): {e}")
                if attempt == 0:
                    continue

        return None

    @staticmethod
    def _parse_json_response(raw: str) -> Optional[Dict[str, Any]]:
        """Try to extract a JSON object from an LLM response string."""
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"\s*```\s*$", "", raw, flags=re.MULTILINE)
        raw = raw.strip()

        try:
            data = json.loads(raw)
            if isinstance(data, dict) and "intent" in data:
                return data
        except json.JSONDecodeError:
            pass

        # Try to find JSON object in the string
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
                if isinstance(data, dict) and "intent" in data:
                    return data
            except json.JSONDecodeError:
                pass

        return None

    # ------------------------------------------------------------------
    # Rule-based fallback
    # ------------------------------------------------------------------

    def _rule_based_extract(
        self,
        user_message: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Keyword-based intent detection as fallback."""
        msg = user_message.lower().strip()

        intent = "GENERAL_QUERY"
        confidence = 0.4
        slots = self._empty_slots()

        # --- WRITE intents (check first – they're safety-critical) ---
        if any(w in msg for w in ["cancel", "cancellation"]):
            intent = "CANCEL_APPOINTMENT"
            confidence = 0.7
        elif any(w in msg for w in [
            "reschedule", "rescheduling", "move appointment",
            "change appointment", "move my",
        ]):
            intent = "RESCHEDULE_APPOINTMENT"
            confidence = 0.7
        elif any(w in msg for w in [
            "book", "create appointment", "new appointment",
            "schedule an appointment",
        ]):
            intent = "CREATE_APPOINTMENT"
            confidence = 0.6

        # --- READ intents ---
        elif any(w in msg for w in ["how many", "count", "number of"]):
            intent = "COUNT_APPOINTMENTS"
            confidence = 0.8

        # PATIENT_LOOKUP must be tested BEFORE general "schedule/appointment"
        # matches to avoid misclassifying "patient record" as PATIENT_UPCOMING.
        elif any(w in msg for w in [
            "find patient", "patient info", "look up patient",
            "patient lookup", "patient record",
        ]):
            intent = "PATIENT_LOOKUP"
            confidence = 0.7

        elif any(w in msg for w in [
            "availability", "open slots", "free slots", "openings",
        ]):
            intent = "AVAILABILITY"
            confidence = 0.7
        elif "available" in msg:
            # "available" is overloaded; prefer AVAILABILITY only when the
            # sentence is clearly about scheduling / time slots.
            if any(w in msg for w in [
                "procedure", "treatment", "service", "consultation",
                "icd", "code",
            ]):
                intent = "GENERAL_QUERY"
                confidence = 0.5
            else:
                intent = "AVAILABILITY"
                confidence = 0.7

        elif any(w in msg for w in [
            "who is coming", "who's coming", "who has appointments",
        ]):
            intent = "LIST_APPOINTMENTS"
            confidence = 0.7

        elif any(w in msg for w in [
            "schedule", "appointments", "appointment", "show me", "show",
            "list",
        ]):
            if any(w in msg for w in ["doctor", "provider", "dr.", "dr "]):
                intent = "PROVIDER_SCHEDULE"
                confidence = 0.7
            elif any(w in msg for w in ["patient", "upcoming"]):
                intent = "PATIENT_UPCOMING"
                confidence = 0.7
            else:
                intent = "LIST_APPOINTMENTS"
                confidence = 0.7

        # --- Extract basic slots via regex ---

        # Appointment identifier  (e.g., "appointment 1234")
        m = re.search(r'\bappointment\s+#?(\d+)\b', msg)
        if m:
            slots["appointment_identifier"] = {"apt_id": m.group(1)}

        # raw_time_expression — expanded patterns
        time_phrases = re.findall(
            r'\b(?:'
            r'today|tomorrow|yesterday|day after tomorrow'
            r'|next\s+\w+'
            r'|this\s+\w+'
            r'|last\s+\w+'                       # "last week", "last Monday"
            r'|early\s+morning|late\s+morning'
            r'|morning|afternoon|evening|night'
            r'|after\s+lunch'
            r'|between\s+\d+\s+and\s+\d+'
            r'|from\s+\d+\s+to\s+\d+'
            r'|in\s+\d+\s+(?:hour|minute|hr|min)s?'  # "in 2 hours", "in 30 minutes"
            r'|(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)'
            r'|\d{1,2}\s*(?:am|pm)'                 # "10am", "3 pm"
            r'|at\s+noon|at\s+midnight'
            r'|(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:\s+\d{4})?'
            r'|\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}'  # DD-MM-YYYY, DD/MM/YY, MM-DD-YYYY
            r'|\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}'    # YYYY-MM-DD
            r')\b',
            msg,
        )
        if time_phrases:
            slots["raw_time_expression"] = " ".join(time_phrases)

        # Patient name — "patient <Name>" or "for <Name> with ..."
        m = re.search(r'\bpatient\s+([\w]+(?:\s+[\w]+)?)', msg)
        if m:
            name_or_id = m.group(1).strip()
            if name_or_id.isdigit():
                slots["patient"] = {"name": None, "id": name_or_id}
            else:
                slots["patient"] = {"name": name_or_id, "id": None}
        else:
            # "for <FirstName> <LastName> with ..."
            m = re.search(
                r'\bfor\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:with|on|at)\b',
                user_message,   # use original case for name extraction
            )
            if m:
                slots["patient"] = {"name": m.group(1).strip(), "id": None}

        # Provider name
        m = re.search(r'\b(?:doctor|provider|dr\.?)\s+([\w]+(?:\s+[\w]+)?)', msg)
        if m:
            name_or_id = m.group(1).strip()
            if name_or_id.isdigit():
                slots["provider"] = {"name": None, "id": name_or_id}
            else:
                slots["provider"] = {"name": name_or_id, "id": None}

        # Status
        for status_word, code in APT_STATUS_REVERSE.items():
            if status_word in msg:
                slots["status"] = status_word
                break

        return {
            "intent": intent,
            "slots": slots,
            "needs_clarification": [],
            "assumptions": ["rule-based fallback used"],
            "confidence": confidence,
        }

    # ------------------------------------------------------------------
    # Post-processing
    # ------------------------------------------------------------------

    def _post_process(
        self,
        result: Dict[str, Any],
        user_message: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Normalise and validate the extracted result."""
        # Ensure intent is known
        intent = result.get("intent", "GENERAL_QUERY")
        if intent not in SUPPORTED_INTENTS:
            result["intent"] = "GENERAL_QUERY"
            result["confidence"] = max(result.get("confidence", 0) - 0.2, 0.0)

        # Ensure slots dict exists
        if "slots" not in result or not isinstance(result.get("slots"), dict):
            result["slots"] = self._empty_slots()

        # Ensure other fields
        result.setdefault("needs_clarification", [])
        result.setdefault("assumptions", [])
        result.setdefault("confidence", 0.5)

        # Inject context defaults
        if context.get("default_provider_id") and not result["slots"].get("provider"):
            result["slots"]["provider"] = {"name": None, "id": str(context["default_provider_id"])}

        # ------------------------------------------------------------------
        # Override: keywords that strongly imply a specific intent
        # (catches cases where the LLM returns GENERAL_QUERY for
        #  "how many appointments were completed last week")
        # ------------------------------------------------------------------
        msg = user_message.lower()
        intent = result["intent"]

        if intent == "GENERAL_QUERY":
            if any(w in msg for w in ("how many", "count", "number of")):
                if any(w in msg for w in ("appointment", "appointments", "schedule", "booking")):
                    result["intent"] = "COUNT_APPOINTMENTS"
                    result["confidence"] = max(result["confidence"], 0.85)
                    result["assumptions"].append("overridden: 'how many appointments' -> COUNT_APPOINTMENTS")
            elif any(w in msg for w in ("list", "show", "display", "what are")):
                if any(w in msg for w in ("appointment", "appointments")):
                    result["intent"] = "LIST_APPOINTMENTS"
                    result["confidence"] = max(result["confidence"], 0.80)
                    result["assumptions"].append("overridden: list/show appointments -> LIST_APPOINTMENTS")

        # Extract status slot from message if not already set
        if not result["slots"].get("status"):
            for status_word, code in APT_STATUS_REVERSE.items():
                if status_word in msg:
                    result["slots"]["status"] = status_word
                    break

        # Preserve raw_time_expression if not set but present in text
        if not result["slots"].get("raw_time_expression"):
            msg = user_message.lower()
            time_phrases = re.findall(
                r'\b(?:'
                r'today|tomorrow|yesterday|day after tomorrow'
                r'|next\s+\w+'
                r'|this\s+\w+'
                r'|last\s+\w+'
                r'|early\s+morning|late\s+morning'
                r'|morning|afternoon|evening|night'
                r'|after\s+lunch'
                r'|between\s+\d+\s+and\s+\d+'
                r'|from\s+\d+\s+to\s+\d+'
                r'|in\s+\d+\s+(?:hour|minute|hr|min)s?'
                r'|(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)'
                r'|\d{1,2}\s*(?:am|pm)'
                r'|at\s+noon|at\s+midnight'
                r'|(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:\s+\d{4})?'
                r'|\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}'  # DD-MM-YYYY, DD/MM/YY, MM-DD-YYYY
                r'|\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}'    # YYYY-MM-DD
                r')\b',
                msg,
            )
            if time_phrases:
                result["slots"]["raw_time_expression"] = " ".join(time_phrases)

        return result

    @staticmethod
    def _empty_slots() -> Dict[str, Any]:
        return {
            "date": None,
            "date_range": None,
            "time_window": None,
            "provider": None,
            "clinic": None,
            "patient": None,
            "status": None,
            "appointment_type": None,
            "appointment_identifier": None,
            "raw_time_expression": None,
            "raw_query_target": None,
        }

    # ------------------------------------------------------------------
    # Legacy compatibility helpers (for Twilio call intent detection)
    # ------------------------------------------------------------------

    def detect_intent(self, user_message: str, ai_response: str = "") -> Dict[str, Any]:
        """
        Synchronous keyword-based intent detection for call-triggering
        (backward-compatible with main.py Twilio flow).
        """
        result = self._rule_based_extract(user_message, {})
        intent_map = {
            "CANCEL_APPOINTMENT": "cancel",
            "RESCHEDULE_APPOINTMENT": "reschedule",
        }
        mapped = intent_map.get(result["intent"], "none")
        return {
            "intent": mapped,
            "confidence": result["confidence"],
            "requires_call": mapped in ("cancel", "reschedule"),
            "extracted_info": {
                "phone_number": None,
                "dates_mentioned": [],
                "original_message": user_message,
            },
        }

    def should_trigger_call(self, intent_result: Dict) -> bool:
        """Determine if a Twilio call should be triggered."""
        return (
            intent_result["intent"] in ("cancel", "reschedule")
            and intent_result["confidence"] >= 0.6
            and intent_result.get("requires_call", False)
        )
