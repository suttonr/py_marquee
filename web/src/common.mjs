// Common JavaScript functionality shared across all non-login pages

// ============================================
// Hamburger Menu Functionality
// ============================================

/**
 * Toggle the hamburger menu open/closed
 */
export function toggleMenu() {
    const menuOverlay = document.getElementById('menuOverlay');
    const menuBackdrop = document.getElementById('menuBackdrop');
    menuOverlay.classList.toggle('open');
    menuBackdrop.classList.toggle('open');
}

// Make toggleMenu globally available
window.toggleMenu = toggleMenu;

// ============================================
// Dark Mode Functionality
// ============================================

/**
 * Initialize dark mode functionality
 * Call this from page-specific init code
 */
export function initDarkMode() {
    const darkModeToggle = document.getElementById('dark-mode');
    if (!darkModeToggle) return;

    // Load saved theme
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        darkModeToggle.checked = true;
    }

    // Listen for toggle changes
    darkModeToggle.addEventListener('change', function() {
        if (this.checked) {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.removeAttribute('data-theme');
            localStorage.setItem('theme', 'light');
        }
    });
}

/**
 * Apply saved theme without requiring a toggle element
 */
export function applySavedTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
    }
}

// ============================================
// Connection Status Functionality
// ============================================

/**
 * Update the connection status indicator
 * @param {boolean} connected - Whether the connection is active
 */
export function updateConnectionStatus(connected) {
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

// ============================================
// Logging Functionality
// ============================================

let logInitialized = false;

/**
 * Initialize the logging system
 * Call this from page-specific init code
 */
export function initLogging() {
    if (logInitialized) return;
    
    const logContent = document.getElementById('logContent');
    if (!logContent) return;

    const originalLog = console.log;
    console.log = function(...args) {
        const message = args.join(' ');
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        logContent.appendChild(entry);
        logContent.scrollTop = logContent.scrollHeight;
        originalLog.apply(console, args);
    };
    
    logInitialized = true;
}

/**
 * Clear the log content
 */
export function clearLog() {
    const logContent = document.getElementById('logContent');
    if (logContent) {
        logContent.innerHTML = '';
    }
}

// ============================================
// Alert System
// ============================================

/**
 * Show an alert message
 * @param {string} message - The message to display
 * @param {string} type - 'success' or 'error'
 */
export function showAlert(message, type) {
    // Create alert element
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 16px;
        border-radius: 8px;
        font-size: 14px;
        z-index: 1000;
        max-width: 300px;
    `;

    if (type === 'success') {
        alert.style.backgroundColor = 'rgba(16, 185, 129, 0.1)';
        alert.style.color = '#10b981';
        alert.style.border = '1px solid rgba(16, 185, 129, 0.2)';
    } else if (type === 'error') {
        alert.style.backgroundColor = 'rgba(239, 68, 68, 0.1)';
        alert.style.color = '#ef4444';
        alert.style.border = '1px solid rgba(239, 68, 68, 0.2)';
    }

    alert.textContent = message;
    document.body.appendChild(alert);

    // Auto-hide after 3 seconds
    setTimeout(() => {
        alert.remove();
    }, 3000);
}

// ============================================
// Tab Switching Functionality
// ============================================

/**
 * Initialize tab switching
 * Call this from page-specific init code
 */
export function initTabs() {
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;

            // Update tab buttons
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');

            // Update tab content
            document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
            const targetPane = document.getElementById(tabName);
            if (targetPane) {
                targetPane.classList.add('active');
            }
        });
    });
}

// ============================================
// Navigation Menu HTML Template
// ============================================

/**
 * Get the navigation menu HTML
 * @param {string} currentPage - The current page filename (e.g., 'index.html')
 * @returns {string} HTML string for the navigation menu
 */
export function getNavigationHtml(currentPage) {
    const pages = [
        { href: 'index.html', icon: 'fa-home', label: 'Home' },
        { href: 'controler.html', icon: 'fa-tv', label: 'Marquee Control' },
        { href: 'launcher.html', icon: 'fa-rocket', label: 'Launcher' },
        { href: 'grafana.html', icon: 'fa-arrow-trend-up', label: 'Grafana' },
        { href: 'admin.html', icon: 'fa-cog', label: 'Administration' }
    ];

    const navItems = pages.map(page => {
        const isActive = page.href === currentPage ? 'active' : '';
        return `
            <a href="${page.href}" class="menu-item ${isActive}">
                <i class="fas ${page.icon}"></i>
                <span>${page.label}</span>
            </a>
        `;
    }).join('');

    // Add logout item
    const logoutItem = `
        <a href="/logout" class="menu-item">
            <i class="fas fa-sign-out-alt"></i>
            <span>Logout</span>
        </a>
    `;

    return `
        <!-- Menu Backdrop -->
        <div class="menu-backdrop" id="menuBackdrop" onclick="toggleMenu()"></div>
        
        <!-- Menu Overlay -->
        <div class="menu-overlay" id="menuOverlay">
            <div class="menu-header">
                <h2>Navigation</h2>
            </div>
            <nav class="menu-items">
                ${navItems}
                ${logoutItem}
            </nav>
        </div>
    `;
}

/**
 * Get the header HTML
 * @param {string} title - The page title
 * @param {string} icon - Font Awesome icon class (e.g., 'fa-tv')
 * @param {boolean} showStatus - Whether to show connection status
 * @param {boolean} showRefresh - Whether to show refresh controls
 * @returns {string} HTML string for the header
 */
export function getHeaderHtml(title, icon, showStatus = false, showRefresh = false) {
    let rightControls = '';

    if (showRefresh) {
        rightControls += `
            <i class="fas fa-sync refresh-icon" id="manual-refresh" title="Manual Refresh"></i>
            <div class="refresh-control">
                <select id="refresh-interval">
                    <option value="0">Off</option>
                    <option value="5">5s</option>
                    <option value="10">10s</option>
                    <option value="30" selected>30s</option>
                    <option value="60">60s</option>
                </select>
            </div>
        `;
    }

    if (showStatus) {
        rightControls += `
            <div class="status">
                <span class="status-dot" id="statusDot"></span>
                <span id="statusText">Connecting...</span>
            </div>
        `;
    }

    return `
        <div class="header">
            <div class="hamburger-menu">
                <button class="hamburger-btn" id="hamburgerBtn" onclick="toggleMenu()" aria-label="Toggle menu">
                    <span></span>
                    <span></span>
                    <span></span>
                </button>
                <h1><i class="fas ${icon}"></i> ${title}</h1>
            </div>
            <div class="right-controls">
                ${rightControls}
            </div>
        </div>
    `;
}

// ============================================
// Common Initialization
// ============================================

/**
 * Initialize all common functionality
 * Call this from page-specific init code
 */
export function initCommon() {
    initDarkMode();
    initLogging();
    initTabs();
}
