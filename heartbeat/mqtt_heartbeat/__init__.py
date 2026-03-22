"""
Heartbeat module for sending periodic health pings to MQTT.

Usage:
    from mqtt_heartbeat import Heartbeat, start_heartbeat

    # Assuming mqtt_client is your paho.mqtt client instance
    heartbeat = Heartbeat(mqtt_client, topic="health/launcher/ping")
    heartbeat.start(interval_seconds=60)

    # Or use the convenience function:
    heartbeat = start_heartbeat(mqtt_client, topic="health/launcher/ping")

    # When shutting down:
    heartbeat.stop()
"""

from mqtt_heartbeat.heartbeat import Heartbeat, start_heartbeat

__all__ = ['Heartbeat', 'start_heartbeat']
