# Twilio Calling Agent Setup Guide

This guide explains how to set up the Twilio calling agent for appointment cancellation and rescheduling.

## Overview

The calling agent automatically detects when a user wants to cancel or reschedule an appointment and initiates a phone call to the patient. The agent uses Twilio's Voice API to handle the call flow and gather information from the patient.

## Features

- **Intent Detection**: Automatically detects cancellation/rescheduling requests from chat messages
- **Phone Call Initiation**: Makes calls to patients using Twilio
- **Interactive Voice Response**: Handles patient input via DTMF (keypad) and voice
- **Rescheduling Flow**: Collects preferred dates/times from patients
- **Cancellation Confirmation**: Confirms appointment cancellations
- **Staff Transfer Option**: Allows patients to speak with staff

## Prerequisites

1. **Twilio Account**: Sign up at [twilio.com](https://www.twilio.com)
2. **Twilio Phone Number**: Purchase a phone number from Twilio
3. **Public URL**: For webhooks (use ngrok for local development)

## Setup Instructions

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Twilio Credentials

Add to `backend/.env`:

```env
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_WEBHOOK_BASE_URL=https://your-domain.com
```

**For Local Development:**
1. Install ngrok: `npm install -g ngrok` or download from [ngrok.com](https://ngrok.com)
2. Start your backend: `python main.py`
3. In another terminal: `ngrok http 8000`
4. Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)
5. Set `TWILIO_WEBHOOK_BASE_URL=https://abc123.ngrok.io` in `.env`

### 3. Configure Twilio Webhooks

1. Go to [Twilio Console](https://console.twilio.com)
2. Navigate to Phone Numbers → Manage → Active Numbers
3. Click on your Twilio phone number
4. Under "Voice & Fax", set:
   - **A CALL COMES IN**: `POST` → `https://your-domain.com/api/twilio/call-handler`
   - **STATUS CALLBACK URL**: `https://your-domain.com/api/twilio/status-callback` (optional)

## How It Works

### 1. Intent Detection

When a user sends a message like:
- "I need to cancel my appointment"
- "Can I reschedule for next week?"
- "I want to change my appointment date"

The system detects the intent and returns `call_info` in the chat response.

### 2. Call Initiation

The frontend shows a modal asking for:
- Patient phone number (required)
- Patient name (optional)

When submitted, the backend initiates a Twilio call.

### 3. Call Flow

**Greeting:**
- "Hello [Patient Name], this is an automated call from your dental office."
- "We received a request to [cancel/reschedule] your appointment."
- "Press 1 to [action], or press 2 to speak with our staff."

**Option 1 - Reschedule:**
- Patient says preferred date/time
- System confirms and notes the preference
- Staff will follow up

**Option 1 - Cancel:**
- Confirms cancellation
- Provides information about rescheduling

**Option 2:**
- Transfers to staff (configure staff number in production)

## API Endpoints

### Initiate Call
```
POST /api/twilio/initiate-call
Body: {
  "phone_number": "+1234567890",
  "intent": "cancel" | "reschedule",
  "patient_name": "John Doe" (optional),
  "appointment_date": "2024-01-15" (optional)
}
```

### Webhook Endpoints (Called by Twilio)

- `POST /api/twilio/call-handler` - Initial call greeting
- `POST /api/twilio/handle-input` - User input (DTMF)
- `POST /api/twilio/handle-reschedule` - Reschedule date/time input
- `POST /api/twilio/handle-confirmation` - Final confirmation

## Testing

### Local Testing with ngrok

1. Start backend: `python main.py`
2. Start ngrok: `ngrok http 8000`
3. Update `.env` with ngrok URL
4. Restart backend
5. Test call initiation from frontend

### Testing Call Flow

1. Send a message like "I need to cancel my appointment"
2. Modal appears asking for phone number
3. Enter test phone number (your own for testing)
4. Click "Initiate Call"
5. Answer the call and follow the prompts

## Production Considerations

1. **Staff Phone Number**: Update `generate_twiml_reschedule()` and `generate_twiml_cancel()` to dial actual staff number
2. **Database Integration**: Store call logs, patient preferences, and appointment changes
3. **Error Handling**: Add retry logic and fallback options
4. **Call Recording**: Enable Twilio call recording for quality assurance
5. **SMS Notifications**: Send SMS confirmation after calls
6. **Call Scheduling**: Schedule calls for specific times
7. **Multi-language Support**: Add support for multiple languages

## Security Notes

- Never expose Twilio credentials in frontend code
- Use environment variables for all sensitive data
- Validate phone numbers before making calls
- Implement rate limiting for call initiation
- Log all call activities for audit purposes
- Use HTTPS for all webhook URLs

## Troubleshooting

**Calls not connecting:**
- Verify Twilio credentials are correct
- Check webhook URL is accessible (use ngrok for local)
- Ensure phone number is in E.164 format (+1234567890)

**Webhook errors:**
- Check Twilio console for webhook logs
- Verify webhook URLs are correct in Twilio dashboard
- Ensure backend is running and accessible

**Intent not detected:**
- Check intent detection keywords in `intent_service.py`
- Review chat logs for message content
- Adjust confidence threshold if needed

