// Mapbox configuration and handling for GoldMine AI

// Prevent multiple initializations
if (window.mapsInitialized) {
    console.log('Maps already initialized, skipping...');
} else {
    // Wait for DOM to be ready before initializing
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            if (!window.mapsInitialized) {
                console.log('DOM ready, attempting to initialize maps...');
                initializeMaps();
            }
        });
    } else {
        // DOM is already ready, initialize maps
        console.log('DOM already ready, initializing maps...');
        initializeMaps();
    }
}

function initializeMaps() {
    console.log('initializeMaps function called');
    
    // Check if we're on the maps page
    if (!document.getElementById('map-container-2d')) {
        console.log('Map container not found, skipping map initialization');
        return;
    }
    
    // Check if maps are already initialized
    if (window.map2D) {
        console.log('Map already exists, skipping initialization...');
        return;
    }
    
    // Check if Mapbox is loaded
    if (typeof mapboxgl === 'undefined') {
        console.error('Mapbox GL JS is not loaded. Please check your internet connection and try again.');
        document.getElementById('map-container-2d').innerHTML = '<div class="p-4 text-center text-red-600">Error: Mapbox GL JS failed to load. Please refresh the page or check your internet connection.</div>';
        return;
    }
    
    // Check if API key is available
    if (!window.MAPBOX_API_KEY) {
        console.error('Mapbox API key is not available');
        document.getElementById('map-container-2d').innerHTML = '<div class="p-4 text-center text-red-600">Error: Mapbox API key is missing. Please contact the administrator.</div>';
        return;
    }
    
    // Mapbox access token
    mapboxgl.accessToken = window.MAPBOX_API_KEY;
    console.log('Mapbox API key set:', window.MAPBOX_API_KEY ? 'Available' : 'Missing');
    
    // Coordinates for Potaro-Siparuni region, Guyana
    const POTARO_SIPARUNI_COORDINATES = {
        center: [-59.45, 4.8],  // Longitude, Latitude - centered on Potaro-Siparuni region
        zoom: 8,
        minZoom: 2,           // Reduced from 7 to allow global view
        maxZoom: 22,          // Increased from 16 to allow closer inspection
        pitch: 0,
        bearing: 0
    };
    
    console.log('Initializing 2D map...');
    // Initialize 2D map
    try {
        const map2D = new mapboxgl.Map({
            container: 'map-container-2d',
            style: 'mapbox://styles/mapbox/satellite-streets-v12',
            ...POTARO_SIPARUNI_COORDINATES
        });
        console.log('✅ 2D map initialized successfully');
        
        // Make map globally accessible
        window.map2D = map2D;
        window.currentMap = map2D; // Set as current map
        window.mapsInitialized = true; // Mark as initialized
        
        console.log('✅ Map is now globally accessible');
        
        // Add map event listeners
        setupMapEventListeners(map2D);
        
        // Load initial data
        loadInitialMapData(map2D);
        
        } catch (error) {
        console.error('Error initializing map:', error);
        document.getElementById('map-container-2d').innerHTML = `<div class="p-4 text-center text-red-600">Error initializing map: ${error.message}</div>`;
        return;
    }
}

function setupMapEventListeners(map) {
    // Map load event
    map.on('load', function() {
        console.log('Map loaded successfully');
        
        // Add navigation controls
        map.addControl(new mapboxgl.NavigationControl(), 'top-right');
        
        // Add fullscreen control
        map.addControl(new mapboxgl.FullscreenControl(), 'top-right');
        
        // Add scale control
        map.addControl(new mapboxgl.ScaleControl({
            maxWidth: 100,
            unit: 'metric'
        }), 'bottom-left');
        
        // Load gold predictions
        loadGoldPredictions(map);
        
        // Load geological features
        loadGeologicalFeatures(map);
    });
    
    // Map click event for showing prediction details
    map.on('click', function(e) {
        const features = map.queryRenderedFeatures(e.point, {
            layers: ['gold-predictions-points', 'geological-features', 'trends-lines']
        });
        
        if (features.length > 0) {
            showFeaturePopup(e.lngLat, features[0]);
        }
    });
    
    // Map style change event
    map.on('style.load', function() {
        console.log('Map style loaded');
        // Re-add data sources and layers after style change
        setTimeout(() => {
            loadGoldPredictions(map);
            loadGeologicalFeatures(map);
        }, 100);
    });
}

function loadInitialMapData(map) {
    // This function will be called after the map is initialized
    // to load any existing data
    console.log('Loading initial map data...');
}

    function loadGoldPredictions(map) {
    if (!map || !map.isStyleLoaded()) {
        console.log('Map not ready, deferring prediction loading');
        setTimeout(() => loadGoldPredictions(map), 100);
            return;
        }
        
    console.log('Loading gold predictions...');
        
    // Fetch predictions from API
        fetch('/api/enhanced-predictions/')
            .then(response => response.json())
            .then(data => {
            if (data.success && data.predictions && data.predictions.length > 0) {
                addPredictionsToMap(map, data.predictions);
            } else {
                console.log('No predictions available or error loading predictions');
            }
        })
        .catch(error => {
            console.error('Error loading predictions:', error);
        });
}

function addPredictionsToMap(map, predictions) {
    if (!map || !map.isStyleLoaded()) return;
    
    // Remove existing prediction layers if they exist
    if (map.getSource('gold-predictions')) {
        map.removeLayer('gold-predictions-heat');
        map.removeLayer('gold-predictions-points');
        map.removeSource('gold-predictions');
    }
    
    // Prepare data for Mapbox
    const predictionFeatures = predictions.map(pred => ({
                        type: 'Feature',
                        geometry: {
                            type: 'Point',
                            coordinates: [pred.longitude, pred.latitude]
                        },
                        properties: {
            id: pred.prediction_id,
            probability: pred.probability,
            confidence: pred.confidence,
            mineral_type: pred.mineral_type,
            geological_formation: pred.geological_formation,
            soil_type: pred.soil_type,
            depth_range: pred.depth_range,
            extraction_difficulty: pred.extraction_difficulty,
            area_name: pred.area_name || 'Unknown Area',
            description: pred.description || 'No description available'
        }
    }));
    
    // Add source
                map.addSource('gold-predictions', {
                    type: 'geojson',
        data: {
            type: 'FeatureCollection',
            features: predictionFeatures
        }
                });
                
    // Add heatmap layer
                map.addLayer({
                    id: 'gold-predictions-heat',
                    type: 'heatmap',
                    source: 'gold-predictions',
                    paint: {
                        'heatmap-weight': [
                            'interpolate',
                            ['linear'],
                            ['get', 'probability'],
                            0, 0,
                            1, 1
                        ],
            'heatmap-intensity': [
                'interpolate',
                ['linear'],
                ['zoom'],
                0, 1,
                9, 3
            ],
                        'heatmap-color': [
                            'interpolate',
                            ['linear'],
                            ['heatmap-density'],
                            0, 'rgba(0, 0, 255, 0)',
                0.2, 'rgb(0, 0, 255)',
                0.4, 'rgb(0, 255, 255)',
                0.6, 'rgb(0, 255, 0)',
                0.8, 'rgb(255, 255, 0)',
                1, 'rgb(255, 0, 0)'
            ],
            'heatmap-radius': [
                'interpolate',
                ['linear'],
                ['zoom'],
                0, 2,
                9, 20
            ],
                        'heatmap-opacity': 0.8
                    }
                });
                
    // Add points layer
                map.addLayer({
                    id: 'gold-predictions-points',
                    type: 'circle',
                    source: 'gold-predictions',
                    paint: {
                        'circle-radius': [
                            'interpolate',
                            ['linear'],
                ['zoom'],
                0, 2,
                9, 8
                        ],
                        'circle-color': [
                            'interpolate',
                            ['linear'],
                ['get', 'probability'],
                0, '#3288bd',   // Blue for low probability
                0.5, '#fee08b', // Yellow for medium probability
                1, '#d53e4f'    // Red for high probability
            ],
            'circle-stroke-color': '#ffffff',
                        'circle-stroke-width': 1,
            'circle-opacity': 0.8
        }
    });
    
    console.log(`Added ${predictions.length} predictions to map`);
}

function loadGeologicalFeatures(map) {
    if (!map || !map.isStyleLoaded()) {
        console.log('Map not ready, deferring geological features loading');
        setTimeout(() => loadGeologicalFeatures(map), 100);
            return;
        }
        
    console.log('Loading geological features...');
    
    // Fetch geological features from API
    fetch('/api/geological-surveys/')
            .then(response => response.json())
            .then(data => {
            if (data.success && data.surveys && data.surveys.length > 0) {
                addGeologicalFeaturesToMap(map, data.surveys);
                } else {
                console.log('No geological features available or error loading features');
                }
            })
            .catch(error => {
            console.error('Error loading geological features:', error);
        });
}

function addGeologicalFeaturesToMap(map, features) {
    if (!map || !map.isStyleLoaded()) return;
    
    // Remove existing geological feature layers if they exist
    if (map.getSource('geological-features')) {
        map.removeLayer('geological-features-points');
        map.removeSource('geological-features');
    }
    
    // Prepare data for Mapbox
    const featureData = features.map(feature => ({
                        type: 'Feature',
                        geometry: {
                            type: 'Point',
            coordinates: [feature.longitude, feature.latitude]
        },
        properties: {
            id: feature.id,
            name: feature.name || 'Unknown Feature',
            type: feature.feature_type || 'Unknown',
            description: feature.description || 'No description available',
            confidence_score: feature.confidence_score || 0
        }
    }));
    
    // Add source
                map.addSource('geological-features', {
                    type: 'geojson',
        data: {
            type: 'FeatureCollection',
            features: featureData
        }
                });
    
    // Add points layer
                map.addLayer({
                    id: 'geological-features-points',
                    type: 'circle',
                    source: 'geological-features',
                    paint: {
            'circle-radius': 6,
            'circle-color': '#00ff00', // Lime green for real survey locations
            'circle-stroke-color': '#ffffff',
                        'circle-stroke-width': 2,
            'circle-opacity': 0.9
        }
    });
    
    console.log(`Added ${features.length} geological features to map`);
}

function showFeaturePopup(lngLat, feature) {
    // Create popup content
    let popupContent = '';
    
    if (feature.layer.id === 'gold-predictions-points') {
        const props = feature.properties;
        popupContent = `
            <div class="prediction-popup">
                <h3 class="font-bold text-lg mb-2">${props.area_name}</h3>
                <div class="space-y-1 text-sm">
                    <p><strong>Probability:</strong> ${(props.probability * 100).toFixed(1)}%</p>
                    <p><strong>Confidence:</strong> ${(props.confidence * 100).toFixed(1)}%</p>
                    <p><strong>Mineral Type:</strong> ${props.mineral_type}</p>
                    <p><strong>Formation:</strong> ${props.geological_formation}</p>
                    <p><strong>Soil Type:</strong> ${props.soil_type}</p>
                    <p><strong>Depth Range:</strong> ${props.depth_range}</p>
                    <p><strong>Extraction Difficulty:</strong> ${props.extraction_difficulty}</p>
                            </div>
                <div class="mt-3 text-xs text-gray-600">
                    ${props.description}
                                </div>
                            </div>
        `;
    } else if (feature.layer.id === 'geological-features-points') {
        const props = feature.properties;
        popupContent = `
            <div class="geological-popup">
                <h3 class="font-bold text-lg mb-2">${props.name}</h3>
                <div class="space-y-1 text-sm">
                    <p><strong>Type:</strong> ${props.type}</p>
                    <p><strong>Confidence:</strong> ${(props.confidence_score * 100).toFixed(1)}%</p>
                            </div>
                <div class="mt-3 text-xs text-gray-600">
                    ${props.description}
                                </div>
                            </div>
        `;
    }
    
    if (popupContent) {
        // Create and show popup
        const popup = new mapboxgl.Popup({
            closeButton: true,
            closeOnClick: false,
            maxWidth: '300px'
        })
        .setLngLat(lngLat)
        .setHTML(popupContent)
        .addTo(window.currentMap);
    }
}

// Global functions for external use
window.loadGoldPredictions = loadGoldPredictions;
window.loadGeologicalFeatures = loadGeologicalFeatures;
window.addPredictionsToMap = addPredictionsToMap;
window.addGeologicalFeaturesToMap = addGeologicalFeaturesToMap;

// Export functions for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initializeMaps,
        loadGoldPredictions,
        loadGeologicalFeatures,
        addPredictionsToMap,
        addGeologicalFeaturesToMap
    };
} 