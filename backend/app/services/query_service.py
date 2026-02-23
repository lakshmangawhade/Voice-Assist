"""
Query Service for analyzing user questions and fetching relevant data
Acts as an interface between LLM and database
"""

import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from app.services.database_service import DatabaseService


class QueryService:
    """Service for analyzing questions and querying database"""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
    
    def analyze_and_query(self, user_message: str, prov_num: Optional[int] = None) -> Dict[str, Any]:
        """
        Analyze user message and fetch relevant data from database
        Dynamically determines which table to query based on user question
        
        Args:
            user_message: User's question
            prov_num: Optional provider number (doctor ID)
        
        Returns:
            Dictionary with query_type, data, and formatted_response
        """
        message_lower = user_message.lower()
        
        # Get available tables
        tables = self.db_service.get_tables()
        table_set = {t.lower() for t in tables}
        
        # Check for schedule/appointment queries
        if any(keyword in message_lower for keyword in ['schedule', 'appointment', 'appointments', 'today', 'tomorrow', 'week']):
            if 'appointment' in table_set:
                return self._handle_schedule_query(user_message, message_lower, prov_num)
        
        # Check for patient queries
        elif any(keyword in message_lower for keyword in ['patient', 'patients', 'who is', 'find patient']):
            if 'patient' in table_set:
                return self._handle_patient_query(user_message, message_lower)
        
        # Check for provider queries
        elif any(keyword in message_lower for keyword in ['provider', 'doctor', 'who am i', 'my info']):
            if 'provider' in table_set:
                return self._handle_provider_query(prov_num)
        
        # Generic table search - try to find relevant table based on keywords
        return self._handle_generic_query(user_message, message_lower, tables)
    
    def _handle_schedule_query(self, user_message: str, message_lower: str, prov_num: Optional[int]) -> Dict[str, Any]:
        """Handle schedule/appointment related queries"""
        today = datetime.now()
        
        # Determine time range
        if 'today' in message_lower:
            appointments = self.db_service.get_appointments_today(prov_num)
            time_range = "today"
        elif 'tomorrow' in message_lower:
            tomorrow = (today + timedelta(days=1)).strftime('%Y-%m-%d')
            appointments = self.db_service.get_appointments_by_date_range(tomorrow, tomorrow, prov_num)
            time_range = "tomorrow"
        elif 'week' in message_lower or 'this week' in message_lower:
            appointments = self.db_service.get_appointments_this_week(prov_num)
            time_range = "this week"
        else:
            # Default to today
            appointments = self.db_service.get_appointments_today(prov_num)
            time_range = "today"
        
        # Format data for LLM - always provide context even if empty
        formatted_data = self._format_appointments(appointments, time_range)
        
        return {
            'query_type': 'appointments',
            'data': appointments,
            'formatted_data': formatted_data,
            'needs_data': True,  # Always True for data queries, even if empty
            'time_range': time_range
        }
    
    def _handle_patient_query(self, user_message: str, message_lower: str) -> Dict[str, Any]:
        """Handle patient-related queries"""
        # Try to extract patient name
        # Look for patterns like "patient John", "John Smith", etc.
        name_patterns = [
            r'patient\s+(\w+)',
            r'(\w+)\s+(\w+)',  # First and last name
            r'who is\s+(\w+)',
            r'find\s+patient\s+(\w+)'
        ]
        
        first_name = ""
        last_name = ""
        
        for pattern in name_patterns:
            match = re.search(pattern, message_lower)
            if match:
                if len(match.groups()) == 2:
                    first_name = match.group(1)
                    last_name = match.group(2)
                else:
                    # Assume it's a last name
                    last_name = match.group(1)
                break
        
        patients = self.db_service.get_patient_by_name(first_name, last_name)
        
        formatted_data = self._format_patients(patients)
        
        return {
            'query_type': 'patients',
            'data': patients,
            'formatted_data': formatted_data,
            'needs_data': True  # Always True for data queries, even if empty
        }
    
    def _handle_provider_query(self, prov_num: Optional[int]) -> Dict[str, Any]:
        """Handle provider-related queries"""
        providers = self.db_service.get_provider_info(prov_num)
        
        formatted_data = self._format_providers(providers)
        
        return {
            'query_type': 'providers',
            'data': providers,
            'formatted_data': formatted_data,
            'needs_data': True  # Always True for data queries, even if empty
        }
    
    def _format_appointments(self, appointments: List[Dict], time_range: str) -> str:
        """Format appointment data for LLM"""
        if not appointments:
            return f"You have no appointments scheduled for {time_range}."
        
        formatted = f"You have {len(appointments)} appointment(s) scheduled for {time_range}:\n\n"
        
        for i, apt in enumerate(appointments, 1):
            # Parse datetime
            apt_datetime = apt.get('AptDateTime', '')
            if apt_datetime and apt_datetime != '0001-01-01 00:00:00':
                try:
                    dt = datetime.strptime(apt_datetime, '%Y-%m-%d %H:%M:%S')
                    date_str = dt.strftime('%B %d, %Y')
                    time_str = dt.strftime('%I:%M %p')
                except:
                    date_str = apt_datetime
                    time_str = ""
            else:
                date_str = "Not scheduled"
                time_str = ""
            
            patient_name = apt.get('PatientName', 'Unknown Patient')
            provider = apt.get('ProviderAbbr', '')
            proc_desc = apt.get('ProcDescript', '')
            note = apt.get('Note', '')
            status = apt.get('AptStatus', 0)
            
            formatted += f"{i}. {date_str}"
            if time_str:
                formatted += f" at {time_str}"
            formatted += f"\n   Patient: {patient_name}"
            if provider:
                formatted += f"\n   Provider: {provider}"
            if proc_desc:
                formatted += f"\n   Procedure: {proc_desc}"
            if note:
                formatted += f"\n   Note: {note}"
            formatted += f"\n   Status: {'Scheduled' if status == 1 else 'Unscheduled' if status == 0 else 'Other'}\n\n"
        
        return formatted
    
    def _format_patients(self, patients: List[Dict]) -> str:
        """Format patient data for LLM"""
        if not patients:
            return "No patients found matching your search."
        
        if len(patients) == 1:
            p = patients[0]
            formatted = f"Patient Information:\n"
            formatted += f"Name: {p.get('FName', '')} {p.get('LName', '')}\n"
            formatted += f"Phone: {p.get('HmPhone', 'N/A')}\n"
            formatted += f"Email: {p.get('Email', 'N/A')}\n"
            formatted += f"Patient Number: {p.get('PatNum', 'N/A')}"
        else:
            formatted = f"Found {len(patients)} patients:\n\n"
            for i, p in enumerate(patients[:10], 1):  # Limit to 10
                formatted += f"{i}. {p.get('FName', '')} {p.get('LName', '')} (ID: {p.get('PatNum', 'N/A')})\n"
        
        return formatted
    
    def _format_providers(self, providers: List[Dict]) -> str:
        """Format provider data for LLM"""
        if not providers:
            return "No provider information found."
        
        p = providers[0]  # Usually just one
        formatted = f"Provider Information:\n"
        formatted += f"Name: {p.get('FName', '')} {p.get('LName', '')}\n"
        formatted += f"Abbreviation: {p.get('Abbr', 'N/A')}\n"
        formatted += f"Provider Number: {p.get('ProvNum', 'N/A')}"
        
        return formatted
    
    def _handle_generic_query(self, user_message: str, message_lower: str, tables: List[str]) -> Dict[str, Any]:
        """
        Handle generic queries by searching across all tables
        Tries to match user question to available tables and columns
        """
        # Extract potential table names from user message
        # Look for table names that might be mentioned
        table_keywords = {
            'appointment': ['appointment', 'schedule', 'booking'],
            'patient': ['patient', 'person', 'client'],
            'provider': ['provider', 'doctor', 'dentist'],
            'icd9': ['icd9', 'icd-9', 'diagnosis', 'code'],
            'procedure': ['procedure', 'treatment', 'service'],
            'procedurecode': ['procedure code', 'treatment code'],
            'claimproc': ['claimproc', 'claim procedure', 'claim proc'],
            'claim': ['claim', 'insurance', 'billing'],
            'payment': ['payment', 'transaction', 'charge'],
        }
        
        # Direct table-name mention has highest priority
        matched_table = None
        # Sort by length desc so claimproc matches before claim
        for table_name in sorted(tables, key=lambda t: len(t), reverse=True):
            if re.search(rf'\b{re.escape(table_name.lower())}\b', message_lower):
                matched_table = table_name
                break

        # Find matching table by keyword map
        for table_name, keywords in table_keywords.items():
            if matched_table:
                break
            if table_name in {t.lower() for t in tables}:
                if any(kw in message_lower for kw in keywords):
                    matched_table = next((t for t in tables if t.lower() == table_name), table_name)
                    break
        
        # If no specific match, try to search in common tables
        if not matched_table:
            # Try searching in tables that might contain the answer
            preferred = {'icd9', 'procedurecode', 'procedure', 'claim', 'payment', 'appointment', 'patient', 'provider'}
            search_tables = [t for t in tables if t.lower() in preferred]
            if search_tables:
                matched_table = search_tables[0]  # Use first available
        
        if not matched_table:
            return {
                'query_type': 'none',
                'data': None,
                'formatted_data': None,
                'needs_data': False
            }
        
        # Get table schema to find searchable columns
        schema = self.db_service.get_table_schema(matched_table)
        if not schema:
            return {
                'query_type': 'none',
                'data': None,
                'formatted_data': None,
                'needs_data': False
            }
        
        # Find text/searchable columns (usually varchar, text, char types)
        text_columns = [col for col, col_type in schema.items() 
                       if any(t in col_type.lower() for t in ['varchar', 'text', 'char', 'string'])]
        
        # Find numeric/ID columns
        id_columns = [col for col in schema.keys() 
                      if any(kw in col.lower() for kw in ['id', 'num', 'code', 'key'])]

        # Extract explicit requested columns from the question
        requested_columns = [
            col for col in schema.keys()
            if re.search(rf'\b{re.escape(col.lower())}\b', message_lower)
        ]

        # Extract explicit filters like "PatNum 4895" or "PatNum=4895"
        where_parts: List[str] = []
        where_params: List[Any] = []
        for col in schema.keys():
            # numeric equality pattern
            num_match = re.search(rf'\b{re.escape(col.lower())}\b\s*(?:=|:)?\s*(\d+)\b', message_lower)
            if num_match:
                where_parts.append(f"`{col}` = %s")
                where_params.append(int(num_match.group(1)))
                continue
            # quoted text equality pattern
            txt_match = re.search(rf'\b{re.escape(col.lower())}\b\s*(?:=|:)?\s*[\"\']([^\"\']+)[\"\']', user_message, re.IGNORECASE)
            if txt_match:
                where_parts.append(f"`{col}` = %s")
                where_params.append(txt_match.group(1).strip())
        
        # Extract search terms from user message
        search_terms = self._extract_search_terms(user_message, message_lower)
        
        # Try to query the table
        results = []
        if where_parts:
            # explicit structured query path
            results = self.db_service.query_table(
                table_name=matched_table,
                columns=requested_columns if requested_columns else None,
                where_clause=" AND ".join(where_parts),
                where_params=where_params,
                limit=20
            )
        elif search_terms:
            # Search in text columns
            if text_columns:
                results = self.db_service.search_table(
                    table_name=matched_table,
                    search_columns=text_columns[:3],  # Limit to first 3 columns
                    search_term=search_terms[0],
                    limit=20
                )
            
            # If no results, try exact match on ID columns using first numeric mention
            if not results and id_columns:
                # Extract numbers from message
                numbers = re.findall(r'\b\d+\b', user_message)
                if numbers:
                    for id_col in id_columns[:2]:  # Try first 2 ID columns
                        try:
                            results = self.db_service.query_table(
                                table_name=matched_table,
                                where_clause=f"`{id_col}` = %s",
                                where_params=[numbers[0]],
                                limit=10
                            )
                            if results:
                                break
                        except:
                            continue
        else:
            # No search terms - get recent/limited records
            results = self.db_service.query_table(
                table_name=matched_table,
                limit=10
            )
        
        formatted_data = self._format_generic_results(results, matched_table)
        
        return {
            'query_type': matched_table,
            'data': results,
            'formatted_data': formatted_data,
            'needs_data': True  # Always True for data queries, even if empty
        }
    
    def _extract_search_terms(self, user_message: str, message_lower: str) -> List[str]:
        """Extract search terms from user message"""
        # Remove common question words
        stop_words = ['what', 'is', 'are', 'the', 'a', 'an', 'for', 'with', 'about', 
                     'show', 'me', 'tell', 'find', 'search', 'get', 'list', 'all']
        
        # Extract quoted strings
        quoted = re.findall(r'["\']([^"\']+)["\']', user_message)
        if quoted:
            return quoted
        
        # Extract words after question keywords
        patterns = [
            r'(?:what|tell|show|find|search|get|list).*?(?:is|are|for|about)\s+([^\s]+(?:\s+[^\s]+){0,3})',
            r'(?:code|description|name|id|number)\s+([^\s]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                term = match.group(1).strip()
                # Remove stop words
                words = [w for w in term.split() if w.lower() not in stop_words]
                if words:
                    return [' '.join(words)]
        
        # Fallback: extract significant words (3+ chars, not stop words)
        words = re.findall(r'\b\w{3,}\b', message_lower)
        significant = [w for w in words if w.lower() not in stop_words]
        return significant[:3]  # Return first 3 significant words
    
    def _format_generic_results(self, results: List[Dict], table_name: str) -> str:
        """Format generic query results for LLM"""
        if not results:
            return f"No information found in {table_name} table matching your query. There are no records available."
        
        if len(results) == 1:
            # Single result - show all fields
            record = results[0]
            formatted = f"Information from {table_name}:\n\n"
            for key, value in record.items():
                if value is not None and str(value).strip():
                    formatted += f"{key}: {value}\n"
            return formatted
        else:
            # Multiple results - show key fields
            formatted = f"Found {len(results)} result(s) from {table_name}:\n\n"
            
            # Identify key columns (usually first few or ID/name columns)
            if results:
                key_columns = list(results[0].keys())[:5]  # First 5 columns
                
                for i, record in enumerate(results[:15], 1):  # Limit to 15
                    formatted += f"{i}. "
                    key_values = []
                    for col in key_columns:
                        val = record.get(col)
                        if val is not None and str(val).strip():
                            key_values.append(f"{col}={val}")
                    formatted += " | ".join(key_values[:3])  # Show first 3 key-value pairs
                    formatted += "\n"
            
            return formatted


