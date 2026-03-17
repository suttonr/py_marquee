# Marquee Control Web Application

A Flask-based web application for controlling an LED matrix display with session-based authentication.

## Features

- **Session-based Authentication**: Secure login system to protect the control panel
- **Real-time Control**: Control LED matrix display via MQTT
- **Multiple Pages**: Main control page, launcher interface, admin, and Grafana
- **Responsive Design**: Works on desktop and mobile devices

## Quick Start

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python3 server.py
```

The web interface will be available at `http://localhost:8888`

## Building and Running with Docker

The project includes a Makefile for easy container management using Podman:

```bash
cd web
```

### Available Makefile Commands

| Command | Description |
|---------|-------------|
| `make build` | Build the Docker image |
| `make create` | Create and start a container |
| `make start` | Start an existing container |
| `make stop` | Stop the container |
| `make restart` | Restart the container |
| `make status` | Show container status and logs |
| `make remove` | Remove the container |
| `make install` | Create container and install as systemd service |
| `make run` | Full install: remove, build, install, start, and show status |
| `make shell` | Open a shell inside the container |
| `make logs` | Follow container logs |
| `make run-debug` | Create and run container in debug mode |

### Docker Examples

```bash
# Build the container
make build

# Create and run the container
make create

# Run the full installation (build, install, start)
make run

# View logs
make logs

# Open shell in container
make shell
```

### Running with Custom Credentials

To set custom login credentials when running Docker, you can pass environment variables:

```bash
# Build first
make build

# Create container with custom credentials
podman create --name marquee-web \
  --publish 8888:8888 \
  -e ADMIN_USERNAME=myuser \
  -e ADMIN_PASSWORD=mypassword \
  localhost/marquee-web:latest

# Start the container
podman start marquee-web
```

Or edit the Makefile to add environment variables to `CONTAINER_OPTS`.

## Authentication

### Default Credentials

- **Username**: `admin`
- **Password**: `marquee123`

### Custom Credentials

Set environment variables to change the default credentials:

```bash
# Linux/macOS
export ADMIN_USERNAME=myuser
export ADMIN_PASSWORD=mypassword

# Run the server
python3 server.py
```

### Additional Security

For production use, set a custom secret key:
```bash
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
```

## Project Structure

```
web/
├── server.py           # Flask application
├── login.html          # Login page
├── common.css          # Shared styles
├── requirements.txt    # Python dependencies
├── Dockerfile          # Docker configuration
├── Makefile           # Build/run commands
├── auth/              # Authentication data
│   └── admin.json     # Admin credentials
└── src/               # Frontend source files
    ├── index.html     # Main control interface
    ├── launcher.html  # Game launcher interface
    ├── admin.html    # Administration interface
    ├── grafana.html  # Grafana dashboard link
    ├── common.mjs    # Shared JavaScript (hamburger menu, dark mode, tabs, logging)
    ├── index.mjs     # Main control page JavaScript
    ├── launcher.mjs   # Launcher page JavaScript
    ├── admin.mjs     # Admin page JavaScript
    ├── mqttHandler.mjs    # MQTT client
    ├── mqttHandler.test.mjs # MQTT handler tests
    ├── secrets.mjs         # MQTT configuration (credentials)
    ├── webauthn_auth.py   # WebAuthn authentication
    ├── mqtt_proxy.py      # MQTT proxy for launcher API
    └── server.py          # Flask application (also at root)
```

## Frontend Architecture

The web application uses ES6 modules to share code between pages:

- **`common.mjs`**: Shared functionality used by all non-login pages
  - Hamburger menu toggle
  - Dark mode initialization and persistence
  - Tab switching
  - Logging system
  - Alert system
  - Connection status management

- **`index.mjs`**: Marquee control page specific functionality
  - Canvas responsive sizing
  - Brightness/pixel scale controls
  - Color picker functionality
  - Auto-refresh functionality

- **`launcher.mjs`**: Game launcher page functionality
  - Health/watching/finders status
  - Schedule loading
  - Game watching controls
  - Game finder controls

- **`admin.mjs`**: Administration page functionality
  - User registration management
  - Users list display
  - MQTT IP allowlist management

## Testing

Run the unit tests:

```bash
cd web
python -m pytest ../tests/web/test_server.py -v
```

## Available Routes

| Route | Description | Auth Required |
|-------|-------------|---------------|
| `/` | Main control page | Yes |
| `/login` | Login page | No |
| `/logout` | Logout | Yes |
| `/launcher.html` | Game launcher | Yes |
| `/admin.html` | Administration | Yes |
| `/grafana.html` | Grafana dashboard | Yes |
| `/api/launcher/*` | Launcher API proxy | Yes |
| `/api/admin/*` | Admin API | Yes |
| `/<file>` | Static files | Yes |

## MQTT Configuration

Edit `src/secrets.mjs` to configure MQTT connection:

```javascript
export const MQTT_BROKER = "your-broker.com"
export const MQTT_PORT = 8080
export const MQTT_USERNAME = "your-username"
export const MQTT_PASSWORD = "your-password"
```
