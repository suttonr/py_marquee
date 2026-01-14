// mqttHandler.js
import { MQTT_BROKER, MQTT_PORT, MQTT_USERNAME, MQTT_PASSWORD } from './secrets.mjs';
// MQTT Broker details
const MQTT_TOPIC_TEMPLATE = "marquee/template";
const MQTT_TOPIC_PIXELS = "marquee/pixels";
const MQTT_TOPIC_MARQUEE_SUB = "marquee/#";
const MQTT_TOPIC_TEST_SUB = "esp32/test/#";

// Create a client instance
const clientID = "mqtt_js_" + Math.random().toString(16).substr(2, 8);
const client = new Paho.Client(MQTT_BROKER, MQTT_PORT, clientID);

// Set callback handlers
client.onConnectionLost = function (responseObject) {
    if (responseObject.errorCode !== 0) {
        console.log("onConnectionLost:", responseObject.errorMessage);
    }
};

client.onMessageArrived = function (message) {
    if ( MQTT_TOPIC_PIXELS == message.topic) {
        console.log("onMessageArrived:", message.topic);
        processPixels(message.payloadString);
    } else {
        try {
            console.log("onMessageArrived:", message.topic, message.payloadString);
        } catch {
            console.log("onMessageArrived:", message.topic, "binary data");
        }
    }
};

// Connect the client
client.connect({
    onSuccess: onConnect,
    userName: MQTT_USERNAME,
    password: MQTT_PASSWORD,
    useSSL: false
});

// Called when the client connects
function onConnect() {
    console.log("Connected to MQTT broker");
    client.subscribe(MQTT_TOPIC_MARQUEE_SUB);
    client.subscribe(MQTT_TOPIC_TEST_SUB);
}

function processPixels(payload) {
    //console.log("processPixels: Start")
    const pixels = JSON.parse(payload);
    window.pixels = pixels
    const canvas = document.getElementById('matrix_canvas');
    const ctx = canvas.getContext('2d');
    const scale = canvas.width === 448 ? 2 : 2; // Both use 2 for visibility
    for (const [key, value] of Object.entries(pixels)) {
        const x = parseInt(key.substring(0,3));
        const y = parseInt(key.substring(3,6));
        let drawX, drawY;
        drawX = x;
        drawY = y;
        ctx.fillStyle = `rgb(${value[0]},${value[1]},${value[2]})`;
        ctx.fillRect(drawX * scale, drawY * scale, scale, scale);
    }
}

export function reconnect() {
    client.connect({
        onSuccess: onConnect,
        userName: MQTT_USERNAME,
        password: MQTT_PASSWORD,
        useSSL: false
    });
}

// Matrix Commands
// Send a set template message
export function sendTemplate(template) {
    const message = new Paho.Message(template);
    message.destinationName = MQTT_TOPIC_TEMPLATE;
    client.send(message);
}

// Set brightness of the display
export function sendBright(brightness) {
    const payload = new Uint8Array([parseInt(brightness)])
    const message = new Paho.Message(payload);
    message.destinationName = "esp32/test/bright";
    client.send(message);
}

// Get pixel status
export function getPixels() {
    const message = new Paho.Message("");
    message.destinationName = "marquee/get_pixels";
    const canvas = document.getElementById('matrix_canvas');
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = 'black';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    client.send(message);
}

// Send some text to the display at a position
export function sendText(message_text="", size=16, x=0, y=8) {
    let encoding = new TextEncoder();
    const x_pos = parseInt(x)
    const y_pos = parseInt(y)
    const address = new Uint8Array([x_pos>>8, x_pos, y_pos])
    const mtext =  encoding.encode(message_text)
    const payload = new Uint8Array([...address, ...mtext])
    console.log("payload", payload)
    console.log("address", address)
    console.log("mtext", mtext)
    const message = new Paho.Message(payload);
    message.destinationName = `esp32/test/text/${size}`;
    client.send(message);
}

// Send image file (simplified, assuming file upload)
export function sendImage(file, x_offset=0, y_offset=0, x_start=0, y_start=0, x_end=null, y_end=null, clear=false) {
    // This would need to process the image, similar to CLI
    // For now, placeholder
    console.log("sendImage not implemented yet");
}

// Clear display
export function sendClear() {
    const message = new Paho.Message("");
    message.destinationName = "esp32/test/clear";
    client.send(message);
}

// Set auto template
export function sendAutoTemplate(arg) {
    const message = new Paho.Message(arg.toString());
    message.destinationName = "marquee/auto_template";
    client.send(message);
}

// Send box message
export function sendBox(message, box, side, inning=null, team=null, game=null) {
    let topic = `marquee/template/gmonster/box/${box}/${side}`;
    if (box === "inning") {
        topic += `/${inning || 10}`;
    }
    if (team && game) {
        topic += `/${team}/${game}`;
    }
    const msg = new Paho.Message(message);
    msg.destinationName = topic;
    client.send(msg);
}

// Set background color
export function sendBgColor(r=0, g=0, b=0) {
    const payload = new Uint8Array([r, g, b]);
    const message = new Paho.Message(payload);
    message.destinationName = "esp32/test/bgcolor";
    client.send(message);
}

// Set foreground color
export function sendFgColor(r=0, g=0, b=0) {
    const payload = new Uint8Array([r, g, b]);
    const message = new Paho.Message(payload);
    message.destinationName = "esp32/test/fgcolor";
    client.send(message);
}

// Reset display
export function sendReset() {
    const message = new Paho.Message("");
    message.destinationName = "esp32/test/reset";
    client.send(message);
}

// Send text to line
export function sendTextLine(message, line=1) {
    const msg = new Paho.Message(message);
    msg.destinationName = `esp32/test/${line}`;
    client.send(msg);
}

// Update batter
export function updateBatter(num) {
    const msg = new Paho.Message(num.toString());
    msg.destinationName = "marquee/template/gmonster/batter";
    client.send(msg);
}

// Update base
export function updateBase(base, val) {
    const msg = new Paho.Message(val.toString());
    msg.destinationName = `marquee/template/gmonster/bases/${base}`;
    client.send(msg);
}

// Update game status
export function updateGame(status) {
    const msg = new Paho.Message(status);
    msg.destinationName = "marquee/template/gmonster/game";
    client.send(msg);
}

// Update count
export function updateCount(name, num) {
    const msg = new Paho.Message(num.toString());
    msg.destinationName = `marquee/template/gmonster/count/${name}`;
    client.send(msg);
}

// Update inning
export function updateInning(inning, status) {
    const msg = new Paho.Message(status);
    msg.destinationName = `marquee/template/gmonster/inning/${inning}`;
    client.send(msg);
}

// Disable win
export function disableWin(status) {
    const msg = new Paho.Message(status);
    msg.destinationName = "marquee/template/gmonster/disable-win";
    client.send(msg);
}

// Disable close
export function disableClose(status) {
    const msg = new Paho.Message(status);
    msg.destinationName = "marquee/template/gmonster/disable-close";
    client.send(msg);
}

// Send MLB game (placeholder, needs game_pk)
export function sendMlbGame(gamePk) {
    console.log(`Send MLB game ${gamePk} - not fully implemented in web`);
    // Would need to replicate CLI logic, perhaps call a backend
}

// Similarly for NHL, NFL, Election
export function sendNhlGame(gamePk) {
    console.log(`Send NHL game ${gamePk} - not fully implemented in web`);
}

export function sendNflGame(gamePk) {
    console.log(`Send NFL game ${gamePk} - not fully implemented in web`);
}

export function sendElection() {
    console.log("Send election - not fully implemented in web");
}
