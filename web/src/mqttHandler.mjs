// mqttHandler.mjs - WebSocket Proxy Version
// Communicates with MQTT broker via WebSocket proxy instead of direct connection

// Socket.IO connection
const socket = io();

// Connection status
socket.on('connect', () => {
    console.log("Connected to WebSocket proxy");
    updateConnectionStatus(true);
    // Subscribe to MQTT topics via proxy
    socket.emit('mqtt_subscribe', { topic: 'marquee/#' });
    socket.emit('mqtt_subscribe', { topic: 'esp32/test/#' });
});

socket.on('disconnect', () => {
    console.log("Disconnected from WebSocket proxy");
    updateConnectionStatus(false);
});

// Handle incoming MQTT messages
socket.on('mqtt_message', (data) => {
    const { topic, payload } = data;
    if (topic === 'marquee/pixels') {
        console.log("Received pixels data");
        processPixels(payload);
    } else {
        console.log(`MQTT message on ${topic}:`, payload);
    }
});

// Handle errors
socket.on('mqtt_error', (data) => {
    console.error("MQTT Error:", data.error);
});

socket.on('mqtt_publish_success', (data) => {
    console.log(`Published to ${data.topic}`);
});

socket.on('mqtt_subscribe_success', (data) => {
    console.log(`Subscribed to ${data.topic}`);
});

// Helper function to update connection status
function updateConnectionStatus(connected) {
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    
    if (statusDot && statusText) {
        if (connected) {
            statusDot.classList.add('connected');
            statusText.textContent = 'Connected';
        } else {
            statusDot.classList.remove('connected');
            statusText.textContent = 'Disconnected';
        }
    }
}

// Helper function to publish MQTT message
function publishMessage(topic, payload) {
    socket.emit('mqtt_publish', { topic, payload });
}

export function processPixels(payload) {
    const pixels = JSON.parse(payload);
    window.pixels = pixels;
    const canvas = document.getElementById('matrix_canvas');
    const ctx = canvas.getContext('2d');
    const scale = parseInt(localStorage.getItem('pixel-scale')) || 2;
    
    for (const [key, value] of Object.entries(pixels)) {
        const x = parseInt(key.substring(0, 3));
        const y = parseInt(key.substring(3, 6));
        let drawX = x;
        let drawY = y;
        ctx.fillStyle = `rgb(${value[0]},${value[1]},${value[2]})`;
        ctx.fillRect(drawX * scale, drawY * scale, scale, scale);
    }
}

export function reconnect() {
    console.log("Reconnecting to WebSocket proxy...");
    if (socket.connected) {
        socket.disconnect();
    }
    socket.connect();
}

// Matrix Commands
export function sendTemplate(template) {
    publishMessage("marquee/template", template);
}

export function sendBright(brightness) {
    const payload = [parseInt(brightness)];
    publishMessage("esp32/test/bright", payload);
}

export function getPixels() {
    const canvas = document.getElementById('matrix_canvas');
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = 'black';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    publishMessage("marquee/get_pixels", "");
}

export function sendText(message_text = "", size = 16, x = 0, y = 8) {
    const encoder = new TextEncoder();
    const x_pos = parseInt(x);
    const y_pos = parseInt(y);
    const address = [x_pos >> 8, x_pos & 0xFF, y_pos];
    const mtext = Array.from(encoder.encode(message_text));
    const payload = [...address, ...mtext];
    
    console.log("payload", payload);
    console.log("address", address);
    console.log("mtext", mtext);
    
    publishMessage(`esp32/test/text/${size}`, payload);
}

export function sendClear() {
    publishMessage("esp32/test/clear", "");
}

export function sendAutoTemplate(arg) {
    publishMessage("marquee/auto_template", arg.toString());
}

export function sendBox(message, box, side, inning = null, team = null, game = null) {
    let topic = `marquee/template/gmonster/box/${box}/${side}`;
    if (box === "inning") {
        topic += `/${inning || 10}`;
    }
    if (team && game) {
        topic += `/${team}/${game}`;
    }
    publishMessage(topic, message);
}

export function sendBgColor(r = 0, g = 0, b = 0) {
    const payload = [parseInt(r), parseInt(g), parseInt(b)];
    publishMessage("esp32/test/bgcolor", payload);
}

export function sendFgColor(r = 0, g = 0, b = 0) {
    const payload = [parseInt(r), parseInt(g), parseInt(b)];
    publishMessage("esp32/test/fgcolor", payload);
}

export function sendReset() {
    publishMessage("esp32/test/reset", "");
}

export function sendTextLine(message, line = 1) {
    publishMessage(`esp32/test/${line}`, message);
}

export function sendScrollText(message, speed = 0.05, direction = "left", loop = true, y_offset = 0) {
    publishMessage(`marquee/template/base/scrolltext/${speed}/${direction}/${loop}/${y_offset}`, message);
}

export function updateBatter(num) {
    publishMessage("marquee/template/gmonster/batter", num.toString());
}

export function updateBase(base, val) {
    publishMessage(`marquee/template/gmonster/bases/${base}`, val.toString());
}

export function updateGame(status) {
    publishMessage("marquee/template/gmonster/game", status);
}

export function updateCount(name, num) {
    publishMessage(`marquee/template/gmonster/count/${name}`, num.toString());
}

export function updateInning(inning, status) {
    publishMessage(`marquee/template/gmonster/inning/${inning}`, status);
}

export function disableWin(status) {
    publishMessage("marquee/template/gmonster/disable-win", status.toString());
}

export function disableClose(status) {
    publishMessage("marquee/template/gmonster/disable-close", status.toString());
}

// Game functions - placeholders
export function sendMlbGame(gamePk) {
    console.log(`Send MLB game ${gamePk} - not fully implemented in web`);
}

export function sendNhlGame(gamePk) {
    console.log(`Send NHL game ${gamePk} - not fully implemented in web`);
}

export function sendNflGame(gamePk) {
    console.log(`Send NFL game ${gamePk} - not fully implemented in web`);
}

export function sendElection() {
    console.log("Send election - not fully implemented in web");
}
