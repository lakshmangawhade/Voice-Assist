# Dental Voice AI Backend

Python FastAPI backend for the Dental Voice AI Assistant application.

## Features

- **LLM Integration**: Groq API integration for AI responses
- **Text-to-Speech**: Deepgram TTS integration for voice output
- **RESTful API**: Clean API endpoints for frontend communication
- **Future-Ready**: Structured for database integration (schedules, appointments)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Edit `.env`:
```
GROQ_API_KEY=your_actual_groq_api_key
DEEPGRAM_API_KEY=your_actual_deepgram_api_key
```

### 3. Run the Server

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Health Check
- `GET /` - Root endpoint
- `GET /health` - Health check with service status

### Chat
- `POST /api/chat` - Get AI response
  ```json
  {
    "message": "User message",
    "conversation_history": [
      {"role": "user", "content": "Previous message"},
      {"role": "assistant", "content": "AI response"}
    ]
  }
  ```

### Text-to-Speech
- `POST /api/tts` - Convert text to speech
  ```json
  {
    "text": "Text to convert to speech"
  }
  ```
  Returns base64 encoded audio data URL

## Project Structure

```
backend/
├── main.py                 # FastAPI application entry point
├── app/
│   ├── __init__.py
│   └── services/
│       ├── __init__.py
│       ├── llm_service.py  # Groq LLM service
│       └── tts_service.py  # Deepgram TTS service
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
└── README.md              # This file
```

## Future Database Integration

The project structure is designed to easily add database integration:

- Database models can be added to `app/models/`
- Database service layer can be added to `app/services/db_service.py`
- API endpoints for schedules/appointments can be added to `main.py`

## Development

- Uses FastAPI for async API handling
- Environment variables loaded via python-dotenv
- CORS configured for frontend communication
- Error handling and validation included

