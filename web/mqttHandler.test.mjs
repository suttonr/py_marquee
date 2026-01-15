import { jest } from '@jest/globals';

// Mock the secrets.mjs module
jest.mock('./secrets.mjs', () => ({
  MQTT_BROKER: 'test-broker',
  MQTT_PORT: 1883,
  MQTT_USERNAME: 'test-user',
  MQTT_PASSWORD: 'test-pass'
}));

// Mock Paho MQTT client
jest.mock('https://cdnjs.cloudflare.com/ajax/libs/paho-mqtt/1.1.0/paho-mqtt.min.js', () => ({}), { virtual: true });

// Mock Paho globally
global.Paho = {
  Client: jest.fn().mockImplementation(() => ({
    connect: jest.fn(),
    subscribe: jest.fn(),
    send: jest.fn(),
    onConnectionLost: null,
    onMessageArrived: null
  })),
  Message: jest.fn().mockImplementation((payload) => ({
    payloadString: payload,
    destinationName: '',
    payload
  }))
};

// Mock DOM elements
const mockCtx = {
  fillStyle: '',
  fillRect: jest.fn(),
  fillText: jest.fn()
};
document.getElementById = jest.fn().mockImplementation((id) => {
  if (id === 'matrix_canvas') {
    return {
      width: 896,
      height: 48,
      getContext: jest.fn(() => mockCtx)
    };
  }
  return null;
});

// Mock TextEncoder
global.TextEncoder = class TextEncoder {
  encode(str) {
    return Buffer.from(str, 'utf-8');
  }
};

describe('mqttHandler', () => {
  let mockClient;
  let reconnect, sendTemplate, sendBright, getPixels, sendText, sendClear,
      sendAutoTemplate, sendBox, sendBgColor, sendFgColor, sendReset, sendTextLine,
      updateBatter, updateBase, updateGame, updateCount, updateInning,
      disableWin, disableClose, sendMlbGame, sendNhlGame, sendNflGame, sendElection;

  beforeEach(() => {
    jest.clearAllMocks();
    // Reset global pixels
    global.pixels = {};
  });

  beforeAll(async () => {
    const module = await import('./mqttHandler.mjs');
    // The module creates the client, so get it from the mock
    mockClient = global.Paho.Client.mock.results[0].value;
    reconnect = module.reconnect;
    sendTemplate = module.sendTemplate;
    sendBright = module.sendBright;
    getPixels = module.getPixels;
    sendText = module.sendText;
    sendClear = module.sendClear;
    sendAutoTemplate = module.sendAutoTemplate;
    sendBox = module.sendBox;
    sendBgColor = module.sendBgColor;
    sendFgColor = module.sendFgColor;
    sendReset = module.sendReset;
    sendTextLine = module.sendTextLine;
    updateBatter = module.updateBatter;
    updateBase = module.updateBase;
    updateGame = module.updateGame;
    updateCount = module.updateCount;
    updateInning = module.updateInning;
    disableWin = module.disableWin;
    disableClose = module.disableClose;
    sendMlbGame = module.sendMlbGame;
    sendNhlGame = module.sendNhlGame;
    sendNflGame = module.sendNflGame;
    sendElection = module.sendElection;
  });

  test('sendTemplate sends correct message', () => {
    sendTemplate('test-template');
    expect(mockClient.send).toHaveBeenCalledWith(
      expect.objectContaining({
        destinationName: 'marquee/template',
        payloadString: 'test-template'
      })
    );
  });

  test('sendBright sends brightness value', () => {
    sendBright(128);
    expect(mockClient.send).toHaveBeenCalledWith(
      expect.objectContaining({
        destinationName: 'esp32/test/bright'
      })
    );
  });

  test('getPixels sends get_pixels message and clears canvas', () => {
    getPixels();
    expect(mockClient.send).toHaveBeenCalledWith(
      expect.objectContaining({
        destinationName: 'marquee/get_pixels'
      })
    );
    // Verify canvas context fillRect was called to clear
    const canvas = document.getElementById('matrix_canvas');
    expect(canvas.getContext().fillRect).toHaveBeenCalledWith(0, 0, canvas.width, canvas.height);
  });

  test('sendText sends text message with correct payload', () => {
    sendText('Hello', 16, 10, 20);
    expect(mockClient.send).toHaveBeenCalledWith(
      expect.objectContaining({
        destinationName: 'esp32/test/text/16'
      })
    );
  });

  test('sendClear sends clear message', () => {
    sendClear();
    expect(mockClient.send).toHaveBeenCalledWith(
      expect.objectContaining({
        destinationName: 'esp32/test/clear'
      })
    );
  });

  test('sendAutoTemplate sends auto template message', () => {
    sendAutoTemplate(5);
    expect(mockClient.send).toHaveBeenCalledWith(
      expect.objectContaining({
        destinationName: 'marquee/auto_template',
        payloadString: '5'
      })
    );
  });

  test('sendBox sends box message', () => {
    sendBox('test message', 'team', 'home');
    expect(mockClient.send).toHaveBeenCalledWith(
      expect.objectContaining({
        destinationName: 'marquee/template/gmonster/box/team/home',
        payloadString: 'test message'
      })
    );
  });

  test('sendBgColor sends background color', () => {
    sendBgColor(255, 0, 0);
    expect(mockClient.send).toHaveBeenCalledWith(
      expect.objectContaining({
        destinationName: 'esp32/test/bgcolor'
      })
    );
  });

  test('sendFgColor sends foreground color', () => {
    sendFgColor(0, 255, 0);
    expect(mockClient.send).toHaveBeenCalledWith(
      expect.objectContaining({
        destinationName: 'esp32/test/fgcolor'
      })
    );
  });

  test('sendReset sends reset message', () => {
    sendReset();
    expect(mockClient.send).toHaveBeenCalledWith(
      expect.objectContaining({
        destinationName: 'esp32/test/reset'
      })
    );
  });

  test('sendTextLine sends text to line', () => {
    sendTextLine('Line text', 2);
    expect(mockClient.send).toHaveBeenCalledWith(
      expect.objectContaining({
        destinationName: 'esp32/test/2',
        payloadString: 'Line text'
      })
    );
  });

  test('updateBatter sends batter update', () => {
    updateBatter(7);
    expect(mockClient.send).toHaveBeenCalledWith(
      expect.objectContaining({
        destinationName: 'marquee/template/gmonster/batter',
        payloadString: '7'
      })
    );
  });

  test('updateBase sends base update', () => {
    updateBase('first', true);
    expect(mockClient.send).toHaveBeenCalledWith(
      expect.objectContaining({
        destinationName: 'marquee/template/gmonster/bases/first',
        payloadString: 'true'
      })
    );
  });

  test('updateGame sends game status', () => {
    updateGame('active');
    expect(mockClient.send).toHaveBeenCalledWith(
      expect.objectContaining({
        destinationName: 'marquee/template/gmonster/game',
        payloadString: 'active'
      })
    );
  });

  test('updateCount sends count update', () => {
    updateCount('balls', 2);
    expect(mockClient.send).toHaveBeenCalledWith(
      expect.objectContaining({
        destinationName: 'marquee/template/gmonster/count/balls',
        payloadString: '2'
      })
    );
  });

  test('updateInning sends inning update', () => {
    updateInning(5, 'top');
    expect(mockClient.send).toHaveBeenCalledWith(
      expect.objectContaining({
        destinationName: 'marquee/template/gmonster/inning/5',
        payloadString: 'top'
      })
    );
  });

  test('disableWin sends win disable status', () => {
    disableWin(true);
    expect(mockClient.send).toHaveBeenCalledWith(
      expect.objectContaining({
        destinationName: 'marquee/template/gmonster/disable-win',
        payloadString: true
      })
    );
  });

  test('disableClose sends close disable status', () => {
    disableClose(false);
    expect(mockClient.send).toHaveBeenCalledWith(
      expect.objectContaining({
        destinationName: 'marquee/template/gmonster/disable-close',
        payloadString: false
      })
    );
  });

  test('sendMlbGame logs message (placeholder)', () => {
    const consoleSpy = jest.spyOn(console, 'log').mockImplementation();
    sendMlbGame('12345');
    expect(consoleSpy).toHaveBeenCalledWith('Send MLB game 12345 - not fully implemented in web');
    consoleSpy.mockRestore();
  });

  test('sendNhlGame logs message (placeholder)', () => {
    const consoleSpy = jest.spyOn(console, 'log').mockImplementation();
    sendNhlGame('67890');
    expect(consoleSpy).toHaveBeenCalledWith('Send NHL game 67890 - not fully implemented in web');
    consoleSpy.mockRestore();
  });

  test('sendNflGame logs message (placeholder)', () => {
    const consoleSpy = jest.spyOn(console, 'log').mockImplementation();
    sendNflGame('11111');
    expect(consoleSpy).toHaveBeenCalledWith('Send NFL game 11111 - not fully implemented in web');
    consoleSpy.mockRestore();
  });

  test('sendElection logs message (placeholder)', () => {
    const consoleSpy = jest.spyOn(console, 'log').mockImplementation();
    sendElection();
    expect(consoleSpy).toHaveBeenCalledWith('Send election - not fully implemented in web');
    consoleSpy.mockRestore();
  });

  test('reconnect calls client connect', () => {
    reconnect();
    expect(mockClient.connect).toHaveBeenCalled();
  });
});
