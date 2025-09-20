# NLP, intent detection, emotion sense - Flask Integration Layer
import sys
import os
# Add parent directory to path to import from Core_Brain
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

# Import the Core_Brain's NLP engine instead of duplicating code
from Core_Brain.nlp_engine.nlp_engine import NLPEngine as CoreNLPEngine
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NLPEngine:
    """
    Wrapper class for Flask integration that uses the Core_Brain's NLPEngine
    This maintains compatibility with existing Flask app code while using the core implementation.
    """
    def __init__(self, model_name="llama3-8b-8192"):
        # Initialize the core NLP engine
        self.core_engine = CoreNLPEngine(model_name=model_name)
        logger.info(f"Flask NLP Engine initialized, using Core_Brain's NLPEngine with model: {model_name}")
        
    def call_groq_model(self, messages, max_tokens=200, temperature=0.7):
        """Wrapper for Groq API call"""
        return self.core_engine.call_groq_model(messages, max_tokens=max_tokens, temperature=temperature)
        
    @lru_cache(maxsize=128)
    def detect_intent_cached(self, user_input: str) -> str:
        return self.detect_intent(user_input)
        
    def detect_intent(self, user_input: str) -> str:
        return self.core_engine.detect_intent(user_input)
        
    def detect_emotion(self, user_input: str) -> dict:
        return self.core_engine.detect_emotion(user_input)
        
    def analyze(self, user_input: str, memory_manager=None) -> dict:
        """Wrapper for analyzing user input with memory context"""
        return self.core_engine.analyze(user_input, memory_manager=memory_manager)
        
    def get_sentiment(self, user_input: str) -> str:
        """Wrapper for sentiment analysis"""
        return self.core_engine.get_sentiment(user_input)
        
    def generate_response(self, user_input: str, context=None, personality=None) -> str:
        """Wrapper for response generation"""
        return self.core_engine.generate_response(user_input, context=context, personality=personality)
        
    def process_message(self, user_message: str, personality=None) -> str:
        """Wrapper for complete message processing"""
        if hasattr(self.core_engine, 'process_message'):
            return self.core_engine.process_message(user_message, personality)
        else:
            # Fallback implementation if method doesn't exist in core engine
            analysis = self.analyze(user_message)
            return self.generate_response(user_message, context=analysis, personality=personality)
        
    # Add any other methods that might be called by the Flask app's personality classes
    def __getattr__(self, name):
        """Fallback to core engine methods not explicitly wrapped"""
        return getattr(self.core_engine, name)


    def detect_emotion(self, user_input: str) -> dict:
        messages = [
            {
                "role": "system", 
                "content": "You are an emotion and sentiment detector. Reply ONLY with JSON like: {\"emotion\": \"sad\", \"sentiment\": \"negative\"}"
            },
            {
                "role": "user",
                "content": user_input
            }
        ]
        
        result = self.call_groq_model(messages, max_tokens=50)
        
        if result.startswith("[Groq Error]"):
            return {"emotion": "neutral", "sentiment": "neutral"}

        try:
            # Extract JSON from response
            start_idx = result.find('{')
            end_idx = result.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = result[start_idx:end_idx]
                parsed_data = json.loads(json_str)
                
                # Validate required fields
                if "emotion" in parsed_data and "sentiment" in parsed_data:
                    return parsed_data
                else:
                    self.logger.warning(f"Missing required fields in emotion detection response: {parsed_data}")
                    return {"emotion": "neutral", "sentiment": "neutral"}
            
        except json.JSONDecodeError as e:
            self.logger.error(f"[JSON Parsing Error]: {e}")
        except Exception as e:
            self.logger.error(f"[Unexpected Error in emotion detection]: {e}")
            
        # Default fallback
        return {"emotion": "neutral", "sentiment": "neutral"}

    # def generate_response(self,intent: str , emotion: str , user_input: str) -> str:
    #     system_prompt = (
    #         f"You are Echo, a caring AI assistant. The user is showing '{emotion}' emotion. "
    #         f"The intent is '{intent}'. Reply in a helpful, warm, or insightful way."
    #         )
    #     return self._call_llm(system_prompt, user_input, max_tokens=300)


    def analyze(self, user_input: str, memory_manager=None) -> dict:
        context = ""
        if memory_manager:
            context = memory_manager.get_context_text()

        intent = self.detect_intent(user_input)
        emotion_data = self.detect_emotion(user_input)
        sentiment = emotion_data.get("sentiment", "neutral") if emotion_data else "neutral"
        text = user_input

        # Inject context into system prompt for better LLM reply
        system_prompt = (
            f"You are Echo, a helpful AI assistant.\n"
            f"User's emotion: {emotion_data['emotion']}\n"
            f"User's intent: {intent}\n"
            f"Sentiment: {sentiment}\n"
            f"User said: {text}\n"
            "Reply as Echo with empathy and understanding (2-3 sentences):"
        )

        if context:
            system_prompt += f"\nHere is the recent conversation:\n{context}\nRespond appropriately."

        # Generate the response using chat format
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        response = self.call_groq_model(messages, max_tokens=150, temperature=0.8)
        
        # Save memory
        if memory_manager:
            memory_manager.add_memory(user_input, response)

        return {
            "intent": intent,
            "emotion": emotion_data["emotion"],
            "sentiment": emotion_data["sentiment"],
            "response": response
        }
