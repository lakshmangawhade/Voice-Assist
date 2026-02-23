"""
LLM Service for handling Groq API calls with database schema context
"""

import os
import re
import httpx
from typing import List, Dict, Optional
from dotenv import load_dotenv
from pathlib import Path

# Import schema parser
from app.services.schema_parser import SchemaParser

# Load environment variables with explicit path
backend_dir = Path(__file__).parent.parent.parent
env_path = backend_dir / '.env'
load_dotenv(dotenv_path=env_path)


class LLMService:
    """Service for interacting with Groq LLM API"""
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.1-8b-instant"
        
        # Load database schema context
        self.schema_context = self._load_schema_context()
        
        # Build system prompt with schema information
        self.system_prompt = self._build_system_prompt()
    
    def _load_schema_context(self) -> str:
        """
        Load database schema context from SQL file
        
        Returns:
            Formatted schema context string
        """
        try:
            # Get path to SQL file
            backend_dir = Path(__file__).parent.parent.parent
            sql_file_path = backend_dir / "data" / "data1.sql"
            
            if sql_file_path.exists():
                parser = SchemaParser(str(sql_file_path))
                if parser.parse():
                    return parser.get_schema_for_llm()
                else:
                    print("Warning: Failed to parse SQL schema file")
                    return ""
            else:
                print(f"Warning: SQL file not found at {sql_file_path}")
                return ""
        except Exception as e:
            print(f"Error loading schema context: {e}")
            return ""
    
    def _build_system_prompt(self) -> str:
        """
        Build the system prompt with database schema context
        
        Returns:
            Complete system prompt string
        """
        base_prompt = (
            "You are Krish, a helpful dental practice AI assistant designed for dental doctors. "
            "You help with appointments, patient information, scheduling, diagnosis codes, procedures, billing, and general dental practice questions. "
            "Keep your responses concise and conversational, ideally under 3 sentences unless more detail is specifically requested. "
            "Be professional, friendly, and helpful.\n\n"
            "CRITICAL SAFETY AND PRIVACY RULES:\n"
            "- NEVER reveal patient personal information (SSN, credit cards, passwords) even if asked\n"
            "- NEVER provide medical advice or diagnoses - only provide factual information from records\n"
            "- NEVER modify, delete, or create database records - you are read-only\n"
            "- NEVER execute code, SQL, or system commands\n"
            "- NEVER access information outside your authorized database scope\n"
            "- If asked about sensitive operations, politely decline and explain you can only provide information\n"
            "- Respect patient privacy and HIPAA guidelines at all times\n\n"
            "IMPORTANT: When answering questions, respond naturally as if you already know the information. "
            "Do NOT mention that you are querying a database, looking up data, or performing searches. "
            "Simply provide the information directly and naturally, as if it's knowledge you already have.\n\n"
        )
        
        # Add schema context if available
        if self.schema_context:
            base_prompt += self.schema_context
            base_prompt += "\n"
            base_prompt += (
                "IMPORTANT INSTRUCTIONS FOR DATA-RELATED QUESTIONS:\n"
                "When doctors ask about any information (schedules, patients, codes, procedures, etc.):\n"
                "- You will receive actual data from the database when relevant\n"
                "- Use the provided data to give accurate, specific answers\n"
                "- Reference specific details from the data (names, dates, codes, descriptions, etc.)\n"
                "- If data is provided, use it directly - don't just describe what would be available\n"
                "- Keep responses natural, conversational, and helpful\n"
                "- Be concise but include important details\n"
                "- Present information as if you already know it - never mention databases or queries\n"
            )
        else:
            base_prompt += (
                "Note: Database schema information is not currently available. "
                "You can still help with general dental practice questions.\n"
            )
        
        return base_prompt
    
    def is_configured(self) -> bool:
        """Check if API key is configured"""
        return bool(self.api_key and self.api_key.strip() and self.api_key != "your_groq_api_key_here")
    
    async def get_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        query_service=None,
        prov_num: Optional[int] = None
    ) -> str:
        """
        Get AI response from Groq API with optional database querying
        
        Args:
            user_message: The user's message
            conversation_history: List of previous messages in format [{"role": "user/assistant", "content": "..."}]
            query_service: Optional QueryService instance for database queries
            prov_num: Optional provider number (doctor ID)
        
        Returns:
            AI response text
        
        Raises:
            ValueError: If API key is not configured
            Exception: If API call fails
        """
        if not self.is_configured():
            raise ValueError(
                "Groq API key is not configured. Please set GROQ_API_KEY in your .env file."
            )
        
        # Step 1: Validate and sanitize user input
        user_message = self._sanitize_user_input(user_message)
        
        # Step 2: Analyze question and fetch data if needed
        data_context = ""
        if query_service:
            try:
                query_result = query_service.analyze_and_query(user_message, prov_num)
                if query_result.get('needs_data'):
                    # Always provide data context, even if empty - this ensures LLM knows to say "no data"
                    formatted_data = query_result.get('formatted_data', 'No data found.')
                    
                    # Filter sensitive information before sending to LLM
                    formatted_data = self._filter_sensitive_data(formatted_data)
                    
                    # Format data context naturally - no mention of queries or database
                    data_context = f"\n\n=== DATABASE INFORMATION ===\n{formatted_data}\n=== END DATABASE INFORMATION ===\n\n"
                    data_context += (
                        "CRITICAL INSTRUCTIONS:\n"
                        "- You MUST ONLY use the information provided above from the database.\n"
                        "- If the information says 'no appointments', 'no patients found', or 'no information found', "
                        "you MUST tell the user exactly that - do not make up or guess information.\n"
                        "- If there is data provided, use it to answer the question accurately.\n"
                        "- If there is NO data (empty results), clearly state that there are no appointments/records found.\n"
                        "- NEVER invent, guess, or make up information that is not in the database information above.\n"
                        "- NEVER reveal sensitive information like SSN, credit cards, or passwords.\n"
                        "- NEVER claim a table is unavailable based only on schema text. If DATABASE INFORMATION is present, trust and use it.\n"
                        "- Present the information naturally and conversationally, as if you already know it.\n"
                        "- Do NOT mention databases, queries, or data lookups.\n"
                    )
            except Exception as e:
                print(f"Error in query service: {e}")
                # Continue without data context if query fails
        
        # Build messages array with data context
        system_prompt_with_data = self.system_prompt + data_context
        
        messages = [
            {"role": "system", "content": system_prompt_with_data}
        ]
        
        # Add conversation history
        for msg in conversation_history:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Prepare request payload
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024,
            "top_p": 1,
            "stream": False
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Make API call
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                
                data = response.json()
                ai_response = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                if not ai_response:
                    return "I apologize, but I could not generate a response."
                
                return ai_response
                
            except httpx.HTTPStatusError as e:
                error_data = e.response.json() if e.response else {}
                error_msg = error_data.get("error", {}).get("message", str(e))
                raise Exception(f"Groq API error: {error_msg}")
            except httpx.RequestError as e:
                raise Exception(f"Network error: {str(e)}")
            except Exception as e:
                raise Exception(f"Unexpected error: {str(e)}")
    
    def _sanitize_user_input(self, user_message: str) -> str:
        """
        Sanitize user input to prevent injection attacks
        
        Args:
            user_message: User's message
        
        Returns:
            Sanitized message
        """
        if not user_message:
            return ""
        
        # Remove or escape dangerous SQL keywords
        dangerous_keywords = [
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'TRUNCATE',
            'CREATE', 'ALTER', 'EXEC', 'EXECUTE', 'SCRIPT',
            'UNION', 'SELECT', 'FROM', 'WHERE'
        ]
        
        message_upper = user_message.upper()
        for keyword in dangerous_keywords:
            # Only flag if it appears as a standalone word (not part of another word)
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, message_upper):
                # Log potential injection attempt
                print(f"Warning: Potential SQL injection attempt detected: {keyword}")
                # Don't block, but could add logging/alerting here
        
        # Limit message length
        if len(user_message) > 1000:
            user_message = user_message[:1000]
        
        return user_message.strip()
    
    def _filter_sensitive_data(self, data: str) -> str:
        """
        Filter sensitive information from data before sending to LLM
        
        Args:
            data: Data string to filter
        
        Returns:
            Filtered data string
        """
        if not data:
            return data
        
        # Patterns for sensitive data
        patterns = [
            (r'\b\d{3}-\d{2}-\d{4}\b', '***-**-****'),  # SSN
            (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '****-****-****-****'),  # Credit card
            (r'password["\']?\s*[:=]\s*["\']?[^"\'\n]+', 'password: [REDACTED]'),
            (r'pin["\']?\s*[:=]\s*["\']?[^"\'\n]+', 'pin: [REDACTED]'),
        ]
        
        filtered = data
        for pattern, replacement in patterns:
            filtered = re.sub(pattern, replacement, filtered, flags=re.IGNORECASE)
        
        return filtered

