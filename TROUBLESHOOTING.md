# Troubleshooting Guide

## Issue 1: API Key Not Found

### Symptoms
- Error message: "Groq API key is not configured"
- Even though you've added the key to `.env` file

### Solutions

1. **Verify .env file location**
   - The `.env` file must be in the **root directory** (same level as `package.json`)
   - Path should be: `dental-ai-demo/.env`

2. **Check .env file format**
   - Must start with `REACT_APP_` prefix
   - No spaces around the `=` sign
   - No quotes needed
   - Example:
   ```
   REACT_APP_GROQ_API_KEY=gsk_your_actual_api_key_here
   ```

3. **Restart the development server**
   - **IMPORTANT**: Environment variables are only loaded when the server starts
   - Stop the server (Ctrl+C)
   - Run `npm start` again
   - The `.env` file is NOT reloaded automatically

4. **Verify the API key**
   - Open browser console (F12)
   - Look for: "✅ API Key configured successfully"
   - If you see "⚠️ API Key not configured", check your `.env` file

5. **Clear browser cache**
   - Sometimes cached environment variables cause issues
   - Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)

## Issue 2: Wake Word "Aria" Not Activating

### Symptoms
- Saying "Aria" doesn't activate the microphone
- Status shows "Waiting for 'Aria'" but nothing happens

### Solutions

1. **Check browser compatibility**
   - **Chrome/Edge**: Full support ✅
   - **Firefox**: Limited support ⚠️
   - **Safari**: Limited support ⚠️
   - Use Chrome or Edge for best results

2. **Grant microphone permissions**
   - Browser will prompt for microphone access
   - Click "Allow" when prompted
   - Check browser settings if prompt doesn't appear:
     - Chrome: Settings → Privacy → Site Settings → Microphone
     - Edge: Settings → Site permissions → Microphone

3. **Check browser console**
   - Open Developer Tools (F12)
   - Look for console messages:
     - "Wake word detection started" ✅
     - "Wake word detection heard: [text]" - shows what it's hearing
     - Any error messages

4. **Try different pronunciations**
   - Say "Aria" clearly
   - Try "aria" (lowercase)
   - Try "A-ria" (with pause)
   - The system listens for the word "aria" in any context

5. **Manual activation test**
   - Click the microphone button manually
   - If manual activation works, the issue is with wake word detection
   - If manual doesn't work, check microphone permissions

6. **Refresh the page**
   - Sometimes speech recognition needs a fresh start
   - Hard refresh: Ctrl+Shift+R

## Issue 3: Microphone Not Working

### Solutions

1. **Check system microphone**
   - Test microphone in other apps (e.g., Windows Voice Recorder)
   - Ensure microphone is not muted
   - Check system sound settings

2. **Browser microphone settings**
   - Chrome: chrome://settings/content/microphone
   - Ensure localhost:3000 is allowed
   - Remove and re-add permission if needed

3. **HTTPS requirement (for production)**
   - Speech recognition requires HTTPS in production
   - Development (localhost) works without HTTPS
   - For production, use HTTPS

## Debug Mode

The app includes debug logging in development mode:

1. Open browser console (F12)
2. Look for these messages:
   - `Wake word detection started` - Wake word system initialized
   - `Wake word detection heard: [text]` - What the system is hearing
   - `✅ Wake word detected: aria` - Wake word recognized
   - `API Key check: {...}` - API key status

## Still Having Issues?

1. **Check the console** for error messages
2. **Verify .env file** is in the correct location
3. **Restart the dev server** after changing .env
4. **Try a different browser** (Chrome recommended)
5. **Check microphone permissions** in browser settings

## Quick Test Checklist

- [ ] `.env` file exists in root directory
- [ ] `.env` file contains `REACT_APP_GROQ_API_KEY=your_key`
- [ ] Development server restarted after adding `.env`
- [ ] Browser console shows "✅ API Key configured successfully"
- [ ] Microphone permission granted
- [ ] Browser console shows "Wake word detection started"
- [ ] Using Chrome or Edge browser
- [ ] Microphone hardware is working

