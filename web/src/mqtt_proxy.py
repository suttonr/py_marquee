"""
MQTT WebSocket Proxy
Provides a WebSocket bridge to MQTT broker for web clients
"""
import threading
import paho.mqtt.client as mqtt
from flask_socketio import emit


class MQTTProxy:
    """Manages MQTT connection and WebSocket bridge"""
    
    def __init__(self, broker, port, username=None, password=None, keepalive=60):
        """
        Initialize MQTT proxy
        
        Args:
            broker: MQTT broker hostname
            port: MQTT broker port
            username: MQTT username (optional)
            password: MQTT password (optional)
            keepalive: Connection keepalive interval in seconds
        """
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        self.keepalive = keepalive
        self.client = None
        self.lock = threading.Lock()
        self.socketio = None
        
    def set_socketio(self, socketio):
        """Set the SocketIO instance for broadcasting messages"""
        self.socketio = socketio
        
    def on_connect(self, client, userdata, flags, rc):
        """Callback for when the MQTT client connects to the broker"""
        if rc == 0:
            print(f"MQTT Proxy: Connected to broker at {self.broker}:{self.port}")
            # Subscribe to all marquee topics
            client.subscribe("marquee/#")
            client.subscribe("esp32/test/#")
        else:
            print(f"MQTT Proxy: Failed to connect to broker, return code {rc}")
    
    def on_message(self, client, userdata, msg):
        """Callback for when an MQTT message is received"""
        try:
            # Decode payload based on topic
            if msg.topic == "marquee/pixels":
                # Pixel data is JSON
                payload = msg.payload.decode('utf-8')
            else:
                # Try to decode as string, fall back to hex for binary
                try:
                    payload = msg.payload.decode('utf-8')
                except:
                    payload = msg.payload.hex()
            
            # Broadcast to all connected WebSocket clients
            if self.socketio:
                self.socketio.emit('mqtt_message', {
                    'topic': msg.topic,
                    'payload': payload
                }, namespace='/')
        except Exception as e:
            print(f"MQTT Proxy: Error processing message: {e}")
    
    def on_disconnect(self, client, userdata, rc):
        """Callback for when the MQTT client disconnects"""
        if rc != 0:
            print(f"MQTT Proxy: Unexpected disconnection, code {rc}")
    
    def connect(self):
        """Initialize and connect the MQTT client"""
        with self.lock:
            if self.client is None:
                self.client = mqtt.Client()
                self.client.on_connect = self.on_connect
                self.client.on_message = self.on_message
                self.client.on_disconnect = self.on_disconnect
                
                if self.username:
                    self.client.username_pw_set(self.username, self.password)
                
                try:
                    self.client.connect(self.broker, self.port, self.keepalive)
                    self.client.loop_start()
                    print("MQTT Proxy: Client loop started")
                except Exception as e:
                    print(f"MQTT Proxy: Failed to connect: {e}")
    
    def disconnect(self):
        """Disconnect the MQTT client"""
        with self.lock:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
                self.client = None
                print("MQTT Proxy: Disconnected")
    
    def publish(self, topic, payload):
        """
        Publish a message to the MQTT broker
        
        Args:
            topic: MQTT topic
            payload: Message payload (bytes, str, or list of bytes)
            
        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        try:
            # Handle binary payload (array of bytes)
            if isinstance(payload, list):
                payload = bytes(payload)
            elif isinstance(payload, str):
                payload = payload.encode('utf-8')
            
            # Publish to MQTT broker
            if self.client and self.client.is_connected():
                result = self.client.publish(topic, payload)
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    return True, None
                else:
                    return False, f'Publish failed with code {result.rc}'
            else:
                return False, 'MQTT client not connected'
        except Exception as e:
            return False, str(e)
    
    def subscribe(self, topic):
        """
        Subscribe to an MQTT topic
        
        Args:
            topic: MQTT topic pattern
            
        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        try:
            if self.client and self.client.is_connected():
                result = self.client.subscribe(topic)
                if result[0] == mqtt.MQTT_ERR_SUCCESS:
                    return True, None
                else:
                    return False, f'Subscribe failed with code {result[0]}'
            else:
                return False, 'MQTT client not connected'
        except Exception as e:
            return False, str(e)
    
    def is_connected(self):
        """Check if MQTT client is connected"""
        return self.client is not None and self.client.is_connected()
