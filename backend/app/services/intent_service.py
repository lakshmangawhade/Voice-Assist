"""
Intent Detection Service for identifying appointment-related requests
"""

import re
from typing import Dict, Optional


class IntentService:
    """Service for detecting user intents from messages"""
    
    def __init__(self):
        # Keywords for appointment cancellation
        self.cancel_keywords = [
            'cancel', 'cancellation', 'cancel appointment', 'cancel my appointment',
            'need to cancel', 'want to cancel', 'cancel the appointment',
            'reschedule', 'rescheduling', 'change appointment', 'move appointment',
            'postpone', 'change date', 'different date', 'another time'
        ]
        
        # Keywords for rescheduling
        self.reschedule_keywords = [
            'reschedule', 'rescheduling', 'change appointment', 'move appointment',
            'postpone', 'change date', 'different date', 'another time',
            'different day', 'better time', 'new appointment'
        ]
    
    def detect_intent(self, user_message: str, ai_response: str = "") -> Dict[str, any]:
        """
        Detect intent from user message and AI response
        
        Args:
            user_message: The user's message
            ai_response: The AI's response (optional, for context)
        
        Returns:
            Dictionary with intent information:
            {
                'intent': 'cancel' | 'reschedule' | 'none',
                'confidence': float (0.0 to 1.0),
                'requires_call': bool,
                'extracted_info': dict
            }
        """
        message_lower = user_message.lower()
        combined_text = f"{user_message} {ai_response}".lower()
        
        # Check for cancellation intent
        cancel_score = sum(1 for keyword in self.cancel_keywords if keyword in message_lower)
        reschedule_score = sum(1 for keyword in self.reschedule_keywords if keyword in message_lower)
        
        # Extract phone number if mentioned
        phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        phone_match = re.search(phone_pattern, user_message)
        phone_number = phone_match.group(0) if phone_match else None
        
        # Extract date/time mentions
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # MM/DD/YYYY
            r'(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
            r'(today|tomorrow|next week|next month)',
        ]
        dates_mentioned = []
        for pattern in date_patterns:
            matches = re.findall(pattern, message_lower)
            dates_mentioned.extend(matches)
        
        # Determine intent
        if cancel_score > 0 or reschedule_score > 0:
            if reschedule_score > cancel_score:
                intent = 'reschedule'
                confidence = min(0.7 + (reschedule_score * 0.1), 1.0)
            else:
                intent = 'cancel'
                confidence = min(0.7 + (cancel_score * 0.1), 1.0)
            
            requires_call = True
            
            return {
                'intent': intent,
                'confidence': confidence,
                'requires_call': requires_call,
                'extracted_info': {
                    'phone_number': phone_number,
                    'dates_mentioned': dates_mentioned,
                    'original_message': user_message
                }
            }
        
        return {
            'intent': 'none',
            'confidence': 0.0,
            'requires_call': False,
            'extracted_info': {}
        }
    
    def should_trigger_call(self, intent_result: Dict) -> bool:
        """Determine if a call should be triggered based on intent"""
        return (
            intent_result['intent'] in ['cancel', 'reschedule'] and
            intent_result['confidence'] >= 0.6 and
            intent_result['requires_call']
        )

