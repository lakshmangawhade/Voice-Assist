# Database Integration Guide

## Overview
This system enables the LLM to access actual data from your SQL file to answer questions about schedules, appointments, and patients.

## How It Works

### Step 1: Database Initialization
When the backend starts, it:
1. Reads the SQL file (`backend/data/data.sql`)
2. Converts MySQL syntax to SQLite
3. Creates a SQLite database (`backend/data/dental_practice.db`)
4. Loads all tables and data

### Step 2: Question Analysis
When a doctor asks a question:
1. **QueryService** analyzes the question
2. Determines if database data is needed
3. Identifies what type of query (appointments, patients, etc.)

### Step 3: Data Retrieval
If data is needed:
1. **DatabaseService** executes safe, predefined queries
2. Formats the results for the LLM
3. Includes the data in the LLM prompt

### Step 4: Response Generation
The LLM:
1. Receives the question + database data
2. Generates an accurate, data-driven response
3. References specific appointments, patients, times, etc.

## Example Questions and Answers

### Question 1: "What's my schedule today?"
**System Process:**
1. QueryService detects "schedule" and "today"
2. Calls `get_appointments_today(prov_num)`
3. Formats appointment data
4. LLM receives: Question + Appointment data

**Expected Answer:**
```
You have 3 appointments scheduled for today:

1. December 15, 2024 at 09:00 AM
   Patient: Smith, John
   Provider: DOC
   Procedure: Cleaning
   Status: Scheduled

2. December 15, 2024 at 02:00 PM
   Patient: Johnson, Mary
   Provider: DOC
   Procedure: Root Canal
   Status: Scheduled

3. December 15, 2024 at 04:30 PM
   Patient: Williams, David
   Provider: DOC
   Procedure: Checkup
   Status: Scheduled
```

### Question 2: "Do I have any appointments this week?"
**System Process:**
1. QueryService detects "appointments" and "this week"
2. Calls `get_appointments_this_week(prov_num)`
3. Formats all appointments for the week
4. LLM receives: Question + Week's appointment data

**Expected Answer:**
```
You have 8 appointments scheduled for this week:

Monday, December 15:
- 9:00 AM: Smith, John - Cleaning
- 2:00 PM: Johnson, Mary - Root Canal
- 4:30 PM: Williams, David - Checkup

Tuesday, December 16:
- 10:00 AM: Brown, Sarah - Filling
- 3:00 PM: Davis, Michael - Extraction

[Continues for rest of week...]
```

### Question 3: "Who is patient John Smith?"
**System Process:**
1. QueryService detects "patient" and extracts "John Smith"
2. Calls `get_patient_by_name("John", "Smith")`
3. Formats patient information
4. LLM receives: Question + Patient data

**Expected Answer:**
```
Patient Information:
Name: John Smith
Phone: 555-1234
Email: john.smith@email.com
Patient Number: 12345
```

### Question 4: "What appointments do I have tomorrow?"
**System Process:**
1. QueryService detects "appointments" and "tomorrow"
2. Calculates tomorrow's date
3. Calls `get_appointments_by_date_range(tomorrow, tomorrow, prov_num)`
4. Formats tomorrow's appointments
5. LLM receives: Question + Tomorrow's appointment data

**Expected Answer:**
```
You have 2 appointments scheduled for tomorrow, December 16:

1. December 16, 2024 at 10:00 AM
   Patient: Brown, Sarah
   Provider: DOC
   Procedure: Filling
   Status: Scheduled

2. December 16, 2024 at 3:00 PM
   Patient: Davis, Michael
   Provider: DOC
   Procedure: Extraction
   Status: Scheduled
```

### Question 5: "Show me my schedule"
**System Process:**
1. QueryService detects "schedule" (defaults to today)
2. Calls `get_appointments_today(prov_num)`
3. Formats today's appointments
4. LLM receives: Question + Today's appointment data

**Expected Answer:**
```
Here's your schedule for today:

1. 9:00 AM - Smith, John (Cleaning)
2. 2:00 PM - Johnson, Mary (Root Canal)
3. 4:30 PM - Williams, David (Checkup)
```

## Key Features

### 1. Automatic Data Detection
- System automatically detects when questions need database data
- No need to explicitly request data - it's included automatically

### 2. Safe Queries
- Only SELECT queries are allowed
- Predefined query methods prevent SQL injection
- No direct SQL execution from user input

### 3. Context-Aware Responses
- LLM receives both the question AND the relevant data
- Responses are accurate and reference actual data
- No generic "I would need to check the database" responses

### 4. Natural Language Processing
- Understands variations: "schedule", "appointments", "today", "this week"
- Extracts patient names from questions
- Handles time references intelligently

## Database Schema Support

The system supports these key tables:
- **appointment**: All appointment records
- **patient**: Patient information
- **provider**: Doctor/provider information
- **clinic**: Clinic locations
- **appointmenttype**: Appointment type definitions
- **procedurelog**: Completed procedures
- **procedurecode**: Procedure codes

## Setup Instructions

1. **Ensure SQL file exists**: `backend/data/data.sql`
2. **Start the backend**: Database initializes automatically
3. **Check health endpoint**: `GET /health` shows `database_initialized: true`
4. **Ask questions**: System automatically queries data when needed

## Troubleshooting

### Database not initializing
- Check that `backend/data/data.sql` exists
- Check file permissions
- Look for error messages in console

### No data returned
- SQL file might not have INSERT statements
- Tables might be empty
- Check database file: `backend/data/dental_practice.db`

### Queries not working
- Verify tables were created: Check SQLite database
- Check query service logs
- Verify provider number if filtering by doctor

## Next Steps

To add more query types:
1. Add method to `DatabaseService` (e.g., `get_appointments_by_patient`)
2. Add handler to `QueryService.analyze_and_query()`
3. Add formatter method in `QueryService`
4. Test with example questions



