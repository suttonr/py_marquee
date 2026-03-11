"""
Flask web server with session-based authentication for Marquee Control
Supports both password and FIDO2/WebAuthn authentication
"""
import os
import json
import secrets as stdlib_secrets
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
import requests

from webauthn_auth import WebAuthnManager

app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app)

# Configuration
app.secret_key = os.environ.get('SECRET_KEY', stdlib_secrets.token_hex(32))

# Launcher configuration
LAUNCHER_HOST = os.environ.get('LAUNCHER_HOST', 'localhost')
LAUNCHER_PORT = int(os.environ.get('LAUNCHER_PORT', 4000))
LAUNCHER_API_KEY = os.environ.get('LAUNCHER_API_KEY', '')
LAUNCHER_BASE_URL = f"http://{LAUNCHER_HOST}:{LAUNCHER_PORT}"

# User credentials - in production, use environment variables or a database
# Default credentials: admin / marquee123
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'marquee123')

# Registration OTP for new passkey registration
REGISTRATION_OTP = os.environ.get('REGISTRATION_OTP', 
                                  'changeme')

# Initialize WebAuthn manager with RP config from environment
webauthn_rp_id = os.environ.get('WEBAUTHN_RP_ID', 'localhost')
webauthn_rp_name = os.environ.get('WEBAUTHN_RP_NAME', 'Marquee Control')
webauthn_rp_host = os.environ.get('WEBAUTHN_RP_HOST', 'http://localhost:8888')
webauthn_cred_file = os.environ.get('WEBAUTHN_CRED_FILE', 'webauthn_credentials.json')
webauthn_manager = WebAuthnManager(webauthn_rp_id, webauthn_rp_name, 
                                   webauthn_rp_host, webauthn_cred_file)

# Static folder configuration
STATIC_FOLDER = os.path.join(os.path.dirname(__file__), '')


def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


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
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['logged_in'] = True
        session['username'] = username
        flash('Successfully logged in!', 'success')
        return redirect(url_for('index'))
    else:
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
@limiter.limit("2 per minute")
def webauthn_has_credentials():
    """Check if user has WebAuthn credentials"""
    username = request.args.get('username', ADMIN_USERNAME)
    has_creds = webauthn_manager.has_credentials(username)
    return jsonify({'has_credentials': has_creds})

@app.route('/api/webauthn/verify-otp', methods=['POST'])
@limiter.limit("1 per minute")
def webauthn_verify_otp():
    """Verify registration OTP for new passkey registration"""
    data = request.get_json()
    username = data.get('username', '')
    otp = data.get('otp', '')

    if not username:
        return jsonify({'error': 'Username required'}), 400

    if not otp:
        return jsonify({'error': 'OTP required'}), 400

    if not REGISTRATION_OTP:
        return jsonify({'error': 'Registration OTP not configured'}), 500

    if otp == REGISTRATION_OTP:
        # Store OTP verification in session
        session['otp_verified'] = True
        session['otp_verified_username'] = username
        return jsonify({'status': 'ok', 'message': 'OTP verified successfully'}), 200
    else:
        return jsonify({'error': 'Invalid OTP'}), 401


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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8888))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    
    print(f"Starting Marquee Control Web Server on port {port}")
    print(f"Login credentials: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
    print(f"Change credentials using ADMIN_USERNAME and ADMIN_PASSWORD environment variables")
    print(f"Launcher proxy configured: {LAUNCHER_BASE_URL}")
    print(f"Launcher API Key: {'Set' if LAUNCHER_API_KEY else 'Not set (optional)'}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
