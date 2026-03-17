// Admin page specific JavaScript
import { showAlert as commonShowAlert } from './common.mjs';

// ============================================
// Registration Status
// ============================================

/**
 * Load current registration status
 */
export async function loadRegistrationStatus() {
    try {
        const response = await fetch('/api/admin/registration-status');
        const data = await response.json();
        document.getElementById('registration-toggle').checked = data.enabled;
        updateStatusMessage(data.enabled);
    } catch (e) {
        console.error('Error loading registration status:', e);
        showAlert('Error loading registration status', 'error');
    }
}

/**
 * Update status message
 */
function updateStatusMessage(enabled) {
    const messageEl = document.getElementById('status-message');
    if (messageEl) {
        if (enabled) {
            messageEl.textContent = 'New user registrations are currently enabled';
            messageEl.style.color = 'var(--success-color)';
        } else {
            messageEl.textContent = 'New user registrations are currently disabled';
            messageEl.style.color = 'var(--error-color)';
        }
    }
}

/**
 * Handle registration toggle change
 */
export async function handleRegistrationToggle(checkbox) {
    const enabled = checkbox.checked;
    try {
        const response = await fetch('/api/admin/registration-status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled })
        });

        if (response.ok) {
            updateStatusMessage(enabled);
            showAlert(`Registrations ${enabled ? 'enabled' : 'disabled'} successfully`, 'success');
        } else {
            // Revert toggle on error
            checkbox.checked = !enabled;
            const error = await response.json();
            showAlert(error.error || 'Failed to update registration status', 'error');
        }
    } catch (e) {
        // Revert toggle on error
        checkbox.checked = !enabled;
        console.error('Error updating registration status:', e);
        showAlert('Error updating registration status', 'error');
    }
}

// ============================================
// Users List
// ============================================

/**
 * Load users list
 */
export async function loadUsers() {
    try {
        const response = await fetch('/api/admin/users');
        const data = await response.json();
        displayUsers(data.users);
    } catch (e) {
        console.error('Error loading users:', e);
        const usersListEl = document.getElementById('users-list');
        if (usersListEl) {
            usersListEl.innerHTML = '<p style="color: var(--error-color);">Error loading users</p>';
        }
    }
}

/**
 * Display users in the UI
 */
function displayUsers(users) {
    const usersListEl = document.getElementById('users-list');
    if (!usersListEl) return;

    if (users.length === 0) {
        usersListEl.innerHTML = '<p>No registered users found.</p>';
        return;
    }

    const usersHtml = users.map(user => `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 0.375rem; margin-bottom: 0.5rem; background: var(--card-bg);">
            <div>
                <strong>${user.username}</strong>
                <br>
                <small style="color: var(--text-secondary);">
                    ${user.credential_count} credential${user.credential_count !== 1 ? 's' : ''}
                </small>
            </div>
            <div style="display: flex; align-items: center;">
                ${user.has_credentials ?
                    '<span style="color: var(--success-color); margin-right: 0.5rem;"><i class="fas fa-check-circle"></i></span>' :
                    '<span style="color: var(--error-color); margin-right: 0.5rem;"><i class="fas fa-times-circle"></i></span>'
                }
            </div>
        </div>
    `).join('');

    usersListEl.innerHTML = usersHtml;
}

// ============================================
// MQTT Allowlist
// ============================================

/**
 * Load MQTT allowlist
 */
export async function loadMqttAllowlist() {
    try {
        const response = await fetch('/api/admin/mqtt-allowlist');
        const data = await response.json();
        displayMqttAllowlist(data.mqtt_allowlist || []);
    } catch (e) {
        console.error('Error loading MQTT allowlist:', e);
        const allowlistEl = document.getElementById('mqtt-allowlist');
        if (allowlistEl) {
            allowlistEl.innerHTML = '<p style="color: var(--error-color);">Error loading allowlist</p>';
        }
    }
}

/**
 * Display MQTT allowlist in the UI
 */
function displayMqttAllowlist(allowlist) {
    const allowlistEl = document.getElementById('mqtt-allowlist');
    if (!allowlistEl) return;

    if (allowlist.length === 0) {
        allowlistEl.innerHTML = '<p style="color: var(--text-secondary);">No IP addresses in allowlist</p>';
        return;
    }

    const allowlistHtml = allowlist.map(ip => `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 0.375rem; margin-bottom: 0.5rem; background: var(--card-bg);">
            <div>
                <i class="fas fa-desktop" style="margin-right: 8px; color: var(--primary-color);"></i>
                <strong>${ip}</strong>
            </div>
            <button onclick="removeIpAddress('${ip}')" style="padding: 6px 12px; background: transparent; color: var(--error-color); border: 1px solid var(--error-color); border-radius: 4px; cursor: pointer; font-size: 0.85rem;">
                <i class="fas fa-trash"></i> Remove
            </button>
        </div>
    `).join('');

    allowlistEl.innerHTML = allowlistHtml;
}

/**
 * Add IP address to allowlist
 */
export async function addIpAddress() {
    const ipInput = document.getElementById('mqtt-ip-input');
    if (!ipInput) return;
    
    const ipAddress = ipInput.value.trim();

    if (!ipAddress) {
        showAlert('Please enter an IP address', 'error');
        return;
    }

    try {
        const response = await fetch('/api/admin/mqtt-allowlist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'add', ip_address: ipAddress })
        });

        const data = await response.json();

        if (response.ok) {
            ipInput.value = '';
            displayMqttAllowlist(data.mqtt_allowlist);
            showAlert('IP address added successfully', 'success');
        } else {
            showAlert(data.error || 'Failed to add IP address', 'error');
        }
    } catch (e) {
        console.error('Error adding IP address:', e);
        showAlert('Error adding IP address', 'error');
    }
}

/**
 * Remove IP address from allowlist
 */
export async function removeIpAddress(ipAddress) {
    try {
        const response = await fetch('/api/admin/mqtt-allowlist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'remove', ip_address: ipAddress })
        });

        const data = await response.json();

        if (response.ok) {
            displayMqttAllowlist(data.mqtt_allowlist);
            showAlert('IP address removed successfully', 'success');
        } else {
            showAlert(data.error || 'Failed to remove IP address', 'error');
        }
    } catch (e) {
        console.error('Error removing IP address:', e);
        showAlert('Error removing IP address', 'error');
    }
}

// ============================================
// Alert System
// ============================================

/**
 * Show an alert message (wraps common.mjs showAlert)
 */
export function showAlert(message, type) {
    commonShowAlert(message, type);
}

// Make functions globally available for onclick handlers
window.addIpAddress = addIpAddress;
window.removeIpAddress = removeIpAddress;

// ============================================
// Initialize Admin Page
// ============================================

/**
 * Initialize admin page
 */
export function initAdmin() {
    // Load status on page load
    loadRegistrationStatus();
    loadUsers();
    loadMqttAllowlist();

    // Set up registration toggle handler
    const registrationToggle = document.getElementById('registration-toggle');
    if (registrationToggle) {
        registrationToggle.addEventListener('change', function() {
            handleRegistrationToggle(this);
        });
    }

    // Set up IP input enter key handler
    const ipInput = document.getElementById('mqtt-ip-input');
    if (ipInput) {
        ipInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                addIpAddress();
            }
        });
    }
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initAdmin);
