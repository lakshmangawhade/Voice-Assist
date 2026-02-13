# Dental Voice AI Assistant - Krish

A voice-activated AI assistant for dental practices with separate Python backend and React frontend. Powered by Groq's Llama 3.1 8B Instant model and Deepgram for high-quality text-to-speech.

## Architecture

- **Frontend**: React application with voice recognition and UI
- **Backend**: Python FastAPI server handling LLM (Groq) and TTS (Deepgram) API calls
- **Security**: API keys stored securely on backend, not exposed to frontend

## Project Structure

```
Voice-Assist/
├── backend/                 # Python FastAPI backend
│   ├── main.py             # FastAPI application entry point
│   ├── app/
│   │   └── services/
│   │       ├── llm_service.py    # Groq LLM service
│   │       └── tts_service.py   # Deepgram TTS service
│   ├── requirements.txt    # Python dependencies
│   └── .env.example        # Backend environment variables template
├── src/                    # React frontend
│   ├── App.js              # Main React component
│   ├── App.css             # Styles
│   └── assets/             # Image assets
├── package.json            # Frontend dependencies
└── .env.example            # Frontend environment variables template
```

## Setup Instructions

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your API keys:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   DEEPGRAM_API_KEY=your_deepgram_api_key_here
   ```

4. **Start the backend server:**
   ```bash
   python main.py
   ```
   
   Or using uvicorn:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   
   Backend will run on `http://localhost:8000`

### Frontend Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env`:
   ```env
   REACT_APP_BACKEND_URL=http://localhost:8000
   ```

3. **Start the frontend:**
   ```bash
   npm start
   ```
   
   Frontend will run on `http://localhost:3000`

## Features

- 🎤 **Wake Word Detection**: Say "krish" to activate voice commands
- 🎯 **Voice Recognition**: Browser-based speech-to-text
- 💬 **Text & Voice Chat**: Interact via text input or voice commands
- 🤖 **AI-Powered**: Powered by Groq's Llama 3.1 8B Instant model (via backend)
- 🔊 **Text-to-Speech**: AI responses spoken via Deepgram TTS (via backend)
- ⏱️ **Continuous Listening**: Mic stays open for 5 seconds after AI response
- 🔒 **Secure**: API keys stored on backend, never exposed to frontend
- 🖼️ **Animated Background**: 24fps image animation

## API Endpoints

### Backend Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check with service status
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
- `POST /api/tts` - Convert text to speech
  ```json
  {
    "text": "Text to convert to speech"
  }
  ```

## Usage

### Wake Word Activation

1. **Say "krish"** - The microphone will automatically activate and start listening
2. Speak your command or question
3. The AI will respond both in text and voice
4. Mic stays open for 5 seconds for continuous conversation

### Manual Activation

- Click the microphone button to manually activate voice input
- Or type your message in the text input field

### Browser Requirements

- **Chrome/Edge**: Full support for wake word detection
- **Firefox/Safari**: May have limited speech recognition support
- **Microphone Access**: Grant microphone permissions when prompted

## Security Notes

- API keys are stored on the backend only, never exposed to the frontend
- Backend validates and sanitizes all inputs
- CORS configured to only allow requests from frontend origin
- Environment variables should never be committed to version control

## Future Enhancements

The project structure is designed to easily add:
- Database integration for schedules and appointments
- User authentication
- Session management
- Appointment booking functionality

## Development

### Running Both Services

**Terminal 1 (Backend):**
```bash
cd backend
python main.py
```

**Terminal 2 (Frontend):**
```bash
npm start
```

### Backend Development

- Uses FastAPI for async API handling
- Environment variables loaded via python-dotenv
- CORS configured for frontend communication
- Error handling and validation included

### Frontend Development

- React with hooks for state management
- Browser Speech Recognition API for voice input
- Fetches audio from backend and plays in browser
- Fallback to browser TTS if backend TTS fails

## Troubleshooting

### Backend not connecting
- Ensure backend is running on port 8000
- Check `REACT_APP_BACKEND_URL` in frontend `.env`
- Verify CORS settings in `backend/main.py`

### API errors
- Check backend `.env` file has correct API keys
- Verify API keys are valid and have credits
- Check backend logs for detailed error messages

### Audio playback issues
- Ensure user has interacted with page (clicked/tapped)
- Check browser console for audio errors
- Browser TTS will be used as fallback automatically

---

This project uses [Create React App](https://github.com/facebook/create-react-app) for the frontend and [FastAPI](https://fastapi.tiangolo.com/) for the backend.
