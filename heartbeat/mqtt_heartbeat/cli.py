"""
Click CLI for heartbeat functionality.

This module provides a command-line interface for sending heartbeats to MQTT,
with support for:
- Sending a single heartbeat
- Watching a port and emitting heartbeat if port is open
- Watching a port and emitting heartbeat if port responds to HTTP GET
"""

import click
import socket
import logging
import time
import threading
import urllib.request
import urllib.error
from datetime import datetime, timezone

from mqtt_heartbeat.heartbeat import Heartbeat

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_mqtt_client(broker, port, topic, message, keepalive=60):
    """
    Create and connect an MQTT client.
    
    Args:
        broker: MQTT broker hostname/IP
        port: MQTT broker port
        topic: MQTT topic to publish to
        message: Custom message to send
        keepalive: Keepalive interval in seconds
    
    Returns:
        Connected MQTT client and Heartbeat instance
    """
    import paho.mqtt.client as mqtt
    
    # Create MQTT client with a unique client ID
    client_id = f"heartbeat_cli_{int(time.time())}"
    client = mqtt.Client(client_id=client_id)
    
    # Connect to broker
    try:
        client.connect(broker, port, keepalive)
        client.loop_start()
        time.sleep(1)  # Give time for connection to establish
    except Exception as e:
        logger.error(f"Failed to connect to MQTT broker: {e}")
        raise
    
    # Create heartbeat instance
    heartbeat = Heartbeat(client, topic=topic, message=message)
    
    return client, heartbeat


@click.group()
@click.option('--broker', default='localhost', help='MQTT broker hostname (default: localhost)')
@click.option('--port', default=1883, type=int, help='MQTT broker port (default: 1883)')
@click.option('--topic', default='health/heartbeat', help='MQTT topic for heartbeats (default: health/heartbeat)')
@click.option('--message', default=None, help='Custom message to send (default: timestamp)')
@click.pass_context
def cli(ctx, broker, port, topic, message):
    """Heartbeat CLI - Send heartbeats to MQTT with various monitoring modes."""
    ctx.ensure_object(dict)
    ctx.obj['broker'] = broker
    ctx.obj['port'] = port
    ctx.obj['topic'] = topic
    ctx.obj['message'] = message or datetime.now(timezone.utc).isoformat()


@cli.command()
@click.pass_context
def once(ctx):
    """Send a single heartbeat immediately."""
    broker = ctx.obj['broker']
    port = ctx.obj['port']
    topic = ctx.obj['topic']
    message = ctx.obj['message']
    
    logger.info(f"Sending single heartbeat to {broker}:{port} on topic '{topic}'")
    
    try:
        client, heartbeat = get_mqtt_client(broker, port, topic, message)
        result = heartbeat.send_once()
        
        if result:
            click.echo(f"Heartbeat sent successfully: {message}")
        else:
            click.echo("Failed to send heartbeat", err=True)
        
        # Give time for message to be sent
        time.sleep(1)
        client.loop_stop()
        client.disconnect()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--host', default='localhost', help='Host to check (default: localhost)')
@click.option('--check-port', required=True, type=int, help='Port to watch and send heartbeat when open')
@click.option('--interval', default=60, type=int, help='Interval between checks in seconds (default: 60)')
@click.pass_context
def watch_port(ctx, host, check_port, interval):
    """Watch a port and emit heartbeat when the port is open."""
    broker = ctx.obj['broker']
    port = ctx.obj['port']
    topic = ctx.obj['topic']
    message = ctx.obj['message']
    
    logger.info(f"Starting port watcher: {host}:{check_port}, will send heartbeat when port is open")
    click.echo(f"Watching {host}:{check_port} - will send heartbeat when port opens")
    
    def check_port_thread():
        """Background thread to check port status."""
        client, heartbeat = get_mqtt_client(broker, port, topic, message)
        
        try:
            while True:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex((host, check_port))
                    sock.close()
                    
                    if result == 0:
                        # Port is open
                        logger.info(f"Port {check_port} is open - sending heartbeat")
                        heartbeat.send_once()
                        click.echo(f"[{datetime.now().isoformat()}] Port {check_port} is OPEN - heartbeat sent")
                    else:
                        logger.debug(f"Port {check_port} is closed")
                    
                except Exception as e:
                    logger.error(f"Error checking port: {e}")
                
                time.sleep(interval)
        except KeyboardInterrupt:
            pass
        finally:
            client.loop_stop()
            client.disconnect()
    
    try:
        check_port_thread()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--url', required=True, help='URL to check (e.g., http://localhost:8080/health)')
@click.option('--interval', default=60, type=int, help='Interval between checks in seconds (default: 60)')
@click.option('--timeout', default=5, type=int, help='HTTP request timeout in seconds (default: 5)')
@click.pass_context
def watch_http(ctx, url, interval, timeout):
    """Watch a URL and emit heartbeat when it responds to HTTP GET."""
    broker = ctx.obj['broker']
    port = ctx.obj['port']
    topic = ctx.obj['topic']
    message = ctx.obj['message']
    
    logger.info(f"Starting HTTP watcher: {url}, will send heartbeat when HTTP responds")
    click.echo(f"Watching {url} - will send heartbeat when HTTP responds")
    
    def check_http_thread():
        """Background thread to check HTTP endpoint."""
        client, heartbeat = get_mqtt_client(broker, port, topic, message)
        
        try:
            while True:
                try:
                    req = urllib.request.Request(url)
                    with urllib.request.urlopen(req, timeout=timeout) as response:
                        status_code = response.getcode()
                        logger.info(f"HTTP GET {url} returned {status_code} - sending heartbeat")
                        heartbeat.send_once()
                        click.echo(f"[{datetime.now().isoformat()}] HTTP {url} responded with {status_code} - heartbeat sent")
                        
                except urllib.error.URLError as e:
                    logger.debug(f"HTTP GET {url} failed: {e}")
                except Exception as e:
                    logger.error(f"Error checking HTTP: {e}")
                
                time.sleep(interval)
        except KeyboardInterrupt:
            pass
        finally:
            client.loop_stop()
            client.disconnect()
    
    try:
        check_http_thread()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    cli()
