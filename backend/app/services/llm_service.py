"""
LLM Service for handling Groq API calls with database schema context
"""

import os
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
            sql_file_path = backend_dir / "data" / "data.sql"
            
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
            "You help with appointments, patient information, scheduling, ICD9 codes, and general dental practice questions. "
            "Keep your responses concise and conversational, ideally under 3 sentences unless more detail is specifically requested. "
            "Be professional, friendly, and helpful.\n\n"
            "IMPORTANT: When answering questions, respond naturally as if you already know the information. "
            "Do NOT mention that you are querying a database, looking up data, or performing searches. "
            "Simply provide the information directly and naturally, as if it's knowledge you already have.\n\n"
        )
        
        # Add schema context if available
        if self.schema_context:
            base_prompt += self.schema_context
            base_prompt += "\n"
            base_prompt += (
                "IMPORTANT INSTRUCTIONS FOR SCHEDULE-RELATED QUESTIONS:\n"
                "When doctors ask about their schedule, appointments, or availability:\n"
                "- You will receive actual data from the database when relevant\n"
                "- Use the provided data to give accurate, specific answers\n"
                "- Reference specific appointments, times, and patient names from the data\n"
                "- If data is provided, use it directly - don't just describe what would be available\n"
                "- Keep responses natural, conversational, and helpful\n"
                "- Be concise but include important details like appointment times and patient names\n"
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
        
        # Step 1: Analyze question and fetch data if needed
        data_context = ""
        if query_service:
            query_result = query_service.analyze_and_query(user_message, prov_num)
            if query_result.get('needs_data') and query_result.get('formatted_data'):
                # Format data context naturally - no mention of queries or database
                data_context = f"\n\n=== INFORMATION ===\n{query_result['formatted_data']}\n=== END INFORMATION ===\n\n"
                data_context += (
                    "Use the information above to answer the user's question naturally and directly. "
                    "Present the information as if it's knowledge you already have. "
                    "Do not mention databases, queries, or data lookups. "
                    "Simply provide the answer using the information above."
                )
        
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

