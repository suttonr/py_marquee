// Index page (Marquee Control) specific JavaScript
import { updateConnectionStatus } from './common.mjs';
import {
    sendTemplate, sendClear, sendBright, sendText, getPixels, reconnect, processPixels,
    sendAutoTemplate, sendBox, sendBgColor, sendFgColor, sendReset, sendTextLine, sendScrollText,
    updateBatter, updateBase, updateGame, updateCount, updateInning, disableWin, disableClose,
    sendMlbGame, sendNhlGame, sendNflGame, sendElection
} from "./mqttHandler.mjs";

// Make functions globally available for onclick handlers
window.sendTemplate = sendTemplate;
window.sendClear = sendClear;
window.sendBright = sendBright;
window.sendText = sendText;
window.getPixels = getPixels;
window.reconnect = reconnect;
window.processPixels = processPixels;
window.sendAutoTemplate = sendAutoTemplate;
window.sendBox = sendBox;
window.sendBgColor = sendBgColor;
window.sendFgColor = sendFgColor;
window.sendReset = sendReset;
window.sendTextLine = sendTextLine;
window.sendScrollText = sendScrollText;
window.updateBatter = updateBatter;
window.updateBase = updateBase;
window.updateGame = updateGame;
window.updateCount = updateCount;
window.updateInning = updateInning;
window.disableWin = disableWin;
window.disableClose = disableClose;
window.sendMlbGame = sendMlbGame;
window.sendNhlGame = sendNhlGame;
window.sendNflGame = sendNflGame;
window.sendElection = sendElection;

// ============================================
// Canvas Functionality
// ============================================

/**
 * Canvas responsive sizing
 */
function resizeCanvas() {
    const canvas = document.getElementById('matrix_canvas');
    const container = document.querySelector('.canvas-container');

    if (window.innerWidth < 768) {
        canvas.width = 448;
        canvas.height = 96;
    } else {
        canvas.width = 896;
        canvas.height = 48;
    }
}

/**
 * Initialize canvas functionality
 */
export function initCanvas() {
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();
}

// ============================================
// Brightness & Pixel Scale
// ============================================

/**
 * Update brightness value display
 */
export function updateBrightnessValue(value) {
    document.getElementById('brightness-value').textContent = value;
}

/**
 * Update pixel scale value display
 */
export function updatePixelScaleValue(value) {
    document.getElementById('pixel-scale-value').textContent = value;
    localStorage.setItem('pixel-scale', value);
    // Refresh canvas to apply new scale
    if (window.pixels) {
        processPixels(JSON.stringify(window.pixels));
    }
}

// ============================================
// Color Picker Functionality
// ============================================

function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : null;
}

function rgbToHex(r, g, b) {
    return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
}

function updateRgbFromColorPicker(colorPickerId, rId, gId, bId) {
    const colorPicker = document.getElementById(colorPickerId);
    const rInput = document.getElementById(rId);
    const gInput = document.getElementById(gId);
    const bInput = document.getElementById(bId);

    colorPicker.addEventListener('input', function() {
        const rgb = hexToRgb(this.value);
        if (rgb) {
            rInput.value = rgb.r;
            gInput.value = rgb.g;
            bInput.value = rgb.b;
        }
    });
}

function updateColorPickerFromRgb(colorPickerId, rId, gId, bId) {
    const colorPicker = document.getElementById(colorPickerId);
    const rInput = document.getElementById(rId);
    const gInput = document.getElementById(gId);
    const bInput = document.getElementById(bId);

    const updateColorPicker = function() {
        const r = parseInt(rInput.value) || 0;
        const g = parseInt(gInput.value) || 0;
        const b = parseInt(bInput.value) || 0;
        colorPicker.value = rgbToHex(r, g, b);
    };

    rInput.addEventListener('input', updateColorPicker);
    gInput.addEventListener('input', updateColorPicker);
    bInput.addEventListener('input', updateColorPicker);
}

/**
 * Initialize color picker functionality
 */
export function initColorPickers() {
    updateRgbFromColorPicker('bg-color-picker', 'bg-r', 'bg-g', 'bg-b');
    updateRgbFromColorPicker('fg-color-picker', 'fg-r', 'fg-g', 'fg-b');
    updateColorPickerFromRgb('bg-color-picker', 'bg-r', 'bg-g', 'bg-b');
    updateColorPickerFromRgb('fg-color-picker', 'fg-r', 'fg-g', 'fg-b');
}

// ============================================
// Auto Refresh Functionality
// ============================================

let refreshIntervalId = null;

function startAutoRefresh(intervalSeconds) {
    if (refreshIntervalId) {
        clearInterval(refreshIntervalId);
    }
    if (intervalSeconds > 0) {
        refreshIntervalId = setInterval(() => {
            console.log(`Auto-refreshing canvas (${intervalSeconds}s interval)`);
            getPixels();
        }, intervalSeconds * 1000);
        console.log(`Auto-refresh enabled: ${intervalSeconds}s`);
    } else {
        console.log('Auto-refresh disabled');
    }
}

function stopAutoRefresh() {
    if (refreshIntervalId) {
        clearInterval(refreshIntervalId);
        refreshIntervalId = null;
        console.log('Auto-refresh stopped');
    }
}

/**
 * Initialize auto refresh functionality
 */
export function initAutoRefresh() {
    // Refresh interval dropdown handler
    const refreshIntervalSelect = document.getElementById('refresh-interval');
    if (refreshIntervalSelect) {
        refreshIntervalSelect.addEventListener('change', function() {
            const intervalSeconds = parseInt(this.value);
            localStorage.setItem('refresh-interval', intervalSeconds);
            startAutoRefresh(intervalSeconds);
        });

        // Manual refresh icon handler
        const manualRefresh = document.getElementById('manual-refresh');
        if (manualRefresh) {
            manualRefresh.addEventListener('click', function() {
                console.log('Manual refresh triggered');
                getPixels();
            });
        }

        // Load saved refresh interval
        const savedRefreshInterval = localStorage.getItem('refresh-interval');
        if (savedRefreshInterval !== null) {
            refreshIntervalSelect.value = savedRefreshInterval;
            startAutoRefresh(parseInt(savedRefreshInterval));
        } else {
            // Initialize with default 30s refresh if no saved value
            startAutoRefresh(30);
        }
    }
}

// ============================================
// Load Saved Settings
// ============================================

/**
 * Load saved pixel scale
 */
export function loadSavedPixelScale() {
    const savedPixelScale = localStorage.getItem('pixel-scale');
    if (savedPixelScale !== null) {
        const pixelScaleSlider = document.getElementById('pixel-scale');
        const pixelScaleValue = document.getElementById('pixel-scale-value');
        if (pixelScaleSlider && pixelScaleValue) {
            pixelScaleSlider.value = savedPixelScale;
            pixelScaleValue.textContent = savedPixelScale;
        }
    }
}

// ============================================
// Auto Template
// ============================================

/**
 * Initialize auto template toggle
 */
export function initAutoTemplate() {
    const autoArgToggle = document.getElementById('auto-arg');
    if (autoArgToggle) {
        autoArgToggle.addEventListener('change', function() {
            sendAutoTemplate(this.checked ? 'true' : 'false');
        });
    }
}

// ============================================
// Connection Status (simulated for now)
// ============================================

/**
 * Initialize connection status check
 */
export function initConnectionStatus() {
    // Check connection status (this would need to be integrated with MQTT handler)
    setTimeout(() => {
        updateConnectionStatus(true); // Assume connected for now
    }, 2000);
}

// ============================================
// Initialize Index Page
// ============================================

/**
 * Initialize all index page functionality
 */
export function initIndex() {
    initCanvas();
    initColorPickers();
    initAutoRefresh();
    loadSavedPixelScale();
    initAutoTemplate();
    initConnectionStatus();
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initIndex);
