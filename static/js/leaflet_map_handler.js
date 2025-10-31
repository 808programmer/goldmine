// Leaflet map handler for GoldMine AI
// This replaces the Mapbox implementation with Leaflet

console.log('🗺️ Loading Leaflet Map Handler...');

// Global variables
let currentMap = null;
let intelligentCoordinatesLayer = null;
let intelligentCoordinatesData = [];

// Initialize map when DOM is ready (guard against double init), or immediately if DOM is already ready
function __initLeafletOnce() {
    if (window.__leafletMapInited) {
        console.log('Leaflet map already initialized (guard)');
        return;
    }
    console.log('DOM ready/already ready, initializing Leaflet map...');
    console.log('Document readyState:', document.readyState);
    console.log('Leaflet available:', typeof L !== 'undefined');
    
    // Wait a bit for Leaflet to load if it's not ready
    if (typeof L === 'undefined') {
        console.log('Waiting for Leaflet to load...');
        setTimeout(__initLeafletOnce, 200);
        return;
    }
    
    initializeMap();
}

// Try multiple times to catch Leaflet when it loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', __initLeafletOnce);
} else {
    __initLeafletOnce();
}

// Also try after a delay in case scripts load out of order
setTimeout(function() {
    if (!window.__leafletMapInited && typeof L !== 'undefined') {
        console.log('Delayed init: Leaflet loaded, initializing...');
        __initLeafletOnce();
    }
}, 500);

function initializeMap() {
    console.log('Initializing Leaflet map...');
    
    // Prevent double-initialization
    if (window.__leafletMapInited || currentMap) {
        console.log('Map already initialized, skipping');
        return;
    }

    // Check if map container exists
    const mapContainer = document.getElementById('map-container-2d');
    if (!mapContainer) {
        console.error('❌ Map container #map-container-2d not found');
        return;
    }
    
    // Check if Leaflet is loaded
    if (typeof L === 'undefined') {
        console.error('❌ Leaflet is not loaded - waiting for script...');
        mapContainer.innerHTML = '<div class="map-error">Error: Leaflet map library failed to load. Please refresh the page.</div>';
        // Retry after a short delay in case Leaflet is still loading
        setTimeout(function() {
            if (typeof L !== 'undefined' && !window.__leafletMapInited) {
                console.log('🔄 Retrying map initialization after Leaflet load...');
                initializeMap();
            }
        }, 500);
        return;
    }
    
    console.log('✅ Leaflet loaded, initializing map...');
    
    try {
        // Clear any loading/error messages first
        mapContainer.innerHTML = '';
        
        // Initialize map centered on Guyana
        currentMap = L.map('map-container-2d').setView([5.0, -58.5], 7);
        
        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(currentMap);
        
        // Add scale control
        L.control.scale().addTo(currentMap);
        
        // Initialize intelligent coordinates layer
        intelligentCoordinatesLayer = L.layerGroup().addTo(currentMap);
        
        console.log('✅ Leaflet map initialized successfully');
        window.__leafletMapInited = true;

        // Ensure map renders if container size was zero at init
        setTimeout(function(){
            try { 
                currentMap.invalidateSize(); 
                console.log('✅ Map size invalidated');
            } catch(e) {
                console.error('Error invalidating size:', e);
            }
        }, 100);
        
        // Load initial data
        loadInitialMapData();
        
    } catch (error) {
        console.error('❌ Error initializing map:', error);
        mapContainer.innerHTML = '<div class="map-error">Error initializing map: ' + error.message + '</div>';
    }
}

function loadInitialMapData() {
    console.log('Loading initial map data...');
    
    // Load geological features
    loadGeologicalFeatures();
    
    // Load any existing intelligent coordinates
    loadIntelligentCoordinates();
}

function loadGeologicalFeatures() {
    console.log('Loading geological features...');
    
    fetch('/api/geological-surveys/')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.surveys && data.surveys.length > 0) {
                addGeologicalFeaturesToMap(data.surveys);
            } else {
                console.log('No geological features available');
            }
        })
        .catch(error => {
            console.error('Error loading geological features:', error);
        });
}

function addGeologicalFeaturesToMap(features) {
    if (!currentMap) return;
    
    console.log(`Adding ${features.length} geological features to map`);
    
    features.forEach(feature => {
        if (feature.latitude && feature.longitude) {
            const marker = L.circleMarker([feature.latitude, feature.longitude], {
                radius: 6,
                fillColor: '#00ff00',
                color: '#ffffff',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.9
            });
            
            marker.bindPopup(`
                <h3><strong>${feature.name || 'Geological Feature'}</strong></h3>
                <p><strong>Type:</strong> ${feature.feature_type || 'Unknown'}</p>
                <p><strong>Confidence:</strong> ${feature.confidence_score || 'Unknown'}</p>
                <p><strong>Description:</strong> ${feature.description || 'No description available'}</p>
            `);
            
            marker.addTo(currentMap);
        }
    });
}

function loadIntelligentCoordinates() {
    console.log('Loading intelligent coordinates...');
    
    fetch('/api/intelligent-coordinates/')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.coordinates && data.coordinates.length > 0) {
                addIntelligentCoordinatesToMap(data.coordinates);
            } else {
                console.log('No intelligent coordinates available');
            }
        })
        .catch(error => {
            console.error('Error loading intelligent coordinates:', error);
        });
}

function addIntelligentCoordinatesToMap(coordinates) {
    console.log('Adding intelligent coordinates to map:', coordinates);
    
    if (!currentMap || !intelligentCoordinatesLayer) {
        console.error('Map or coordinates layer not available');
        return;
    }
    
    // Clear existing coordinates
    intelligentCoordinatesLayer.clearLayers();
    intelligentCoordinatesData = coordinates;
    
    // Add each coordinate as a marker
    coordinates.forEach((coord, index) => {
        const lat = coord.lat || coord.latitude || coord.y;
        const lng = coord.lng || coord.longitude || coord.x;
        
        if (!lat || !lng) {
            console.error(`Invalid coordinates for point ${index + 1}:`, coord);
            return;
        }
        
        // Create a color based on confidence level
        const color = getColorByConfidence(coord.confidence);
        
        const marker = L.circleMarker([lat, lng], {
            radius: 8,
            fillColor: color,
            color: '#ffffff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.8
        });
        
        // Add popup with coordinate data
        marker.bindPopup(`
            <h3><strong>${coord.name || 'Geological Point'}</strong></h3>
            <p><strong>Formation:</strong> ${coord.formation || 'Unknown'}</p>
            <p><strong>Minerals:</strong> ${(coord.minerals || []).join(', ') || 'Unknown'}</p>
            <p><strong>Confidence:</strong> ${coord.confidence || 'Unknown'}</p>
            <p><strong>Description:</strong> ${coord.description || 'No description available'}</p>
        `);
        
        marker.addTo(intelligentCoordinatesLayer);
    });
    
    // Fit map to show all coordinates
    if (coordinates.length > 0) {
        const bounds = L.latLngBounds(coordinates.map(coord => {
            const lat = coord.lat || coord.latitude || coord.y;
            const lng = coord.lng || coord.longitude || coord.x;
            return [lat, lng];
        }).filter(coord => coord[0] && coord[1]));
        
        if (bounds.isValid()) {
            currentMap.fitBounds(bounds, { padding: [20, 20] });
        }
    }
    
    console.log('✅ Intelligent coordinates added to map');
}

// Generate intelligent coordinates via API (migrated from inline script)
function generateIntelligentCoordinates() {
    console.log('🚀 Generate button clicked!');
    alert('🚀 Generating intelligent coordinates...');

    if (!currentMap) {
        alert('Map not ready yet. Please wait for the map to load.');
        return;
    }

    const numCoordinatesEl = document.getElementById('num-coordinates');
    const confidenceEl = document.getElementById('mapping-confidence');
    const statusEl = document.getElementById('intelligent-mapping-status');

    const numCoordinates = numCoordinatesEl ? numCoordinatesEl.value : 25;
    const confidence = confidenceEl ? confidenceEl.value : 'all';

    console.log('Parameters being sent:', { numCoordinates, confidence });

    if (statusEl) {
        statusEl.innerHTML = `🔄 Generating ${numCoordinates} intelligent coordinates with ${confidence} confidence...`;
    }

    fetch('/api/simple-intelligent-coordinates/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            num_points: parseInt(numCoordinates),
            confidence_filter: confidence
        })
    })
    .then(response => {
        console.log('API Response status:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('API Response data:', data);
        if (data.success) {
            const requested = parseInt(numCoordinates);
            const received = data.coordinates.length;
            const statusMessage = `✅ Generated ${received} intelligent coordinates (requested: ${requested})`;
            if (statusEl) statusEl.innerHTML = statusMessage;
            if (requested !== received) {
                console.warn(`Coordinate count mismatch: requested ${requested}, received ${received}`);
            }
            addIntelligentCoordinatesToMap(data.coordinates);
        } else {
            if (statusEl) statusEl.innerHTML = `❌ Error: ${data.error}`;
            alert(`Error: ${data.error}`);
        }
    })
    .catch(error => {
        console.error('Error generating intelligent coordinates:', error);
        if (statusEl) statusEl.innerHTML = '❌ Error generating coordinates';
        alert('Error generating coordinates. Check console for details.');
    });
}

// Helper to read CSRF cookie (migrated from inline script)
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function getColorByConfidence(confidence) {
    switch(confidence?.toLowerCase()) {
        case 'high':
            return '#ff0000'; // Red - High confidence
        case 'medium':
            return '#ff6600'; // Orange - Medium confidence
        case 'low':
            return '#00ff00'; // Green - Low confidence
        default:
            return '#999999'; // Gray - Unknown confidence
    }
}

function clearIntelligentCoordinates() {
    if (intelligentCoordinatesLayer) {
        intelligentCoordinatesLayer.clearLayers();
        intelligentCoordinatesData = [];
        console.log('Intelligent coordinates cleared');
    }
}

function clearAllCoordinates() {
    clearIntelligentCoordinates();
    // Clear any other coordinate layers if they exist
    console.log('All coordinates cleared');
}

function toggleIntelligentCoordinates() {
    if (intelligentCoordinatesLayer) {
        if (currentMap.hasLayer(intelligentCoordinatesLayer)) {
            currentMap.removeLayer(intelligentCoordinatesLayer);
            console.log('Intelligent coordinates hidden');
        } else {
            currentMap.addLayer(intelligentCoordinatesLayer);
            console.log('Intelligent coordinates shown');
        }
    }
}

function exportIntelligentCoordinatesToGeoJSON() {
    if (intelligentCoordinatesData.length === 0) {
        alert('No intelligent coordinates to export');
        return;
    }
    
    const geojson = {
        type: 'FeatureCollection',
        features: intelligentCoordinatesData.map(coord => ({
            type: 'Feature',
            geometry: {
                type: 'Point',
                coordinates: [coord.lng || coord.longitude || coord.x, coord.lat || coord.latitude || coord.y]
            },
            properties: {
                name: coord.name || 'Geological Point',
                formation: coord.formation || 'Unknown',
                minerals: coord.minerals || [],
                confidence: coord.confidence || 'Unknown',
                description: coord.description || 'No description available'
            }
        }))
    };
    
    const dataStr = JSON.stringify(geojson, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'intelligent_coordinates.geojson';
    link.click();
    URL.revokeObjectURL(url);
    
    console.log('GeoJSON exported');
}

// Test functions
function testButton() {
    console.log('Test button clicked - Leaflet map handler is working!');
    alert('✅ Leaflet map handler is working correctly!');
}

function checkMapStatus() {
    const status = currentMap ? 'Map is initialized' : 'Map is not initialized';
    const leafletStatus = typeof L !== 'undefined' ? 'Leaflet is loaded' : 'Leaflet is not loaded';
    const coordinatesCount = intelligentCoordinatesData.length;
    
    const info = `${status}\n${leafletStatus}\nCoordinates: ${coordinatesCount}`;
    document.getElementById('map-status-info').textContent = info;
    console.log('Map status:', info);
}

console.log('✅ Leaflet Map Handler loaded successfully');

