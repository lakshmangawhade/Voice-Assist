"""
Twilio Service for making phone calls and handling call flows
"""

import os
from typing import Optional, Dict
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from dotenv import load_dotenv

load_dotenv()


class TwilioService:
    """Service for interacting with Twilio API"""
    
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.phone_number = os.getenv("TWILIO_PHONE_NUMBER")
        self.webhook_base_url = os.getenv("TWILIO_WEBHOOK_BASE_URL", "http://localhost:8000")
        
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            self.client = None
    
    def is_configured(self) -> bool:
        """Check if Twilio is configured"""
        return bool(
            self.account_sid and 
            self.account_sid.strip() and 
            self.account_sid != "your_twilio_account_sid" and
            self.auth_token and 
            self.auth_token.strip() and
            self.auth_token != "your_twilio_auth_token"
        )
    
    def make_call(
        self,
        to_phone: str,
        intent: str,
        patient_name: Optional[str] = None,
        appointment_date: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Make a phone call to the patient
        
        Args:
            to_phone: Patient's phone number (E.164 format)
            intent: 'cancel' or 'reschedule'
            patient_name: Patient's name (optional)
            appointment_date: Current appointment date (optional)
        
        Returns:
            Dictionary with call information
        """
        if not self.is_configured():
            raise ValueError(
                "Twilio is not configured. Please set TWILIO_ACCOUNT_SID, "
                "TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER in your .env file."
            )
        
        # Format phone number (ensure E.164 format)
        if not to_phone.startswith('+'):
            # Assume US number if no country code
            to_phone = f"+1{to_phone.replace('-', '').replace(' ', '').replace('(', '').replace(')', '')}"
        
        # Build webhook URL with parameters
        webhook_url = f"{self.webhook_base_url}/api/twilio/call-handler"
        webhook_url += f"?intent={intent}"
        if patient_name:
            webhook_url += f"&patient_name={patient_name}"
        if appointment_date:
            webhook_url += f"&appointment_date={appointment_date}"
        
        try:
            call = self.client.calls.create(
                to=to_phone,
                from_=self.phone_number,
                url=webhook_url,
                method='POST'
            )
            
            return {
                'success': True,
                'call_sid': call.sid,
                'status': call.status,
                'to': to_phone,
                'from': self.phone_number
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_twiml_greeting(self, intent: str, patient_name: Optional[str] = None) -> str:
        """
        Generate TwiML for call greeting
        
        Args:
            intent: 'cancel' or 'reschedule'
            patient_name: Patient's name (optional)
        
        Returns:
            TwiML XML string
        """
        response = VoiceResponse()
        
        # Greeting
        if patient_name:
            greeting = f"Hello {patient_name}, this is an automated call from your dental office."
        else:
            greeting = "Hello, this is an automated call from your dental office."
        
        response.say(greeting, voice='alice', language='en-US')
        
        # Context based on intent
        if intent == 'cancel':
            message = "We received a request to cancel your appointment. "
            message += "Please press 1 to confirm cancellation, or press 2 to speak with our staff."
        elif intent == 'reschedule':
            message = "We received a request to reschedule your appointment. "
            message += "Please press 1 to reschedule, or press 2 to speak with our staff."
        else:
            message = "How can we help you today?"
        
        response.say(message, voice='alice', language='en-US')
        
        # Gather input
        gather = Gather(
            input='dtmf',
            timeout=10,
            num_digits=1,
            action=f'{self.webhook_base_url}/api/twilio/handle-input?intent={intent}',
            method='POST'
        )
        gather.say("Please press a number.", voice='alice', language='en-US')
        response.append(gather)
        
        # Fallback if no input
        response.say("We didn't receive your input. Please call us back at your convenience.", voice='alice', language='en-US')
        response.hangup()
        
        return str(response)
    
    def generate_twiml_reschedule(self, selected_option: str) -> str:
        """
        Generate TwiML for rescheduling flow
        
        Args:
            selected_option: User's selected option ('1' for reschedule, '2' for staff)
        
        Returns:
            TwiML XML string
        """
        response = VoiceResponse()
        
        if selected_option == '1':
            # Reschedule flow
            response.say(
                "Thank you for choosing to reschedule. "
                "Please say the date and time that works best for you. "
                "For example, you can say 'Monday at 2 PM' or 'Next Friday morning'.",
                voice='alice',
                language='en-US'
            )
            
            # Gather voice input for preferred date/time
            gather = Gather(
                input='speech',
                timeout=15,
                action=f'{self.webhook_base_url}/api/twilio/handle-reschedule',
                method='POST',
                speech_timeout='auto',
                language='en-US'
            )
            gather.say("Please say your preferred date and time.", voice='alice', language='en-US')
            response.append(gather)
            
            # Fallback
            response.say(
                "We didn't catch that. Please call us back or visit our office to reschedule.",
                voice='alice',
                language='en-US'
            )
            
        elif selected_option == '2':
            # Transfer to staff
            response.say(
                "Thank you. Please hold while we transfer you to our staff. "
                "They will be able to assist you with your appointment.",
                voice='alice',
                language='en-US'
            )
            # In production, you would dial a staff number here
            # response.dial('+1234567890')  # Staff phone number
            response.say(
                "Our staff is currently unavailable. Please call us during business hours.",
                voice='alice',
                language='en-US'
            )
        else:
            response.say("Invalid option selected. Goodbye.", voice='alice', language='en-US')
        
        response.hangup()
        return str(response)
    
    def generate_twiml_cancel(self, selected_option: str) -> str:
        """
        Generate TwiML for cancellation flow
        
        Args:
            selected_option: User's selected option ('1' to confirm, '2' for staff)
        
        Returns:
            TwiML XML string
        """
        response = VoiceResponse()
        
        if selected_option == '1':
            # Confirm cancellation
            response.say(
                "Your appointment has been cancelled. "
                "We're sorry we won't see you, but we look forward to serving you in the future. "
                "If you'd like to schedule a new appointment, please call us or visit our website.",
                voice='alice',
                language='en-US'
            )
        elif selected_option == '2':
            # Transfer to staff
            response.say(
                "Thank you. Please hold while we transfer you to our staff. "
                "They will be able to assist you with your appointment cancellation.",
                voice='alice',
                language='en-US'
            )
            # In production, you would dial a staff number here
            response.say(
                "Our staff is currently unavailable. Please call us during business hours.",
                voice='alice',
                language='en-US'
            )
        else:
            response.say("Invalid option selected. Goodbye.", voice='alice', language='en-US')
        
        response.hangup()
        return str(response)
    
    def generate_twiml_confirmation(self, preferred_date: str, intent: str) -> str:
        """
        Generate TwiML for confirming rescheduled appointment
        
        Args:
            preferred_date: Patient's preferred date/time
            intent: 'reschedule'
        
        Returns:
            TwiML XML string
        """
        response = VoiceResponse()
        
        confirmation_message = (
            f"Thank you. We have noted your preference for {preferred_date}. "
            "Our staff will review your request and contact you to confirm the new appointment time. "
            "Is there anything else we can help you with?"
        )
        
        response.say(confirmation_message, voice='alice', language='en-US')
        
        # Gather yes/no response
        gather = Gather(
            input='speech',
            timeout=5,
            action=f'{self.webhook_base_url}/api/twilio/handle-confirmation',
            method='POST',
            speech_timeout='auto',
            language='en-US'
        )
        gather.say("Please say yes or no.", voice='alice', language='en-US')
        response.append(gather)
        
        response.say("Thank you for calling. Have a great day!", voice='alice', language='en-US')
        response.hangup()
        
        return str(response)

