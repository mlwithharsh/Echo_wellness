# Flask AI Integration Layer
import sys
import os
import logging

# Add the parent directory to sys.path to access Core_Brain
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.join(current_dir, '..', '..')
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from Core_Brain import stt, tts, nlp, memory, get_core_status, is_core_ready
from .personality_router import PersonalityRouter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FlaskAIIntegration:
    """
    Integration class for connecting Flask frontend with Core_Brain components
    """
    def __init__(self):
        self.core_initialized = is_core_ready()
        self.status = get_core_status()
        self.personality_router = PersonalityRouter()
        
        if self.core_initialized:
            logger.info("Core Brain components initialized successfully for Flask integration")
        else:
            failed = [name for name, ready in self.status.items() if not ready]
            logger.warning(f"Some Core Brain components failed to initialize: {failed}")
    
    def get_ai_response(self, user_input, memory_manager=None, personality_name=None):
        """
        Get AI response using the selected personality and memory manager
        """
        try:
            # Use provided memory manager or the core memory
            current_memory = memory_manager if memory_manager else memory
            
            # Set personality if specified
            if personality_name:
                self.personality_router.set_personality(personality_name)
            
            # Get response from personality router
            response = self.personality_router.get_response(user_input, current_memory)
            
            return {
                'success': True,
                'response': response
            }
        except Exception as e:
            logger.error(f"Error getting AI response: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': "I'm sorry, I couldn't process your request at the moment."
            }
    
    def process_speech(self, audio_bytes):
        """
        Process speech input and return transcript
        """
        try:
            if not stt:
                return {
                    'success': False,
                    'error': 'Speech-to-Text component not available'
                }
            
            transcript = stt.process_audio_bytes(audio_bytes)
            return {
                'success': True,
                'transcript': transcript
            }
        except Exception as e:
            logger.error(f"Error processing speech: {e}")
            return {
                'success': False,
                'error': str(e),
                'transcript': ""
            }
    
    def generate_speech(self, text):
        """
        Generate speech from text
        """
        try:
            if not tts:
                return {
                    'success': False,
                    'error': 'Text-to-Speech component not available'
                }
            
            audio_path = tts.speak(text)
            if "[TTS Error]" in str(audio_path):
                return {
                    'success': False,
                    'error': 'Text-to-Speech generation failed'
                }
            
            return {
                'success': True,
                'audio_path': audio_path
            }
        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def analyze_message(self, user_input, memory_manager=None):
        """
        Analyze user input for intent, emotion, and sentiment
        """
        try:
            if not nlp:
                return {
                    'success': False,
                    'error': 'NLP component not available',
                    'analysis': {
                        'intent': 'unknown',
                        'emotion': 'neutral',
                        'sentiment': 'neutral'
                    }
                }
            
            current_memory = memory_manager if memory_manager else memory
            analysis = nlp.analyze(user_input, memory_manager=current_memory)
            
            return {
                'success': True,
                'analysis': analysis
            }
        except Exception as e:
            logger.error(f"Error analyzing message: {e}")
            return {
                'success': False,
                'error': str(e),
                'analysis': {
                    'intent': 'unknown',
                    'emotion': 'neutral',
                    'sentiment': 'neutral'
                }
            }
            
    def call_groq_model(self, messages, max_tokens=150, temperature=0.7):
        """
        Make a direct call to the Groq model through the NLP engine
        """
        try:
            if not nlp:
                logger.warning("NLP component not available for Groq model call")
                return "I'm sorry, I'm having trouble processing your request at the moment."
            
            if hasattr(nlp, 'call_groq_model'):
                return nlp.call_groq_model(messages, max_tokens=max_tokens, temperature=temperature)
            else:
                logger.warning("NLP engine doesn't support call_groq_model method")
                return "I'm sorry, I'm having trouble generating a response."
        except Exception as e:
            logger.error(f"Error calling Groq model: {e}")
            return "I'm sorry, I encountered an error processing your request."

# Create a singleton instance of the integration
flask_ai_integration = FlaskAIIntegration()

# Export the instance and necessary functions
def get_integration():
    return flask_ai_integration

# Helper functions for direct access
def get_response(user_input, memory_manager=None, personality_name=None):
    return flask_ai_integration.get_ai_response(user_input, memory_manager, personality_name)

def speech_to_text(audio_bytes):
    return flask_ai_integration.process_speech(audio_bytes)

def text_to_speech(text):
    return flask_ai_integration.generate_speech(text)

def analyze_text(user_input, memory_manager=None):
    return flask_ai_integration.analyze_message(user_input, memory_manager)