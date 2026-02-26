"""
LLM Service for handling Groq API calls with database schema context
and the new Intent+SQL pipeline integration.
"""

import os
import re
import httpx
from typing import List, Dict, Optional
from dotenv import load_dotenv
from pathlib import Path

# Import schema parser (still used for building the base system prompt context)
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
            "You are Giva, a helpful dental practice AI assistant designed for dental doctors. "
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
            "ABSOLUTE ANTI-HALLUCINATION RULE: If you are provided DATABASE INFORMATION, "
            "every specific value you state (IDs, patient numbers, times, dates, names, counts) "
            "MUST come from the DETAILED DATA rows in that section. "
            "If a value is not present in those rows, you MUST say you don't have it — "
            "NEVER guess or make up a number, time, or name.\n\n"
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
        formatted_data: str = "",
    ) -> str:
        """
        Get a conversational AI response from Groq API.

        This method is ONLY called for GENERAL_QUERY or purely conversational
        messages (greetings, small-talk, etc.).  For structured data intents
        (appointments, patients, providers, etc.) the pipeline speech is
        returned directly by ``main.py`` — the LLM is never consulted.

        Args:
            user_message: The user's message (already sanitised by main.py).
            conversation_history: Previous messages.
            formatted_data: Optional data context from the pipeline
                (for GENERAL_QUERY where the pipeline found DB rows).

        Returns:
            AI response text.
        """
        if not self.is_configured():
            raise ValueError(
                "Groq API key is not configured. Please set GROQ_API_KEY in your .env file."
            )

        user_message = self._sanitize_user_input(user_message)

        # If the pipeline provided data context, inject it
        data_context = ""
        if formatted_data:
            formatted_data = self._filter_sensitive_data(formatted_data)
            data_context = (
                f"\n\n=== DATABASE INFORMATION (GROUND TRUTH) ===\n"
                f"{formatted_data}\n"
                f"=== END DATABASE INFORMATION ===\n\n"
                f"ABSOLUTE RULES:\n"
                f"1. Every value you state MUST come from the DETAILED DATA rows above.\n"
                f"2. NEVER invent, guess, or round any value.\n"
                f"3. If no data is available, say so clearly.\n"
                f"4. Present naturally. Do NOT mention databases or queries.\n"
                f"5. Be concise — under 3 sentences unless the user asks for a full list.\n"
            )

        # Build messages
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
        """
        if not user_message:
            return ""

        dangerous_keywords = [
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'TRUNCATE',
            'CREATE', 'ALTER', 'EXEC', 'EXECUTE', 'SCRIPT',
            'UNION', 'SELECT', 'FROM', 'WHERE'
        ]

        message_upper = user_message.upper()
        for keyword in dangerous_keywords:
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, message_upper):
                print(f"Warning: Potential SQL injection attempt detected: {keyword}")

        # Limit message length
        from app.config import MAX_MESSAGE_LENGTH
        if len(user_message) > MAX_MESSAGE_LENGTH:
            user_message = user_message[:MAX_MESSAGE_LENGTH]

        return user_message.strip()

    def _filter_sensitive_data(self, data: str) -> str:
        """
        Filter sensitive information from data before sending to LLM
        """
        if not data:
            return data

        patterns = [
            (r'\b\d{3}-\d{2}-\d{4}\b', '***-**-****'),  # SSN
            (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '****-****-****-****'),  # CC
            (r'password["\']?\s*[:=]\s*["\']?[^"\'\n]+', 'password: [REDACTED]'),
            (r'pin["\']?\s*[:=]\s*["\']?[^"\'\n]+', 'pin: [REDACTED]'),
        ]

        filtered = data
        for pattern, replacement in patterns:
            filtered = re.sub(pattern, replacement, filtered, flags=re.IGNORECASE)

        return filtered
