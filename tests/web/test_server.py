"""
Tests for the Flask web server authentication
"""
import pytest
import sys
import os

# Add the web directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'web'))

from server import app, limiter


@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    app.config['TESTING'] = True
    limiter.enabled = False  # Disable rate limiting in tests
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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
