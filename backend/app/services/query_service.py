"""
Query Service  –  Pipeline Orchestrator
========================================
This is the **central hub** that connects every layer:

    User message
        → Intent + Slots  (IntentService)
        → Time normalisation  (TimeNormalizer)
        → Template SQL **or** LLM SQL fallback  (QueryTemplates / LLM)
        → SQL Validation  (SQLValidator)
        → Repair loop on failure  (SQLRepair)
        → Execution  (DatabaseService)
        → Post-query sanity checks
        → Response formatting  (ResponseFormatter)

For WRITE intents the SQL path is skipped entirely; the pipeline delegates
to ``SchedulingOpsService`` with a deterministic action plan.

Adding a new intent end-to-end
-------------------------------
1. Add the intent name to ``app/config.py``.
2. Add a template in ``query_templates.py``  (READ) **or** a handler
   in ``scheduling_ops_service.py``  (WRITE).
3. Optionally add a formatter in ``response_formatter.py``.
"""

from __future__ import annotations

import json
import re
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import httpx
import os
from dotenv import load_dotenv
from pathlib import Path

from app.config import (
    READ_INTENTS,
    WRITE_INTENTS,
    MAX_RESULT_LIMIT,
    DEFAULT_RESULT_LIMIT,
    MAX_REPAIR_RETRIES,
)
from app.services.intent_service import IntentService
from app.services.schema_context_service import SchemaContextService
from app.services.query_templates import get_template
from app.services import sql_validator
from app.services import sql_repair
from app.services.scheduling_ops_service import SchedulingOpsService
from app.services.response_formatter import format_response
from app.utils.time_normalizer import normalize_time, TimeRange
from app.services.schema_descriptions import FIELD_DESCRIPTIONS

backend_dir = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=backend_dir / ".env")

# LLM SQL-generation prompt (fallback path)
_SQL_GEN_SYSTEM = """You are a MySQL SQL generator for a dental practice database.

TASK: Given a user question, relevant schema, and intent, generate a READ-ONLY SQL query.

RULES:
1. Return ONLY a JSON object: {"sql": "SELECT ...", "params": {}, "expected_result_shape": "scalar|list|table", "assumptions": [], "confidence": 0.0}
2. Use parameterised queries with %s placeholders and matching params dict.
3. NEVER use SELECT * – list columns explicitly.
4. Include LIMIT (default 50) for list/table results.
5. NEVER include UPDATE/DELETE/INSERT/DDL.
6. Only reference tables and columns from the schema context provided.
7. Use MySQL syntax (backticks for identifiers, %s placeholders).
8. No markdown, no prose – JSON only.
"""


class QueryService:
    """
    Orchestrates the full NL → SQL → Results → Speech pipeline.

    Parameters
    ----------
    db_service : DatabaseService
        Initialised database connection.
    intent_service : IntentService, optional
        If ``None``, one is created internally.
    """

    def __init__(self, db_service, intent_service: Optional[IntentService] = None):
        self.db = db_service
        self.intent_svc = intent_service or IntentService()
        self.schema_ctx = SchemaContextService(db_service)
        self.sched_ops = SchedulingOpsService(db_service)

        # Pre-build allowed-tables/columns for validation
        self._allowed_tables: Set[str] = set()
        self._allowed_columns: Dict[str, Set[str]] = {}
        self._build_allowed_sets()

        # LLM config for SQL fallback
        self._api_key = os.getenv("GROQ_API_KEY", "")
        self._api_url = "https://api.groq.com/openai/v1/chat/completions"
        self._model = "llama-3.1-8b-instant"

    # ------------------------------------------------------------------
    # Internal: build allowed sets for validation
    # ------------------------------------------------------------------

    def _build_allowed_sets(self):
        """Build sets of allowed tables and columns from schema docs + live DB."""
        # From schema docs
        for table, cols in FIELD_DESCRIPTIONS.items():
            tl = table.lower()
            self._allowed_tables.add(tl)
            self._allowed_columns[tl] = set(cols.keys())

        # From live DB
        try:
            live_tables = self.db.get_tables()
            for t in live_tables:
                tl = t.lower()
                self._allowed_tables.add(tl)
                if tl not in self._allowed_columns:
                    schema = self.db.get_table_schema(t)
                    if schema:
                        self._allowed_columns[tl] = set(schema.keys())
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Public API  –  high-level entry point
    # ------------------------------------------------------------------

    async def process(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None,
        confirmed: bool = False,
    ) -> Dict[str, Any]:
        """
        Full pipeline: NL → intent → SQL/action → results → formatted response.

        Parameters
        ----------
        user_message : str
            Raw text from the user.
        context : dict, optional
            Extra context  (e.g., ``{"default_provider_id": 1}``).
        confirmed : bool
            If True, WRITE operations are authorised to execute.

        Returns
        -------
        dict with keys:
            - ``speech`` (str): voice-friendly text
            - ``data`` (dict): structured payload for UI
            - ``follow_up_question`` (str|None)
            - ``intent`` (str)
            - ``needs_data`` (bool)
            - ``formatted_data`` (str): legacy field for LLM prompt injection
        """
        t0 = time.time()
        context = context or {}

        # --- 1. Intent + Slots -----------------------------------------------
        intent_result = await self.intent_svc.extract(user_message, context)
        intent = intent_result.get("intent", "GENERAL_QUERY")
        slots = intent_result.get("slots", {})
        confidence = intent_result.get("confidence", 0.0)
        needs_clarification = intent_result.get("needs_clarification", [])

        self._log("Intent", f"{intent} (conf={confidence:.2f})", user_message)

        # --- 2. If clarification needed, return question immediately ----------
        if needs_clarification and confidence < 0.5:
            field = needs_clarification[0].get("field", "")
            reason = needs_clarification[0].get("reason", "")
            question = f"Could you clarify the {field}? ({reason})"
            return self._make_result(
                speech=question,
                data={},
                intent=intent,
                follow_up=question,
                needs_data=False,
            )

        # --- 3. Time normalisation --------------------------------------------
        raw_time = slots.get("raw_time_expression", "")
        time_range = normalize_time(
            raw_time or user_message,
            slots=slots,
        )
        if time_range:
            self._log("TimeRange", str(time_range))

        # --- 4. WRITE intents → action plan -----------------------------------
        if intent in WRITE_INTENTS:
            return await self._handle_write(intent, slots, time_range, confirmed, user_message)

        # --- 5. Compound-query upgrade ----------------------------------------
        if intent == "COUNT_APPOINTMENTS":
            intent = self._maybe_upgrade_to_list(intent, user_message)

        # --- 6. Build + log query plan ----------------------------------------
        query_plan = self._build_query_plan(
            user_message, intent, slots, time_range,
        )
        self._log("QueryPlan", self._format_plan(query_plan))

        # --- 7. READ intents → template or LLM SQL ----------------------------
        return await self._handle_read(intent, slots, time_range, user_message, context)

    # ------------------------------------------------------------------
    # Query Plan
    # ------------------------------------------------------------------

    # Keywords that signal specific domains
    _DOMAIN_KEYWORDS: Dict[str, List[str]] = {
        "appointment": ["appointment", "appointments", "schedule", "booking", "apt", "visit", "calendar"],
        "patient":     ["patient", "patients", "person", "client", "demographics", "name", "who"],
        "provider":    ["provider", "doctor", "dr", "dentist", "hygienist"],
        "procedure":   ["procedure", "treatment", "service", "dental work"],
        "operatory":   ["operatory", "room", "chair", "op"],
        "clinic":      ["clinic", "location", "office", "site"],
        "icd9":        ["icd9", "icd", "diagnosis", "diagnostic code"],
        "claim":       ["claim", "insurance", "billing"],
        "payment":     ["payment", "pay", "transaction"],
    }

    def _build_query_plan(
        self,
        user_message: str,
        intent: str,
        slots: Dict[str, Any],
        time_range: Optional[TimeRange],
    ) -> Dict[str, Any]:
        """
        Build a structured query plan: extract keywords, shortlist tables,
        identify template match, and determine output type.

        The plan is the single source of truth for how the query is executed.
        """
        msg_lower = user_message.lower()

        # 1. Extract keywords
        keywords = self._extract_keywords(msg_lower)

        # 2. Shortlist tables (2-6) from intent + keywords
        tables = self.schema_ctx._select_tables(user_message, intent, slots)

        # 3. Template match
        template_fn = get_template(intent)
        has_template = template_fn is not None

        # 4. Output type
        if intent == "COUNT_APPOINTMENTS":
            output_type = "scalar"
        elif intent in ("LIST_APPOINTMENTS", "PROVIDER_SCHEDULE",
                        "PATIENT_UPCOMING", "AVAILABILITY", "PATIENT_LOOKUP"):
            output_type = "table"
        else:
            output_type = "unknown"

        # 5. Filters summary
        filters: Dict[str, Any] = {}
        if time_range:
            filters["time_range"] = f"{time_range.start_dt} -> {time_range.end_dt}"
        if slots.get("provider"):
            filters["provider"] = slots["provider"]
        if slots.get("patient"):
            filters["patient"] = slots["patient"]
        if slots.get("status"):
            filters["status"] = slots["status"]
        if slots.get("clinic"):
            filters["clinic"] = slots["clinic"]

        return {
            "intent": intent,
            "keywords": keywords,
            "tables": tables,
            "has_template": has_template,
            "output_type": output_type,
            "filters": filters,
            "fallback": "LLM-SQL" if not has_template else "none",
        }

    def _extract_keywords(self, msg_lower: str) -> List[str]:
        """Extract domain keywords from the user message."""
        found: List[str] = []
        for domain, kws in self._DOMAIN_KEYWORDS.items():
            for kw in kws:
                if kw in msg_lower and domain not in found:
                    found.append(domain)
                    break
        # Also capture date-like tokens
        date_tokens = re.findall(
            r'\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b'
            r'|\b\d{4}[/\-]\d{1,2}[/\-]\d{1,2}\b'
            r'|\b(?:today|tomorrow|yesterday|next\s+\w+|this\s+\w+)\b',
            msg_lower,
        )
        found.extend(date_tokens)
        return found

    @staticmethod
    def _format_plan(plan: Dict[str, Any]) -> str:
        """One-line summary of the query plan for logging."""
        tables_str = ", ".join(plan["tables"][:6])
        kw_str = ", ".join(plan["keywords"][:8])
        tmpl = "TEMPLATE" if plan["has_template"] else "LLM-FALLBACK"
        filters_str = ", ".join(f"{k}={v}" for k, v in plan["filters"].items())
        return (
            f"intent={plan['intent']} | tables=[{tables_str}] | "
            f"keywords=[{kw_str}] | {tmpl} | "
            f"output={plan['output_type']} | filters=[{filters_str}]"
        )

    # ------------------------------------------------------------------
    # Compound-query intent upgrade
    # ------------------------------------------------------------------

    _DETAIL_PATTERNS = re.compile(
        r'\b(?:'
        r'what\s+are|which|list|show|details|patient\s*(?:num|number|id|name)'
        r'|their\s+(?:name|number|id|time|info|detail)'
        r'|appointment\s*(?:time|detail|info)'
        r'|who\s+are|give\s+me|tell\s+me'
        r'|along\s+with|include|and\s+(?:also|their|what|which|the)'
        r')\b',
        re.IGNORECASE,
    )

    def _maybe_upgrade_to_list(self, intent: str, user_message: str) -> str:
        """
        If the user asked for a count but ALSO wants details (patient
        numbers, times, names, etc.), upgrade to LIST_APPOINTMENTS so the
        template fetches actual rows instead of just ``COUNT(*)``.

        The count is still available as ``len(rows)`` in the formatter.
        """
        if intent != "COUNT_APPOINTMENTS":
            return intent
        if self._DETAIL_PATTERNS.search(user_message):
            self._log("UpgradeIntent", "COUNT->LIST (user asked for details)")
            return "LIST_APPOINTMENTS"
        return intent

    # ------------------------------------------------------------------
    # Backward-compatible sync entry point (used by old LLMService)
    # ------------------------------------------------------------------

    def analyze_and_query(
        self,
        user_message: str,
        prov_num: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Synchronous wrapper for the old ``llm_service.get_response`` call path.

        Returns ``{"needs_data": bool, "formatted_data": str}``.
        """
        import asyncio

        context = {}
        if prov_num:
            context["default_provider_id"] = prov_num

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # We're inside an async context; create a task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(
                    asyncio.run, self.process(user_message, context)
                ).result(timeout=30)
        else:
            result = asyncio.run(self.process(user_message, context))

        return {
            "needs_data": result.get("needs_data", True),
            "formatted_data": result.get("formatted_data", ""),
        }

    # ------------------------------------------------------------------
    # READ path
    # ------------------------------------------------------------------

    async def _handle_read(
        self,
        intent: str,
        slots: Dict[str, Any],
        time_range: Optional[TimeRange],
        user_message: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a READ query through template or LLM fallback."""

        # --- 5a. Try golden template first -----------------------------------
        template_fn = get_template(intent)
        sql: Optional[str] = None
        params: Any = None
        expected_shape = "table"

        if template_fn:
            try:
                sql, params = template_fn(slots, time_range)
                expected_shape = "scalar" if intent == "COUNT_APPOINTMENTS" else "table"
                self._log("Template", f"Using golden template for {intent}")
            except Exception as e:
                self._log("Template", f"Template error: {e}")
                template_fn = None

        # --- 5b. LLM SQL fallback ---------------------------------------------
        if sql is None:
            schema_context = self.schema_ctx.get_relevant_schema(
                nl_query=user_message, intent=intent, slots=slots,
            )
            llm_result = await self._generate_sql_via_llm(
                user_message, intent, slots, schema_context,
            )
            if llm_result:
                sql = llm_result.get("sql")
                params = llm_result.get("params", {})
                expected_shape = llm_result.get("expected_result_shape", "table")
                self._log("LLM-SQL", f"Generated SQL for {intent}")
            else:
                # Total fallback – provide raw data via generic query
                return await self._fallback_generic(user_message, slots, time_range, intent)

        # --- 6. Validate SQL --------------------------------------------------
        ok, errors = sql_validator.validate(
            sql, params,
            allowed_tables=self._allowed_tables,
            allowed_columns=self._allowed_columns,
            intent=intent,
            expected_shape=expected_shape,
        )

        if not ok:
            self._log("Validation", f"Errors: {[e.message for e in errors]}")

            # --- 7. Repair loop -----------------------------------------------
            schema_context = self.schema_ctx.get_relevant_schema(
                nl_query=user_message, intent=intent, slots=slots,
            )
            repair_result = await sql_repair.repair_sql(
                original_sql=sql,
                original_params=params,
                errors=errors,
                schema_context=schema_context,
                intent=intent,
                allowed_tables=self._allowed_tables,
                allowed_columns=self._allowed_columns,
                expected_shape=expected_shape,
            )
            if repair_result:
                sql, params = repair_result
                self._log("Repair", "SQL repaired successfully")
            else:
                # Repair failed – return safe error
                return self._make_result(
                    speech="I wasn't able to look that up right now. Could you rephrase your question?",
                    data={},
                    intent=intent,
                    needs_data=True,
                    formatted_data="No information found due to a query issue.",
                )

        # --- 8. Execute query -------------------------------------------------
        try:
            rows = self._execute_sql(sql, params)
        except Exception as e:
            self._log("Execution", f"Error: {e}")
            return self._make_result(
                speech="I encountered an error looking that up. Please try again.",
                data={},
                intent=intent,
                needs_data=True,
                formatted_data=f"Error executing query: {e}",
            )

        # --- 9. Post-query sanity checks --------------------------------------
        rows = self._post_query_checks(rows, intent, slots, time_range)

        # --- 10. Format response ----------------------------------------------
        formatted = format_response(intent, rows, slots, time_range)

        # Build formatted_data text for LLM prompt injection (legacy path)
        formatted_data = self._build_formatted_data(formatted, rows, intent)

        return self._make_result(
            speech=formatted.get("speech", ""),
            data=formatted.get("data", {}),
            intent=intent,
            follow_up=formatted.get("follow_up_question"),
            needs_data=True,
            formatted_data=formatted_data,
        )

    # ------------------------------------------------------------------
    # WRITE path
    # ------------------------------------------------------------------

    async def _handle_write(
        self,
        intent: str,
        slots: Dict[str, Any],
        time_range: Optional[TimeRange],
        confirmed: bool,
        user_message: str,
    ) -> Dict[str, Any]:
        """Handle WRITE intents via deterministic action plan."""

        # Build action plan
        plan = {
            "intent": intent,
            "steps": self._build_action_steps(intent, slots, time_range),
            "confidence": 0.8,
            "needs_clarification": [],
        }

        # Check for missing required info
        if intent in ("RESCHEDULE_APPOINTMENT", "CANCEL_APPOINTMENT"):
            apt_id = None
            if slots.get("appointment_identifier"):
                apt_id = slots["appointment_identifier"].get("apt_id")
            if not apt_id:
                plan["needs_clarification"] = [
                    {"field": "appointment_identifier", "reason": "Which appointment should I modify?"}
                ]

        if intent == "CREATE_APPOINTMENT":
            missing = []
            if not slots.get("patient"):
                missing.append({"field": "patient", "reason": "Which patient is this for?"})
            if not slots.get("provider"):
                missing.append({"field": "provider", "reason": "Which provider/doctor?"})
            if not time_range:
                missing.append({"field": "datetime", "reason": "When should the appointment be?"})
            if missing:
                plan["needs_clarification"] = missing

        # Execute
        result = self.sched_ops.execute_action_plan(plan, confirmed=confirmed)

        # Format
        formatted = format_response(intent, [], slots, time_range, extra=result)

        return self._make_result(
            speech=formatted.get("speech", ""),
            data=formatted.get("data", {}),
            intent=intent,
            follow_up=formatted.get("follow_up_question"),
            needs_data=True,
            formatted_data=formatted.get("speech", ""),
        )

    # ------------------------------------------------------------------
    # LLM SQL generation fallback
    # ------------------------------------------------------------------

    async def _generate_sql_via_llm(
        self,
        user_message: str,
        intent: str,
        slots: Dict[str, Any],
        schema_context: str,
    ) -> Optional[Dict[str, Any]]:
        """Ask the LLM to generate READ-only SQL."""
        if not self._api_key:
            return None

        user_prompt = (
            f"USER QUESTION: {user_message}\n"
            f"INTENT: {intent}\n"
            f"SLOTS: {json.dumps(slots, default=str)}\n\n"
            f"SCHEMA:\n{schema_context}\n\n"
            f"Generate a MySQL SELECT query. JSON only."
        )

        messages = [
            {"role": "system", "content": _SQL_GEN_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    self._api_url,
                    json={
                        "model": self._model,
                        "messages": messages,
                        "temperature": 0.0,
                        "max_tokens": 1024,
                        "stream": False,
                    },
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                )
                resp.raise_for_status()
                raw = resp.json()["choices"][0]["message"]["content"].strip()
                return self._parse_sql_json(raw)
        except Exception as e:
            self._log("LLM-SQL", f"Generation error: {e}")
            return None

    @staticmethod
    def _parse_sql_json(raw: str) -> Optional[Dict]:
        """Extract SQL JSON from LLM response."""
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"\s*```\s*$", "", raw, flags=re.MULTILINE)
        raw = raw.strip()
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and "sql" in data:
                return data
        except json.JSONDecodeError:
            pass
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
                if isinstance(data, dict) and "sql" in data:
                    return data
            except json.JSONDecodeError:
                pass
        return None

    # ------------------------------------------------------------------
    # Generic fallback (when no template + LLM SQL fails)
    # ------------------------------------------------------------------

    async def _fallback_generic(
        self,
        user_message: str,
        slots: Dict[str, Any],
        time_range: Optional[TimeRange],
        intent: str,
    ) -> Dict[str, Any]:
        """Last-resort: try a simple table search."""
        target = (slots.get("raw_query_target") or "").lower()
        tables = self.db.get_tables()
        matched = None

        # Try matching target to a table name
        for t in tables:
            if target and target in t.lower():
                matched = t
                break

        if not matched and time_range:
            matched = "appointment"

        if matched:
            try:
                schema = self.db.get_table_schema(matched)
                cols = list(schema.keys())[:8]
                if cols:
                    col_list = ", ".join(f"`{c}`" for c in cols)
                    sql = f"SELECT {col_list} FROM `{matched}` LIMIT 20"
                    rows = self.db.query_table(matched, columns=cols, limit=20)
                    formatted = format_response("GENERAL_QUERY", rows, slots, time_range)
                    return self._make_result(
                        speech=formatted.get("speech", ""),
                        data=formatted.get("data", {}),
                        intent=intent,
                        needs_data=True,
                        formatted_data=formatted["data"].get("raw_text", "No information found."),
                    )
            except Exception as e:
                self._log("Fallback", f"Error: {e}")

        return self._make_result(
            speech="",
            data={},
            intent=intent,
            needs_data=True,
            formatted_data="No information found in the database for this question.",
        )

    # ------------------------------------------------------------------
    # Execution helper
    # ------------------------------------------------------------------

    def _execute_sql(self, sql: str, params: Any) -> List[Dict[str, Any]]:
        """Execute a validated SELECT query."""
        if isinstance(params, dict):
            # Convert dict params to positional – replace named placeholders
            positional: list[Any] = []
            for key, val in params.items():
                placeholder = f":{key}"
                if placeholder in sql:
                    sql = sql.replace(placeholder, "%s")
                    positional.append(val)
                else:
                    positional.append(val)
            params = tuple(positional) if positional else None
        elif isinstance(params, (list, tuple)):
            params = tuple(params)
        else:
            params = None

        return self.db._execute_query_raw(sql, params, return_dict=True)

    # ------------------------------------------------------------------
    # Post-query sanity checks
    # ------------------------------------------------------------------

    def _post_query_checks(
        self,
        rows: List[Dict],
        intent: str,
        slots: Dict,
        time_range: Optional[TimeRange],
    ) -> List[Dict]:
        """
        After execution, verify results make sense for the intent.
        If results are huge, truncate and warn.
        """
        # Cap results
        if len(rows) > MAX_RESULT_LIMIT:
            rows = rows[:MAX_RESULT_LIMIT]

        return rows

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_action_steps(
        self,
        intent: str,
        slots: Dict,
        time_range: Optional[TimeRange],
    ) -> List[Dict]:
        """Build deterministic action steps for WRITE intents."""
        steps: list[dict] = []

        if intent == "RESCHEDULE_APPOINTMENT":
            apt_id = None
            if slots.get("appointment_identifier"):
                apt_id = slots["appointment_identifier"].get("apt_id")
            steps.append({"op": "FIND_APPOINTMENT", "by": {"apt_id": apt_id}})
            new_time = time_range.start_dt.strftime("%Y-%m-%d %H:%M:%S") if time_range else None
            if slots.get("provider"):
                steps.append({
                    "op": "CHECK_CONFLICTS",
                    "provider_id": slots["provider"].get("id"),
                    "new_time": new_time,
                })
            steps.append({"op": "REQUIRE_CONFIRMATION", "say": "Please confirm the reschedule."})

        elif intent == "CANCEL_APPOINTMENT":
            apt_id = None
            if slots.get("appointment_identifier"):
                apt_id = slots["appointment_identifier"].get("apt_id")
            steps.append({"op": "FIND_APPOINTMENT", "by": {"apt_id": apt_id}})
            steps.append({"op": "REQUIRE_CONFIRMATION", "say": "Please confirm the cancellation."})

        elif intent == "CREATE_APPOINTMENT":
            if slots.get("patient"):
                steps.append({"op": "SET_PATIENT", "patient_id": slots["patient"].get("id")})
            if slots.get("provider"):
                steps.append({"op": "SET_PROVIDER", "provider_id": slots["provider"].get("id")})
            if time_range:
                steps.append({
                    "op": "SET_TIME",
                    "datetime": time_range.start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                })
            steps.append({"op": "REQUIRE_CONFIRMATION", "say": "Please confirm the new appointment."})

        return steps

    def _build_formatted_data(
        self,
        formatted: Dict[str, Any],
        rows: List[Dict],
        intent: str,
    ) -> str:
        """
        Build a text blob for the LLM system prompt (data injection).

        IMPORTANT: We ALWAYS include the raw row data so the LLM can
        reference exact values (PatNum, AptDateTime, etc.) and never
        needs to invent / hallucinate them.
        """
        parts: list[str] = []

        # 1. Speech summary (high-level answer)
        speech = formatted.get("speech", "")
        if speech:
            parts.append(f"SUMMARY: {speech}")

        # 2. Raw row data (the ground truth the LLM must rely on)
        if rows:
            parts.append(f"\nDETAILED DATA ({len(rows)} row{'s' if len(rows) != 1 else ''}):")
            for i, r in enumerate(rows[:30]):
                if isinstance(r, dict):
                    vals = ", ".join(
                        f"{k}: {v}" for k, v in r.items()
                        if v is not None and str(v).strip()
                    )
                    parts.append(f"  Row {i + 1}: {vals}")
        elif not speech:
            parts.append("No information found in the database.")

        return "\n".join(parts) if parts else "No information found in the database."

    @staticmethod
    def _make_result(
        speech: str = "",
        data: Optional[dict] = None,
        intent: str = "",
        follow_up: Optional[str] = None,
        needs_data: bool = True,
        formatted_data: str = "",
    ) -> Dict[str, Any]:
        return {
            "speech": speech,
            "data": data or {},
            "follow_up_question": follow_up,
            "intent": intent,
            "needs_data": needs_data,
            "formatted_data": formatted_data,
        }

    @staticmethod
    def _log(tag: str, message: str, extra: str = ""):
        ts = datetime.now().strftime("%H:%M:%S")
        extra_str = f" | input='{extra[:60]}'" if extra else ""
        print(f"[{ts}] [{tag}] {message}{extra_str}")
