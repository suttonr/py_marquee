"""
Heartbeat class for sending periodic health pings to MQTT.

This module provides a simple interface for components to send heartbeat
messages to an MQTT broker. The MQTT client is assumed to be set up
by the caller and passed to this module.
"""

import threading
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class Heartbeat:
    """
    Sends periodic heartbeat messages to an MQTT topic.
    
    Args:
        mqtt_client: A paho.mqtt client instance (already connected)
        topic: The MQTT topic to publish heartbeats to (default: "health/launcher/ping")
        message: Optional custom message content (default: includes timestamp)
    """
    
    def __init__(self, mqtt_client, topic="health/health/ping", message=None):
        self.mqtt_client = mqtt_client
        self.topic = topic
        self.custom_message = message
        self.interval_seconds = 60
        self._thread = None
        self._stop_event = threading.Event()
        self._running = False
    
    def set_interval(self, seconds):
        """Set the heartbeat interval in seconds."""
        self.interval_seconds = seconds
    
    def set_topic(self, topic):
        """Set the MQTT topic for heartbeats."""
        self.topic = topic
    
    def _get_message(self):
        """Generate the heartbeat message."""
        if self.custom_message:
            return self.custom_message
        return datetime.now(timezone.utc).isoformat()
    
    def _heartbeat_loop(self):
        """Internal loop for sending heartbeats."""
        while not self._stop_event.is_set():
            try:
                msg = self._get_message()
                self.mqtt_client.publish(self.topic, msg)
                logger.debug(f"Heartbeat sent to {self.topic}: {msg}")
            except Exception as e:
                logger.error(f"Failed to send heartbeat: {e}")
            
            # Wait for interval or stop signal
            self._stop_event.wait(self.interval_seconds)
    
    def start(self, interval_seconds=None):
        """
        Start sending heartbeats.
        
        Args:
            interval_seconds: Heartbeat interval in seconds (default: 60)
        """
        if interval_seconds is not None:
            self.interval_seconds = interval_seconds
        
        if self._running:
            logger.warning("Heartbeat already running")
            return
        
        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._thread.start()
        logger.info(f"Heartbeat started: topic={self.topic}, interval={self.interval_seconds}s")
    
    def stop(self):
        """Stop sending heartbeats."""
        if not self._running:
            return
        
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._running = False
        logger.info("Heartbeat stopped")
    
    def send_once(self):
        """Send a single heartbeat immediately."""
        try:
            msg = self._get_message()
            self.mqtt_client.publish(self.topic, msg)
            logger.debug(f"Single heartbeat sent to {self.topic}: {msg}")
            return True
        except Exception as e:
            logger.error(f"Failed to send single heartbeat: {e}")
            return False


def start_heartbeat(mqtt_client, topic="health/launcher/ping", interval_seconds=60):
    """
    Convenience function to start a heartbeat in a single call.
    
    Args:
        mqtt_client: A paho.mqtt client instance (already connected)
        topic: The MQTT topic to publish heartbeats to
        interval_seconds: Heartbeat interval in seconds
    
    Returns:
        Heartbeat instance (call .stop() to shut down)
    """
    heartbeat = Heartbeat(mqtt_client, topic, interval_seconds)
    heartbeat.start()
    return heartbeat
