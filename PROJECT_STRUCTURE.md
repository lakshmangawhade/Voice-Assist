# Project Structure

This document outlines the complete structure of the Dental Voice AI Assistant project.

## Directory Structure

```
Voice-Assist/
│
├── backend/                          # Python FastAPI Backend
│   ├── main.py                      # FastAPI application entry point
│   ├── requirements.txt            # Python dependencies
│   ├── .env.example                # Backend environment variables template
│   ├── README.md                   # Backend-specific documentation
│   │
│   └── app/                         # Application package
│       ├── __init__.py             # Package initialization
│       │
│       └── services/               # Service layer
│           ├── __init__.py
│           ├── llm_service.py      # Groq LLM API service
│           └── tts_service.py      # Deepgram TTS API service
│
├── src/                             # React Frontend
│   ├── App.js                      # Main React component
│   ├── App.css                     # Application styles
│   ├── index.js                    # React entry point
│   ├── index.css                   # Global styles
│   │
│   └── assets/                     # Image assets
│       ├── tooth1_1.png
│       ├── tooth1_2.png
│       └── ... (27 total images)
│
├── public/                          # Static public files
│   ├── index.html
│   ├── favicon.ico
│   └── ...
│
├── package.json                     # Frontend dependencies
├── .env.example                     # Frontend environment variables template
├── .gitignore                       # Git ignore rules
├── README.md                        # Main project documentation
├── SETUP.md                         # Detailed setup guide
└── PROJECT_STRUCTURE.md            # This file

```

## Architecture Overview

### Backend (Python FastAPI)

**Purpose**: Handle all external API calls and business logic

**Key Components**:
- `main.py`: FastAPI application with REST endpoints
- `app/services/llm_service.py`: Groq API integration for AI responses
- `app/services/tts_service.py`: Deepgram API integration for text-to-speech

**API Endpoints**:
- `GET /` - Root endpoint
- `GET /health` - Health check
- `POST /api/chat` - Get AI response
- `POST /api/tts` - Convert text to speech

**Security**:
- API keys stored in backend `.env` file
- CORS configured for frontend origin only
- Input validation and error handling

### Frontend (React)

**Purpose**: User interface and voice interaction

**Key Components**:
- `App.js`: Main component with voice recognition and chat UI
- Voice recognition using browser Speech Recognition API
- Image animation at 24fps
- Communication with backend via REST API

**Features**:
- Wake word detection ("krish")
- Voice input and text input
- Real-time chat interface
- Audio playback from backend TTS

## Data Flow

```
User Voice Input
    ↓
Browser Speech Recognition API
    ↓
Frontend (App.js)
    ↓
POST /api/chat → Backend (main.py)
    ↓
LLM Service → Groq API
    ↓
AI Response → Backend
    ↓
POST /api/tts → Backend
    ↓
TTS Service → Deepgram API
    ↓
Audio Data → Frontend
    ↓
Browser Audio Playback
```

## Environment Variables

### Backend (.env)
```env
GROQ_API_KEY=your_groq_api_key
DEEPGRAM_API_KEY=your_deepgram_api_key
```

### Frontend (.env)
```env
REACT_APP_BACKEND_URL=http://localhost:8000
```

## Future Database Integration

The structure is designed to easily add database functionality:

### Proposed Structure
```
backend/
├── app/
│   ├── models/              # Database models (SQLAlchemy/ORM)
│   │   ├── appointment.py
│   │   └── schedule.py
│   │
│   ├── services/
│   │   ├── db_service.py   # Database operations
│   │   └── ...
│   │
│   └── api/
│       └── routes/         # API route handlers
│           ├── appointments.py
│           └── schedules.py
```

### Database Service Example
```python
# backend/app/services/db_service.py
class DatabaseService:
    def get_appointments(self, date):
        # Database query logic
        pass
    
    def create_appointment(self, appointment_data):
        # Database insert logic
        pass
```

## Security Considerations

1. **API Keys**: Never exposed to frontend, stored only on backend
2. **CORS**: Configured to allow only frontend origin
3. **Input Validation**: Pydantic models validate all inputs
4. **Error Handling**: Proper error messages without exposing internals
5. **Environment Variables**: Never committed to version control

## Development Guidelines

### Backend
- Use async/await for API calls
- Keep services modular and testable
- Add new endpoints in `main.py`
- Create new services in `app/services/`

### Frontend
- Keep components focused and reusable
- Use React hooks for state management
- Handle errors gracefully with fallbacks
- Maintain responsive design

## Testing

### Backend Testing
```bash
cd backend
pytest  # When tests are added
```

### Frontend Testing
```bash
npm test
```

## Deployment

### Backend Deployment
- Use production WSGI server (Gunicorn + Uvicorn)
- Set environment variables securely
- Configure CORS for production domain

### Frontend Deployment
- Build: `npm run build`
- Serve static files
- Update backend URL in production `.env`

## Maintenance

- Keep dependencies updated
- Monitor API usage and costs
- Review and update security practices
- Add logging for debugging
- Monitor error rates

