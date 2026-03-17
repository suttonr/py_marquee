// Launcher page specific JavaScript
import { updateConnectionStatus, initLogging, clearLog } from './common.mjs';

// Configuration - use API proxy through the web server
const LAUNCHER_API_BASE = window.location.protocol + '//' + window.location.hostname + ':' + window.location.port  + '/api/launcher';

// ============================================
// API Helper Functions
// ============================================

/**
 * Make an API call
 */
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${LAUNCHER_API_BASE}${endpoint}`, options);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        console.log(`API Error: ${error.message}`);
        throw error;
    }
}

// ============================================
// Status Functions
// ============================================

/**
 * Load health status
 */
export async function loadHealthStatus() {
    try {
        const health = await apiCall('/health');
        document.getElementById('health-status').innerHTML = `
            <p><strong>Status:</strong> ${health.status}</p>
            <p><strong>Active Watchers:</strong> ${health.active_watchers}</p>
        `;
        updateConnectionStatus(true);
    } catch (error) {
        document.getElementById('health-status').innerHTML = `
            <p style="color: var(--error-color);"><strong>Error:</strong> ${error.message}</p>
        `;
        updateConnectionStatus(false);
    }
}

/**
 * Load watching status
 */
export async function loadWatchingStatus() {
    try {
        const watching = await apiCall('/games/watching');
        const watchingList = watching.watching_games;
        if (watchingList.length === 0) {
            document.getElementById('watching-status').innerHTML = '<p>No games currently being watched.</p>';
        } else {
            document.getElementById('watching-status').innerHTML = `
                <p><strong>Watching ${watchingList.length} game(s):</strong></p>
                <div class="watching-list">
                    ${watchingList.map(gamePk => `
                        <div class="watching-item" style="padding: 0.5rem; border: 1px solid var(--border-color); border-radius: 0.25rem; margin-bottom: 0.5rem; background: var(--card-bg);">
                            <div style="margin-bottom: 0.5rem;">
                                <strong>Game ${gamePk}</strong>
                            </div>
                            <div style="display: flex; gap: 0.5rem;">
                                <button class="btn btn-primary btn-sm" onclick="backfillCurrentGame()">
                                    <i class="fas fa-history"></i> Backfill
                                </button>
                                <button class="btn btn-danger btn-sm" onclick="stopWatching(${gamePk})">
                                    <i class="fas fa-stop"></i> Stop
                                </button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }
    } catch (error) {
        document.getElementById('watching-status').innerHTML = `
            <p style="color: var(--error-color);"><strong>Error:</strong> ${error.message}</p>
        `;
    }
}

/**
 * Helper function to format time until next game
 */
function formatTimeUntil(seconds) {
    if (seconds === null || seconds === undefined) {
        return 'No upcoming games';
    }
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
}

/**
 * Load finders status
 */
export async function loadFindersStatus() {
    try {
        const finders = await apiCall('/games/finders');
        const findersList = finders.active_finders;
        if (findersList.length === 0) {
            document.getElementById('finders-status').innerHTML = '<p>No active finders.</p>';
        } else {
            document.getElementById('finders-status').innerHTML = `
                <p><strong>${findersList.length} active finder(s):</strong></p>
                <div class="finder-list">
                    ${findersList.map(finder => `
                        <div class="finder-item" style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem; border: 1px solid var(--border-color); border-radius: 0.25rem; margin-bottom: 0.5rem; background: var(--card-bg);">
                            <div>
                                <strong>Finder ${finder.team_filter}</strong><br>
                                <small>Team: ${finder.team_filter || 'All'} | Interval: ${finder.sleep_minutes}min | Priority: ${finder.priority || 0} | Auto-launch: ${finder.auto_launch ? 'Yes' : 'No'}<br>
                                Next Game: ${formatTimeUntil(finder.time_until_next_game)} | Running: ${Math.floor(finder.runtime_seconds / 60)}m ${Math.floor(finder.runtime_seconds % 60)}s</small>
                            </div>
                            <button class="btn btn-danger btn-sm" onclick="stopFinder(${finder.finder_id})">
                                <i class="fas fa-stop"></i> Stop
                            </button>
                        </div>
                    `).join('')}
                </div>
            `;
        }
    } catch (error) {
        document.getElementById('finders-status').innerHTML = `
            <p style="color: var(--error-color);"><strong>Error:</strong> ${error.message}</p>
        `;
    }
}

// ============================================
// Schedule Functions
// ============================================

/**
 * Load schedule
 */
export async function loadSchedule() {
    const teamFilter = document.getElementById('team-filter').value.trim();
    const params = new URLSearchParams();
    if (teamFilter) {
        params.append('team_filter', teamFilter);
    }

    try {
        const schedule = await apiCall(`/schedule?${params}`);
        displayGames(schedule.games);
        console.log(`Loaded ${schedule.games.length} games`);
    } catch (error) {
        document.getElementById('game-list').innerHTML = `
            <p style="color: var(--error-color);">Error loading schedule: ${error.message}</p>
        `;
    }
}

/**
 * Display games in the UI
 */
function displayGames(games) {
    const gameList = document.getElementById('game-list');
    if (games.length === 0) {
        gameList.innerHTML = '<p>No games found for today.</p>';
        return;
    }

    gameList.innerHTML = games.map(game => `
        <div class="game-item">
            <div class="game-info">
                <div class="game-time">${new Date(game.gameDate).toLocaleTimeString()}</div>
                <div class="game-teams">${game.awayTeam} vs ${game.homeTeam}</div>
                <div class="game-status">${game.hoursUntil > 0 ? `${game.hoursUntil.toFixed(1)} hours until start` : 'Starting soon!'}</div>
            </div>
            <div class="game-actions">
                <button class="btn btn-primary btn-sm" onclick="watchGame(${game.gamePk})">
                    <i class="fas fa-play"></i> Watch
                </button>
            </div>
        </div>
    `).join('');
}

// ============================================
// Control Functions
// ============================================

/**
 * Start watching a game
 */
export async function startWatching() {
    const gamePk = document.getElementById('watch-game-pk').value.trim();
    const interval = document.getElementById('watch-interval').value;
    const priority = document.getElementById('watch-priority').value;

    if (!gamePk) {
        alert('Please enter a game PK');
        return;
    }

    try {
        const result = await apiCall('/games/' + gamePk + '/watch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                interval: parseInt(interval),
                priority: parseInt(priority)
            })
        });
        console.log(result.message + ` (Priority: ${result.priority})`);
        loadWatchingStatus();
    } catch (error) {
        console.log(`Error: ${error.message}`);
    }
}

/**
 * Watch a game from schedule
 */
export async function watchGame(gamePk, priority = 0) {
    try {
        const result = await apiCall('/games/' + gamePk + '/watch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                interval: 20,
                priority: priority
            })
        });
        console.log(result.message + ` (Priority: ${result.priority})`);
        loadWatchingStatus();
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

/**
 * Start game finder
 */
export async function startGameFinder() {
    const teamFilter = document.getElementById('finder-team-filter').value.trim();
    const sleepMinutes = document.getElementById('finder-sleep-minutes').value;
    const autoLaunch = document.getElementById('finder-auto-launch').checked;
    const priority = document.getElementById('finder-priority').value;

    try {
        const result = await apiCall('/games/find', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                team_filter: teamFilter || null,
                sleep_minutes: parseInt(sleepMinutes),
                auto_launch: autoLaunch,
                priority: parseInt(priority)
            })
        });
        console.log(result.message + ` (Priority: ${result.priority})`);
        loadFindersStatus();
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

/**
 * Stop a finder
 */
export async function stopFinder(finderId) {
    try {
        const result = await apiCall('/games/finders/' + finderId + '/stop', {
            method: 'POST'
        });
        console.log(result.message);
        loadFindersStatus();
    } catch (error) {
        alert(`Error stopping finder: ${error.message}`);
    }
}

/**
 * Stop all watching
 */
export async function stopAllWatching() {
    try {
        // Get list of watching games
        const watching = await apiCall('/games/watching');
        const promises = watching.watching_games.map(gamePk =>
            apiCall('/games/' + gamePk + '/stop', { method: 'POST' })
        );

        await Promise.all(promises);
        console.log('Stopped all watching games');
        loadWatchingStatus();
    } catch (error) {
        alert(`Error stopping games: ${error.message}`);
    }
}

/**
 * Stop all finders
 */
export async function stopAllFinders() {
    try {
        const result = await apiCall('/games/finders/stop-all', {
            method: 'POST'
        });
        console.log(result.message);
        loadFindersStatus();
    } catch (error) {
        alert(`Error stopping finders: ${error.message}`);
    }
}

/**
 * Stop watching a specific game
 */
export async function stopWatching(gamePk) {
    try {
        const result = await apiCall('/games/' + gamePk + '/stop', {
            method: 'POST'
        });
        console.log(result.message);
        loadWatchingStatus();
    } catch (error) {
        alert(`Error stopping game ${gamePk}: ${error.message}`);
    }
}

/**
 * Backfill current game
 */
export async function backfillCurrentGame() {
    try {
        const result = await apiCall('/backfill', {
            method: 'POST'
        });
        console.log(result.message);
    } catch (error) {
        alert(`Error performing backfill: ${error.message}`);
    }
}

// Make functions globally available for onclick handlers
window.loadSchedule = loadSchedule;
window.startWatching = startWatching;
window.watchGame = watchGame;
window.startGameFinder = startGameFinder;
window.stopFinder = stopFinder;
window.stopAllWatching = stopAllWatching;
window.stopAllFinders = stopAllFinders;
window.stopWatching = stopWatching;
window.backfillCurrentGame = backfillCurrentGame;
window.clearLog = clearLog;

// ============================================
// Auto-refresh
// ============================================

let refreshIntervalId = null;

/**
 * Start auto-refresh of status
 */
function startStatusAutoRefresh() {
    if (refreshIntervalId) {
        clearInterval(refreshIntervalId);
    }
    refreshIntervalId = setInterval(async () => {
        await loadHealthStatus();
        await loadWatchingStatus();
        await loadFindersStatus();
    }, 30000);
}

/**
 * Initialize launcher page
 */
export function initLauncher() {
    // Initialize logging first
    initLogging();
    
    // Initial load
    loadHealthStatus();
    loadWatchingStatus();
    loadFindersStatus();

    // Auto-refresh status every 30 seconds
    startStatusAutoRefresh();
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initLauncher);
