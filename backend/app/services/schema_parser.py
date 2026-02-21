"""
Schema Parser for extracting table information from SQL file
Lightweight approach: Parse schemas and provide context to LLM without executing queries
"""

import re
from typing import Dict, List, Optional
from pathlib import Path


class SchemaParser:
    """Parse SQL file to extract table schemas for LLM context"""
    
    def __init__(self, sql_file_path: str):
        self.sql_file_path = sql_file_path
        self.table_schemas = {}
        self.important_tables = [
            'appointment', 'patient', 'provider', 'clinic', 
            'appointmenttype', 'procedurelog', 'procedurecode',
            'histappointment', 'appointmentrule'
        ]
    
    def parse(self) -> bool:
        """
        Parse the SQL file to extract table schemas
        
        Returns:
            True if parsing successful, False otherwise
        """
        try:
            with open(self.sql_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            self._extract_schemas(content)
            return True
        except Exception as e:
            print(f"Error parsing SQL file: {e}")
            return False
    
    def _extract_schemas(self, content: str):
        """Extract table schemas from SQL content"""
        # Pattern to match CREATE TABLE statements
        # Matches: CREATE TABLE `table_name` ( ... ) ENGINE
        pattern = r'CREATE TABLE\s+`?(\w+)`?\s*\((.*?)\)\s*ENGINE'
        
        matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            table_name = match.group(1).lower()
            table_def = match.group(2)
            
            # Only process important tables for dental practice
            if table_name not in self.important_tables:
                continue
            
            columns = []
            primary_key = None
            
            # Parse column definitions
            for line in table_def.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                # Skip constraint definitions for now (but note PRIMARY KEY)
                if line.upper().startswith('PRIMARY KEY'):
                    pk_match = re.search(r'`?(\w+)`?', line)
                    if pk_match:
                        primary_key = pk_match.group(1)
                    continue
                
                if any(line.upper().startswith(k) for k in ['KEY', 'UNIQUE', 'FOREIGN KEY', 'INDEX']):
                    continue
                
                # Extract column name and type
                # Pattern: `ColumnName` type(size) attributes, or ColumnName type attributes,
                col_match = re.match(r'`?(\w+)`?\s+([^,]+?)(?:,|$)', line)
                if col_match:
                    col_name = col_match.group(1)
                    col_def = col_match.group(2).strip()
                    
                    # Extract just the type (first word, handling things like bigint(20), varchar(255))
                    type_match = re.match(r'(\w+(?:\([^)]+\))?)', col_def)
                    col_type = type_match.group(1) if type_match else col_def.split()[0]
                    
                    # Check for NOT NULL, DEFAULT, etc.
                    is_required = 'NOT NULL' in col_def.upper()
                    has_default = 'DEFAULT' in col_def.upper()
                    
                    columns.append({
                        'name': col_name,
                        'type': col_type,
                        'required': is_required,
                        'has_default': has_default
                    })
            
            self.table_schemas[table_name] = {
                'columns': columns,
                'primary_key': primary_key
            }
    
    def get_schema_for_llm(self) -> str:
        """
        Format schema information for LLM context
        Focuses on tables relevant to scheduling and appointments
        """
        if not self.table_schemas:
            return ""
        
        schema_text = "=== DATABASE SCHEMA INFORMATION ===\n\n"
        schema_text += "You have access to the following database tables that contain dental practice information:\n\n"
        
        # Appointment table (most important for scheduling)
        if 'appointment' in self.table_schemas:
            schema_text += "**APPOINTMENT TABLE** (Primary table for scheduling):\n"
            schema_text += "This table stores all appointment information.\n"
            schema_text += "Key columns:\n"
            for col in self.table_schemas['appointment']['columns']:
                if col['name'] in ['AptNum', 'PatNum', 'AptDateTime', 'AptStatus', 'ProvNum', 
                                   'ProcDescript', 'Note', 'ClinicNum', 'AppointmentTypeNum', 
                                   'Confirmed', 'IsNewPatient', 'IsHygiene']:
                    schema_text += f"  - {col['name']}: {col['type']}"
                    if col['required']:
                        schema_text += " (required)"
                    schema_text += "\n"
            schema_text += "\n"
            schema_text += "Important notes:\n"
            schema_text += "  - AptNum: Unique appointment ID\n"
            schema_text += "  - PatNum: Links to patient table\n"
            schema_text += "  - AptDateTime: Date and time of appointment\n"
            schema_text += "  - AptStatus: Appointment status (0=unscheduled, 1=scheduled, etc.)\n"
            schema_text += "  - ProvNum: Provider/doctor ID\n"
            schema_text += "  - ProcDescript: Description of procedure\n"
            schema_text += "  - Confirmed: Confirmation status\n"
            schema_text += "  - IsNewPatient: Whether this is a new patient\n"
            schema_text += "  - IsHygiene: Whether this is a hygiene appointment\n"
            schema_text += "\n"
        
        # Patient table
        if 'patient' in self.table_schemas:
            schema_text += "**PATIENT TABLE** (Patient information):\n"
            schema_text += "Key columns:\n"
            for col in self.table_schemas['patient']['columns']:
                if col['name'] in ['PatNum', 'LName', 'FName', 'Preferred', 'HmPhone', 
                                   'WirelessPhone', 'Email', 'Birthdate', 'PatStatus', 
                                   'PriProv', 'ClinicNum', 'DateFirstVisit']:
                    schema_text += f"  - {col['name']}: {col['type']}\n"
            schema_text += "\n"
        
        # Provider table
        if 'provider' in self.table_schemas:
            schema_text += "**PROVIDER TABLE** (Doctor/provider information):\n"
            schema_text += "Key columns:\n"
            for col in self.table_schemas['provider']['columns']:
                if col['name'] in ['ProvNum', 'Abbr', 'LName', 'FName', 'IsHidden', 'ProvStatus']:
                    schema_text += f"  - {col['name']}: {col['type']}\n"
            schema_text += "\n"
        
        # AppointmentType table
        if 'appointmenttype' in self.table_schemas:
            schema_text += "**APPOINTMENTTYPE TABLE** (Appointment type definitions):\n"
            schema_text += "Key columns:\n"
            for col in self.table_schemas['appointmenttype']['columns']:
                if col['name'] in ['AppointmentTypeNum', 'AppointmentTypeName', 'AppointmentTypeColor']:
                    schema_text += f"  - {col['name']}: {col['type']}\n"
            schema_text += "\n"
        
        # Clinic table
        if 'clinic' in self.table_schemas:
            schema_text += "**CLINIC TABLE** (Clinic/location information):\n"
            schema_text += "Key columns:\n"
            for col in self.table_schemas['clinic']['columns']:
                if col['name'] in ['ClinicNum', 'Description', 'Address', 'City', 'State', 'Phone']:
                    schema_text += f"  - {col['name']}: {col['type']}\n"
            schema_text += "\n"
        
        # Procedure-related tables
        if 'procedurelog' in self.table_schemas:
            schema_text += "**PROCEDURELOG TABLE** (Completed procedures):\n"
            schema_text += "Contains records of procedures performed on patients.\n"
            schema_text += "\n"
        
        schema_text += "=== HOW TO USE THIS INFORMATION ===\n"
        schema_text += "When doctors ask about their schedule or appointments:\n"
        schema_text += "1. Reference the APPOINTMENT table structure to understand what information is available\n"
        schema_text += "2. Understand that appointments are linked to patients (PatNum) and providers (ProvNum)\n"
        schema_text += "3. Appointment times are stored in AptDateTime\n"
        schema_text += "4. Appointment status indicates if it's scheduled, confirmed, etc.\n"
        schema_text += "5. You can explain what information would be available in the database\n"
        schema_text += "6. If asked about specific appointments, explain that you understand the data structure\n"
        schema_text += "   but would need actual database queries to retrieve specific records\n"
        schema_text += "\n"
        schema_text += "Example responses:\n"
        schema_text += "- 'I can help you understand appointment information. The database contains appointment records'\n"
        schema_text += "  'with details like date/time, patient, provider, and procedure descriptions.'\n"
        schema_text += "- 'To check your schedule, I would query the appointment table filtered by your provider number'\n"
        schema_text += "  'and date range. The appointments include patient information, times, and status.'\n"
        schema_text += "\n"
        
        return schema_text
    
    def get_table_names(self) -> List[str]:
        """Get list of parsed table names"""
        return list(self.table_schemas.keys())
    
    def get_table_schema(self, table_name: str) -> Optional[Dict]:
        """Get schema for a specific table"""
        return self.table_schemas.get(table_name.lower())


