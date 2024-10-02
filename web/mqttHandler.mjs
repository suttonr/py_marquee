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
    console.log("processPixels: Start")
    const pixels = JSON.parse(payload);
    console.log("processPixels: Parsed")
    window.pixels = pixels
    for (const [key, value] of Object.entries(pixels)) {
        //console.log(`${key}: ${value}`);
        const x = parseInt(key.substring(0,3));
        const y = parseInt(key.substring(3,6));
        const pixelDiv = document.querySelector(`#pix-${x}-${y}`)

        if ( pixelDiv !== null ) {
            pixelDiv.style.backgroundColor = `rgb(${value.join(',')})`
        }
    }
    console.log("processPixels: End")
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

// Clears the display
export function sendClear() {
    const message = new Paho.Message("");
    message.destinationName = "esp32/test/clear";
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
    //const payload = new Uint8Array([parseInt(brightness)])
    const message = new Paho.Message("");
    message.destinationName = "marquee/get_pixels";
    const pixel_divs = document.querySelectorAll('.matrix-cell');
    pixel_divs.forEach((pix) => {
        pix.style.backgroundColor = "black"
    });
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

