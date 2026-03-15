"""
Tests for the MQTT WebSocket Proxy
"""
import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch, call
import paho.mqtt.client as mqtt

# Add the web/src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'web', 'src'))

from mqtt_proxy import MQTTProxy


@pytest.fixture
def mock_mqtt_client():
    """Create a mock MQTT client"""
    with patch('mqtt_proxy.mqtt.Client') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.is_connected.return_value = True
        yield mock_client


@pytest.fixture
def mqtt_proxy():
    """Create an MQTTProxy instance for testing"""
    with patch('mqtt_proxy.mqtt.Client'):
        proxy = MQTTProxy(
            broker='test.broker.com',
            port=1883,
            username='test_user',
            password='test_pass',
            keepalive=60
        )
        yield proxy


@pytest.fixture
def mock_socketio():
    """Create a mock SocketIO instance"""
    mock_sio = MagicMock()
    return mock_sio


class TestMQTTProxyInit:
    """Tests for MQTTProxy initialization"""
    
    def test_init_with_credentials(self):
        """Test initialization with username and password"""
        with patch('mqtt_proxy.mqtt.Client'):
            proxy = MQTTProxy(
                broker='test.broker.com',
                port=1883,
                username='testuser',
                password='testpass',
                keepalive=60
            )
            assert proxy.broker == 'test.broker.com'
            assert proxy.port == 1883
            assert proxy.username == 'testuser'
            assert proxy.password == 'testpass'
            assert proxy.keepalive == 60
            assert proxy.client is None
            assert proxy.socketio is None
    
    def test_init_without_credentials(self):
        """Test initialization without username and password"""
        with patch('mqtt_proxy.mqtt.Client'):
            proxy = MQTTProxy(
                broker='test.broker.com',
                port=1883
            )
            assert proxy.broker == 'test.broker.com'
            assert proxy.port == 1883
            assert proxy.username is None
            assert proxy.password is None


class TestMQTTProxyConnection:
    """Tests for MQTT connection management"""
    
    def test_connect_success(self, mqtt_proxy, mock_mqtt_client):
        """Test successful MQTT connection"""
        mqtt_proxy.connect()
        
        # Verify client was created
        assert mqtt_proxy.client is not None
        
        # Verify callbacks were set
        assert mqtt_proxy.client.on_connect is not None
        assert mqtt_proxy.client.on_message is not None
        assert mqtt_proxy.client.on_disconnect is not None
        
        # Verify connect and loop_start were called
        mqtt_proxy.client.connect.assert_called_once_with('test.broker.com', 1883, 60)
        mqtt_proxy.client.loop_start.assert_called_once()
    
    def test_connect_with_credentials(self, mock_mqtt_client):
        """Test connection with username and password"""
        with patch('mqtt_proxy.mqtt.Client') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            proxy = MQTTProxy(
                broker='test.broker.com',
                port=1883,
                username='testuser',
                password='testpass'
            )
            proxy.connect()
            
            # Verify username_pw_set was called
            mock_client.username_pw_set.assert_called_once_with('testuser', 'testpass')
    
    def test_connect_exception_handling(self, mqtt_proxy, mock_mqtt_client):
        """Test connection exception handling"""
        mock_mqtt_client.connect.side_effect = Exception("Connection failed")
        
        # Should not raise exception
        mqtt_proxy.connect()
        
        # Client should still be set
        assert mqtt_proxy.client is not None
    
    def test_disconnect(self, mqtt_proxy, mock_mqtt_client):
        """Test MQTT disconnection"""
        mqtt_proxy.client = mock_mqtt_client
        mqtt_proxy.disconnect()
        
        # Verify disconnect methods were called
        mock_mqtt_client.loop_stop.assert_called_once()
        mock_mqtt_client.disconnect.assert_called_once()
        
        # Client should be set to None
        assert mqtt_proxy.client is None
    
    def test_disconnect_without_client(self, mqtt_proxy):
        """Test disconnect when client is None"""
        mqtt_proxy.client = None
        # Should not raise exception
        mqtt_proxy.disconnect()
        assert mqtt_proxy.client is None


class TestMQTTProxyCallbacks:
    """Tests for MQTT callback handlers"""
    
    def test_on_connect_success(self, mqtt_proxy, mock_mqtt_client):
        """Test on_connect callback with successful connection"""
        mqtt_proxy.client = mock_mqtt_client
        
        # Simulate successful connection (rc=0)
        mqtt_proxy.on_connect(mock_mqtt_client, None, None, 0)
        
        # Verify subscriptions were made
        assert mock_mqtt_client.subscribe.call_count == 2
        mock_mqtt_client.subscribe.assert_any_call("marquee/#")
        mock_mqtt_client.subscribe.assert_any_call("esp32/test/#")
    
    def test_on_connect_failure(self, mqtt_proxy, mock_mqtt_client):
        """Test on_connect callback with failed connection"""
        mqtt_proxy.client = mock_mqtt_client
        
        # Simulate failed connection (rc != 0)
        mqtt_proxy.on_connect(mock_mqtt_client, None, None, 5)
        
        # Verify no subscriptions were made
        mock_mqtt_client.subscribe.assert_not_called()
    
    def test_on_message_pixels(self, mqtt_proxy, mock_socketio):
        """Test on_message callback for pixel data"""
        mqtt_proxy.set_socketio(mock_socketio)
        
        # Create a mock message
        mock_msg = MagicMock()
        mock_msg.topic = "marquee/pixels"
        mock_msg.payload = b'{"000000": [255, 0, 0]}'
        
        mqtt_proxy.on_message(None, None, mock_msg)
        
        # Verify socketio emit was called
        mock_socketio.emit.assert_called_once()
        call_args = mock_socketio.emit.call_args
        assert call_args[0][0] == 'mqtt_message'
        assert call_args[0][1]['topic'] == 'marquee/pixels'
        assert call_args[0][1]['payload'] == '{"000000": [255, 0, 0]}'
    
    def test_on_message_text(self, mqtt_proxy, mock_socketio):
        """Test on_message callback for text data"""
        mqtt_proxy.set_socketio(mock_socketio)
        
        # Create a mock message
        mock_msg = MagicMock()
        mock_msg.topic = "esp32/test/text"
        mock_msg.payload = b'Hello World'
        
        mqtt_proxy.on_message(None, None, mock_msg)
        
        # Verify socketio emit was called with decoded text
        mock_socketio.emit.assert_called_once()
        call_args = mock_socketio.emit.call_args
        assert call_args[0][1]['payload'] == 'Hello World'
    
    def test_on_message_binary(self, mqtt_proxy, mock_socketio):
        """Test on_message callback for binary data"""
        mqtt_proxy.set_socketio(mock_socketio)
        
        # Create a mock message with binary data
        mock_msg = MagicMock()
        mock_msg.topic = "esp32/test/binary"
        mock_msg.payload = b'\xff\xfe\xfd'
        
        mqtt_proxy.on_message(None, None, mock_msg)
        
        # Verify socketio emit was called with hex representation
        mock_socketio.emit.assert_called_once()
        call_args = mock_socketio.emit.call_args
        assert call_args[0][1]['payload'] == 'fffefd'
    
    def test_on_message_without_socketio(self, mqtt_proxy):
        """Test on_message callback when socketio is not set"""
        mqtt_proxy.socketio = None
        
        # Create a mock message
        mock_msg = MagicMock()
        mock_msg.topic = "test/topic"
        mock_msg.payload = b'test'
        
        # Should not raise exception
        mqtt_proxy.on_message(None, None, mock_msg)
    
    def test_on_disconnect_unexpected(self, mqtt_proxy):
        """Test on_disconnect callback with unexpected disconnect"""
        # rc != 0 indicates unexpected disconnect
        mqtt_proxy.on_disconnect(None, None, 5)
        # Should not raise exception
    
    def test_on_disconnect_expected(self, mqtt_proxy):
        """Test on_disconnect callback with expected disconnect"""
        # rc == 0 indicates expected disconnect
        mqtt_proxy.on_disconnect(None, None, 0)
        # Should not raise exception


class TestMQTTProxyPublish:
    """Tests for MQTT publish functionality"""
    
    def test_publish_string(self, mqtt_proxy, mock_mqtt_client):
        """Test publishing a string message"""
        mqtt_proxy.client = mock_mqtt_client
        mock_result = MagicMock()
        mock_result.rc = mqtt.MQTT_ERR_SUCCESS
        mock_mqtt_client.publish.return_value = mock_result
        
        success, error = mqtt_proxy.publish('test/topic', 'Hello')
        
        assert success is True
        assert error is None
        mock_mqtt_client.publish.assert_called_once_with('test/topic', b'Hello')
    
    def test_publish_bytes(self, mqtt_proxy, mock_mqtt_client):
        """Test publishing a bytes message"""
        mqtt_proxy.client = mock_mqtt_client
        mock_result = MagicMock()
        mock_result.rc = mqtt.MQTT_ERR_SUCCESS
        mock_mqtt_client.publish.return_value = mock_result
        
        success, error = mqtt_proxy.publish('test/topic', b'Hello')
        
        assert success is True
        assert error is None
        mock_mqtt_client.publish.assert_called_once_with('test/topic', b'Hello')
    
    def test_publish_list(self, mqtt_proxy, mock_mqtt_client):
        """Test publishing a list of bytes"""
        mqtt_proxy.client = mock_mqtt_client
        mock_result = MagicMock()
        mock_result.rc = mqtt.MQTT_ERR_SUCCESS
        mock_mqtt_client.publish.return_value = mock_result
        
        success, error = mqtt_proxy.publish('test/topic', [72, 101, 108, 108, 111])
        
        assert success is True
        assert error is None
        # Verify it was converted to bytes
        call_args = mock_mqtt_client.publish.call_args
        assert isinstance(call_args[0][1], bytes)
    
    def test_publish_failure(self, mqtt_proxy, mock_mqtt_client):
        """Test publish failure"""
        mqtt_proxy.client = mock_mqtt_client
        mock_result = MagicMock()
        mock_result.rc = mqtt.MQTT_ERR_NO_CONN
        mock_mqtt_client.publish.return_value = mock_result
        
        success, error = mqtt_proxy.publish('test/topic', 'Hello')
        
        assert success is False
        assert 'Publish failed' in error
    
    def test_publish_not_connected(self, mqtt_proxy, mock_mqtt_client):
        """Test publish when not connected"""
        mqtt_proxy.client = mock_mqtt_client
        mock_mqtt_client.is_connected.return_value = False
        
        success, error = mqtt_proxy.publish('test/topic', 'Hello')
        
        assert success is False
        assert error == 'MQTT client not connected'
    
    def test_publish_no_client(self, mqtt_proxy):
        """Test publish when client is None"""
        mqtt_proxy.client = None
        
        success, error = mqtt_proxy.publish('test/topic', 'Hello')
        
        assert success is False
        assert error == 'MQTT client not connected'
    
    def test_publish_exception(self, mqtt_proxy, mock_mqtt_client):
        """Test publish with exception"""
        mqtt_proxy.client = mock_mqtt_client
        mock_mqtt_client.publish.side_effect = Exception("Publish error")
        
        success, error = mqtt_proxy.publish('test/topic', 'Hello')
        
        assert success is False
        assert error == 'Publish error'


class TestMQTTProxySubscribe:
    """Tests for MQTT subscribe functionality"""
    
    def test_subscribe_success(self, mqtt_proxy, mock_mqtt_client):
        """Test successful subscription"""
        mqtt_proxy.client = mock_mqtt_client
        mock_mqtt_client.subscribe.return_value = (mqtt.MQTT_ERR_SUCCESS, 1)
        
        success, error = mqtt_proxy.subscribe('test/topic/#')
        
        assert success is True
        assert error is None
        mock_mqtt_client.subscribe.assert_called_once_with('test/topic/#')
    
    def test_subscribe_failure(self, mqtt_proxy, mock_mqtt_client):
        """Test subscription failure"""
        mqtt_proxy.client = mock_mqtt_client
        mock_mqtt_client.subscribe.return_value = (mqtt.MQTT_ERR_NO_CONN, None)
        
        success, error = mqtt_proxy.subscribe('test/topic/#')
        
        assert success is False
        assert 'Subscribe failed' in error
    
    def test_subscribe_not_connected(self, mqtt_proxy, mock_mqtt_client):
        """Test subscribe when not connected"""
        mqtt_proxy.client = mock_mqtt_client
        mock_mqtt_client.is_connected.return_value = False
        
        success, error = mqtt_proxy.subscribe('test/topic/#')
        
        assert success is False
        assert error == 'MQTT client not connected'
    
    def test_subscribe_no_client(self, mqtt_proxy):
        """Test subscribe when client is None"""
        mqtt_proxy.client = None
        
        success, error = mqtt_proxy.subscribe('test/topic/#')
        
        assert success is False
        assert error == 'MQTT client not connected'
    
    def test_subscribe_exception(self, mqtt_proxy, mock_mqtt_client):
        """Test subscribe with exception"""
        mqtt_proxy.client = mock_mqtt_client
        mock_mqtt_client.subscribe.side_effect = Exception("Subscribe error")
        
        success, error = mqtt_proxy.subscribe('test/topic/#')
        
        assert success is False
        assert error == 'Subscribe error'


class TestMQTTProxyUtility:
    """Tests for utility methods"""
    
    def test_set_socketio(self, mqtt_proxy, mock_socketio):
        """Test setting the SocketIO instance"""
        mqtt_proxy.set_socketio(mock_socketio)
        assert mqtt_proxy.socketio == mock_socketio
    
    def test_is_connected_true(self, mqtt_proxy, mock_mqtt_client):
        """Test is_connected when connected"""
        mqtt_proxy.client = mock_mqtt_client
        mock_mqtt_client.is_connected.return_value = True
        
        assert mqtt_proxy.is_connected() is True
    
    def test_is_connected_false(self, mqtt_proxy, mock_mqtt_client):
        """Test is_connected when not connected"""
        mqtt_proxy.client = mock_mqtt_client
        mock_mqtt_client.is_connected.return_value = False
        
        assert mqtt_proxy.is_connected() is False
    
    def test_is_connected_no_client(self, mqtt_proxy):
        """Test is_connected when client is None"""
        mqtt_proxy.client = None
        
        assert mqtt_proxy.is_connected() is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
