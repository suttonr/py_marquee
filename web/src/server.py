"""
Flask web server with session-based authentication for Marquee Control
Supports both password and FIDO2/WebAuthn authentication
"""
import os
import sys
import json
import secrets as stdlib_secrets
import ipaddress
import logging
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash, jsonify
from flask_socketio import SocketIO, emit
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
import requests

# Import heartbeat module (installed as py-marquee-heartbeat package)
try:
    from heartbeat import start_heartbeat
    HEARTBEAT_AVAILABLE = True
except ImportError:
    HEARTBEAT_AVAILABLE = False
    print("Warning: heartbeat module not available, health pings disabled")

# Import health monitor module
try:
    from health_monitor import (
        subscribe_to_health_topics,
        get_health_data,
        get_all_component_statuses
    )
    HEALTH_MONITOR_AVAILABLE = True
except ImportError:
    HEALTH_MONITOR_AVAILABLE = False
    print("Warning: health_monitor module not available")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import datetime for health timestamps
from datetime import datetime, timezone

# Access logger for request logs
access_logger = logging.getLogger('access_logger')
access_logger.setLevel(logging.INFO)

from webauthn_auth import WebAuthnManager
from mqtt_proxy import MQTTProxy

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
limiter = Limiter(get_remote_address, app=app)

# Configuration
app.secret_key = os.environ.get('SECRET_KEY', stdlib_secrets.token_hex(32))

# MQTT Configuration
MQTT_BROKER = os.environ.get('MQTT_BROKER', 'mqtt.ryanmsutton.com')
MQTT_PORT = int(os.environ.get('MQTT_PORT', 1883))
MQTT_USERNAME = os.environ.get('MQTT_USERNAME', 'py_marquee')
MQTT_PASSWORD = os.environ.get('MQTT_PASSWORD', '')
MQTT_KEEPALIVE = int(os.environ.get('MQTT_KEEPALIVE', 60))

# Grafana Configuration
GRAFANA_HOST = os.environ.get('GRAFANA_HOST', 'localhost')
GRAFANA_PORT = int(os.environ.get('GRAFANA_PORT', 3000))

# Launcher configuration
LAUNCHER_HOST = os.environ.get('LAUNCHER_HOST', 'localhost')
LAUNCHER_PORT = int(os.environ.get('LAUNCHER_PORT', 4000))
LAUNCHER_API_KEY = os.environ.get('LAUNCHER_API_KEY', '')
LAUNCHER_BASE_URL = f"http://{LAUNCHER_HOST}:{LAUNCHER_PORT}"

# User credentials - in production, use environment variables or a database
# Default credentials: admin / marquee123
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'marquee123')

WEB_RATE = os.environ.get('WEB_RATE', '4')

# Allow static password authentication
ALLOW_STATIC_PASSWORDS = os.environ.get('ALLOW_STATIC_PASSWORDS', 'false').lower() == 'true'

# Registration OTP for new passkey registration
REGISTRATION_OTP = os.environ.get('REGISTRATION_OTP',
                                  'changeme')

# Static folder configuration
STATIC_FOLDER = os.path.join(os.path.dirname(__file__), '')
# Auth directory for user JSON files
AUTH_DIR = os.environ.get('AUTH_DIR', '/auth')

# Initialize WebAuthn manager with RP config from environment
webauthn_rp_id = os.environ.get('WEBAUTHN_RP_ID', 'localhost')
webauthn_rp_name = os.environ.get('WEBAUTHN_RP_NAME', 'Marquee Control')
webauthn_rp_host = os.environ.get('WEBAUTHN_RP_HOST', 'http://localhost:8888')
webauthn_manager = WebAuthnManager(webauthn_rp_id, webauthn_rp_name,
                                   webauthn_rp_host, AUTH_DIR)

# Registration enabled/disabled setting
REGISTRATION_ENABLED = os.environ.get(
        'REGISTRATION_ENABLED', str(not webauthn_manager.has_credentials("admin"))
    ).lower() == 'true'

# Initialize MQTT Proxy
mqtt_proxy = MQTTProxy(
    broker=MQTT_BROKER,
    port=MQTT_PORT,
    username=MQTT_USERNAME,
    password=MQTT_PASSWORD,
    keepalive=MQTT_KEEPALIVE
)
mqtt_proxy.set_socketio(socketio)
mqtt_proxy.connect()


@app.after_request
def log_request(response):
    """Log request details including X-Real-IP"""
    real_ip = request.headers.get('X-Real-IP', request.remote_addr or '-')
    access_logger.info(f"{request.method} {request.path} - {response.status_code} - X-Real-IP: {real_ip}")
    return response


def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            next_url = request.url
            return redirect(url_for('login', next=next_url))
        return f(*args, **kwargs)
    return decorated_function

def check_user_data(username):
    """Check user JSON file"""
    user_file = os.path.join(AUTH_DIR, f'{username}.json')
    try:
        if os.path.exists(user_file):
            return True
    except Exception as e:
        print(f"No user file for {username}: {e}")
    return False

# WebSocket Event Handlers
@socketio.on('connect')
def handle_connect():
    """Handle WebSocket client connection - requires authentication"""
    # Flask's @login_required doesn't work with Socket.IO - check session manually
    if 'logged_in' not in session:
        print(f"WebSocket connection rejected: not authenticated - {request.sid}")
        return False
    print(f"WebSocket client connected: {request.sid}")
    return True

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket client disconnection"""
    # Check session exists before logging (may have been cleared)
    if session.get('logged_in'):
        print(f"WebSocket client disconnected: {request.sid}")

@socketio.on('mqtt_publish')
def handle_mqtt_publish(data):
    """Handle MQTT publish request from WebSocket client"""
    # Check authentication for each event
    if 'logged_in' not in session:
        emit('mqtt_error', {'error': 'Not authenticated'})
        return
    topic = data.get('topic')
    payload = data.get('payload', '')
    
    if not topic:
        emit('mqtt_error', {'error': 'Topic is required'})
        return
    
    success, error = mqtt_proxy.publish(topic, payload)
    if success:
        emit('mqtt_publish_success', {'topic': topic})
    else:
        emit('mqtt_error', {'error': error})

@socketio.on('mqtt_subscribe')
def handle_mqtt_subscribe(data):
    """Handle MQTT subscribe request from WebSocket client"""
    # Check authentication for each event
    if 'logged_in' not in session:
        emit('mqtt_error', {'error': 'Not authenticated'})
        return
    topic = data.get('topic')
    if not topic:
        emit('mqtt_error', {'error': 'Topic is required'})
        return
    
    success, error = mqtt_proxy.subscribe(topic)
    if success:
        emit('mqtt_subscribe_success', {'topic': topic})
    else:
        emit('mqtt_error', {'error': error})



@app.route('/api/launcher/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def proxy_to_launcher(path):
    """Proxy API requests to the launcher service"""
    # Build the target URL
    target_url = f"{LAUNCHER_BASE_URL}/{path}"
    
    # Forward the request method and headers (except host)
    method = request.method
    headers = {key: value for key, value in request.headers if key.lower() != 'host'}

    # Add API key to the request headers for the launcher
    if LAUNCHER_API_KEY:
        headers['X-API-Key'] = LAUNCHER_API_KEY
    
    # Prepare request data
    data = request.get_data() if method in ['POST', 'PUT'] else None
    
    try:
        response = requests.request(
            method=method,
            url=target_url,
            headers=headers,
            data=data,
            params=request.args,
            timeout=30
        )
        
        # Return the response from the launcher
        return response.content, response.status_code, response.headers.items()
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Unable to connect to launcher service'}), 502
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Launcher service request timed out'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/launcher', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def proxy_to_launcher_root():
    """Proxy API requests to the launcher service (root endpoint)"""
    return proxy_to_launcher('')


@app.route('/grafana/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
@app.route('/grafana/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
@login_required
def proxy_to_grafana(path):
    """Proxy requests to Grafana running on localhost:3000"""
    # Build the target URL
    grafana_url = f"http://{GRAFANA_HOST}:{GRAFANA_PORT}/{path}"
    
    # Forward the request method and headers (except host)
    method = request.method
    headers = {key: value for key, value in request.headers if key.lower() not in ['host', 'connection']}
    
    # Add the logged-in username to the headers
    if 'username' in session:
        headers['X-WEBAUTH-USER'] = session['username']
    
    # Prepare request data
    data = request.get_data() if method in ['POST', 'PUT', 'PATCH'] else None
    
    try:
        response = requests.request(
            method=method,
            url=grafana_url,
            headers=headers,
            data=data,
            params=request.args,
            timeout=30,
            allow_redirects=False,
            stream=True
        )
        
        # Build response headers, excluding certain headers that shouldn't be forwarded
        excluded_headers = ['connection', 'keep-alive', 'transfer-encoding', 'content-encoding', 'content-length', 'x-frame-options']
        response_headers = [(name, value) for (name, value) in response.headers.items() 
                           if name.lower() not in excluded_headers]
        
        # Return the response from Grafana
        return response.content, response.status_code, response_headers
    except requests.exceptions.ConnectionError:
        return jsonify({'error': 'Unable to connect to Grafana service on localhost:3000'}), 502
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Grafana service request timed out'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/')
@login_required
def index():
    """Main control page"""
    return send_from_directory('.', 'index.html')


@app.route('/login')
def login():
    """Login page"""
    if 'logged_in' in session:
        return redirect(url_for('index'))
    return send_from_directory('.', 'login.html')


@app.route('/login.html')
def login_html():
    """Login page (html extension)"""
    if 'logged_in' in session:
        return redirect(url_for('index'))
    return send_from_directory('.', 'login.html')


@app.route('/login', methods=['POST'])
def login_post():
    """Handle login form submission"""
    # Get the next URL to redirect to after login
    next_url = request.form.get('next') or request.args.get('next')
    # Validate that next_url is a safe redirect (same domain)
    if next_url:
        from urllib.parse import urlparse
        parsed = urlparse(next_url)
        if parsed.netloc and parsed.netloc != request.host:
            next_url = None  # Don't allow redirects to other domains
    
    if not ALLOW_STATIC_PASSWORDS:
        flash('Password authentication is disabled', 'error')
        return redirect(url_for('login'))

    username = request.form.get('username', '')
    password = request.form.get('password', '')

    if not password:
        flash('Password is required', 'error')
        return redirect(url_for('login'))

    # Check hardcoded admin credentials for backward compatibility
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['logged_in'] = True
        session['username'] = username
        flash('Successfully logged in!', 'success')
        if next_url:
            return redirect(next_url)
        return redirect(url_for('index'))

    # Check user file for password
    user_file = os.path.join(AUTH_DIR, f'{username}.json')
    if os.path.exists(user_file):
        try:
            with open(user_file, 'r') as f:
                user_data = json.load(f)
            stored_password = user_data.get('password')
            if stored_password and password == stored_password:
                session['logged_in'] = True
                session['username'] = username
                flash('Successfully logged in!', 'success')
                if next_url:
                    return redirect(next_url)
                return redirect(url_for('index'))
        except Exception as e:
            print(f"Error loading user data for {username}: {e}")

    flash('Invalid username or password', 'error')
    return redirect(url_for('login'))


# WebAuthn API Routes

@app.route('/api/webauthn/register/options', methods=['POST'])
def webauthn_register_options():
    """Get WebAuthn registration options"""
    data = request.get_json()
    username = data.get('username', '')
    
    if not username:
        return jsonify({'error': 'Username required'}), 400
    
    return webauthn_manager.get_registration_options(username)


@app.route('/api/webauthn/register', methods=['POST'])
def webauthn_register():
    """Verify and complete WebAuthn registration"""
    data = request.get_json()
    username = data.get('username', '')
    attestation_response = data.get('attestationResponse', {})

    if not username:
        return jsonify({'error': 'Username required'}), 400
    if not check_user_data(username):
        return jsonify({'error': 'Access Denied or Not Found'}), 404
    if not REGISTRATION_ENABLED:
        return jsonify({'error': 'New registrations are currently disabled'}), 403

    # Check if OTP has been verified for this user
    if not session.get('otp_verified') or session.get('otp_verified_username') != username:
        return jsonify({'error': 'OTP verification required before registration'}), 403

    result = webauthn_manager.verify_registration(username, attestation_response)

    # Clear OTP verification flags after successful registration
    if result[1] == 200:  # If registration was successful
        session.pop('otp_verified', None)
        session.pop('otp_verified_username', None)

    return result


@app.route('/api/webauthn/authenticate/options', methods=['POST'])
def webauthn_authenticate_options():
    """Get WebAuthn authentication options"""
    data = request.get_json()
    username = data.get('username', '')
    
    if not username:
        return jsonify({'error': 'Username required'}), 400
    
    return webauthn_manager.get_authentication_options(username)


@app.route('/api/webauthn/authenticate', methods=['POST'])
def webauthn_authenticate():
    """Verify WebAuthn authentication"""
    data = request.get_json()
    username = data.get('username', '')
    credential_id = data.get('credentialId', '')
    authenticator_response = data.get('authenticatorResponse', {})
    
    if not username:
        return jsonify({'error': 'Username required'}), 400
    
    result, status_code = webauthn_manager.verify_authentication(username, credential_id, authenticator_response)
    
    if status_code == 200:
        # Set session on successful WebAuthn authentication
        session['logged_in'] = True
        session['username'] = username
        session['webauthn_authenticated'] = True
    
    return result, status_code


@app.route('/api/webauthn/has-credentials', methods=['GET'])
@limiter.limit(f"{WEB_RATE} per minute")
def webauthn_has_credentials():
    """Check if user has WebAuthn credentials"""
    username = request.args.get('username', ADMIN_USERNAME)
    has_creds = webauthn_manager.has_credentials(username)
    return jsonify({'has_credentials': has_creds})

@app.route('/api/webauthn/verify-otp', methods=['POST'])
@limiter.limit("{WEB_RATE} per minute")
def webauthn_verify_otp():
    """Verify registration OTP for new passkey registration"""
    data = request.get_json()
    username = data.get('username', '')
    otp = data.get('otp', '')

    if not username:
        return jsonify({'error': 'Username required'}), 400
    if not otp:
        return jsonify({'error': 'OTP required'}), 400
    if not check_user_data(username):
        return jsonify({'error': 'Access Denied or Not Found'}), 404
    if not REGISTRATION_ENABLED:
        return jsonify({'error': 'New registrations are currently disabled'}), 403
    if not REGISTRATION_OTP:
        return jsonify({'error': 'Registration OTP not configured'}), 500

    if otp == REGISTRATION_OTP:
        # Store OTP verification in session
        session['otp_verified'] = True
        session['otp_verified_username'] = username
        return jsonify({'status': 'ok', 'message': 'OTP verified successfully'}), 200
    else:
        return jsonify({'error': 'Invalid OTP'}), 401


@app.route('/admin')
@login_required
def admin():
    """Administration page"""
    return send_from_directory('.', 'admin.html')


@app.route('/api/admin/registration-status', methods=['GET'])
@app.route('/registration-status', methods=['GET'])
def get_registration_status():
    """Get current registration status"""
    return jsonify({'enabled': REGISTRATION_ENABLED})


@app.route('/api/admin/registration-status', methods=['POST'])
@login_required
def set_registration_status():
    """Set registration status"""
    global REGISTRATION_ENABLED
    data = request.get_json()
    enabled = data.get('enabled', True)
    REGISTRATION_ENABLED = bool(enabled)
    return jsonify({'enabled': REGISTRATION_ENABLED})


@app.route('/api/admin/users', methods=['GET'])
@login_required
def get_users():
    """Get list of registered users"""
    users = webauthn_manager.get_users()
    return jsonify({'users': users})


@app.route('/api/admin/mqtt-allowlist', methods=['GET'])
@login_required
def get_mqtt_allowlist():
    """Get current user's MQTT IP allowlist"""
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_file = os.path.join(AUTH_DIR, f'{username}.json')
    try:
        if os.path.exists(user_file):
            with open(user_file, 'r') as f:
                user_data = json.load(f)
            allowlist = user_data.get('mqtt_allowlist', [])
            return jsonify({'mqtt_allowlist': allowlist})
        else:
            return jsonify({'mqtt_allowlist': []})
    except Exception as e:
        print(f"Error loading mqtt_allowlist for {username}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/mqtt-allowlist', methods=['POST'])
@login_required
def update_mqtt_allowlist():
    """Update current user's MQTT IP allowlist"""
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    action = data.get('action')
    ip_address = data.get('ip_address', '').strip()
    
    if not action or action not in ['add', 'remove']:
        return jsonify({'error': 'Invalid action. Must be "add" or "remove"'}), 400
    
    if action == 'add' and not ip_address:
        return jsonify({'error': 'IP address is required for add action'}), 400
    
    user_file = os.path.join(AUTH_DIR, f'{username}.json')
    try:
        # Load existing user data
        user_data = {}
        if os.path.exists(user_file):
            with open(user_file, 'r') as f:
                user_data = json.load(f)
        
        # Initialize mqtt_allowlist if not present
        if 'mqtt_allowlist' not in user_data:
            user_data['mqtt_allowlist'] = []
        
        allowlist = user_data['mqtt_allowlist']
        
        if action == 'add':
            # Validate IP address format using Python's ipaddress module
            try:
                # This will validate both IPv4 and IPv6 addresses
                ipaddress.ip_address(ip_address)
            except ValueError:
                return jsonify({'error': 'Invalid IP address format'}), 400
            
            # Check if already in allowlist
            if ip_address not in allowlist:
                allowlist.append(ip_address)
                user_data['mqtt_allowlist'] = allowlist
            else:
                return jsonify({'error': 'IP address already in allowlist'}), 400
        elif action == 'remove':
            if ip_address in allowlist:
                allowlist.remove(ip_address)
                user_data['mqtt_allowlist'] = allowlist
            else:
                return jsonify({'error': 'IP address not in allowlist'}), 404
        
        # Save updated user data
        with open(user_file, 'w') as f:
            json.dump(user_data, f, indent=2)
        
        return jsonify({'mqtt_allowlist': allowlist})
    except Exception as e:
        print(f"Error updating mqtt_allowlist for {username}: {e}")
        return jsonify({'error': str(e)}), 500



@app.route('/api/auth/config', methods=['GET'])
def get_auth_config():
    """Get authentication configuration"""
    return jsonify({
        'allow_static_passwords': ALLOW_STATIC_PASSWORDS,
        'registration_enabled': REGISTRATION_ENABLED
    })


@app.route('/system/health', methods=['GET'])
@login_required
def get_system_health():
    """Get health status of all system components.
    
    Returns health data from MQTT health ping topics.
    Components should publish to 'health/[component]/ping' topics.
    """
    if not HEALTH_MONITOR_AVAILABLE:
        return jsonify({
            'error': 'Health monitoring not available',
            'components': {}
        }), 500
    
    # Get health data from all components
    health_data = get_health_data()
    component_statuses = get_all_component_statuses(max_age_seconds=120)
    
    # Combine health data with computed statuses
    result = {
        'components': {},
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    for component, data in health_data.items():
        result['components'][component] = {
            'status': component_statuses.get(component, 'unknown'),
            'last_ping': data.get('last_ping'),
            'topic': data.get('topic'),
            'payload': data.get('payload')
        }
    
    # Add components that haven't reported yet as unknown
    known_components = {'web', 'launcher', 'matrix', 'mqtt', 'grafana'}
    for component in known_components:
        if component not in result['components']:
            result['components'][component] = {
                'status': 'unknown',
                'last_ping': None,
                'topic': f'health/{component}/ping',
                'payload': None
            }
    
    return jsonify(result)


@app.route('/system/health/<component>', methods=['GET'])
@login_required
def get_component_health(component):
    """Get health status of a specific component."""
    if not HEALTH_MONITOR_AVAILABLE:
        return jsonify({
            'error': 'Health monitoring not available'
        }), 500
    
    health_data = get_health_data()
    component_statuses = get_all_component_statuses(max_age_seconds=120)
    
    if component in health_data:
        data = health_data[component]
        return jsonify({
            'component': component,
            'status': component_statuses.get(component, 'unknown'),
            'last_ping': data.get('last_ping'),
            'topic': data.get('topic'),
            'payload': data.get('payload')
        })
    else:
        return jsonify({
            'component': component,
            'status': 'unknown',
            'last_ping': None,
            'topic': f'health/{component}/ping',
            'payload': None
        })


@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))


@app.route('/<path:filename>')
@login_required
def serve_static(filename):
    """Serve static files (HTML, CSS, JS)"""
    # Allow common static file extensions
    allowed_extensions = {
        'html', 'css', 'js', 'mjs', 'map', 
        'woff', 'woff2', 'ttf', 'svg', 'png', 
        'jpg', 'jpeg', 'gif'}
    
    # Get the file extension
    ext = filename.split('.')[-1] if '.' in filename else ''
    
    # Check if the file should be served
    if ext in allowed_extensions or '.' not in filename:
        try:
            return send_from_directory('.', filename)
        except:
            pass
    
    # Default to index.html for SPA-style routing
    return send_from_directory('.', 'index.html')


# Global heartbeat instance for cleanup
web_heartbeat = None

def cleanup_web_heartbeat():
    """Clean up heartbeat on shutdown."""
    global web_heartbeat
    if web_heartbeat:
        try:
            web_heartbeat.stop()
            print("Web heartbeat stopped")
        except Exception as e:
            print(f"Error stopping web heartbeat: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8888))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    
    print(f"Starting Marquee Control Web Server on port {port}")
    print(f"Login credentials: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
    print(f"Change credentials using ADMIN_USERNAME and ADMIN_PASSWORD environment variables")
    print(f"Launcher proxy configured: {LAUNCHER_BASE_URL}")
    print(f"Launcher API Key: {'Set' if LAUNCHER_API_KEY else 'Not set (optional)'}")
    print(f"MQTT proxy configured: {MQTT_BROKER}:{MQTT_PORT}")
    
    # Start heartbeat on 'health/web/ping' topic using the MQTT proxy client
    if HEARTBEAT_AVAILABLE:
        try:
            # Wait for MQTT proxy to connect (with timeout)
            import time
            for _ in range(10):
                if mqtt_proxy.is_connected():
                    break
                time.sleep(0.5)
            
            if mqtt_proxy.is_connected():
                web_heartbeat = start_heartbeat(
                    mqtt_proxy.client,
                    topic="health/web/ping",
                    interval_seconds=60
                )
                print("Web heartbeat started on 'health/web/ping'")
            else:
                print("Warning: MQTT proxy not connected, health pings disabled")
        except Exception as e:
            print(f"Warning: Failed to start web heartbeat: {e}")
    
    # Subscribe to health topics from other components
    if HEALTH_MONITOR_AVAILABLE:
        try:
            import time
            for _ in range(10):
                if mqtt_proxy.is_connected():
                    break
                time.sleep(0.5)
            
            if mqtt_proxy.is_connected():
                subscribe_to_health_topics(mqtt_proxy.client)
                print("Health topic subscriptions enabled")
            else:
                print("Warning: MQTT proxy not connected, health monitoring disabled")
        except Exception as e:
            print(f"Warning: Failed to subscribe to health topics: {e}")
    
    # Register cleanup handler
    import atexit
    atexit.register(cleanup_web_heartbeat)
    
    socketio.run(app, host='0.0.0.0', port=port, debug=debug, allow_unsafe_werkzeug=True)
