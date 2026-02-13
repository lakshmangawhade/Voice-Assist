"""
TTS Service for handling Deepgram API calls
"""

import os
import base64
import httpx
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class TTSService:
    """Service for interacting with Deepgram TTS API"""
    
    def __init__(self):
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        self.api_url = "https://api.deepgram.com/v1/speak"
        self.model = "aura-asteria-en"
    
    def is_configured(self) -> bool:
        """Check if API key is configured"""
        return bool(self.api_key and self.api_key.strip() and self.api_key != "your_deepgram_api_key_here")
    
    async def synthesize_speech(self, text: str) -> str:
        """
        Convert text to speech using Deepgram TTS
        
        Args:
            text: The text to convert to speech
        
        Returns:
            Base64 encoded audio data (data URL format)
        
        Raises:
            ValueError: If API key is not configured
            Exception: If API call fails
        """
        if not self.is_configured():
            raise ValueError(
                "Deepgram API key is not configured. Please set DEEPGRAM_API_KEY in your .env file."
            )
        
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Prepare request
        url = f"{self.api_url}?model={self.model}"
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "text": text
        }
        
        # Make API call
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                
                # Get audio data
                audio_bytes = response.content
                
                if not audio_bytes or len(audio_bytes) == 0:
                    raise Exception("Empty audio data received from Deepgram")
                
                # Convert to base64 data URL
                audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                audio_data_url = f"data:audio/mpeg;base64,{audio_base64}"
                
                return audio_data_url
                
            except httpx.HTTPStatusError as e:
                error_text = e.response.text if e.response else str(e)
                raise Exception(f"Deepgram TTS API error: {e.response.status_code} - {error_text}")
            except httpx.RequestError as e:
                raise Exception(f"Network error: {str(e)}")
            except Exception as e:
                raise Exception(f"Unexpected error: {str(e)}")

