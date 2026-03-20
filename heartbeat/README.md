# Heartbeat Module

Sends periodic health pings to an MQTT topic. Designed to be reusable across multiple components of the marquee system.

## Overview

The heartbeat module provides a simple interface for components to send heartbeat messages to an MQTT broker. The MQTT client is assumed to be set up by the caller and passed to the module.

## Installation

Requires `paho-mqtt`:
```bash
pip install paho-mqtt
```

## Usage

```python
from paho.mqtt import client as mqtt_client
from heartbeat import Heartbeat

# Setup your MQTT client (as the caller)
mqtt_client_instance = mqtt_client.Client(client_id="my-service")
mqtt_client_instance.username_pw_set("username", "password")
mqtt_client_instance.connect("broker.example.com", 1883)
mqtt_client_instance.loop_start()

# Create heartbeat instance
heartbeat = Heartbeat(
    mqtt_client=mqtt_client_instance,
    topic="health/my-service/ping"
)
heartbeat.start(interval_seconds=60)

# ... your application code ...

# When shutting down:
heartbeat.stop()
mqtt_client_instance.loop_stop()
mqtt_client_instance.disconnect()
```

## Quick Start

Use the convenience function for one-liner setup:

```python
from heartbeat import start_heartbeat

heartbeat = start_heartbeat(mqtt_client, interval_seconds=30)
```

## API

### Heartbeat Class

```python
Heartbeat(mqtt_client, topic="health/launcher/ping", message=None)
```

**Parameters:**
- `mqtt_client`: A paho.mqtt client instance (must be already connected)
- `topic`: MQTT topic to publish heartbeats to (default: "health/launcher/ping")
- `message`: Optional custom message content (default: includes UTC timestamp)

**Methods:**
- `start(interval_seconds=60)` - Start sending periodic heartbeats
- `stop()` - Stop sending heartbeats
- `send_once()` - Send a single heartbeat immediately
- `set_interval(seconds)` - Change the heartbeat interval
- `set_topic(topic)` - Change the MQTT topic

### Convenience Function

```python
start_heartbeat(mqtt_client, topic="health/launcher/ping", interval_seconds=60)
```

Returns a Heartbeat instance that has been started. Call `.stop()` on the returned instance to shut down.

## Message Format

By default, heartbeats are sent as ISO 8601 UTC timestamps:
```
2026-03-19T21:55:00.000000+00:00
```

You can provide a custom message:
```python
heartbeat = Heartbeat(mqtt_client, message="service is running")
```

## Example

See `example.py` for a complete working example.
