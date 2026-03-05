# Marquee Launcher Service

A REST API service version of the marquee_launcher.py CLI tool, containerized and running as a systemd service.

## Features

- REST API for MLB game schedule management
- Background game watching with automatic display updates
- Display control endpoints (clear, text, brightness)
- Health monitoring
- Containerized with Docker
- Runs as systemd user service

## API Endpoints

### Health & Status
- `GET /health` - Service health check

### Schedule Management
- `GET /schedule?date=YYYY-MM-DD&team_filter=BOS` - Get MLB schedule

### Game Watching
- `POST /games/find` - Start background game finder
- `POST /games/<game_pk>/watch` - Start watching specific game
- `POST /games/<game_pk>/stop` - Stop watching game
- `GET /games/watching` - List currently watched games

### Display Control
- `POST /display/clear` - Clear the marquee display
- `POST /display/text` - Send text to display
- `POST /display/brightness/<0-255>` - Set display brightness

## Installation & Usage

### Build and Run as Systemd Service

```bash
cd launcher
make run
```

This will:
1. Build the Docker container
2. Create a systemd user service
3. Start the service
4. Enable auto-start on boot

### Manual Commands

```bash
# Build container
make build

# Create systemd service
make install

# Start service
make start

# Check status
make status

# View logs
make logs

# Stop service
make stop
```

## Configuration

The service uses the same `secrets.py` file as the original CLI tool for MQTT and API credentials.

## Example API Usage

```bash
# Health check
curl http://localhost:5000/health

# Get today's schedule for Boston
curl "http://localhost:5000/schedule?team_filter=BOS"

# Start watching a game
curl -X POST http://localhost:5000/games/123456/watch -H "Content-Type: application/json" -d '{"interval": 20}'

# Clear display
curl -X POST http://localhost:5000/display/clear

# Send text
curl -X POST http://localhost:5000/display/text -H "Content-Type: application/json" -d '{"message": "Hello World", "line": 1}'