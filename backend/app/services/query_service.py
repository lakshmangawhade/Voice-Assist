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
        Analyze user message and fetch relevant data
        
        Args:
            user_message: User's question
            prov_num: Optional provider number (doctor ID)
        
        Returns:
            Dictionary with query_type, data, and formatted_response
        """
        message_lower = user_message.lower()
        
        # Check for schedule/appointment queries
        if any(keyword in message_lower for keyword in ['schedule', 'appointment', 'appointments', 'today', 'tomorrow', 'week']):
            return self._handle_schedule_query(user_message, message_lower, prov_num)
        
        # Check for patient queries
        elif any(keyword in message_lower for keyword in ['patient', 'patients', 'who is', 'find patient']):
            return self._handle_patient_query(user_message, message_lower)
        
        # Check for provider queries
        elif any(keyword in message_lower for keyword in ['provider', 'doctor', 'who am i', 'my info']):
            return self._handle_provider_query(prov_num)
        
        # Check for ICD9 queries (more specific patterns first)
        elif any(keyword in message_lower for keyword in ['icd9', 'icd-9', 'icd code', 'diagnosis code']) or \
             (re.search(r'\b\d{3}(?:\.\d+)?\b', user_message) and any(kw in message_lower for kw in ['code', 'icd'])):
            return self._handle_icd9_query(user_message, message_lower)
        
        # Default: no data needed
        return {
            'query_type': 'none',
            'data': None,
            'formatted_data': None,
            'needs_data': False
        }
    
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
        
        # Format data for LLM
        formatted_data = self._format_appointments(appointments, time_range)
        
        return {
            'query_type': 'appointments',
            'data': appointments,
            'formatted_data': formatted_data,
            'needs_data': True,
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
            'needs_data': True
        }
    
    def _handle_provider_query(self, prov_num: Optional[int]) -> Dict[str, Any]:
        """Handle provider-related queries"""
        providers = self.db_service.get_provider_info(prov_num)
        
        formatted_data = self._format_providers(providers)
        
        return {
            'query_type': 'providers',
            'data': providers,
            'formatted_data': formatted_data,
            'needs_data': True
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
    
    def _handle_icd9_query(self, user_message: str, message_lower: str) -> Dict[str, Any]:
        """Handle ICD9-related queries"""
        # Extract ICD9 code (e.g., "001", "001.0", "ICD9 001")
        code_pattern = r'\b(\d{3}(?:\.\d+)?)\b'
        code_match = re.search(code_pattern, user_message)
        icd9_code = code_match.group(1) if code_match else None
        
        # Extract ICD9 number
        num_pattern = r'\bicd9\s*num(?:ber)?\s*:?\s*(\d+)\b|\bid\s*:?\s*(\d{4,})\b'
        num_match = re.search(num_pattern, message_lower)
        icd9_num = None
        if num_match:
            icd9_num = int(num_match.group(1) or num_match.group(2)) if (num_match.group(1) or num_match.group(2)) else None
        
        # Extract date
        date_patterns = [
            r'\b(\d{4}-\d{2}-\d{2})\b',  # YYYY-MM-DD
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',  # MM/DD/YYYY
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2}),?\s+(\d{4})\b',
        ]
        
        date_str = None
        for pattern in date_patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                if len(match.groups()) == 1:
                    date_str = match.group(1)
                elif len(match.groups()) == 3:
                    # Month name format
                    month_name = match.group(1).lower()
                    day = match.group(2)
                    year = match.group(3)
                    months = ['january', 'february', 'march', 'april', 'may', 'june',
                             'july', 'august', 'september', 'october', 'november', 'december']
                    month_num = str(months.index(month_name) + 1).zfill(2)
                    date_str = f"{year}-{month_num}-{day.zfill(2)}"
                break
        
        # Extract description keywords
        description_keywords = []
        if any(kw in message_lower for kw in ['description', 'what is', 'tell me about', 'search for', 'find']):
            # Try to extract description search terms after keywords
            desc_pattern = r'(?:description|what is|tell me about|search for|find).*?["\']?([^"\']+)["\']?'
            desc_match = re.search(desc_pattern, message_lower)
            if desc_match:
                desc_text = desc_match.group(1).strip()
                # Remove common words
                desc_text = re.sub(r'\b(icd9|icd-9|code|for|the|a|an)\b', '', desc_text, flags=re.IGNORECASE).strip()
                if desc_text:
                    description_keywords.append(desc_text)
        
        # Query database efficiently
        icd9_records = self.db_service.search_icd9(
            code=icd9_code,
            description=description_keywords[0] if description_keywords else None,
            date=date_str,
            icd9_num=icd9_num,
            limit=20
        )
        
        formatted_data = self._format_icd9(icd9_records)
        
        return {
            'query_type': 'icd9',
            'data': icd9_records,
            'formatted_data': formatted_data,
            'needs_data': True
        }
    
    def _format_icd9(self, icd9_records: List[Dict]) -> str:
        """Format ICD9 data for LLM"""
        if not icd9_records:
            return "No ICD9 codes found matching your search."
        
        if len(icd9_records) == 1:
            # Single result - detailed format
            record = icd9_records[0]
            formatted = f"ICD9 Code: {record.get('ICD9Code', 'N/A')}\n"
            formatted += f"Description: {record.get('Description', 'N/A')}\n"
            formatted += f"ICD9 Number: {record.get('ICD9Num', 'N/A')}"
            if record.get('DateTStamp'):
                try:
                    dt = datetime.strptime(record.get('DateTStamp', ''), '%Y-%m-%d %H:%M:%S')
                    formatted += f"\nDate: {dt.strftime('%B %d, %Y')}"
                except:
                    formatted += f"\nDate: {record.get('DateTStamp', 'N/A')}"
        else:
            # Multiple results - concise format
            formatted = f"Found {len(icd9_records)} ICD9 code(s):\n\n"
            for i, record in enumerate(icd9_records[:15], 1):  # Limit to 15
                formatted += f"{i}. Code: {record.get('ICD9Code', 'N/A')} - {record.get('Description', 'N/A')[:60]}"
                if record.get('ICD9Num'):
                    formatted += f" (ID: {record.get('ICD9Num')})"
                formatted += "\n"
        
        return formatted


