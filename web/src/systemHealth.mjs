// systemHealth.mjs - System health monitoring and diagram management
// Uses Mermaid liveUpdate for dynamic diagram updates

// Health status colors (Mermaid format)
const STATUS_COLORS = {
    healthy: '#059669',
    warning: '#d97706', 
    error: '#dc2626',
    unknown: '#6b7280'
};

// Default fill color
const DEFAULT_FILL = '#f4f4f4';

// Map server component names to node IDs in diagram
const componentMap = {
    'web': 'WebServer',
    'launcher': 'Launcher', 
    'matrix': 'Matrix',
    'mqtt': 'MQTT',
    'grafana': 'Grafana'
};

// Base diagram definition
const baseDiagram = `graph LR
    Browser[Browser] --> WebServer(Web Server)
    WebServer --> MQTT(MQTT Broker)
    MQTT --> Matrix(Matrix)
    WebServer --> Launcher(Launcher)
    WebServer --> Grafana(Grafana)`;

// Current diagram with status colors
let currentDiagram = baseDiagram;

// Update the Mermaid diagram with new colors
async function updateDiagram(healthData) {
    // Default all to unknown first
    let webStatus = 'unknown';
    let launcherStatus = 'unknown';
    let matrixStatus = 'unknown';
    let mqttStatus = 'unknown';
    let grafanaStatus = 'unknown';
    
    // Web is always healthy (the server is running!)
    webStatus = 'healthy';
    
    // Update from health data if available
    if (healthData && healthData.components) {
        const components = healthData.components;
        
        if (components.launcher) {
            launcherStatus = components.launcher.status || 'unknown';
        }
        if (components.matrix) {
            matrixStatus = components.matrix.status || 'unknown';
        }
        if (components.mqtt) {
            mqttStatus = components.mqtt.status || 'unknown';
        }
        if (components.grafana) {
            grafanaStatus = components.grafana.status || 'unknown';
        }
    }
    
    // Create class definitions with fill colors
    const statuses = {
        WebServer: webStatus,
        Launcher: launcherStatus,
        Matrix: matrixStatus,
        MQTT: mqttStatus,
        Grafana: grafanaStatus,
        Browser: 'healthy'
    };
    
    // Build the diagram with inline styles
    let diagram = `graph LR
    classDef default fill:${DEFAULT_FILL},stroke:#333,stroke-width:1px\n`;
    
    // Add class definitions for each node with status color
    for (const [node, status] of Object.entries(statuses)) {
        const color = STATUS_COLORS[status] || STATUS_COLORS.unknown;
        diagram += `    classDef ${node} fill:${color},stroke:${color},color:white\n`;
    }
    
    // Add node definitions
    diagram += `    Browser[Browser]\n`;
    diagram += `    WebServer(Web Server)\n`;
    diagram += `    MQTT(MQTT Broker)\n`;
    diagram += `    Matrix(Matrix)\n`;
    diagram += `    Launcher(Launcher)\n`;
    diagram += `    Grafana(Grafana)\n`;
    
    // Add relationships
    diagram += `    Browser --> WebServer\n`;
    diagram += `    WebServer --> MQTT\n`;
    diagram += `    MQTT --> Matrix\n`;
    diagram += `    WebServer --> Launcher\n`;
    diagram += `    WebServer --> Grafana\n`;
    
    // Apply classes
    for (const [node, status] of Object.entries(statuses)) {
        diagram += `    class ${node} ${node}\n`;
    }
    
    try {
        const { svg } = await mermaid.render('health-diagram', diagram);
        const container = document.getElementById('diagram-container');
        if (container) {
            container.innerHTML = svg;
        }
    } catch (error) {
        console.error('Error rendering diagram:', error);
    }
}

// Initialize health monitoring
export async function initSystemHealth() {
    const container = document.getElementById('diagram-container');
    if (!container) {
        console.log('Diagram container not found');
        return;
    }
    
    // Render initial diagram
    await updateDiagram(null);
    
    // Fetch and update health every 30 seconds
    async function fetchAndUpdate() {
        try {
            const response = await fetch('/system/health', {
                method: 'GET',
                headers: { 
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                credentials: 'same-origin',
                signal: AbortSignal.timeout(10000)
            });
            
            if (response.ok) {
                const data = await response.json();
                await updateDiagram(data);
            }
        } catch (error) {
            console.error('Health fetch error:', error);
            await updateDiagram(null);
        }
    }
    
    // Initial fetch
    setTimeout(fetchAndUpdate, 1000);
    
    // Periodic updates
    setInterval(fetchAndUpdate, 30000);
}

// Export
export { updateDiagram };
