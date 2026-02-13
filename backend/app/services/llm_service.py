"""
LLM Service for handling Groq API calls
"""

import os
import httpx
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class LLMService:
    """Service for interacting with Groq LLM API"""
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.1-8b-instant"
        self.system_prompt = (
            "You are a helpful dental practice AI assistant named Krish. "
            "You help with appointments, patient information, scheduling, and general dental practice questions. "
            "Keep your responses concise and conversational, ideally under 3 sentences unless more detail is specifically requested. "
            "Be professional and friendly."
        )
    
    def is_configured(self) -> bool:
        """Check if API key is configured"""
        return bool(self.api_key and self.api_key.strip() and self.api_key != "your_groq_api_key_here")
    
    async def get_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        Get AI response from Groq API
        
        Args:
            user_message: The user's message
            conversation_history: List of previous messages in format [{"role": "user/assistant", "content": "..."}]
        
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
        
        # Build messages array
        messages = [
            {"role": "system", "content": self.system_prompt}
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

