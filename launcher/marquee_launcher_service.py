#!/usr/bin/env python3
"""
Marquee Launcher Service - REST API version of marquee_launcher.py
Runs as a web service exposing endpoints for MLB game management.
"""

import os
import sys
import time
import threading
import logging
from functools import wraps
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import paho.mqtt.client as mqtt

# Import existing modules
import cli.mlb as mlb
import cli.secrets
import local_secrets as local_secrets

# Import heartbeat module (py-marquee-heartbeat package)
from mqtt_heartbeat import start_heartbeat


# Configure logging
logging.basicConfig(
    stream=sys.stdout,
    format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Access logger for request logs
access_logger = logging.getLogger('access_logger')
access_logger.setLevel(logging.INFO)

# Flask app
app = Flask(__name__)
CORS(app)


@app.after_request
def log_request(response):
    """Log request details including X-Real-IP"""
    real_ip = request.headers.get('X-Real-IP', request.remote_addr or '-')
    access_logger.info(f"{request.method} {request.path} - {response.status_code} - X-Real-IP: {real_ip}")
    return response


# Global variables for background tasks
active_watchers = {}  # game_pk -> {'thread': thread, 'priority': int}
active_finders = {}   # finder_id -> {'thread': thread, 'team_filter': filter, 'sleep_minutes': minutes, 'auto_launch': bool, 'priority': int, 'start_time': datetime}
watcher_lock = threading.Lock()
finder_lock = threading.Lock()
finder_counter = 0


def require_api_key(f):
    """Decorator to require valid API key for endpoint access.
    Supports both 'Authorization: Bearer <key>' and 'X-API-Key: <key>' headers.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = None
        
        # Check Authorization header for Bearer token
        auth_header = request.headers.get('Authorization')
        if auth_header:
            if auth_header.startswith('Bearer '):
                api_key = auth_header[7:]  # Extract token after "Bearer "
        
        # If no Bearer token, check X-API-Key header
        if not api_key:
            api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            logger.warning("Request missing API key")
            logger.debug(f"Headers: {request.headers}")
            logger.debug(f"X-API-Key: {request.headers.get('X-API-Key')}")
            logger.debug(f"Key: {api_key}")
            return jsonify({
                "error": "API key required. Use 'Authorization: Bearer <key>' or 'X-API-Key: <key>' header."
            }), 401
        
        # Check if API key is valid
        if api_key not in local_secrets.API_KEYS:
            logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
            return jsonify({"error": "Invalid API key"}), 401
        
        return f(*args, **kwargs)
    return decorated_function


def finder_thread(finder_id, team_filter, sleep_minutes, auto_launch, priority):
    """Background thread to find and optionally watch games"""
    try:
        while True:
            # Check if this finder was stopped
            with finder_lock:
                if finder_id not in active_finders:
                    break

            logger.info(f"Finder {finder_id}: Finding games iteration")
            now = datetime.now(ZoneInfo("America/New_York"))
            date_str = now.strftime("%Y-%m-%d")

            sch = mlb.schedule(date_str, cli.secrets.MLB_SCHEDULE_URL)
            games = sch.get_games(team_filter)

            # Find the next upcoming game and update time_until_next_game
            min_delta = None
            for game in games:
                # Check if this finder was stopped
                with finder_lock:
                    if finder_id not in active_finders:
                        break

                game_dt = datetime.fromisoformat(game.get("gameDate"))
                delta_to_game = game_dt - now
                logger.info(f'Finder {finder_id}: {game.get("gameDate")} {game.get("gamePk")} {game.get("awayTeam")} vs {game.get("homeTeam")} in {delta_to_game}')

                # Track the minimum time until next game
                if game_dt > now:
                    if min_delta is None or delta_to_game < min_delta:
                        min_delta = delta_to_game

                if auto_launch and game_dt > now and delta_to_game < timedelta(hours=1):
                    game_pk_to_watch = game.get("gamePk")
                    interval = 20
                    
                    # Check if we should start watching this game
                    should_watch = False
                    with watcher_lock:
                        if not active_watchers:
                            should_watch = True
                        else:
                            # Check priority of existing watcher
                            for existing_pk, watcher_info in active_watchers.items():
                                existing_priority = watcher_info.get('priority', 0)
                                if priority > existing_priority:
                                    logger.info(f"Auto-launch: Game {game_pk_to_watch} has higher priority ({priority}) than existing watcher ({existing_priority})")
                                    active_watchers.clear()
                                    should_watch = True
                                elif priority == existing_priority and existing_pk != game_pk_to_watch:
                                    # Same priority, allow if it's a different game
                                    should_watch = True
                                break
                    
                    if should_watch:
                        thread = threading.Thread(target=watch_game_thread, args=(game_pk_to_watch, interval, priority), daemon=True)
                        already_watched = False
                        with watcher_lock:
                            already_watched = game_pk_to_watch in active_watchers
                            active_watchers[game_pk_to_watch] = {
                                'thread': thread,
                                'priority': priority
                            }
                        if not already_watched:
                            thread.start()
                            logger.info(f"Auto-launched watcher for game {game_pk_to_watch}")

            # Update time_until_next_game in finder info
            with finder_lock:
                if finder_id in active_finders:
                    if min_delta is not None:
                        active_finders[finder_id]['time_until_next_game'] = min_delta.total_seconds()
                    else:
                        active_finders[finder_id]['time_until_next_game'] = None

            # Check if this finder was stopped before sleeping
            with finder_lock:
                if finder_id not in active_finders:
                    break

            time.sleep(sleep_minutes * 60)
    except Exception as e:
        logger.error(f"Error in finder thread {finder_id}: {e}")
    finally:
        with finder_lock:
            if finder_id in active_finders:
                del active_finders[finder_id]
        logger.info(f"Finder {finder_id} stopped")

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "active_watchers": len(active_watchers),
        "active_finders": len(active_finders)
    })

@app.route('/schedule', methods=['GET'])
@require_api_key
def get_schedule():
    """
    Get MLB schedule for a date with optional team filter
    Query params: date (YYYY-MM-DD), team_filter
    """
    try:
        date_str = request.args.get('date')
        team_filter = request.args.get('team_filter')

        now = datetime.now(ZoneInfo("America/New_York"))
        if not date_str:
            date_str = now.strftime("%Y-%m-%d")

        sch = mlb.schedule(date_str, cli.secrets.MLB_SCHEDULE_URL)
        games = sch.get_games(team_filter)

        result = []
        for game in games:
            game_dt = datetime.fromisoformat(game.get("gameDate"))
            delta_to_game = game_dt - now
            result.append({
                "gameDate": game.get("gameDate"),
                "gamePk": game.get("gamePk"),
                "awayTeam": game.get("awayTeam"),
                "homeTeam": game.get("homeTeam"),
                "hoursUntil": delta_to_game.total_seconds() / 3600,
                "isStartingSoon": delta_to_game < timedelta(hours=1) and game_dt > now
            })

        return jsonify({"games": result})

    except Exception as e:
        logger.error(f"Failed to get schedule: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/games/find', methods=['POST'])
@require_api_key
def find_games():
    """
    Start background task to find and watch games
    Body: {"team_filter": "BOS", "sleep_minutes": 30, "auto_launch": true, "priority": 10}
    """
    data = request.get_json() or {}
    team_filter = data.get('team_filter')
    sleep_minutes = data.get('sleep_minutes', 30)
    auto_launch = data.get('auto_launch', False)
    priority = data.get('priority', 0)

    global finder_counter

    with finder_lock:
        finder_counter += 1
        finder_id = finder_counter

        thread = threading.Thread(target=finder_thread, args=(finder_id, team_filter, sleep_minutes, auto_launch, priority), daemon=True)
        active_finders[finder_id] = {
            'thread': thread,
            'team_filter': team_filter,
            'sleep_minutes': sleep_minutes,
            'auto_launch': auto_launch,
            'priority': priority,
            'start_time': datetime.now(ZoneInfo("America/New_York"))
        }
        thread.start()

    return jsonify({
        "message": f"Game finder {finder_id} started",
        "finder_id": finder_id,
        "team_filter": team_filter,
        "sleep_minutes": sleep_minutes,
        "auto_launch": auto_launch,
        "priority": priority
    })

@app.route('/games/<int:game_pk>/watch', methods=['POST'])
@require_api_key
def start_watching_game(game_pk):
    """
    Start watching a specific MLB game
    Body: {"interval": 20, "priority": 10}
    """
    data = request.get_json() or {}
    interval = data.get('interval', 20)
    priority = data.get('priority', 0)

    # Check for existing watchers and handle priority
    with watcher_lock:
        if active_watchers:
            # Get existing watcher info
            for existing_pk, watcher_info in active_watchers.items():
                existing_priority = watcher_info.get('priority', 0)
                
                if priority < existing_priority:
                    logger.info(f"Game {game_pk} has lower priority ({priority}) than existing watcher ({existing_priority}), not starting")
                    return jsonify({"error": f"Existing watcher has higher priority ({existing_priority})"}), 409
                elif priority > existing_priority:
                    logger.info(f"Game {game_pk} has higher priority ({priority}) than existing watcher ({existing_priority}), stopping old and starting new")
                    active_watchers.clear()
                break

    thread = threading.Thread(target=watch_game_thread, args=(game_pk, interval, priority), daemon=True)
    
    # Add to active watchers before starting the thread to avoid race condition
    already_watched = False
    with watcher_lock:
        already_watched = game_pk in active_watchers
        active_watchers[game_pk] = {
            'thread': thread,
            'priority': priority
        }
    if not already_watched:
        thread.start()
        return jsonify({"message": f"Started watching game {game_pk}", "priority": priority})
    else:
        return jsonify({"message": f"Game {game_pk} already watched, not starting another", "priority": priority})

@app.route('/games/<int:game_pk>/stop', methods=['POST'])
@require_api_key
def stop_watching_game(game_pk):
    """Stop watching a specific game"""
    with watcher_lock:
        if game_pk not in active_watchers:
            return jsonify({"error": f"Not watching game {game_pk}"}), 400

        # Note: Daemon threads will be terminated when main process exits
        # For proper cleanup, we'd need a more sophisticated approach
        del active_watchers[game_pk]

    return jsonify({"message": f"Stopped watching game {game_pk}"})

@app.route('/games/watching', methods=['GET'])
@require_api_key
def list_watching_games():
    """List currently watched games"""
    with watcher_lock:
        watching = list(active_watchers.keys())

    return jsonify({"watching_games": watching})

@app.route('/games/finders', methods=['GET'])
@require_api_key
def list_active_finders():
    """List currently active game finders"""
    with finder_lock:
        finders = []
        for finder_id, finder_info in active_finders.items():
            runtime = datetime.now(ZoneInfo("America/New_York")) - finder_info['start_time']
            finder_data = {
                "finder_id": finder_id,
                "team_filter": finder_info['team_filter'],
                "sleep_minutes": finder_info['sleep_minutes'],
                "auto_launch": finder_info['auto_launch'],
                "priority": finder_info.get('priority', 0),
                "start_time": finder_info['start_time'].isoformat(),
                "runtime_seconds": runtime.total_seconds(),
                "time_until_next_game": finder_info.get('time_until_next_game')
            }
            finders.append(finder_data)

    return jsonify({"active_finders": finders})

@app.route('/games/finders/<int:finder_id>', methods=['GET'])
@require_api_key
def get_finder(finder_id):
    """Get a specific game finder by ID"""
    with finder_lock:
        if finder_id not in active_finders:
            return jsonify({"error": f"Finder {finder_id} not found"}), 404

        finder_info = active_finders[finder_id]
        runtime = datetime.now(ZoneInfo("America/New_York")) - finder_info['start_time']
        finder_data = {
            "finder_id": finder_id,
            "team_filter": finder_info['team_filter'],
            "sleep_minutes": finder_info['sleep_minutes'],
            "auto_launch": finder_info['auto_launch'],
            "priority": finder_info.get('priority', 0),
            "start_time": finder_info['start_time'].isoformat(),
            "runtime_seconds": runtime.total_seconds(),
            "time_until_next_game": finder_info.get('time_until_next_game')
        }

    return jsonify(finder_data)

@app.route('/games/finders/<int:finder_id>/stop', methods=['POST'])
@require_api_key
def stop_finder(finder_id):
    """Stop a specific game finder"""
    with finder_lock:
        if finder_id >= len(active_finders) or finder_id < 0:
            return jsonify({"error": f"Finder {finder_id} not found"}), 404

        # Remove from active finders - the thread will detect this and stop
        del active_finders[finder_id]

    return jsonify({"message": f"Stopped finder {finder_id}"})

@app.route('/games/finders/stop-all', methods=['POST'])
@require_api_key
def stop_all_finders():
    """Stop all active game finders"""
    with finder_lock:
        finder_ids = list(active_finders.keys())
        active_finders.clear()

    return jsonify({"message": f"Stopped {len(finder_ids)} finders", "stopped_finders": finder_ids})

@app.route('/backfill', methods=['POST'])
@require_api_key
def backfill_game():
    """Backfill the currently watched game"""
    with watcher_lock:
        if not active_watchers:
            return jsonify({"error": "No game currently being watched"}), 400

        game_pk = list(active_watchers.keys())[0]  # Assuming only one game watched at a time

    try:
        result = subprocess.run([
            sys.executable, "cli/matrix-cli.py", "send-mlb-game", "-g", str(game_pk), "--backfill"
        ], capture_output=True, text=True, cwd=os.path.dirname(__file__))

        if result.returncode not in [0, 80, 81, 89, 98]:
            logger.error(f"Backfill failed for game {game_pk}: {result.stderr}")
            return jsonify({"error": f"Backfill failed: {result.stderr}"}), 500
    except Exception as e:
        logger.error(f"Error during backfill for game {game_pk}: {e}")
        return jsonify({"error": str(e)}), 500
    return jsonify({"message": "backfill success"})

@app.route('/display/clear', methods=['POST'])
@require_api_key
def clear_display():
    """Clear the marquee display"""
    try:
        result = subprocess.run([
            sys.executable, "cli/matrix-cli.py", "clear"
        ], capture_output=True, text=True, cwd=os.path.dirname(__file__))

        if result.returncode == 0:
            return jsonify({"message": "Display cleared"})
        else:
            return jsonify({"error": "Failed to clear display"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/display/text', methods=['POST'])
@require_api_key
def send_text():
    """Send text to display"""
    data = request.get_json() or {}
    message = data.get('message', '')
    line = data.get('line', 1)

    try:
        result = subprocess.run([
            sys.executable, "cli/matrix-cli.py", "text-line", "--line", str(line), message
        ], capture_output=True, text=True, cwd=os.path.dirname(__file__))

        if result.returncode == 0:
            return jsonify({"message": f"Text sent: {message}"})
        else:
            return jsonify({"error": "Failed to send text"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/display/brightness/<int:brightness>', methods=['POST'])
@require_api_key
def set_brightness(brightness):
    """Set display brightness (0-255)"""
    if not 0 <= brightness <= 255:
        return jsonify({"error": "Brightness must be 0-255"}), 400

    try:
        result = subprocess.run([
            sys.executable, "cli/matrix-cli.py", "brightness", str(brightness)
        ], capture_output=True, text=True, cwd=os.path.dirname(__file__))

        if result.returncode == 0:
            return jsonify({"message": f"Brightness set to {brightness}"})
        else:
            return jsonify({"error": "Failed to set brightness"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def watch_game_thread(game_pk, interval, priority=0):
    """Background thread to watch a game
    
    Args:
        game_pk: The MLB game primary key
        interval: Polling interval in seconds
        priority: Priority level (higher number = higher priority)
    
    Note: The watcher should already be added to active_watchers before this thread starts
    """
    logger.info(f"Watch thread started for game {game_pk} with priority {priority}")

    retcode = 0
    sweet_caroline = False
    dirty_water = False

    try:
        while retcode == 0 or retcode in [80, 81, 89, 98]:
            # Check if this watcher was stopped
            with watcher_lock:
                if game_pk not in active_watchers:
                    break

            result = subprocess.run([
                sys.executable, "cli/matrix-cli.py", "send-mlb-game", "-g", str(game_pk)
            ], capture_output=True, text=True, cwd=os.path.dirname(__file__))

            retcode = result.returncode
            sleep_time = interval

            logger.debug(f"Game {game_pk} result: {retcode}")

            for line in result.stdout.split('\n'):
                if line.strip():
                    logger.info(f"Game {game_pk}: {line}")

            for line in result.stderr.split("\n"):
                if line.strip():
                    logger.error(f"Game {game_pk}: {line}")

            if retcode == 0:
                logger.debug(f"Game {game_pk}: active")
            elif retcode == 80:
                logger.debug(f"Game {game_pk}: active (Sweet Caroline)")
                if not sweet_caroline:
                    trigger_webhook("http://192.168.2.178/apps/api/493/trigger?access_token=cd3abd09-23eb-4e75-acca-f0ecbbab11d0")
                    sweet_caroline = True
            elif retcode == 81:
                logger.debug(f"Game {game_pk}: active (Dirty Water)")
                if not dirty_water:
                    trigger_webhook("http://192.168.2.178/apps/api/489/trigger?access_token=d45b8e96-30a9-4987-9fea-0936c4af7a28")
                    dirty_water = True
            elif retcode == 98:
                logger.info(f"Game {game_pk}: pregame, longer sleep")
                sleep_time *= 10
            elif retcode == 99:
                logger.info(f"Game {game_pk}: ended")
                break
            else:
                logger.error(f"Game {game_pk}: error sending")

            time.sleep(sleep_time)

    except Exception as e:
        logger.error(f"Error watching game {game_pk}: {e}")
    finally:
        with watcher_lock:
            logger.info(f"Game {game_pk}: Watching Stopped")
            if game_pk in active_watchers:
                del active_watchers[game_pk]

def trigger_webhook(url):
    """Trigger a webhook URL"""
    try:
        result = subprocess.run(["/usr/bin/curl", url], capture_output=True, text=True)
        logger.info(f"Webhook triggered: {url}")
    except Exception as e:
        logger.error(f"Failed to trigger webhook {url}: {e}")

# Global MQTT client and heartbeat for cleanup
mqtt_client = None
launcher_heartbeat = None

def setup_mqtt_and_heartbeat():
    """Set up MQTT client and start heartbeat."""
    global mqtt_client, launcher_heartbeat
    
    try:
        # Create MQTT client
        mqtt_client = mqtt.Client(client_id="marquee_launcher")
        mqtt_client.username_pw_set(cli.secrets.MQTT_USERNAME, cli.secrets.MQTT_PASSWORD)
        mqtt_client.connect(cli.secrets.MQTT_BROKER, cli.secrets.MQTT_PORT, 60)
        mqtt_client.loop_start()
        
        # Start heartbeat on 'health/launcher/ping' topic
        launcher_heartbeat = start_heartbeat(
            mqtt_client,
            topic="health/launcher/ping",
            interval_seconds=60
        )
        logger.info("MQTT client connected and heartbeat started on 'health/launcher/ping'")
        return True
    except Exception as e:
        logger.error(f"Failed to set up MQTT/heartbeat: {e}")
        return False

def cleanup_mqtt_and_heartbeat():
    """Clean up MQTT client and stop heartbeat."""
    global mqtt_client, launcher_heartbeat
    
    if launcher_heartbeat:
        try:
            launcher_heartbeat.stop()
            logger.info("Heartbeat stopped")
        except Exception as e:
            logger.error(f"Error stopping heartbeat: {e}")
    
    if mqtt_client:
        try:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
            logger.info("MQTT client disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting MQTT client: {e}")

if __name__ == '__main__':
    # Set up MQTT and start heartbeat
    setup_mqtt_and_heartbeat()
    
    # Register cleanup handlers for graceful shutdown
    import atexit
    atexit.register(cleanup_mqtt_and_heartbeat)
    
    # Start default finder if WATCH_TEAM is set
    watch_team = os.environ.get('WATCH_TEAM', 'Red Sox')
    if watch_team:
        finder_id = 0
        sleep_minutes = 30
        auto_launch = True
        priority = 5  # Default priority for startup finder
        with finder_lock:
            thread = threading.Thread(
                target=finder_thread, 
                args=(finder_id, watch_team, sleep_minutes, auto_launch, priority), 
                daemon=True
            )
            active_finders[finder_id] = {
                'thread': thread,
                'team_filter': watch_team,
                'sleep_minutes': sleep_minutes,
                'auto_launch': auto_launch,
                'priority': priority,
                'start_time': datetime.now(ZoneInfo("America/New_York"))
            }
            thread.start()
        logger.info(f"Started startup finder for team: {watch_team}")

    port = int(os.environ.get('PORT', 4000))
    debug_mode = os.environ.get('DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
