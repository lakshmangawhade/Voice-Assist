"""
FastAPI Backend for Dental Voice AI Assistant
Handles LLM (Groq), Deepgram TTS, and Twilio calling agent
"""

from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
from dotenv import load_dotenv

from app.services.llm_service import LLMService
from app.services.tts_service import TTSService
from app.services.intent_service import IntentService
from app.services.twilio_service import TwilioService
from app.services.database_service import DatabaseService
from app.services.query_service import QueryService
from twilio.twiml.voice_response import VoiceResponse

# Load environment variables
load_dotenv()
print(f"GROQ_API_KEY exists: {bool(os.getenv('GROQ_API_KEY'))}")
print(f"DEEPGRAM_API_KEY exists: {bool(os.getenv('DEEPGRAM_API_KEY'))}")
print(f"TWILIO_ACCOUNT_SID exists: {bool(os.getenv('TWILIO_ACCOUNT_SID'))}")

# Initialize FastAPI app
app = FastAPI(
    title="Dental Voice AI Backend",
    description="Backend API for Dental Voice AI Assistant",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://127.0.0.1:3000",
        # Add production frontend URL here when deploying
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
llm_service = LLMService()
tts_service = TTSService()
intent_service = IntentService()
twilio_service = TwilioService()

# Initialize database and query services
db_service = DatabaseService()
db_initialized = db_service.initialize()  # Use initialize() method
query_service = QueryService(db_service) if db_initialized else None

if db_initialized:
    print("✓ Database initialized successfully. Query service available.")
else:
    print("⚠ Warning: Database initialization failed. Query service unavailable.")


# Request/Response models
class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: List[Message]


class ChatResponse(BaseModel):
    response: str
    success: bool
    error: Optional[str] = None
    call_info: Optional[Dict] = None


class TTSRequest(BaseModel):
    text: str


class TTSResponse(BaseModel):
    audio_url: str
    success: bool
    error: Optional[str] = None


class CallRequest(BaseModel):
    phone_number: str
    intent: str  # 'cancel' or 'reschedule'
    patient_name: Optional[str] = None
    appointment_date: Optional[str] = None


class CallResponse(BaseModel):
    success: bool
    call_sid: Optional[str] = None
    error: Optional[str] = None


# Health check endpoint
@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "Dental Voice AI Backend",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "llm_configured": llm_service.is_configured(),
        "tts_configured": tts_service.is_configured(),
        "twilio_configured": twilio_service.is_configured(),
        "database_initialized": db_initialized
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process user message and get AI response using Groq LLM
    Also detects intents for appointment cancellation/rescheduling
    """
    try:
        if not request.message or not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Get provider number from request if available (for doctor-specific queries)
        # For now, we'll use None (all appointments) or you can add prov_num to ChatRequest
        prov_num = None  # TODO: Extract from request if needed
        
        response_text = await llm_service.get_response(
            user_message=request.message,
            conversation_history=request.conversation_history,
            query_service=query_service,
            prov_num=prov_num
        )
        
        # Detect intent
        intent_result = intent_service.detect_intent(request.message, response_text)
        
        # Check if call should be triggered
        call_info = None
        if intent_service.should_trigger_call(intent_result):
            call_info = {
                'intent': intent_result['intent'],
                'requires_call': True,
                'extracted_info': intent_result['extracted_info']
            }
        
        return ChatResponse(
            response=response_text,
            success=True,
            call_info=call_info
        )
    except Exception as e:
        error_message = str(e) if str(e) else "An error occurred while processing your request."
        return ChatResponse(
            response=f"I apologize, but I encountered an error: {error_message}. Please try again.",
            success=False,
            error=error_message
        )


@app.post("/api/tts", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest):
    """
    Convert text to speech using Deepgram TTS
    Returns base64 encoded audio data
    """
    try:
        if not request.text or not request.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        audio_data = await tts_service.synthesize_speech(request.text)
        
        return TTSResponse(
            audio_url=audio_data,
            success=True
        )
    except Exception as e:
        return TTSResponse(
            audio_url="",
            success=False,
            error=str(e)
        )


@app.post("/api/twilio/initiate-call", response_model=CallResponse)
async def initiate_call(request: CallRequest):
    """
    Initiate a phone call to a patient for appointment cancellation/rescheduling
    """
    try:
        if not twilio_service.is_configured():
            return CallResponse(
                success=False,
                error="Twilio is not configured. Please set Twilio credentials in .env file."
            )
        
        if request.intent not in ['cancel', 'reschedule']:
            return CallResponse(
                success=False,
                error="Intent must be 'cancel' or 'reschedule'"
            )
        
        result = twilio_service.make_call(
            to_phone=request.phone_number,
            intent=request.intent,
            patient_name=request.patient_name,
            appointment_date=request.appointment_date
        )
        
        if result.get('success'):
            return CallResponse(
                success=True,
                call_sid=result.get('call_sid')
            )
        else:
            return CallResponse(
                success=False,
                error=result.get('error', 'Unknown error')
            )
    except Exception as e:
        return CallResponse(
            success=False,
            error=str(e)
        )


@app.post("/api/twilio/call-handler")
async def call_handler(request: Request):
    """
    Twilio webhook handler for incoming call
    Generates TwiML for call greeting and menu
    """
    try:
        form_data = await request.form()
        intent = request.query_params.get('intent', 'reschedule')
        patient_name = request.query_params.get('patient_name', None)
        
        twiml = twilio_service.generate_twiml_greeting(
            intent=intent,
            patient_name=patient_name
        )
        
        return Response(content=twiml, media_type="application/xml")
    except Exception as e:
        # Return error TwiML
        response = VoiceResponse()
        response.say("We're sorry, there was an error processing your call. Please try again later.", voice='alice')
        response.hangup()
        return Response(content=str(response), media_type="application/xml")


@app.post("/api/twilio/handle-input")
async def handle_input(request: Request):
    """
    Twilio webhook handler for user input (DTMF or voice)
    """
    try:
        form_data = await request.form()
        digits = form_data.get('Digits', '')
        intent = request.query_params.get('intent', 'reschedule')
        
        if intent == 'reschedule':
            twiml = twilio_service.generate_twiml_reschedule(digits)
        elif intent == 'cancel':
            twiml = twilio_service.generate_twiml_cancel(digits)
        else:
            twiml = twilio_service.generate_twiml_greeting(intent)
        
        return Response(content=twiml, media_type="application/xml")
    except Exception as e:
        response = VoiceResponse()
        response.say("We're sorry, there was an error. Please try again later.", voice='alice')
        response.hangup()
        return Response(content=str(response), media_type="application/xml")


@app.post("/api/twilio/handle-reschedule")
async def handle_reschedule(request: Request):
    """
    Twilio webhook handler for reschedule date/time input
    """
    try:
        form_data = await request.form()
        speech_result = form_data.get('SpeechResult', '')
        confidence = form_data.get('Confidence', '0')
        
        # Process the speech result (preferred date/time)
        # In production, you would parse this and store it
        print(f"Reschedule request: {speech_result} (confidence: {confidence})")
        
        twiml = twilio_service.generate_twiml_confirmation(
            preferred_date=speech_result,
            intent='reschedule'
        )
        
        return Response(content=twiml, media_type="application/xml")
    except Exception as e:
        response = VoiceResponse()
        response.say("We're sorry, we didn't catch that. Please call us back to reschedule.", voice='alice')
        response.hangup()
        return Response(content=str(response), media_type="application/xml")


@app.post("/api/twilio/handle-confirmation")
async def handle_confirmation(request: Request):
    """
    Twilio webhook handler for final confirmation
    """
    try:
        form_data = await request.form()
        speech_result = form_data.get('SpeechResult', '').lower()
        
        response = VoiceResponse()
        
        if 'yes' in speech_result or 'yeah' in speech_result:
            response.say("Thank you. We'll be in touch soon. Have a great day!", voice='alice')
        else:
            response.say("Thank you for calling. Have a great day!", voice='alice')
        
        response.hangup()
        return Response(content=str(response), media_type="application/xml")
    except Exception as e:
        response = VoiceResponse()
        response.say("Thank you for calling. Goodbye!", voice='alice')
        response.hangup()
        return Response(content=str(response), media_type="application/xml")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
