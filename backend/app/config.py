"""
Application configuration for the dental voice assistant pipeline.

Add new intents by appending to SUPPORTED_INTENTS.
Add new clinic timezone mappings to CLINIC_TIMEZONE_MAP.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Timezone configuration
# ---------------------------------------------------------------------------
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Asia/Kolkata")

# Map clinic IDs / names to IANA timezone strings.
# Extend this dict when multi-site support is needed.
CLINIC_TIMEZONE_MAP: dict[str, str] = {
    # "1": "America/New_York",
}

# ---------------------------------------------------------------------------
# Query / safety limits
# ---------------------------------------------------------------------------
MAX_RESULT_LIMIT = 50          # hard cap sent in LIMIT clause
DEFAULT_RESULT_LIMIT = 20      # used when caller does not specify
MAX_REPAIR_RETRIES = 2         # LLM SQL repair attempts before failing
MAX_MESSAGE_LENGTH = 2000      # sanitise long voice transcripts

# ---------------------------------------------------------------------------
# Supported intents (READ + WRITE)
# ---------------------------------------------------------------------------
READ_INTENTS = frozenset({
    "COUNT_APPOINTMENTS",
    "LIST_APPOINTMENTS",
    "PROVIDER_SCHEDULE",
    "PATIENT_UPCOMING",
    "AVAILABILITY",
    "PATIENT_LOOKUP",
    "GENERAL_QUERY",
})

WRITE_INTENTS = frozenset({
    "RESCHEDULE_APPOINTMENT",
    "CANCEL_APPOINTMENT",
    "CREATE_APPOINTMENT",
})

SUPPORTED_INTENTS = READ_INTENTS | WRITE_INTENTS

# ---------------------------------------------------------------------------
# Tables the scheduling pipeline is allowed to touch
# ---------------------------------------------------------------------------
SCHEDULING_TABLES = [
    "appointment",
    "patient",
    "provider",
    "operatory",
    "appointmenttype",
    "clinic",
    "procedurelog",
    "procedurecode",
    "schedule",
    "scheduleop",
]

# ---------------------------------------------------------------------------
# Appointment status mapping  (Open Dental conventions)
# ---------------------------------------------------------------------------
APT_STATUS = {
    1: "Scheduled",
    2: "Complete",
    3: "UnschedList",
    4: "ASAP",
    5: "Broken",
    6: "Planned",
}

APT_STATUS_REVERSE = {v.lower(): k for k, v in APT_STATUS.items()}

