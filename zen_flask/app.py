from flask import Flask, render_template, request, jsonify, make_response, url_for, redirect
import firebase_admin
from firebase_admin import credentials, auth
from ai_integration.integration import flask_ai_integration, get_response, speech_to_text, text_to_speech
from Core_Brain.memory_manager import MemoryManager
import uuid
# Add this at the top
import os

# Get backend API URL from environment variables
BACKEND_API_URL = os.environ.get('BACKEND_API_URL', 'http://localhost:8000')

# Modify the get_ai_response route
@app.route('/get_ai_response', methods=['POST'])
def get_ai_response():
    user_input = request.json.get('message')
    if not user_input:
        return jsonify({'error': 'No message provided'}), 400

    personality_name = request.json.get('personality', 'echo')
    
    try:
        # Call backend API instead of local Core_Brain
        import requests
        response = requests.post(
            f"{BACKEND_API_URL}/api/response",
            json={
                'message': user_input,
                'personality': personality_name
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'response': data['response'],
                'success': data['success']
            })
        else:
            return jsonify({
                'response': "Backend service unavailable",
                'error': "Backend returned non-200 status",
                'success': False
            }), 500
    except Exception as e:
        print(f"Error in get_ai_response: {e}")
        return jsonify({
            'response': "I'm sorry, I couldn't process your request at the moment.",
            'error': str(e),
            'success': False
        }), 500
app = Flask(__name__)

# Initialize Firebase Admin SDK
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

# In-memory storage for user sessions
user_sessions = {}

# Helper function to get or create user memory
# Note: In a production app, this would use a persistent storage solution

def get_user_memory(user_id):
    if user_id not in user_sessions:
        # Create a new memory manager for this user
        user_sessions[user_id] = {
            'memory': MemoryManager(),
            'last_active': datetime.utcnow()
        }
    return user_sessions[user_id]['memory']

# Import datetime for session management
import datetime

# Periodic cleanup function could be implemented here in production



@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/features')
def features():
    return render_template('features.html')

@app.route('/chat')
def chat_page():
    # Retrieve the session cookie
    session_cookie = request.cookies.get('session')
    if not session_cookie:
        # Redirect to login if no session cookie is found
        return redirect('/login')

    try:
        # Verify the session cookie
        decoded_token = auth.verify_session_cookie(session_cookie, check_revoked=True)
        user = auth.get_user(decoded_token['uid'])
        user_profile_pic = user.photo_url if user.photo_url else url_for('static', filename='default_profile.png')
        user_name = user.display_name if user.display_name else "User"
        
        # Ensure a memory manager exists for this user
        get_user_memory(decoded_token['uid'])
        
        return render_template('chat.html', user_profile_pic=user_profile_pic, user_name=user_name)
    except Exception as e:
        print(f"Error verifying session cookie: {e}")
        # Redirect to login if session cookie is invalid or revoked
        return redirect('/login')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/get_ai_response', methods=['POST'])
def get_ai_response():
    user_input = request.json.get('message')
    if not user_input:
        return jsonify({'error': 'No message provided'}), 400

    # Get session cookie to identify the user
    session_cookie = request.cookies.get('session')
    personality_name = request.json.get('personality', 'echo')  # Default to 'echo' personality
    
    try:
        # If user is authenticated, use their personal memory
        if session_cookie:
            decoded_token = auth.verify_session_cookie(session_cookie, check_revoked=True)
            user_id = decoded_token['uid']
            user_memory = get_user_memory(user_id)
        else:
            # For unauthenticated users, use a temporary anonymous memory
            anonymous_id = request.json.get('anonymous_id') or str(uuid.uuid4())
            user_memory = get_user_memory(anonymous_id)
        
        # Get AI response using the integration layer
        result = get_response(user_input, memory_manager=user_memory, personality_name=personality_name)
        
        if result['success']:
            return jsonify({
                'response': result['response'],
                'success': True
            })
        else:
            return jsonify({
                'response': result['response'],
                'error': result['error'],
                'success': False
            }), 500
            
    except Exception as e:
        print(f"Error in get_ai_response: {e}")
        # Fallback to using the integration without user-specific memory
        result = get_response(user_input, personality_name=personality_name)
        return jsonify({
            'response': result['response'],
            'error': str(e),
            'success': result['success']
        }), 500 if not result['success'] else 200

# Removed duplicated chat route - use /get_ai_response instead

@app.route('/text-to-speech', methods=['POST'])
def text_to_speech_route():
    text = request.json.get('text')
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    # Generate speech using the integration layer
    result = text_to_speech(text)
    
    if result['success']:
        return jsonify({
            'audio_path': result['audio_path'],
            'success': True
        })
    else:
        return jsonify({
            'error': result['error'],
            'success': False
        }), 500

@app.route('/speech-to-text', methods=['POST'])
def speech_to_text_route():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    audio_file = request.files['audio']
    audio_bytes = audio_file.read()
    
    # Process speech using the integration layer
    result = speech_to_text(audio_bytes)
    
    if result['success']:
        return jsonify({
            'transcript': result['transcript'],
            'success': True
        })
    else:
        return jsonify({
            'transcript': result['transcript'],  # May be empty
            'error': result['error'],
            'success': False
        }), 500

@app.route('/sessionLogin', methods=['POST'])
def session_login():
    print("Session login route hit!") # Debug print statement
    id_token = request.json.get('idToken')
    if not id_token:
        return jsonify({'error': 'ID token not provided'}), 400

    try:
        # Verify the ID token while checking if the token is revoked by passing check_revoked=True.
        decoded_token = auth.verify_id_token(id_token, check_revoked=True)
    except auth.RevokedIdTokenError:
        # Token revoked, inform the user to re-authenticate or sign out.
        return jsonify({'error': 'ID token revoked'}), 401
    except Exception as e:
        # Catch any other exceptions and return a JSON error response
        return jsonify({'error': str(e)}), 401

    session_cookie = auth.create_session_cookie(id_token, expires_in=3600 * 24 * 5) # 5 days in seconds
    response = make_response(jsonify({'status': 'success'}))
    response.set_cookie('session', session_cookie, httponly=True, secure=True)
    return response

@app.route('/sessionLogout', methods=['POST'])
def session_logout():
    response = make_response(jsonify({'status': 'success'}))
    response.set_cookie('session', '', expires=0, httponly=True, secure=True)
    return response

if __name__ == '__main__':
    app.run(debug=True)