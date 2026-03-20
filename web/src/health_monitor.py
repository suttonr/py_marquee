"""
Health Monitor - Subscribes to MQTT health topics and provides a REST API endpoint.

This module monitors health pings from various system components that publish
to 'health/[component]/ping' MQTT topics.
"""
import threading
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Health data storage
health_data = {}
health_data_lock = threading.Lock()


def handle_health_message(client, userdata, msg):
    """Handle incoming health messages from MQTT.
    
    Args:
        client: The MQTT client
        userdata: User data (unused)
        msg: The MQTT message
    """
    try:
        topic = msg.topic
        payload = msg.payload.decode('utf-8') if msg.payload else ''
        
        # Parse topic: health/[component]/ping
        parts = topic.split('/')
        if len(parts) >= 3 and parts[0] == 'health' and parts[2] == 'ping':
            component = parts[1]
            timestamp = datetime.now(timezone.utc).isoformat()
            
            with health_data_lock:
                health_data[component] = {
                    'status': 'healthy',
                    'last_ping': timestamp,
                    'topic': topic,
                    'payload': payload
                }
            logger.info(f"Health update received from {component}")
    except Exception as e:
        logger.error(f"Error handling health message: {e}")


def get_health_data():
    """Get current health data for all components.
    
    Returns:
        dict: Health data for all components with their last ping time
    """
    with health_data_lock:
        return dict(health_data)


def get_component_health(component):
    """Get health data for a specific component.
    
    Args:
        component: The component name
        
    Returns:
        dict or None: Health data for the component, or None if not found
    """
    with health_data_lock:
        return health_data.get(component)


def subscribe_to_health_topics(mqtt_client):
    """Subscribe to all health ping topics.
    
    Args:
        mqtt_client: The MQTT client to subscribe with
    """
    try:
        # Add message callback for health topics
        mqtt_client.message_callback_add('health/+/ping', handle_health_message)
        mqtt_client.subscribe('health/+/ping')
        logger.info("Subscribed to health/+/ping topics")
    except Exception as e:
        logger.error(f"Error subscribing to health topics: {e}")


def check_component_status(component, max_age_seconds=120):
    """Check if a component is healthy based on last ping time.
    
    Args:
        component: The component name
        max_age_seconds: Maximum age in seconds before considering component unhealthy
        
    Returns:
        str: 'healthy', 'warning', 'error', or 'unknown'
    """
    with health_data_lock:
        component_data = health_data.get(component)
    
    if not component_data:
        return 'unknown'
    
    try:
        last_ping = datetime.fromisoformat(component_data['last_ping'])
        now = datetime.now(timezone.utc)
        age_seconds = (now - last_ping).total_seconds()
        
        if age_seconds < max_age_seconds:
            return 'healthy'
        elif age_seconds < max_age_seconds * 2:
            return 'warning'
        else:
            return 'error'
    except Exception:
        return 'unknown'


def get_all_component_statuses(max_age_seconds=120):
    """Get health status for all components.
    
    Args:
        max_age_seconds: Maximum age in seconds before considering component unhealthy
        
    Returns:
        dict: Component names mapped to their health status
    """
    with health_data_lock:
        components = list(health_data.keys())
    
    statuses = {}
    for component in components:
        statuses[component] = check_component_status(component, max_age_seconds)
    
    return statuses
