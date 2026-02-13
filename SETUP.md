# Setup Guide

This guide will help you set up both the backend and frontend of the Dental Voice AI Assistant.

## Prerequisites

- **Node.js** (v14 or higher) and npm
- **Python** (v3.8 or higher) and pip
- **API Keys**:
  - Groq API Key: [Get it here](https://console.groq.com/)
  - Deepgram API Key: [Get it here](https://console.deepgram.com/)

## Quick Start

### Step 1: Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - **Windows:**
     ```bash
     venv\Scripts\activate
     ```
   - **macOS/Linux:**
     ```bash
     source venv/bin/activate
     ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Create `.env` file:
   ```bash
   cp .env.example .env
   ```

6. Edit `.env` and add your API keys:
   ```env
   GROQ_API_KEY=your_actual_groq_api_key
   DEEPGRAM_API_KEY=your_actual_deepgram_api_key
   ```

7. Start the backend server:
   ```bash
   python main.py
   ```
   
   You should see: `Uvicorn running on http://0.0.0.0:8000`

### Step 2: Frontend Setup

1. Open a **new terminal** and navigate to the project root:
   ```bash
   cd Voice-Assist
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create `.env` file:
   ```bash
   cp .env.example .env
   ```

4. Edit `.env` and set the backend URL:
   ```env
   REACT_APP_BACKEND_URL=http://localhost:8000
   ```

5. Start the frontend:
   ```bash
   npm start
   ```
   
   The app will open automatically at `http://localhost:3000`

## Verifying Setup

1. **Backend Health Check:**
   - Open browser: `http://localhost:8000/health`
   - Should return JSON with `status: "healthy"` and service configuration status

2. **Frontend Connection:**
   - When frontend loads, check browser console
   - Should see: `✅ Backend connected successfully`

3. **Test Voice:**
   - Say "krish" to activate
   - Or click the microphone button
   - Speak a message and wait for AI response

## Troubleshooting

### Backend Issues

**Port already in use:**
```bash
# Change port in backend/main.py or use:
uvicorn main:app --reload --port 8001
```

**Module not found:**
```bash
# Ensure virtual environment is activated
# Reinstall dependencies:
pip install -r requirements.txt
```

**API Key errors:**
- Verify `.env` file exists in `backend/` directory
- Check API keys are correct (no extra spaces)
- Restart backend server after changing `.env`

### Frontend Issues

**Cannot connect to backend:**
- Ensure backend is running (`http://localhost:8000`)
- Check `REACT_APP_BACKEND_URL` in frontend `.env`
- Verify CORS settings in `backend/main.py`

**API errors:**
- Check backend terminal for error messages
- Verify API keys in backend `.env` are valid
- Check browser console for detailed errors

**Audio not playing:**
- Click/tap anywhere on the page first (browser autoplay policy)
- Check browser console for audio errors
- Browser TTS will be used as fallback automatically

## Development Workflow

### Running Both Services

**Terminal 1 - Backend:**
```bash
cd backend
python main.py
```

**Terminal 2 - Frontend:**
```bash
npm start
```

### Making Changes

- **Backend changes**: Backend auto-reloads (if using `--reload`)
- **Frontend changes**: React auto-reloads on save
- **Environment changes**: Restart both services

## Production Deployment

### Backend
- Use production WSGI server (e.g., Gunicorn with Uvicorn workers)
- Set proper CORS origins for production domain
- Use environment variables or secrets management for API keys

### Frontend
- Build: `npm run build`
- Serve static files from `build/` directory
- Update `REACT_APP_BACKEND_URL` to production backend URL

## Next Steps

- Database integration for schedules (see `backend/app/services/` for service structure)
- User authentication
- Session management
- Appointment booking endpoints

