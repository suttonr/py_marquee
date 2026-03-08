"""
Tests for the Flask web server authentication
"""
import pytest
import sys
import os

# Add the web directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'web'))

from server import app


@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    app.config['TESTING'] = True
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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
