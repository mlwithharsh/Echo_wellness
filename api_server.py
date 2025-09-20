from flask import Flask, request, jsonify
from Core_Brain import stt, tts, nlp, memory
from flask_cors import CORS
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Security (optional)
API_KEY = os.environ.get("API_KEY", None)

app = Flask(__name__)
CORS(app)

def check_api_key(req):
    """Check if API key is valid"""
    if API_KEY:
        client_key = req.headers.get("x-api-key")
        if client_key != API_KEY:
            return False
    return True

@app.route('/api/response', methods=['POST'])
def api_response():
    if not check_api_key(request):
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        data = request.json
        user_input = data.get('message')
        personality_name = data.get('personality', 'echo')

        if not user_input:
            return jsonify({"success": False, "error": "No input message provided"}), 400

        # Use Core NLP module
        response_text = nlp.generate_response(user_input, personality=personality_name) \
            if hasattr(nlp, "generate_response") else f"You said: {user_input}"

        # Memory (if implemented)
        if hasattr(memory, "store"):
            memory.store(user_input, response_text)

        return jsonify({
            'success': True,
            'response': response_text
        })

    except Exception as e:
        logging.error("Error in /api/response", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'response': "I'm sorry, I couldn't process your request at the moment."
        }), 500

@app.route('/api/stt', methods=['POST'])
def api_stt():
    if not check_api_key(request):
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        audio_file = request.files.get("audio")
        if not audio_file:
            return jsonify({"success": False, "error": "No audio file uploaded"}), 400

        text_output = stt.transcribe(audio_file) if hasattr(stt, "transcribe") else "STT not implemented"
        return jsonify({"success": True, "text": text_output})

    except Exception as e:
        logging.error("Error in /api/stt", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/tts', methods=['POST'])
def api_tts():
    if not check_api_key(request):
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        data = request.json
        text_input = data.get("text")

        if not text_input:
            return jsonify({"success": False, "error": "No text provided"}), 400

        audio_output = tts.speak(text_input) if hasattr(tts, "speak") else None

        if audio_output:
            return jsonify({"success": True, "audio": audio_output})  # You might return a file/url instead
        else:
            return jsonify({"success": False, "error": "TTS not implemented"}), 500

    except Exception as e:
        logging.error("Error in /api/tts", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
