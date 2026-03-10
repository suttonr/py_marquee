"""
Flask web server with session-based authentication for Marquee Control
"""
import os
import secrets as stdlib_secrets
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash, jsonify
from functools import wraps
import requests

# Launcher configuration
LAUNCHER_HOST = os.environ.get('LAUNCHER_HOST', 'localhost')
LAUNCHER_PORT = int(os.environ.get('LAUNCHER_PORT', 4000))
LAUNCHER_API_KEY = os.environ.get('LAUNCHER_API_KEY', 'demokey')

# Build the launcher base URL
LAUNCHER_BASE_URL = f"http://{LAUNCHER_HOST}:{LAUNCHER_PORT}"

app = Flask(__name__)

# Configuration
app.secret_key = os.environ.get('SECRET_KEY', stdlib_secrets.token_hex(32))

# User credentials - in production, use environment variables or a database
# Default credentials: admin / marquee123
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'marquee123')

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
        print("Headers",headers)
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
    allowed_extensions = {'', 'html', 'css', 'js', 'mjs', 'map', 'woff', 'woff2', 'ttf', 'svg', 'png', 'jpg', 'jpeg', 'gif'}
    
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
