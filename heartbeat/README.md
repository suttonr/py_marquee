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

## CLI Usage

The heartbeat module also provides a command-line interface for sending heartbeats to MQTT.

### Installation

```bash
pip install mqtt-heartbeat
```

Or install from source:
```bash
cd heartbeat
pip install .
```

### Commands

#### Send a single heartbeat

```bash
mqtt-heartbeat once
```

With custom settings:
```bash
mqtt-heartbeat once --broker localhost --port 1883 --topic "health/myapp"
```

#### Watch a port and emit heartbeat when open

Watch port 8080 on localhost and send heartbeat when it's open:

```bash
mqtt-heartbeat watch-port --check-port 8080
```

With custom interval (30 seconds):
```bash
mqtt-heartbeat watch-port --check-port 8080 --interval 30
```

Watch a different host:
```bash
mqtt-heartbeat watch-port --check-port 8080 --host 192.168.1.100
```

#### Watch a URL and emit heartbeat on HTTP response

Watch a health endpoint and send heartbeat when it responds:

```bash
mqtt-heartbeat watch-http --url http://localhost:8080/health
```

With custom interval:
```bash
mqtt-heartbeat watch-http --url http://localhost:8080/health --interval 30
```

### Global Options

These can be combined with any command:

- `--broker TEXT`: MQTT broker hostname (default: localhost)
- `--port INTEGER`: MQTT broker port (default: 1883)
- `--topic TEXT`: MQTT topic for heartbeats (default: health/heartbeat)
- `--message TEXT`: Custom message to send (default: timestamp)

## Example

See `example.py` for a complete working example.

## Systemd Service

To run the heartbeat CLI as a systemd service, create a unit file:

```ini
[Unit]
Description=MQTT Heartbeat Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/py_marquee
ExecStart=/usr/local/bin/mqtt-heartbeat watch-http --url http://localhost:8080/health --interval 30 --broker localhost --topic health/marquee/ping
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Optional: Environment variables for MQTT credentials
# Environment="MQTT_USERNAME=heartbeat"
# Environment="MQTT_PASSWORD=secret"

[Install]
WantedBy=multi-user.target
```

### Installation

1. Save the unit file:
   ```bash
   sudo cp marquee-heartbeat.service /etc/systemd/system/
   ```

2. Reload systemd:
   ```bash
   sudo systemctl daemon-reload
   ```

3. Enable and start the service:
   ```bash
   sudo systemctl enable --now marquee-heartbeat.service
   ```

### Status and Logs

Check service status:
```bash
sudo systemctl status marquee-heartbeat.service
```

View logs:
```bash
sudo journalctl -u marquee-heartbeat.service -f
```
