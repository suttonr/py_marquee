"""
Tests for the Flask web server authentication and MQTT WebSocket proxy
"""
import pytest
import sys
import os
import json
import tempfile
from unittest.mock import Mock, MagicMock, patch

# Set AUTH_DIR to a writable temp directory before importing server
TEST_AUTH_DIR = tempfile.mkdtemp()
os.environ['AUTH_DIR'] = TEST_AUTH_DIR

# Add the web/src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'web', 'src'))

from server import app, limiter, socketio, mqtt_proxy


def create_test_user_file(username):
    """Create a test user file in the AUTH_DIR"""
    user_file = os.path.join(TEST_AUTH_DIR, f'{username}.json')
    os.makedirs(TEST_AUTH_DIR, exist_ok=True)
    with open(user_file, 'w') as f:
        json.dump({'username': username}, f)


@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    app.config['TESTING'] = True
    limiter.enabled = False  # Disable rate limiting in tests
    
    # Create test user files
    create_test_user_file('testuser')
    create_test_user_file('user1')
    create_test_user_file('user2')
    
    with app.test_client() as client:
        yield client


@pytest.fixture
def authenticated_client(client):
    """Create an authenticated test client"""
    # Login with default credentials
    client.post('/login', data={
        'username': 'admin',
        'password': 'marquee123'
    })
    return client


@pytest.fixture
def client_with_rate_limiting():
    """Create a test client with rate limiting enabled (for testing rate limits)"""
    app.config['TESTING'] = True
    limiter.enabled = True  # Enable rate limiting for these specific tests
    with app.test_client() as client:
        yield client
    # Reset limiter state after test
    limiter.enabled = False


class TestAuthentication:
    """Tests for authentication functionality"""
    
    def test_login_page_loads(self, client):
        """Test that login page loads successfully"""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'Marquee Control' in response.data
    
    def test_login_success(self, client):
        """Test successful login"""
        response = client.post('/login', data={
            'username': 'admin',
            'password': 'marquee123'
        }, follow_redirects=True)
        assert response.status_code == 200
    
    def test_login_failure(self, client):
        """Test failed login with wrong credentials"""
        response = client.post('/login', data={
            'username': 'admin',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        assert response.status_code == 200
        # Should redirect back to login page
        assert b'Login' in response.data or b'Sign In' in response.data
    
    def test_login_failure_invalid_username(self, client):
        """Test failed login with invalid username"""
        response = client.post('/login', data={
            'username': 'invaliduser',
            'password': 'anypassword'
        }, follow_redirects=True)
        assert response.status_code == 200
    
    def test_logout(self, authenticated_client):
        """Test logout functionality"""
        response = authenticated_client.get('/logout', follow_redirects=True)
        assert response.status_code == 200
        # Should redirect to login page
        assert b'Login' in response.data or b'Sign In' in response.data


class TestProtectedRoutes:
    """Tests for protected routes requiring authentication"""
    
    def test_index_requires_auth(self, client):
        """Test that index page requires authentication"""
        response = client.get('/')
        # Should redirect to login
        assert response.status_code == 302
    
    def test_index_accessible_when_authenticated(self, authenticated_client):
        """Test that index page is accessible when authenticated"""
        response = authenticated_client.get('/')
        assert response.status_code == 200
    
    def test_launcher_requires_auth(self, client):
        """Test that launcher page requires authentication"""
        response = client.get('/launcher.html')
        # Should redirect to login
        assert response.status_code == 302
    
    def test_launcher_accessible_when_authenticated(self, authenticated_client):
        """Test that launcher page is accessible when authenticated"""
        response = authenticated_client.get('/launcher.html')
        assert response.status_code == 200
    
    def test_static_file_requires_auth(self, client):
        """Test that static files require authentication"""
        response = client.get('/common.css')
        # Should redirect to login
        assert response.status_code == 302
    
    def test_static_file_accessible_when_authenticated(self, authenticated_client):
        """Test that static files are accessible when authenticated"""
        response = authenticated_client.get('/common.css')
        assert response.status_code == 200


class TestSessionManagement:
    """Tests for session management"""
    
    def test_session_created_on_login(self, client):
        """Test that session is created on successful login"""
        response = client.post('/login', data={
            'username': 'admin',
            'password': 'marquee123'
        })
        # Check that session cookie is set
        assert 'session' in response.headers.get('Set-Cookie', '').lower() or \
               'set-cookie' in [h.lower() for h in response.headers]
    
    def test_session_cleared_on_logout(self, authenticated_client):
        """Test that session is cleared on logout - user should be redirected to login"""
        # First verify we're logged in
        response = authenticated_client.get('/')
        assert response.status_code == 200
        
        # Now logout
        logout_response = authenticated_client.get('/logout', follow_redirects=True)
        assert logout_response.status_code == 200
        
        # After logout, trying to access protected route should redirect to login
        # (This is the important test - session is effectively cleared)
        protected_response = authenticated_client.get('/')
        assert protected_response.status_code == 302


class TestWebAuthnOTP:
    """Tests for WebAuthn OTP verification and enforcement"""

    def test_verify_otp_success(self, client):
        """Test successful OTP verification"""
        response = client.post('/api/webauthn/verify-otp', json={
            'username': 'testuser',
            'otp': 'changeme'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
        assert 'OTP verified successfully' in data['message']

    def test_verify_otp_failure(self, client):
        """Test failed OTP verification"""
        response = client.post('/api/webauthn/verify-otp', json={
            'username': 'testuser',
            'otp': 'wrongotp'
        })
        assert response.status_code == 401
        data = response.get_json()
        assert 'Invalid OTP' in data['error']

    def test_verify_otp_missing_fields(self, client):
        """Test OTP verification with missing fields"""
        # Missing username
        response = client.post('/api/webauthn/verify-otp', json={
            'otp': 'changeme'
        })
        assert response.status_code == 400

        # Missing OTP
        response = client.post('/api/webauthn/verify-otp', json={
            'username': 'testuser'
        })
        assert response.status_code == 400

    def test_webauthn_register_without_otp(self, client):
        """Test that WebAuthn registration fails without OTP verification"""
        response = client.post('/api/webauthn/register', json={
            'username': 'testuser',
            'attestationResponse': {}
        })
        assert response.status_code == 403
        data = response.get_json()
        assert 'OTP verification required' in data['error']

    def test_webauthn_register_with_wrong_user_otp(self, client):
        """Test that WebAuthn registration fails with OTP verified for different user"""
        # Verify OTP for user1
        client.post('/api/webauthn/verify-otp', json={
            'username': 'user1',
            'otp': 'changeme'
        })

        # Try to register for user2
        response = client.post('/api/webauthn/register', json={
            'username': 'user2',
            'attestationResponse': {}
        })
        assert response.status_code == 403
        data = response.get_json()
        assert 'OTP verification required' in data['error']


class TestRoutes:
    """Tests for route handling"""

    def test_mqtt_handler_accessible_when_authenticated(self, authenticated_client):
        """Test that mqttHandler.mjs is accessible when authenticated"""
        response = authenticated_client.get('/mqttHandler.mjs')
        assert response.status_code == 200

    def test_login_html_accessible_without_auth(self, client):
        """Test that login.html is accessible without authentication"""
        response = client.get('/login.html')
        assert response.status_code == 200


class TestRateLimiting:
    """Tests for rate limiting functionality"""

    def test_verify_otp_rate_limit(self, client_with_rate_limiting):
        """Test that /api/webauthn/verify-otp is rate limited to 1 per minute"""
        # First request should succeed
        response1 = client_with_rate_limiting.post('/api/webauthn/verify-otp', json={
            'username': 'testuser',
            'otp': 'changeme'
        })
        assert response1.status_code == 200

        # Second request within the same minute should be rate limited
        response2 = client_with_rate_limiting.post('/api/webauthn/verify-otp', json={
            'username': 'testuser',
            'otp': 'changeme'
        })
        assert response2.status_code == 429

    def test_has_credentials_rate_limit(self, client_with_rate_limiting):
        """Test that /api/webauthn/has-credentials is rate limited to 2 per minute"""
        # First two requests should succeed
        response1 = client_with_rate_limiting.get('/api/webauthn/has-credentials?username=testuser')
        assert response1.status_code == 200

        response2 = client_with_rate_limiting.get('/api/webauthn/has-credentials?username=testuser')
        assert response2.status_code == 200

        # Third request should be rate limited
        response3 = client_with_rate_limiting.get('/api/webauthn/has-credentials?username=testuser')
        assert response3.status_code == 429


class TestWebSocketHandlers:
    """Tests for WebSocket MQTT proxy handlers"""
    
    @patch.object(mqtt_proxy, 'publish')
    def test_mqtt_publish_handler(self, mock_publish):
        """Test WebSocket mqtt_publish handler"""
        mock_publish.return_value = (True, None)
        
        # Create a test client for SocketIO
        test_client = socketio.test_client(app)
        
        # Emit mqtt_publish event
        test_client.emit('mqtt_publish', {
            'topic': 'test/topic',
            'payload': 'test message'
        })
        
        # Verify publish was called
        mock_publish.assert_called_once_with('test/topic', 'test message')
        
        # Check for success response
        received = test_client.get_received()
        assert len(received) > 0
        assert any(msg['name'] == 'mqtt_publish_success' for msg in received)
        
        test_client.disconnect()
    
    @patch.object(mqtt_proxy, 'publish')
    def test_mqtt_publish_handler_failure(self, mock_publish):
        """Test WebSocket mqtt_publish handler with failure"""
        mock_publish.return_value = (False, 'Connection error')
        
        test_client = socketio.test_client(app)
        
        # Emit mqtt_publish event
        test_client.emit('mqtt_publish', {
            'topic': 'test/topic',
            'payload': 'test message'
        })
        
        # Check for error response
        received = test_client.get_received()
        assert len(received) > 0
        error_msgs = [msg for msg in received if msg['name'] == 'mqtt_error']
        assert len(error_msgs) > 0
        assert error_msgs[0]['args'][0]['error'] == 'Connection error'
        
        test_client.disconnect()
    
    def test_mqtt_publish_handler_missing_topic(self):
        """Test WebSocket mqtt_publish handler with missing topic"""
        test_client = socketio.test_client(app)
        
        # Emit mqtt_publish event without topic
        test_client.emit('mqtt_publish', {
            'payload': 'test message'
        })
        
        # Check for error response
        received = test_client.get_received()
        assert len(received) > 0
        error_msgs = [msg for msg in received if msg['name'] == 'mqtt_error']
        assert len(error_msgs) > 0
        assert 'Topic is required' in error_msgs[0]['args'][0]['error']
        
        test_client.disconnect()
    
    @patch.object(mqtt_proxy, 'subscribe')
    def test_mqtt_subscribe_handler(self, mock_subscribe):
        """Test WebSocket mqtt_subscribe handler"""
        mock_subscribe.return_value = (True, None)
        
        test_client = socketio.test_client(app)
        
        # Emit mqtt_subscribe event
        test_client.emit('mqtt_subscribe', {
            'topic': 'test/topic/#'
        })
        
        # Verify subscribe was called
        mock_subscribe.assert_called_once_with('test/topic/#')
        
        # Check for success response
        received = test_client.get_received()
        assert len(received) > 0
        assert any(msg['name'] == 'mqtt_subscribe_success' for msg in received)
        
        test_client.disconnect()
    
    @patch.object(mqtt_proxy, 'subscribe')
    def test_mqtt_subscribe_handler_failure(self, mock_subscribe):
        """Test WebSocket mqtt_subscribe handler with failure"""
        mock_subscribe.return_value = (False, 'Subscription error')
        
        test_client = socketio.test_client(app)
        
        # Emit mqtt_subscribe event
        test_client.emit('mqtt_subscribe', {
            'topic': 'test/topic/#'
        })
        
        # Check for error response
        received = test_client.get_received()
        assert len(received) > 0
        error_msgs = [msg for msg in received if msg['name'] == 'mqtt_error']
        assert len(error_msgs) > 0
        assert error_msgs[0]['args'][0]['error'] == 'Subscription error'
        
        test_client.disconnect()
    
    def test_mqtt_subscribe_handler_missing_topic(self):
        """Test WebSocket mqtt_subscribe handler with missing topic"""
        test_client = socketio.test_client(app)
        
        # Emit mqtt_subscribe event without topic
        test_client.emit('mqtt_subscribe', {})
        
        # Check for error response
        received = test_client.get_received()
        assert len(received) > 0
        error_msgs = [msg for msg in received if msg['name'] == 'mqtt_error']
        assert len(error_msgs) > 0
        assert 'Topic is required' in error_msgs[0]['args'][0]['error']
        
        test_client.disconnect()
    
    def test_websocket_connect_disconnect(self):
        """Test WebSocket connection and disconnection"""
        test_client = socketio.test_client(app)
        
        # Verify connection
        assert test_client.is_connected()
        
        # Disconnect
        test_client.disconnect()
        
        # Verify disconnection
        assert not test_client.is_connected()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
