"""
Example usage of the heartbeat module.

This demonstrates how to integrate the heartbeat module with a component
that manages its own MQTT client connection.
"""

from paho.mqtt import client as mqtt_client
import secrets
import time

from mqtt_heartbeat import Heartbeat

def main():
    """Example: Using heartbeat with a custom MQTT client setup."""
    
    # Setup your own MQTT client (as the caller)
    mqtt_client_instance = mqtt_client.Client(
        client_id="launcher-example",
        clean_session=True
    )
    mqtt_client_instance.username_pw_set(
        secrets.MQTT_USERNAME,
        secrets.MQTT_PASSWORD
    )
    
    # Connect to the broker
    mqtt_client_instance.connect(
        secrets.MQTT_BROKER,
        secrets.MQTT_PORT,
        keepalive=60
    )
    mqtt_client_instance.loop_start()
    
    try:
        # Create heartbeat instance, passing in our MQTT client
        heartbeat = Heartbeat(
            mqtt_client=mqtt_client_instance,
            topic="health/launcher/ping",
            message="launcher alive"  # Optional custom message
        )
        
        # Start sending heartbeats every 60 seconds (default)
        heartbeat.start()
        
        # Or use the convenience function:
        # heartbeat = start_heartbeat(mqtt_client_instance, interval_seconds=30)
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        # Stop the heartbeat when done
        heartbeat.stop()
        mqtt_client_instance.loop_stop()
        mqtt_client_instance.disconnect()


if __name__ == "__main__":
    main()
