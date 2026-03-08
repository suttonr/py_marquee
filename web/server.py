"""
Flask web server with session-based authentication for Marquee Control
"""
import os
import secrets as stdlib_secrets
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash
from functools import wraps

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
    
    app.run(host='0.0.0.0', port=port, debug=debug)
