# ICD9 Query Examples

## Overview
The system can now query ICD9 codes by:
- **ICD9 Code** (e.g., "001", "001.0")
- **Description** (partial text search)
- **Date** (DateTStamp field)
- **ICD9Num** (primary key)

## Example Questions and Answers

### Question 1: "What is ICD9 code 001?"
**System Process:**
1. Extracts code "001"
2. Queries `get_icd9_by_code("001")`
3. Returns matching records

**Expected Answer:**
```
ICD9 Code: 001
Description: CHOLERA
ICD9 Number: 1
Date: July 12, 2011
```

### Question 2: "Tell me about ICD9 code 001.0"
**System Process:**
1. Extracts code "001.0"
2. Queries `get_icd9_by_code("001.0")`
3. Returns specific record

**Expected Answer:**
```
ICD9 Code: 001.0
Description: CHOLERA DUE TO VIBRIO CHOLERAE
ICD9 Number: 2
Date: November 15, 2011
```

### Question 3: "What ICD9 codes are related to cholera?"
**System Process:**
1. Extracts description keyword "cholera"
2. Queries `get_icd9_by_description("cholera")`
3. Returns all matching records

**Expected Answer:**
```
Found 4 ICD9 code(s):

1. Code: 001 - CHOLERA (ID: 1)
2. Code: 001.0 - CHOLERA DUE TO VIBRIO CHOLERAE (ID: 2)
3. Code: 001.1 - CHOLERA DUE TO VIBRIO CHOLERAE EL TOR (ID: 3)
4. Code: 001.9 - CHOLERA UNSPECIFIED (ID: 4)
```

### Question 4: "Show me ICD9 codes from 2011-11-15"
**System Process:**
1. Extracts date "2011-11-15"
2. Queries `get_icd9_by_date("2011-11-15")`
3. Returns all records with that date

**Expected Answer:**
```
Found 20 ICD9 code(s):

1. Code: 001.0 - CHOLERA DUE TO VIBRIO CHOLERAE (ID: 2)
2. Code: 001.1 - CHOLERA DUE TO VIBRIO CHOLERAE EL TOR (ID: 3)
3. Code: 001.9 - CHOLERA UNSPECIFIED (ID: 4)
[... continues with all codes from that date]
```

### Question 5: "What is ICD9Num 12345?"
**System Process:**
1. Extracts ICD9Num "12345"
2. Queries `get_icd9_by_num(12345)`
3. Returns specific record

**Expected Answer:**
```
ICD9 Code: [code from record]
Description: [description from record]
ICD9 Number: 12345
Date: [date from record]
```

### Question 6: "Find ICD9 codes for typhoid"
**System Process:**
1. Extracts description keyword "typhoid"
2. Queries `get_icd9_by_description("typhoid")`
3. Returns matching records

**Expected Answer:**
```
Found 6 ICD9 code(s):

1. Code: 002 - TYPHOID AND PARATYPHOID FEVERS (ID: 5)
2. Code: 002.0 - TYPHOID FEVER (ID: 6)
3. Code: 002.1 - PARATYPHOID FEVER A (ID: 7)
[... continues]
```

## Natural Language Variations

The system understands various phrasings:
- "What is ICD9 code X?"
- "Tell me about code X"
- "ICD9 X"
- "Show me codes for [description]"
- "Find ICD9 codes from [date]"
- "What's the description for code X?"

## Response Style

**Important:** The LLM will respond naturally without mentioning:
- ❌ "I'm querying the database..."
- ❌ "Let me search for..."
- ❌ "Based on the query results..."
- ✅ Simply provides the information directly

**Example:**
- ❌ Bad: "I found 3 ICD9 codes matching your query: ..."
- ✅ Good: "Here are 3 ICD9 codes related to cholera: ..."

## Efficiency Features

1. **Smart Query Selection**: Automatically chooses the most specific query method
2. **Result Limiting**: Limits results to prevent overwhelming responses
3. **Caching Ready**: Database service structure supports future caching
4. **Indexed Queries**: Uses indexed columns (ICD9Code, ICD9Num) for fast lookups


