# Database Setup - Complete Guide

## Current Status

The database integration system has been fully implemented with:

1. **DatabaseService** - Handles SQL parsing, conversion, and queries
2. **QueryService** - Analyzes questions and fetches relevant data
3. **LLMService** - Updated to use database data naturally

## Implementation Details

### Database Service (`database_service.py`)

**Key Methods:**
- `initialize_database()` - Parses SQL file and creates SQLite database
- `get_icd9_by_code(code)` - Query ICD9 by code
- `get_icd9_by_description(desc)` - Search ICD9 by description
- `get_icd9_by_date(date)` - Query ICD9 by date
- `get_icd9_by_num(num)` - Query ICD9 by ICD9Num
- `search_icd9()` - Flexible search with multiple criteria
- `get_appointments_today()` - Get today's appointments
- `get_appointments_this_week()` - Get week's appointments
- `get_patient_by_name()` - Search patients
- `get_provider_info()` - Get provider information

### Query Service (`query_service.py`)

**Key Features:**
- Automatically detects when questions need database data
- Extracts ICD9 codes, dates, descriptions from natural language
- Formats data for LLM consumption
- Handles appointments, patients, providers, and ICD9 codes

### LLM Service (`llm_service.py`)

**Key Updates:**
- Receives database data automatically when needed
- Responds naturally without mentioning queries/databases
- Uses actual data to provide accurate answers

## Testing the System

### Step 1: Verify Database Initialization

```python
from app.services.database_service import DatabaseService
import sqlite3

db = DatabaseService()
result = db.initialize_database()

# Check tables
conn = sqlite3.connect('data/dental_practice.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]
print(f"Tables created: {len(tables)}")
print(f"Critical tables: {set(['icd9', 'appointment', 'patient', 'provider']) & set(tables)}")
```

### Step 2: Test ICD9 Queries

```python
# Test ICD9 queries
result = db.get_icd9_by_code('001')
print(f"ICD9 code 001: {len(result)} records")

result = db.get_icd9_by_description('cholera', limit=5)
print(f"ICD9 cholera search: {len(result)} records")
```

### Step 3: Test Query Service

```python
from app.services.query_service import QueryService

query_service = QueryService(db)
result = query_service.analyze_and_query("What is ICD9 code 001?")
print(f"Query type: {result['query_type']}")
print(f"Formatted data: {result['formatted_data']}")
```

### Step 4: Test LLM Integration

```python
from app.services.llm_service import LLMService
import asyncio

llm_service = LLMService()
response = await llm_service.get_response(
    user_message="What is ICD9 code 001?",
    conversation_history=[],
    query_service=query_service
)
print(response)
```

## Expected Behavior

### Question: "What is ICD9 code 001?"

**System Process:**
1. QueryService detects "ICD9 code" and extracts "001"
2. DatabaseService queries `get_icd9_by_code('001')`
3. Data is formatted and sent to LLM
4. LLM responds: "ICD9 Code: 001, Description: CHOLERA, ICD9 Number: 1"

### Question: "Tell me about ICD9 codes for cholera"

**System Process:**
1. QueryService detects "ICD9" and "cholera"
2. DatabaseService queries `get_icd9_by_description('cholera')`
3. Multiple records returned and formatted
4. LLM responds with list of matching ICD9 codes

### Question: "What's my schedule today?"

**System Process:**
1. QueryService detects "schedule" and "today"
2. DatabaseService queries `get_appointments_today()`
3. Appointments formatted with times and patient names
4. LLM responds with today's schedule

## Troubleshooting

### Issue: No tables created

**Solution:**
- Check SQL file exists at `backend/data/data.sql`
- Verify SQL parsing regex is matching CREATE TABLE statements
- Check for syntax errors in converted SQL
- Review error messages during initialization

### Issue: ICD9 queries return empty

**Solution:**
- Verify ICD9 table exists: `SELECT COUNT(*) FROM icd9`
- Check if INSERT statements were executed
- Verify table has data: `SELECT * FROM icd9 LIMIT 5`

### Issue: LLM doesn't use database data

**Solution:**
- Verify QueryService is passed to LLM service
- Check if `needs_data` is True in query result
- Verify formatted_data is not empty
- Check LLM system prompt includes data context

## Next Steps

1. **Verify Database Creation**: Run initialization and check all tables exist
2. **Test Queries**: Verify each query method returns correct data
3. **Test LLM Integration**: Ensure LLM receives and uses data correctly
4. **Production Readiness**: Add error handling, logging, and monitoring

## Files Modified

1. `backend/app/services/database_service.py` - Database operations
2. `backend/app/services/query_service.py` - Question analysis and queries
3. `backend/app/services/llm_service.py` - LLM integration with data
4. `backend/main.py` - Service initialization and integration

## Notes

- Database file location: `backend/data/dental_practice.db`
- SQL file location: `backend/data/data.sql`
- All queries are read-only (SELECT only) for security
- Database initializes automatically on backend startup


