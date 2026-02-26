"""
SQL Repair Service
==================
When the ``sql_validator`` flags errors in LLM-generated SQL, this service
sends the errors, the original SQL, and the schema context back to the LLM
with a constrained repair prompt.  Retries up to ``MAX_REPAIR_RETRIES`` times.

If repair still fails, it returns ``None`` so the caller can return a safe
error message to the user.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx
import os
from dotenv import load_dotenv
from pathlib import Path

from app.config import MAX_REPAIR_RETRIES
from app.services.sql_validator import validate, ValidationError

backend_dir = Path(__file__).parent.parent.parent
load_dotenv(dotenv_path=backend_dir / ".env")


_REPAIR_SYSTEM = """You are a SQL repair engine for a MySQL dental-practice database.

TASK: Fix the SQL query below based on the validation errors.

RULES:
1. Return ONLY a JSON object: {"sql": "...", "params": {...}, "confidence": 0.0}
2. The SQL must be a parameterised SELECT statement (use %s for MySQL placeholders).
3. Do NOT use SELECT * – list columns explicitly.
4. Include LIMIT for list/table outputs.
5. Only reference tables and columns from the provided schema.
6. No UPDATE/DELETE/INSERT/DDL.
7. No markdown, no prose, no explanation – JSON only.
"""


async def repair_sql(
    original_sql: str,
    original_params: Any,
    errors: List[ValidationError],
    schema_context: str,
    intent: str,
    allowed_tables: set,
    allowed_columns: dict,
    expected_shape: str = "table",
) -> Optional[Tuple[str, dict]]:
    """
    Attempt to repair invalid SQL via LLM.

    Parameters
    ----------
    original_sql : str
        The SQL that failed validation.
    original_params : any
        The original parameters.
    errors : list[ValidationError]
        Errors from ``sql_validator.validate()``.
    schema_context : str
        Compact schema text to include in the prompt.
    intent : str
        The detected intent.
    allowed_tables : set
        Valid table names (lowercase).
    allowed_columns : dict
        ``{table: set_of_columns}``.
    expected_shape : str
        ``"scalar"`` | ``"list"`` | ``"table"``.

    Returns
    -------
    (sql, params) or None
        Repaired SQL+params if repair succeeded, ``None`` if all retries
        failed.
    """
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return None

    api_url = "https://api.groq.com/openai/v1/chat/completions"
    model = "llama-3.1-8b-instant"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    error_descriptions = "\n".join(f"- [{e.code}] {e.message}" for e in errors)

    user_prompt = (
        f"ORIGINAL SQL:\n{original_sql}\n\n"
        f"ORIGINAL PARAMS:\n{json.dumps(original_params, default=str)}\n\n"
        f"VALIDATION ERRORS:\n{error_descriptions}\n\n"
        f"INTENT: {intent}\n"
        f"EXPECTED RESULT SHAPE: {expected_shape}\n\n"
        f"SCHEMA CONTEXT:\n{schema_context}\n\n"
        f"Fix the SQL and return ONLY JSON: "
        f'{{"sql": "...", "params": {{}}, "confidence": 0.0}}'
    )

    messages = [
        {"role": "system", "content": _REPAIR_SYSTEM},
        {"role": "user", "content": user_prompt},
    ]

    for attempt in range(MAX_REPAIR_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.0,
                    "max_tokens": 1024,
                    "top_p": 1,
                    "stream": False,
                }
                resp = await client.post(api_url, json=payload, headers=headers)
                resp.raise_for_status()

                raw = resp.json()["choices"][0]["message"]["content"].strip()
                parsed = _parse_repair_response(raw)
                if parsed is None:
                    messages.append({"role": "assistant", "content": raw})
                    messages.append({
                        "role": "user",
                        "content": "Invalid response. Return ONLY JSON: {\"sql\": \"...\", \"params\": {}, \"confidence\": 0.0}",
                    })
                    continue

                repaired_sql = parsed["sql"]
                repaired_params = parsed.get("params", {})

                # Validate the repaired SQL
                ok, new_errors = validate(
                    repaired_sql,
                    repaired_params,
                    allowed_tables=allowed_tables,
                    allowed_columns=allowed_columns,
                    intent=intent,
                    expected_shape=expected_shape,
                )

                if ok:
                    print(f"[SQLRepair] Repair succeeded on attempt {attempt + 1}")
                    return repaired_sql, repaired_params

                # Still invalid – feed errors back
                new_err_text = "\n".join(f"- [{e.code}] {e.message}" for e in new_errors)
                messages.append({"role": "assistant", "content": raw})
                messages.append({
                    "role": "user",
                    "content": f"Still invalid:\n{new_err_text}\nFix again. JSON only.",
                })

        except Exception as e:
            print(f"[SQLRepair] Error on attempt {attempt + 1}: {e}")

    print("[SQLRepair] All repair attempts failed")
    return None


def _parse_repair_response(raw: str) -> Optional[dict]:
    """Extract JSON from repair LLM response."""
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

