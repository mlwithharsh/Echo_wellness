import os
import json
import uuid
import datetime
import logging
from flask import Flask, render_template, request, jsonify, make_response, url_for, redirect
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Configuration
BACKEND_API_URL = os.environ.get('BACKEND_API_URL', 'http://localhost:8000')
FIREBASE_ENABLED = False

# Initialize Firebase Admin SDK safely
try:
    import firebase_admin
    from firebase_admin import credentials, auth
    
    # Try environment variable first (production)
    if 'FIREBASE_CREDENTIALS' in os.environ:
        cred_dict = json.loads(os.environ['FIREBASE_CREDENTIALS'])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        FIREBASE_ENABLED = True
        logger.info("Firebase initialized from environment variable")
    
    # Fallback to local file (development only)
    elif os.path.exists("serviceAccountKey.json"):
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
        FIREBASE_ENABLED = True
        logger.info("Firebase initialized from local file")
    
    else:
        logger.warning("Firebase credentials not found - authentication disabled")
        
except ImportError:
    logger.warning("Firebase Admin SDK not installed - authentication disabled")
except Exception as e:
    logger.error(f"Firebase initialization failed: {e}")

# In-memory storage for user sessions (use Redis/database in production)
user_sessions = {}

class SimpleMemoryManager:
    """Simplified memory manager that doesn't depend on external modules"""
    def __init__(self):
        self.conversations = []
        self.user_context = {}
    
    def add_interaction(self, user_input, ai_response):
        self.conversations.append({
            'timestamp': datetime.datetime.utcnow(),
            'user': user_input,
            'ai': ai_response
        })
        # Keep only last 10 interactions
        if len(self.conversations) > 10:
            self.conversations = self.conversations[-10:]
    
    def get_context(self):
        return self.conversations[-3:] if self.conversations else []

def get_user_memory(user_id):
    """Get or create user memory manager"""
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            'memory': SimpleMemoryManager(),
            'last_active': datetime.datetime.utcnow()
        }
    
    # Update last active time
    user_sessions[user_id]['last_active'] = datetime.datetime.utcnow()
    return user_sessions[user_id]['memory']

def cleanup_old_sessions():
    """Clean up sessions older than 24 hours"""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    old_sessions = [
        user_id for user_id, session in user_sessions.items()
        if session['last_active'] < cutoff
    ]
    for user_id in old_sessions:
        del user_sessions[user_id]
    logger.info(f"Cleaned up {len(old_sessions)} old sessions")

# Routes
@app.route('/')
def landing():
    try:
        return render_template('landing.html')
    except Exception as e:
        logger.error(f"Template error: {e}")
        return jsonify({
            'status': 'EchoV1 Flask App Running',
            'message': 'Landing page template not found',
            'firebase_enabled': FIREBASE_ENABLED
        })

@app.route('/features')
def features():
    try:
        return render_template('features.html')
    except Exception as e:
        logger.error(f"Template error: {e}")
        return jsonify({
            'status': 'Features page',
            'message': 'Features template not found'
        })

@app.route('/chat')
def chat_page():
    # Skip authentication if Firebase is disabled
    if not FIREBASE_ENABLED:
        logger.info("Firebase disabled - allowing anonymous chat access")
        return render_template('chat.html', 
                             user_profile_pic=url_for('static', filename='default_profile.png'),
                             user_name="Guest User") if template_exists('chat.html') else jsonify({
            'message': 'Chat interface',
            'user': 'Guest User',
            'firebase_enabled': False
        })
    
    # Check session cookie
    session_cookie = request.cookies.get('session')
    if not session_cookie:
        return redirect('/login')
    
    try:
        # Verify the session cookie
        decoded_token = auth.verify_session_cookie(session_cookie, check_revoked=True)
        user = auth.get_user(decoded_token['uid'])
        user_profile_pic = user.photo_url or url_for('static', filename='default_profile.png')
        user_name = user.display_name or "User"
        
        # Ensure a memory manager exists for this user
        get_user_memory(decoded_token['uid'])
        
        if template_exists('chat.html'):
            return render_template('chat.html', 
                                 user_profile_pic=user_profile_pic, 
                                 user_name=user_name)
        else:
            return jsonify({
                'message': 'Chat interface',
                'user': user_name,
                'authenticated': True
            })
            
    except Exception as e:
        logger.error(f"Error verifying session cookie: {e}")
        return redirect('/login')

@app.route('/login')
def login():
    if not FIREBASE_ENABLED:
        return redirect('/chat')  # Skip login if Firebase is disabled
    
    if template_exists('login.html'):
        return render_template('login.html')
    else:
        return jsonify({
            'message': 'Login page',
            'firebase_enabled': True,
            'note': 'Template not found - implement frontend'
        })

@app.route('/signup')
def signup():
    if not FIREBASE_ENABLED:
        return redirect('/chat')  # Skip signup if Firebase is disabled
    
    if template_exists('signup.html'):
        return render_template('signup.html')
    else:
        return jsonify({
            'message': 'Signup page',
            'firebase_enabled': True,
            'note': 'Template not found - implement frontend'
        })

@app.route('/get_ai_response', methods=['POST'])
def get_ai_response():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        user_input = data.get('message')
        if not user_input:
            return jsonify({'error': 'No message provided'}), 400

        personality_name = data.get('personality', 'echo')
        
        # Get user ID for memory management
        user_id = None
        if FIREBASE_ENABLED:
            session_cookie = request.cookies.get('session')
            if session_cookie:
                try:
                    decoded_token = auth.verify_session_cookie(session_cookie, check_revoked=True)
                    user_id = decoded_token['uid']
                except:
                    pass
        
        # Use anonymous ID if not authenticated
        if not user_id:
            user_id = data.get('anonymous_id', f"anon_{uuid.uuid4().hex[:8]}")
        
        # Get user memory
        user_memory = get_user_memory(user_id)
        
        # Try backend API first
        try:
            response = requests.post(
                f"{BACKEND_API_URL}/api/response",
                json={
                    'message': user_input,
                    'personality': personality_name,
                    'context': user_memory.get_context()
                },
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                ai_response = response_data.get('response', 'No response from backend')
                
                # Store interaction in memory
                user_memory.add_interaction(user_input, ai_response)
                
                return jsonify({
                    'response': ai_response,
                    'success': True,
                    'source': 'backend'
                })
                
        except requests.RequestException as e:
            logger.error(f"Backend API failed: {e}")
        
        # Fallback response with simple context awareness
        context = user_memory.get_context()
        if context:
            fallback_response = f"I understand you're saying '{user_input}'. I remember our recent conversation, but my AI backend is currently unavailable. This is a fallback response."
        else:
            fallback_response = f"Hello! I received your message: '{user_input}'. My AI backend is currently unavailable, so this is a fallback response. How can I help you?"
        
        # Store interaction
        user_memory.add_interaction(user_input, fallback_response)
        
        return jsonify({
            'response': fallback_response,
            'success': True,
            'source': 'fallback'
        })
        
    except Exception as e:
        logger.error(f"Error in get_ai_response: {e}")
        return jsonify({
            'response': "I apologize, but I'm having trouble processing your request right now. Please try again.",
            'error': str(e),
            'success': False
        }), 500

@app.route('/text-to-speech', methods=['POST'])
def text_to_speech_route():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        text = data.get('text')
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Placeholder - TTS functionality disabled for deployment safety
        return jsonify({
            'audio_path': None,
            'message': 'Text-to-speech feature is currently disabled for deployment safety',
            'success': False
        })
        
    except Exception as e:
        logger.error(f"Error in text-to-speech: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/speech-to-text', methods=['POST'])
def speech_to_text_route():
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        # Placeholder - STT functionality disabled for deployment safety
        return jsonify({
            'transcript': 'Speech-to-text feature is currently disabled for deployment safety',
            'message': 'Feature temporarily unavailable',
            'success': False
        })
        
    except Exception as e:
        logger.error(f"Error in speech-to-text: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/sessionLogin', methods=['POST'])
def session_login():
    if not FIREBASE_ENABLED:
        return jsonify({
            'status': 'success',
            'message': 'Authentication disabled - using guest mode'
        })
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        id_token = data.get('idToken')
        if not id_token:
            return jsonify({'error': 'ID token not provided'}), 400

        # Verify the ID token
        decoded_token = auth.verify_id_token(id_token, check_revoked=True)
        
        # Create session cookie
        session_cookie = auth.create_session_cookie(id_token, expires_in=3600 * 24 * 5)
        response = make_response(jsonify({'status': 'success'}))
        response.set_cookie('session', session_cookie, httponly=True, secure=True, samesite='Lax')
        
        logger.info(f"User {decoded_token['uid']} logged in successfully")
        return response
        
    except auth.RevokedIdTokenError:
        return jsonify({'error': 'ID token revoked'}), 401
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': str(e)}), 401

@app.route('/sessionLogout', methods=['POST'])
def session_logout():
    response = make_response(jsonify({'status': 'success'}))
    response.set_cookie('session', '', expires=0, httponly=True, secure=True, samesite='Lax')
    return response

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    cleanup_old_sessions()  # Clean up old sessions
    
    return jsonify({
        'status': 'healthy',
        'firebase_enabled': FIREBASE_ENABLED,
        'backend_url': BACKEND_API_URL,
        'active_sessions': len(user_sessions),
        'timestamp': datetime.datetime.utcnow().isoformat()
    })

@app.route('/api/status')
def api_status():
    """API status endpoint"""
    return jsonify({
        'app_name': 'EchoV1 Flask Backend',
        'version': '1.0.0',
        'firebase_auth': FIREBASE_ENABLED,
        'features': {
            'chat': True,
            'authentication': FIREBASE_ENABLED,
            'text_to_speech': False,  # Disabled for safe deployment
            'speech_to_text': False   # Disabled for safe deployment
        }
    })

# Utility functions
def template_exists(template_name):
    """Check if template file exists"""
    try:
        app.jinja_env.get_template(template_name)
        return True
    except:
        return False

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Not found',
        'message': 'The requested resource was not found',
        'available_endpoints': [
            '/', '/health', '/api/status', '/chat', '/get_ai_response'
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'error': 'Internal server error',
        'message': 'Something went wrong on our end'
    }), 500

# Development vs Production configuration
if __name__ == '__main__':
    # Development mode
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
else:
    # Production mode - configure logging
    if not app.debug:
        import logging
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('EchoV1 Flask app startup')
