// Mapbox configuration and handling for GoldMine AI
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the maps page
    if (!document.getElementById('map-container-2d') || !document.getElementById('map-container-3d')) {
        return;
    }
    
    // Mapbox access token
    mapboxgl.accessToken = window.MAPBOX_API_KEY;
    
    // Coordinates for Potaro-Siparuni region, Guyana
    const POTARO_SIPARUNI_COORDINATES = {
        center: [-59.45, 4.8],  // Longitude, Latitude - centered on Potaro-Siparuni region
        zoom: 8,
        minZoom: 2,           // Reduced from 7 to allow global view
        maxZoom: 22,          // Increased from 16 to allow closer inspection
        pitch: 0,
        bearing: 0
    };
    
    // Initialize 2D map
    const map2D = new mapboxgl.Map({
        container: 'map-container-2d',
        style: 'mapbox://styles/mapbox/satellite-streets-v12',
        ...POTARO_SIPARUNI_COORDINATES
    });
    
    // Initialize 3D map with terrain
    const map3D = new mapboxgl.Map({
        container: 'map-container-3d',
        style: 'mapbox://styles/mapbox/satellite-v9',
        ...POTARO_SIPARUNI_COORDINATES,
        pitch: 60, // Tilt the map for 3D view
        bearing: 30
    });
    
    // Make maps globally accessible
    window.map2D = map2D;
    window.map3D = map3D;
    window.currentMap = map2D; // Default to 2D map
    
    // Add map controls to both maps
    const navControl = new mapboxgl.NavigationControl();
    const geolocateControl = new mapboxgl.GeolocateControl({
        positionOptions: {
            enableHighAccuracy: true
        },
        trackUserLocation: true
    });
    const fullscreenControl = new mapboxgl.FullscreenControl();
    const scaleControl = new mapboxgl.ScaleControl({
        maxWidth: 200,
        unit: 'metric'
    });
    
    map2D.addControl(navControl, 'top-right');
    map2D.addControl(geolocateControl, 'top-right');
    map2D.addControl(fullscreenControl, 'top-right');
    map2D.addControl(scaleControl, 'bottom-right');
    
    map3D.addControl(navControl, 'top-right');
    map3D.addControl(geolocateControl, 'top-right');
    map3D.addControl(fullscreenControl, 'top-right');
    map3D.addControl(scaleControl, 'bottom-right');
    
    // Add terrain to 3D map
    map3D.on('style.load', function() {
        map3D.addSource('mapbox-dem', {
            'type': 'raster-dem',
            'url': 'mapbox://mapbox.mapbox-terrain-dem-v1',
            'tileSize': 512,
            'maxzoom': 14
        });
        
        map3D.setTerrain({ 'source': 'mapbox-dem', 'exaggeration': 1.5 });
        
        // Add sky layer for improved 3D visual
        map3D.addLayer({
            'id': 'sky',
            'type': 'sky',
            'paint': {
                'sky-type': 'atmosphere',
                'sky-atmosphere-sun': [0.0, 0.0],
                'sky-atmosphere-sun-intensity': 15
            }
        });
    });
    
    // Add Guyana boundary outlines to both maps
    map2D.on('load', function() {
        loadGuyanaData(map2D);
        loadGoldPredictions(map2D);
        loadIntelligentCoordinates(map2D);
        loadMineralizationTrends(map2D);
        loadGeologicalFeatures(map2D);
    });
    
    map3D.on('load', function() {
        loadGuyanaData(map3D);
        loadGoldPredictions(map3D);
        loadIntelligentCoordinates(map3D);
        loadMineralizationTrends(map3D);
        loadGeologicalFeatures(map3D);
    });
    
    // Map search functionality
    const searchForm = document.getElementById('map-search-form');
    const searchInput = document.getElementById('map-search-input');
    
    if (searchForm && searchInput) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const searchQuery = searchInput.value.trim();
            
            if (searchQuery) {
                // Search on the 2D and 3D maps
                searchLocation(searchQuery);
                
                // Dispatch a custom event for the Cesium globe
                const searchEvent = new CustomEvent('mapSearch', {
                    detail: { query: searchQuery }
                });
                document.dispatchEvent(searchEvent);
                
                console.log('Search event dispatched for:', searchQuery);
            }
        });
    }
    
    // Load Guyana GIS data
    function loadGuyanaData(map) {
        // Check if sources already exist and remove them first
        if (map.getSource('guyana-boundaries')) {
            map.removeLayer('guyana-boundaries-layer');
            map.removeSource('guyana-boundaries');
        }
        if (map.getSource('potaro-siparuni')) {
            map.removeLayer('potaro-siparuni-line');
            map.removeSource('potaro-siparuni');
        }
        if (map.getSource('guyana-settlements')) {
            map.removeLayer('settlement-labels');
            map.removeLayer('settlements');
            map.removeSource('guyana-settlements');
        }
        
        // Add Guyana administrative boundaries
        map.addSource('guyana-boundaries', {
            'type': 'geojson',
            'data': '/static/data/guyana_boundaries.geojson'
        });
        
        map.addLayer({
            'id': 'guyana-boundaries-layer',
            'type': 'line',
            'source': 'guyana-boundaries',
            'paint': {
                'line-color': '#ffffff',
                'line-width': 2,
                'line-opacity': 0.7
            }
        });
        
        // Add Potaro-Siparuni region highlight
        map.addSource('potaro-siparuni', {
            'type': 'geojson',
            'data': '/static/data/potaro_siparuni_boundary.geojson'
        });
        
        // map.addLayer({
        //     'id': 'potaro-siparuni-fill',
        //     'type': 'fill',
        //     'source': 'potaro-siparuni',
        //     'paint': {
        //         'fill-color': '#FFD700',
        //         'fill-opacity': 0.15
        //     }
        // });
        
        map.addLayer({
            'id': 'potaro-siparuni-line',
            'type': 'line',
            'source': 'potaro-siparuni',
            'paint': {
                'line-color': '#FFD700',
                'line-width': 3,
                'line-opacity': 0.8
            }
        });
        
        // Add rivers, roads and settlements
        // map.addSource('guyana-rivers', {
        //     'type': 'geojson',
        //     'data': '/static/data/guyana_rivers.geojson'
        // });
        
        // map.addLayer({
        //     'id': 'rivers',
        //     'type': 'line',
        //     'source': 'guyana-rivers',
        //     'paint': {
        //         'line-color': '#0080ff',
        //         'line-width': ['get', 'width'],
        //         'line-opacity': 0.8
        //     }
        // });
        
        map.addSource('guyana-settlements', {
            'type': 'geojson',
            'data': '/static/data/guyana_settlements.geojson'
        });
        
        map.addLayer({
            'id': 'settlements',
            'type': 'circle',
            'source': 'guyana-settlements',
            'paint': {
                'circle-radius': ['case', 
                    ['==', ['get', 'type'], 'city'], 8,
                    ['==', ['get', 'type'], 'town'], 6,
                    4
                ],
                'circle-color': '#ffffff',
                'circle-stroke-width': 1,
                'circle-stroke-color': '#000000'
            }
        });
        
        map.addLayer({
            'id': 'settlement-labels',
            'type': 'symbol',
            'source': 'guyana-settlements',
            'layout': {
                'text-field': ['get', 'name'],
                'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
                'text-size': ['case', 
                    ['==', ['get', 'type'], 'city'], 14,
                    ['==', ['get', 'type'], 'town'], 12,
                    10
                ],
                'text-offset': [0, 1.5],
                'text-anchor': 'top'
            },
            'paint': {
                'text-color': '#ffffff',
                'text-halo-color': '#000000',
                'text-halo-width': 1
            }
        });
    }
    
    // Helper to find a feature at or near a coordinate
    function findNearbyFeature(features, lng, lat, tolerance = 0.0005) {
        return features.find(f => Math.abs(f.geometry.coordinates[0] - lng) < tolerance && Math.abs(f.geometry.coordinates[1] - lat) < tolerance);
    }

    // Store loaded geojson data for all layers
    let goldPredictionsGeoJSON = null;
    let geologicalFeaturesGeoJSON = null;
    let intelligentCoordinatesGeoJSON = null;

    // Update loadGoldPredictions to store geojson
    function loadGoldPredictions(map) {
        fetch('/api/enhanced-predictions/')
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    console.error('Error loading predictions:', data.error);
                    return;
                }
                // Convert prediction data to GeoJSON
                const features = data.predictions.map(item => {
                    return {
                        type: 'Feature',
                        geometry: {
                            type: 'Point',
                            coordinates: [item.longitude, item.latitude]
                        },
                        properties: { ...item }
                    };
                });
                goldPredictionsGeoJSON = {
                    type: 'FeatureCollection',
                    features: features
                };
                
                // Check if source already exists and remove it first
                if (map.getSource('gold-predictions')) {
                    map.removeLayer('gold-predictions-heat');
                    map.removeLayer('gold-predictions-points');
                    map.removeSource('gold-predictions');
                }
                
                map.addSource('gold-predictions', {
                    type: 'geojson',
                    data: goldPredictionsGeoJSON
                });
                map.addLayer({
                    id: 'gold-predictions-points',
                    type: 'circle',
                    source: 'gold-predictions',
                    paint: {
                        'circle-radius': 8,
                        'circle-color': [
                            'case',
                            // Check if it's an AI-enhanced prediction (has supporting_features)
                            ['has', 'supporting_features'],
                            // AI-Enhanced Predictions colors (exact colors from legend)
                            [
                                'case',
                                ['<', ['get', 'probability'], 0.33], 'cyan',
                                ['<', ['get', 'probability'], 0.66], 'orange',
                                'magenta'
                            ],
                            // Regular Gold Predictions colors (exact colors from legend)
                            [
                                'case',
                                ['<', ['get', 'probability'], 0.33], '#3288bd',
                                ['<', ['get', 'probability'], 0.66], '#fee08b',
                                '#d53e4f'
                            ]
                        ],
                        'circle-opacity': 0.8,
                        'circle-stroke-width': 1,
                        'circle-stroke-color': '#ffffff'
                    }
                });
                
                // Create a heatmap for gold probability
                map.addLayer({
                    id: 'gold-predictions-heat',
                    type: 'heatmap',
                    source: 'gold-predictions',
                    maxzoom: 15,
                    paint: {
                        'heatmap-weight': [
                            'interpolate', ['linear'], ['get', 'probability'],
                            0, 0,
                            0.5, 0.5,
                            1, 1
                        ],
                        'heatmap-intensity': [
                            'interpolate', ['linear'], ['zoom'],
                            7, 0.5,
                            12, 1.5
                        ],
                        'heatmap-color': [
                            'interpolate', ['linear'], ['heatmap-density'],
                            0, 'rgba(0, 0, 255, 0)',
                            0.2, 'rgba(0, 255, 255, 0.5)',
                            0.4, 'rgba(0, 255, 0, 0.5)',
                            0.6, 'rgba(255, 255, 0, 0.5)',
                            0.8, 'rgba(255, 128, 0, 0.7)',
                            1, 'rgba(255, 0, 0, 0.8)'
                        ],
                        'heatmap-radius': [
                            'interpolate', ['linear'], ['zoom'],
                            7, 10,
                            10, 20,
                            15, 30
                        ],
                        'heatmap-opacity': [
                            'interpolate', ['linear'], ['zoom'],
                            7, 0.7,
                            15, 0.3
                        ]
                    }
                }, 'gold-predictions-points');
                
                // Add popup on click
                const popup = new mapboxgl.Popup({
                    closeButton: false,
                    closeOnClick: false
                });
                
                map.on('mouseenter', 'gold-predictions-points', function(e) {
                    map.getCanvas().style.cursor = 'pointer';
                    
                    const coordinates = e.features[0].geometry.coordinates.slice();
                    const properties = e.features[0].properties;
                    
                    // Find nearby geological feature
                    let geoFeature = geologicalFeaturesGeoJSON ? findNearbyFeature(geologicalFeaturesGeoJSON.features, coordinates[0], coordinates[1]) : null;
                    // Build combined tooltip
                    let html = `<strong>Gold Prediction</strong><br>
                        Lat: ${coordinates[1].toFixed(4)}, Lng: ${coordinates[0].toFixed(4)}<br>
                        Elevation: ${properties.elevation}m<br>
                        Probability: <span style="color: ${properties.probability < 0.33 ? '#3288bd' : properties.probability < 0.66 ? '#fee08b' : '#d53e4f'};">${(properties.probability * 100).toFixed(1)}%</span><br>`;
                    if (geoFeature) {
                        html += `<hr style='margin:4px 0'><strong>Geological Feature</strong><br>
                            Type: ${geoFeature.properties.feature_type}<br>
                            Description: ${geoFeature.properties.description}<br>
                            Confidence: ${(geoFeature.properties.confidence * 100).toFixed(1)}%<br>
                            Survey: ${geoFeature.properties.survey_title}`;
                    }
                    
                    while (Math.abs(e.lngLat.lng - coordinates[0]) > 180) {
                        coordinates[0] += e.lngLat.lng > coordinates[0] ? 360 : -360;
                    }
                    
                    popup.setLngLat(coordinates)
                        .setHTML(html)
                        .addTo(map);
                });
                
                map.on('mouseleave', 'gold-predictions-points', function() {
                    map.getCanvas().style.cursor = '';
                    popup.remove();
                });
                
                console.log(`Loaded ${data.total_predictions} gold predictions`);
            })
            .catch(error => {
                console.error('Error loading prediction data:', error);
                loadOriginalPredictions(map);
            });
    }
    
    // Load intelligent coordinates (AI-generated) with distinct styling
    function loadIntelligentCoordinates(map) {
        fetch('/api/intelligent-coordinates/')
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    console.error('Error loading intelligent coordinates:', data.error);
                    return;
                }
                
                // Convert intelligent coordinates to GeoJSON
                const features = data.coordinates.map(item => {
                    return {
                        type: 'Feature',
                        geometry: {
                            type: 'Point',
                            coordinates: [item.longitude, item.latitude]
                        },
                        properties: { ...item }
                    };
                });
                
                intelligentCoordinatesGeoJSON = {
                    type: 'FeatureCollection',
                    features: features
                };
                
                // Check if source already exists and remove it first
                if (map.getSource('intelligent-coordinates')) {
                    map.removeLayer('intelligent-coordinates-points');
                    map.removeSource('intelligent-coordinates');
                }
                
                // Add intelligent coordinates source
                map.addSource('intelligent-coordinates', {
                    type: 'geojson',
                    data: intelligentCoordinatesGeoJSON
                });
                
                // Add intelligent coordinates layer with distinct styling
                map.addLayer({
                    id: 'intelligent-coordinates-points',
                    type: 'circle',
                    source: 'intelligent-coordinates',
                    paint: {
                        'circle-radius': 12,  // Larger than regular predictions
                        'circle-color': [
                            'case',
                            ['<', ['get', 'gold_probability'], 0.33], '#00ffff',  // Cyan for low
                            ['<', ['get', 'gold_probability'], 0.66], '#ff8c00',  // Dark orange for medium
                            '#ff00ff'  // Magenta for high
                        ],
                        'circle-opacity': 0.9,
                        'circle-stroke-width': 3,  // Thicker border
                        'circle-stroke-color': '#000000'  // Black border
                    }
                });  // Don't specify layer ordering to avoid dependency issues
                
                // Add popup for intelligent coordinates
                const intelligentPopup = new mapboxgl.Popup({
                    closeButton: false,
                    closeOnClick: false
                });
                
                map.on('mouseenter', 'intelligent-coordinates-points', function(e) {
                    map.getCanvas().style.cursor = 'pointer';
                    
                    const coordinates = e.features[0].geometry.coordinates.slice();
                    const properties = e.features[0].properties;
                    
                    const html = `<strong>🤖 AI-Generated Exploration Point</strong><br>
                        Lat: ${coordinates[1].toFixed(4)}, Lng: ${coordinates[0].toFixed(4)}<br>
                        Elevation: ${properties.elevation}m<br>
                        Gold Probability: <span style="color: ${properties.gold_probability < 0.33 ? '#00ffff' : properties.gold_probability < 0.66 ? '#ff8c00' : '#ff00ff'};">${(properties.gold_probability * 100).toFixed(1)}%</span><br>
                        Confidence: ${(properties.confidence_score * 100).toFixed(1)}%<br>
                        Priority: <span style="color: ${properties.exploration_priority === 'high' ? '#ff0000' : '#ff8c00'};">${properties.exploration_priority.toUpperCase()}</span><br>
                        Source: ${properties.source}<br>
                        Created: ${new Date(properties.created_at).toLocaleDateString()}`;
                    
                    while (Math.abs(e.lngLat.lng - coordinates[0]) > 180) {
                        coordinates[0] += e.lngLat.lng > coordinates[0] ? 360 : -360;
                    }
                    
                    intelligentPopup.setLngLat(coordinates)
                        .setHTML(html)
                        .addTo(map);
                });
                
                map.on('mouseleave', 'intelligent-coordinates-points', function() {
                    map.getCanvas().style.cursor = '';
                    intelligentPopup.remove();
                });
                
                console.log(`Loaded ${data.total_coordinates} intelligent coordinates`);
            })
            .catch(error => {
                console.error('Error loading intelligent coordinates:', error);
            });
    }
    
    function loadOriginalPredictions(map) {
        // Fallback to original prediction history endpoint
        fetch('/api/enhanced-predictions/')
            .then(response => response.json())
            .then(data => {
                // Check if data has the expected structure
                if (!data.success || !data.predictions || !Array.isArray(data.predictions)) {
                    console.warn('Invalid prediction data structure:', data);
                    return;
                }
                
                // Convert prediction history to GeoJSON
                const features = data.predictions.map(item => {
                    return {
                        type: 'Feature',
                        geometry: {
                            type: 'Point',
                            coordinates: [item.longitude, item.latitude]
                        },
                        properties: {
                            elevation: item.elevation,
                            soil_type: item.soil_type,
                            geological_formation: item.geological_formation,
                            probability: item.probability,
                            confidence: item.confidence,
                            created_at: item.created_at
                        }
                    };
                });
                
                const geojson = {
                    type: 'FeatureCollection',
                    features: features
                };
                
                // Check if source already exists and remove it first
                if (map.getSource('gold-predictions')) {
                    map.removeLayer('gold-predictions-heat');
                    map.removeLayer('gold-predictions-points');
                    map.removeSource('gold-predictions');
                }
                
                // Add gold prediction points
                map.addSource('gold-predictions', {
                    type: 'geojson',
                    data: geojson
                });
                
                map.addLayer({
                    id: 'gold-predictions-points',
                    type: 'circle',
                    source: 'gold-predictions',
                    paint: {
                        'circle-radius': 8,
                        'circle-color': [
                            'case',
                            // Check if it's an AI-enhanced prediction (has supporting_features)
                            ['has', 'supporting_features'],
                            // AI-Enhanced Predictions colors (exact colors from legend)
                            [
                                'case',
                                ['<', ['get', 'probability'], 0.33], 'cyan',
                                ['<', ['get', 'probability'], 0.66], 'orange',
                                'magenta'
                            ],
                            // Regular Gold Predictions colors (exact colors from legend)
                            [
                                'case',
                                ['<', ['get', 'probability'], 0.33], '#3288bd',
                                ['<', ['get', 'probability'], 0.66], '#fee08b',
                                '#d53e4f'
                            ]
                        ],
                        'circle-opacity': 0.8,
                        'circle-stroke-width': 1,
                        'circle-stroke-color': '#ffffff'
                    }
                });
                
                // Create a heatmap for gold probability
                map.addLayer({
                    id: 'gold-predictions-heat',
                    type: 'heatmap',
                    source: 'gold-predictions',
                    maxzoom: 15,
                    paint: {
                        'heatmap-weight': [
                            'interpolate', ['linear'], ['get', 'probability'],
                            0, 0,
                            0.5, 0.5,
                            1, 1
                        ],
                        'heatmap-intensity': [
                            'interpolate', ['linear'], ['zoom'],
                            7, 0.5,
                            12, 1.5
                        ],
                        'heatmap-color': [
                            'interpolate', ['linear'], ['heatmap-density'],
                            0, 'rgba(0, 0, 255, 0)',
                            0.2, 'rgba(0, 255, 255, 0.5)',
                            0.4, 'rgba(0, 255, 0, 0.5)',
                            0.6, 'rgba(255, 255, 0, 0.5)',
                            0.8, 'rgba(255, 128, 0, 0.7)',
                            1, 'rgba(255, 0, 0, 0.8)'
                        ],
                        'heatmap-radius': [
                            'interpolate', ['linear'], ['zoom'],
                            7, 10,
                            10, 20,
                            15, 30
                        ],
                        'heatmap-opacity': [
                            'interpolate', ['linear'], ['zoom'],
                            7, 0.7,
                            15, 0.3
                        ]
                    }
                }, 'gold-predictions-points');
                
                // Add popup on click
                const popup = new mapboxgl.Popup({
                    closeButton: false,
                    closeOnClick: false
                });
                
                map.on('mouseenter', 'gold-predictions-points', function(e) {
                    map.getCanvas().style.cursor = 'pointer';
                    
                    const coordinates = e.features[0].geometry.coordinates.slice();
                    const properties = e.features[0].properties;
                    
                    // Find nearby geological feature
                    let geoFeature = geologicalFeaturesGeoJSON ? findNearbyFeature(geologicalFeaturesGeoJSON.features, coordinates[0], coordinates[1]) : null;
                    // Build combined tooltip
                    let html = `<strong>Gold Prediction</strong><br>
                        Lat: ${coordinates[1].toFixed(4)}, Lng: ${coordinates[0].toFixed(4)}<br>
                        Elevation: ${properties.elevation}m<br>
                        Probability: <span style="color: ${properties.probability < 0.33 ? '#3288bd' : properties.probability < 0.66 ? '#fee08b' : '#d53e4f'};">${(properties.probability * 100).toFixed(1)}%</span><br>`;
                    if (geoFeature) {
                        html += `<hr style='margin:4px 0'><strong>Geological Feature</strong><br>
                            Type: ${geoFeature.properties.feature_type}<br>
                            Description: ${geoFeature.properties.description}<br>
                            Confidence: ${(geoFeature.properties.confidence * 100).toFixed(1)}%<br>
                            Survey: ${geoFeature.properties.survey_title}`;
                    }
                    
                    while (Math.abs(e.lngLat.lng - coordinates[0]) > 180) {
                        coordinates[0] += e.lngLat.lng > coordinates[0] ? 360 : -360;
                    }
                    
                    popup.setLngLat(coordinates)
                        .setHTML(html)
                        .addTo(map);
                });
                
                map.on('mouseleave', 'gold-predictions-points', function() {
                    map.getCanvas().style.cursor = '';
                    popup.remove();
                });
            })
            .catch(error => {
                console.error('Error loading prediction data:', error);
            });
    }
    
    // Search for a location
    function searchLocation(query) {
        // First try to parse as coordinates
        const coordRegex = /^[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)$/;
        
        if (coordRegex.test(query)) {
            // It's coordinates, format: "latitude, longitude"
            const [lat, lng] = query.split(',').map(c => parseFloat(c.trim()));
            flyToLocation([lng, lat]); // Note: Mapbox uses [lng, lat] format
            return;
        }
        
        // Search for location name worldwide
        fetch(`https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(query)}.json?access_token=${mapboxgl.accessToken}`)
            .then(response => response.json())
            .then(data => {
                if (data.features && data.features.length > 0) {
                    const location = data.features[0];
                    
                    // Add marker for the found location
                    addLocationMarker(location.center, location.place_name);
                    
                    // Fly to the location
                    flyToLocation(location.center);
                } else {
                    // If no results found globally
                    alert('Location not found. Please try another search term or use coordinates.');
                }
            })
            .catch(error => {
                console.error('Error searching location:', error);
                alert('An error occurred during the search. Please try again.');
            });
    }
    
    // Add a marker for the found location
    function addLocationMarker(center, placeName) {
        // Remove existing marker if any
        if (window.searchMarker) {
            window.searchMarker.remove();
        }
        
        // Create a custom marker element
        const markerEl = document.createElement('div');
        markerEl.className = 'search-marker';
        markerEl.style.width = '24px';
        markerEl.style.height = '24px';
        markerEl.style.backgroundImage = 'url(/static/img/marker.svg)';
        markerEl.style.backgroundSize = 'cover';
        
        // Create the marker
        window.searchMarker = new mapboxgl.Marker({
            element: markerEl,
            anchor: 'bottom'
        })
        .setLngLat(center)
        .setPopup(new mapboxgl.Popup({ offset: 25 })
            .setHTML(`<h3>${placeName}</h3>`))
        .addTo(map2D);
        
        // Add marker to 3D map as well
        const marker3D = new mapboxgl.Marker({
            element: markerEl.cloneNode(true),
            anchor: 'bottom'
        })
        .setLngLat(center)
        .setPopup(new mapboxgl.Popup({ offset: 25 })
            .setHTML(`<h3>${placeName}</h3>`))
        .addTo(map3D);
    }
    
    // Fly to a location on both maps
    function flyToLocation(center) {
        // Get the search query to determine appropriate zoom level
        const searchQuery = document.getElementById('map-search-input')?.value.trim().toLowerCase() || '';
        
        // Determine zoom level based on search query
        let zoomLevel = 12; // Default zoom level
        
        if (searchQuery.includes('world') || searchQuery.includes('earth') || searchQuery.includes('globe')) {
            zoomLevel = 3; // Global view
        } else if (searchQuery.includes('continent') || searchQuery.includes('hemisphere')) {
            zoomLevel = 4; // Continental view
        } else if (searchQuery.includes('country') || searchQuery.includes('nation')) {
            zoomLevel = 5; // Country level
        } else if (searchQuery.includes('region') || searchQuery.includes('state') || searchQuery.includes('province')) {
            zoomLevel = 7; // Region level
        } else if (searchQuery.includes('city') || searchQuery.includes('town')) {
            zoomLevel = 10; // City level
        } else if (searchQuery.includes('district') || searchQuery.includes('area') || searchQuery.includes('neighborhood')) {
            zoomLevel = 13; // District level
        } else if (searchQuery.includes('street') || searchQuery.includes('road') || searchQuery.includes('avenue')) {
            zoomLevel = 15; // Street level
        } else if (searchQuery.includes('building') || searchQuery.includes('house') || searchQuery.includes('address')) {
            zoomLevel = 18; // Building level
        }
        
        map2D.flyTo({
            center: center,
            zoom: zoomLevel,
            essential: true
        });
        
        map3D.flyTo({
            center: center,
            zoom: zoomLevel,
            essential: true
        });
    }

    // Create coordinate tooltip for both maps (DISABLED)
    // const tooltip2D = document.createElement('div');
    // tooltip2D.className = 'coordinate-tooltip';
    // tooltip2D.style.display = 'none';
    // document.body.appendChild(tooltip2D);

    // const tooltip3D = document.createElement('div');
    // tooltip3D.className = 'coordinate-tooltip';
    // tooltip3D.style.display = 'none';
    // document.body.appendChild(tooltip3D);

    // Remove any existing coordinate tooltips from DOM
    document.addEventListener('DOMContentLoaded', function() {
        const existingTooltips = document.querySelectorAll('.coordinate-tooltip, .cesium-coordinate-tooltip');
        existingTooltips.forEach(tooltip => {
            tooltip.remove();
        });
    });

    // Add coordinate display functionality to both maps
    function addCoordinateDisplay(map, tooltip) {
        // Check if tooltip exists before adding event listeners
        if (!tooltip) {
            console.warn('Tooltip element is null, skipping coordinate display setup');
            return;
        }
        
        let tooltipTimeout;
        let isHoveringTooltip = false;
        
        // Make tooltip interactive so it can be hovered
        tooltip.addEventListener('mouseenter', function() {
            isHoveringTooltip = true;
            clearTimeout(tooltipTimeout);
        });
        
        tooltip.addEventListener('mouseleave', function() {
            isHoveringTooltip = false;
            tooltipTimeout = setTimeout(() => {
                if (!isHoveringTooltip) {
                    tooltip.style.display = 'none';
                }
            }, 100);
        });

        map.on('mouseleave', function() {
            if (!isHoveringTooltip) {
                clearTimeout(tooltipTimeout);
                tooltipTimeout = setTimeout(() => {
                    if (!isHoveringTooltip) {
                        tooltip.style.display = 'none';
                    }
                }, 200);
            }
        });
    }

    // Add coordinate display to both maps (DISABLED)
    // map2D.on('load', function() {
    //     addCoordinateDisplay(map2D, tooltip2D);
    // });

    // map3D.on('load', function() {
    //     addCoordinateDisplay(map3D, tooltip3D);
    // });

    // Add this function to load geological features and store geojson
    function loadGeologicalFeatures(map) {
        fetch('/api/map-coordinates/')
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    console.error('Error loading geological features:', data.error);
                    return;
                }
                const features = data.coordinates.map(item => {
                    return {
                        type: 'Feature',
                        geometry: {
                            type: 'Point',
                            coordinates: [item.longitude, item.latitude]
                        },
                        properties: { ...item }
                    };
                });
                geologicalFeaturesGeoJSON = {
                    type: 'FeatureCollection',
                    features: features
                };
                
                // Check if source already exists and remove it first
                if (map.getSource('geological-features')) {
                    map.removeLayer('geological-features-points');
                    map.removeSource('geological-features');
                }
                
                map.addSource('geological-features', {
                    type: 'geojson',
                    data: geologicalFeaturesGeoJSON
                });
                map.addLayer({
                    id: 'geological-features-points',
                    type: 'circle',
                    source: 'geological-features',
                    paint: {
                        'circle-radius': 12,
                        'circle-color': '#32cd32',  // Lime green to match legend
                        'circle-opacity': 0.9,
                        'circle-stroke-width': 2,
                        'circle-stroke-color': '#000000'
                    }
                });
                
                // Add hover effects for geological features
                let hoveredFeatureId = null;
                let geologicalFeaturePopup = null;
                let hoverTimeout = null;
                
                // Create popup for geological features
                function createGeologicalFeaturePopup() {
                    if (!geologicalFeaturePopup) {
                        geologicalFeaturePopup = new mapboxgl.Popup({
                            closeButton: false,
                            closeOnClick: false,
                            maxWidth: '350px',
                            className: 'geological-feature-popup'
                        });
                    }
                    return geologicalFeaturePopup;
                }
                
                // Show geological feature hover popup
                function showGeologicalFeatureHoverPopup(e) {
                    // Clear any existing timeout
                    if (hoverTimeout) {
                        clearTimeout(hoverTimeout);
                        hoverTimeout = null;
                    }
                    
                    const feature = e.features[0];
                    if (!feature) return;
                    
                    const properties = feature.properties;
                    const coordinates = feature.geometry.coordinates;
                    
                    // Generate a unique ID for this feature
                    const featureId = `${properties.latitude}-${properties.longitude}-${properties.feature_type}`;
                    
                    // If we're already showing a popup for this exact feature, don't recreate
                    if (hoveredFeatureId === featureId && geologicalFeaturePopup && geologicalFeaturePopup.isOpen()) {
                        return;
                    }
                    
                    // Set a small delay to prevent rapid popup creation
                    hoverTimeout = setTimeout(() => {
                        hoveredFeatureId = featureId;
                        
                        // Format coordinates
                        const lat = coordinates[1].toFixed(4);
                        const lng = coordinates[0].toFixed(4);
                        const coordString = `${lat}°N, ${lng}°W`;
                        
                        // Determine if this is an intelligent prediction or real geological feature
                        const isIntelligentPrediction = properties.source === 'AI Generated';
                        
                        // Create comprehensive popup content
                        let html = `<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 350px;">
                            <div style="border-left: 4px solid #22c55e; padding-left: 8px; margin-bottom: 8px;">
                                <strong style="color: #22c55e; font-size: 14px;">${isIntelligentPrediction ? 'AI Prediction' : '📋 Geological Survey Data'}</strong>
                            </div>
                            <div style="font-size: 12px; line-height: 1.4;">
                                <div style="margin-bottom: 4px;">
                                    <strong>Type:</strong> ${properties.feature_type || 'Unknown'}
                                </div>
                                <div style="margin-bottom: 4px;">
                                    <strong>Location:</strong> ${coordString}
                                </div>`;
                        
                        if (properties.elevation) {
                            html += `<div style="margin-bottom: 4px;">
                                <strong>Elevation:</strong> ${properties.elevation}m
                            </div>`;
                        }
                        
                        if (properties.confidence) {
                            const confidenceColor = properties.confidence > 0.7 ? '#22c55e' : 
                                                   properties.confidence > 0.4 ? '#eab308' : '#ef4444';
                            html += `<div style="margin-bottom: 4px;">
                                <strong>Confidence:</strong> <span style="color: ${confidenceColor};">${(properties.confidence * 100).toFixed(1)}%</span>
                            </div>`;
                        }
                        
                        if (isIntelligentPrediction) {
                            // Show AI-specific information
                            html += `<div style="margin-bottom: 4px;">
                                <strong>Source:</strong> <span style="color: #8b5cf6;">AI Analysis</span>
                            </div>
                            <div style="margin-bottom: 4px;">
                                <strong>Status:</strong> <span style="color: #f59e0b;">Unexplored Area</span>
                            </div>`;
                            
                            // Add location-specific geological assessment
                            html += `<hr style="margin: 8px 0; border: none; border-top: 1px solid #e5e7eb;">
                            <div style="margin-bottom: 4px;">
                                <strong>Geological Assessment:</strong>
                            </div>
                            <div style="font-size: 11px; color: #6b7280; line-height: 1.3; background: #f0f9ff; padding: 6px; border-radius: 4px; border-left: 3px solid #3b82f6;">
                                <strong>Formation:</strong> ${properties.description.split(' in ')[1]?.split(' with ')[0] || 'Potaro Group metasediments'}<br>
                                <strong>Structure:</strong> NE-SW trending shear zones<br>
                                <strong>Alteration:</strong> Silicification, sericitization<br>
                                <strong>Mineralization Style:</strong> Orogenic gold-quartz veins
                            </div>`;
                            
                            // Add location-specific technical specifications
                            const expectedDepth = properties.elevation > 400 ? '100-300m' : '50-200m';
                            const veinWidth = properties.confidence > 0.7 ? '1.0-3.0m' : '0.5-2.0m';
                            const gradePotential = properties.gold_probability > 0.7 ? '5-12 g/t Au' : '3-8 g/t Au';
                            
                            html += `<div style="margin-top: 6px; font-size: 11px; color: #6b7280; line-height: 1.3; background: #fef3c7; padding: 6px; border-radius: 4px; border-left: 3px solid #f59e0b;">
                                <strong>Technical Specs:</strong><br>
                                • Expected depth: ${expectedDepth}<br>
                                • Vein width: ${veinWidth}<br>
                                • Grade potential: ${gradePotential}<br>
                                • Host rock: Greenschist facies<br>
                                • Gold probability: ${(properties.gold_probability * 100).toFixed(1)}%
                            </div>`;
                            
                            // Add soil information if available
                            if (properties.soil_type && properties.soil_type !== 'unknown') {
                                html += `<div style="margin-top: 6px; font-size: 11px; color: #6b7280; line-height: 1.3; background: #ecfdf5; padding: 6px; border-radius: 4px; border-left: 3px solid #10b981;">
                                    <strong>Soil Analysis:</strong><br>
                                    • Type: ${properties.soil_type}<br>
                                    • pH: ${properties.ph_level?.toFixed(1) || '6.0-7.0'}<br>
                                    • Organic content: ${properties.organic_content?.toFixed(1) || '2-4'}%<br>
                                    • Mineral content: ${properties.mineral_content || 'Quartz, feldspar, mica'}
                                </div>`;
                            }
                        } else {
                            // Show real geological survey data information
                            html += `<div style="margin-bottom: 4px;">
                                <strong>Data Type:</strong> <span style="color: #10b981;">📋 Real Survey Data</span>
                            </div>`;
                            if (properties.survey_title && properties.survey_title !== 'Unknown') {
                                html += `<div style="margin-bottom: 4px;">
                                    <span style="font-size:15px;">📄</span> <strong>Survey:</strong> ${properties.survey_title}
                                </div>`;
                            }
                            if (properties.survey_date) {
                                html += `<div style="margin-bottom: 4px;">
                                    <span style="font-size:15px;">📅</span> <strong>Date:</strong> ${properties.survey_date}
                                </div>`;
                            }
                            if (properties.feature_type) {
                                html += `<div style="margin-bottom: 4px;">
                                    <span style="font-size:15px;">🪨</span> <strong>Feature Type:</strong> ${properties.feature_type}
                                </div>`;
                            }
                            if (properties.elevation) {
                                html += `<div style="margin-bottom: 4px;">
                                    <span style="font-size:15px;">⛰️</span> <strong>Elevation:</strong> ${properties.elevation} m
                                </div>`;
                            }
                            if (properties.soil_type && properties.soil_type !== 'unknown') {
                                html += `<div style="margin-bottom: 4px;">
                                    <span style="font-size:15px;">🌱</span> <strong>Soil Type:</strong> ${properties.soil_type}
                                </div>`;
                            }
                            if (properties.minerals && Array.isArray(properties.minerals) && properties.minerals.length > 0) {
                                html += `<div style="margin-bottom: 4px;">
                                    <span style="font-size:15px;">⛏️</span> <strong>Minerals:</strong> ${properties.minerals.slice(0, 3).join(', ')}${properties.minerals.length > 3 ? '...' : ''}
                                </div>`;
                            } else if (properties.minerals && typeof properties.minerals === 'string') {
                                html += `<div style="margin-bottom: 4px;">
                                    <span style="font-size:15px;">⛏️</span> <strong>Minerals:</strong> ${properties.minerals}
                                </div>`;
                            }
                            if (typeof properties.gold_probability === 'number') {
                                html += `<div style="margin-bottom: 4px;">
                                    <span style="font-size:15px;">🥇</span> <strong>Gold Probability:</strong> ${(properties.gold_probability * 100).toFixed(1)}%
                                </div>`;
                            }
                            if (typeof properties.confidence === 'number') {
                                html += `<div style="margin-bottom: 4px;">
                                    <span style="font-size:15px;">✅</span> <strong>Confidence:</strong> ${(properties.confidence * 100).toFixed(1)}%
                                </div>`;
                            }
                            if (properties.description) {
                                html += `<hr style="margin: 8px 0; border: none; border-top: 1px solid #e5e7eb;">
                                <div style="margin-bottom: 4px;">
                                    <span style="font-size:15px;">📝</span> <strong>Description:</strong>
                                </div>
                                <div style="font-size: 11px; color: #6b7280; line-height: 1.3;">
                                    ${properties.description.length > 150 ? properties.description.substring(0, 150) + '...' : properties.description}
                                </div>`;
                            }
                            // Add survey metadata
                            html += `<hr style="margin: 8px 0; border: none; border-top: 1px solid #e5e7eb;">
                            <div style="margin-bottom: 4px;">
                                <span style="font-size:15px;">📁</span> <strong>Source Document:</strong> ${properties.source_file || 'Uploaded PDF'}
                            </div>
                            <div style="margin-bottom: 4px;">
                                <span style="font-size:15px;">🤖</span> <strong>Extraction Method:</strong> LLM text analysis
                            </div>`;
                            // Add soil analysis details if available
                            if (typeof properties.ph_level === 'number' || typeof properties.organic_content === 'number' || properties.mineral_content) {
                                html += `<div style="margin-top: 6px; font-size: 11px; color: #6b7280; line-height: 1.3; background: #ecfdf5; padding: 6px; border-radius: 4px; border-left: 3px solid #10b981;">
                                    <strong>Soil Analysis:</strong><br>
                                    ${typeof properties.ph_level === 'number' ? '• pH: ' + properties.ph_level.toFixed(1) + '<br>' : ''}
                                    ${typeof properties.organic_content === 'number' ? '• Organic content: ' + properties.organic_content.toFixed(1) + '%<br>' : ''}
                                    ${properties.mineral_content ? '• Mineral content: ' + properties.mineral_content + '<br>' : ''}
                                </div>`;
                            }
                        }
                        
                        html += '</div></div>';
                        
                        const popup = createGeologicalFeaturePopup();
                        popup.setHTML(html);
                        popup.setLngLat(e.lngLat).addTo(map);
                        
                        // Change cursor
                        map.getCanvas().style.cursor = 'pointer';
                    }, 100); // 100ms delay to prevent rapid popup creation
                }
                
                // Hide geological feature hover popup
                function hideGeologicalFeatureHoverPopup() {
                    // Clear any pending timeout
                    if (hoverTimeout) {
                        clearTimeout(hoverTimeout);
                        hoverTimeout = null;
                    }
                    
                    if (geologicalFeaturePopup) {
                        geologicalFeaturePopup.remove();
                        geologicalFeaturePopup = null;
                    }
                    
                    hoveredFeatureId = null;
                    map.getCanvas().style.cursor = '';
                }
                
                // Add event listeners for geological features
                map.on('mouseenter', 'geological-features-points', showGeologicalFeatureHoverPopup);
                map.on('mouseleave', 'geological-features-points', hideGeologicalFeatureHoverPopup);
                
                // Add click event for geological features
                map.on('click', 'geological-features-points', function(e) {
                    const feature = e.features[0];
                    if (!feature) return;
                    
                    const properties = feature.properties;
                    const coordinates = feature.geometry.coordinates;
                    
                    // Fly to the feature location
                    map.flyTo({
                        center: coordinates,
                        zoom: Math.max(map.getZoom(), 12),
                        duration: 1000
                    });
                    
                    // Show a more detailed popup on click
                    const clickPopup = new mapboxgl.Popup({
                        closeButton: true,
                        maxWidth: '400px'
                    });
                    
                    const lat = coordinates[1].toFixed(4);
                    const lng = coordinates[0].toFixed(4);
                    const coordString = `${lat}°N, ${lng}°W`;
                    
                    // Determine if this is an intelligent prediction or real geological feature
                    const isIntelligentPrediction = properties.source === 'AI Generated';
                    
                    let clickHtml = `<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                        <div style="border-left: 4px solid #22c55e; padding-left: 8px; margin-bottom: 12px;">
                            <strong style="color: #22c55e; font-size: 16px;">${isIntelligentPrediction ? 'AI Prediction Details' : '📋 Geological Survey Data Details'}</strong>
                        </div>
                        <div style="font-size: 13px; line-height: 1.5;">
                            <div style="margin-bottom: 6px;">
                                <strong>Type:</strong> ${properties.feature_type || 'Unknown'}
                            </div>
                            <div style="margin-bottom: 6px;">
                                <strong>Location:</strong> ${coordString}
                            </div>`;
                    
                    if (properties.elevation) {
                        clickHtml += `<div style="margin-bottom: 6px;">
                            <strong>Elevation:</strong> ${properties.elevation}m
                        </div>`;
                    }
                    
                    if (properties.confidence) {
                        const confidenceColor = properties.confidence > 0.7 ? '#22c55e' : 
                                               properties.confidence > 0.4 ? '#eab308' : '#ef4444';
                        clickHtml += `<div style="margin-bottom: 6px;">
                            <strong>Confidence:</strong> <span style="color: ${confidenceColor};">${(properties.confidence * 100).toFixed(1)}%</span>
                        </div>`;
                    }
                    
                    if (isIntelligentPrediction) {
                        // Show AI-specific detailed information
                        clickHtml += `<div style="margin-bottom: 6px;">
                            <strong>Source:</strong> <span style="color: #8b5cf6;">AI Analysis</span>
                        </div>
                        <div style="margin-bottom: 6px;">
                            <strong>Status:</strong> <span style="color: #f59e0b;">Unexplored Area</span>
                        </div>
                        <div style="margin-bottom: 6px;">
                            <strong>Prediction Method:</strong> <span style="color: #3b82f6;">Machine Learning</span>
                        </div>`;
                        
                        // Add comprehensive geological assessment
                        const formation = properties.description.split(' in ')[1]?.split(' with ')[0] || 'Potaro Group metasediments';
                        const descriptionParts = properties.description.split('. ');
                        
                        clickHtml += `<hr style="margin: 12px 0; border: none; border-top: 1px solid #e5e7eb;">
                        <div style="margin-bottom: 6px;">
                            <strong>Geological Assessment:</strong>
                        </div>
                        <div style="font-size: 12px; color: #374151; line-height: 1.4; background: #f0f9ff; padding: 10px; border-radius: 6px; border-left: 4px solid #3b82f6;">
                            <strong>Regional Geology:</strong> ${formation} (Proterozoic)<br>
                            <strong>Structural Setting:</strong> NE-SW trending shear zones, D2 deformation<br>
                            <strong>Metamorphic Grade:</strong> Greenschist to lower amphibolite facies<br>
                            <strong>Alteration Assemblage:</strong> Silicification, sericitization, carbonatization<br>
                            <strong>Mineralization Style:</strong> Orogenic gold-quartz vein systems<br>
                            <strong>Ore Controls:</strong> Shear zone intersections, competency contrasts<br>
                            <strong>AI Analysis:</strong> ${descriptionParts[0] || 'Location-specific geological modeling'}
                        </div>`;
                        
                        // Add location-specific technical specifications
                        const expectedDepth = properties.elevation > 400 ? '100-300m (oxidized zone: 0-50m)' : '50-200m (oxidized zone: 0-30m)';
                        const veinWidth = properties.confidence > 0.7 ? '1.0-3.0m width' : '0.5-2.0m width';
                        const gradePotential = properties.gold_probability > 0.7 ? '5-12 g/t Au (high-grade shoots: 15-25 g/t)' : '3-8 g/t Au (high-grade shoots: 10-20 g/t)';
                        const strikeLength = properties.confidence > 0.6 ? '300-800m (high potential for extension)' : '200-500m (potential for extension)';
                        
                        clickHtml += `<div style="margin-top: 12px; margin-bottom: 6px;">
                            <strong>Technical Specifications:</strong>
                        </div>
                        <div style="font-size: 12px; color: #374151; line-height: 1.4; background: #fef3c7; padding: 10px; border-radius: 6px; border-left: 4px solid #f59e0b;">
                            <strong>Depth Range:</strong> ${expectedDepth}<br>
                            <strong>Vein Characteristics:</strong> ${veinWidth}, steeply dipping (60-80°)<br>
                            <strong>Grade Potential:</strong> ${gradePotential}<br>
                            <strong>Host Rock:</strong> Greenschist facies metasediments<br>
                            <strong>Strike Length:</strong> ${strikeLength}<br>
                            <strong>Ore Minerals:</strong> ${properties.minerals?.join(', ') || 'Native gold, pyrite, arsenopyrite'}<br>
                            <strong>Gangue Minerals:</strong> Quartz, sericite, carbonate<br>
                            <strong>Gold Probability:</strong> ${(properties.gold_probability * 100).toFixed(1)}%
                        </div>`;
                        
                        // Add exploration program
                        clickHtml += `<div style="margin-top: 12px; margin-bottom: 6px;">
                            <strong>Recommended Exploration Program:</strong>
                        </div>
                        <div style="font-size: 12px; color: #374151; line-height: 1.4; background: #ecfdf5; padding: 10px; border-radius: 6px; border-left: 4px solid #10b981;">
                            <strong>Phase 1 - Reconnaissance (2-3 months):</strong><br>
                            • 1:10,000 geological mapping<br>
                            • Soil geochemistry (50m x 50m grid)<br>
                            • Rock chip sampling (100 samples)<br>
                            • Cost estimate: $50,000-75,000<br><br>
                            
                            <strong>Phase 2 - Detailed Exploration (4-6 months):</strong><br>
                            • 1:2,000 geological mapping<br>
                            • Ground magnetic survey (25m x 25m)<br>
                            • Induced polarization (IP) survey<br>
                            • Trenching program (500m total)<br>
                            • Cost estimate: $150,000-200,000<br><br>
                            
                            <strong>Phase 3 - Drilling (6-12 months):</strong><br>
                            • RC drilling: 2,000m (20 holes)<br>
                            • Diamond drilling: 1,000m (10 holes)<br>
                            • Metallurgical testing<br>
                            • Resource estimation<br>
                            • Cost estimate: $500,000-750,000
                        </div>`;
                        
                        // Add soil analysis if available
                        if (properties.soil_type && properties.soil_type !== 'unknown') {
                            clickHtml += `<div style="margin-top: 12px; margin-bottom: 6px;">
                                <strong>Soil Analysis:</strong>
                            </div>
                            <div style="font-size: 12px; color: #374151; line-height: 1.4; background: #ecfdf5; padding: 10px; border-radius: 6px; border-left: 4px solid #10b981;">
                                <strong>Soil Type:</strong> ${properties.soil_type}<br>
                                <strong>pH Level:</strong> ${properties.ph_level?.toFixed(1) || '6.0-7.0'}<br>
                                <strong>Organic Content:</strong> ${properties.organic_content?.toFixed(1) || '2-4'}%<br>
                                <strong>Mineral Content:</strong> ${properties.mineral_content || 'Quartz, feldspar, mica'}<br>
                                <strong>Geochemical Suitability:</strong> ${properties.ph_level > 6.5 ? 'Favorable for gold leaching' : 'Standard processing required'}
                            </div>`;
                        }
                        
                        // Add mining considerations
                        clickHtml += `<div style="margin-top: 12px; margin-bottom: 6px;">
                            <strong>Mining Considerations:</strong>
                        </div>
                        <div style="font-size: 12px; color: #374151; line-height: 1.4; background: #fef2f2; padding: 10px; border-radius: 6px; border-left: 4px solid #ef4444;">
                            <strong>Mining Method:</strong> Open pit (oxide) + Underground (sulfide)<br>
                            <strong>Processing:</strong> Gravity + CIL circuit<br>
                            <strong>Recovery:</strong> 85-90% (oxide), 75-80% (sulfide)<br>
                            <strong>Infrastructure:</strong> Road access required, power grid 15km<br>
                            <strong>Environmental:</strong> EIA required, water management plan<br>
                            <strong>Permitting:</strong> Mining license, environmental clearance<br>
                            <strong>CAPEX Estimate:</strong> $5-10M (small-scale operation)
                        </div>`;
                        
                        // Add regulatory requirements
                        clickHtml += `<div style="margin-top: 12px; padding: 8px; background: #f3f4f6; border-radius: 4px; border-left: 3px solid #6b7280;">
                            <strong style="color: #374151;">Regulatory Requirements:</strong><br>
                            • Guyana Geology and Mines Commission (GGMC) permit<br>
                            • Environmental Protection Agency (EPA) clearance<br>
                            • Amerindian consultation (if applicable)<br>
                            • Water license and waste management plan<br>
                            • Safety and health management system
                        </div>`;
                    } else {
                        // Show real geological survey data information
                        clickHtml += `<div style="margin-bottom: 6px;">
                            <strong>Data Type:</strong> <span style="color: #10b981;">📋 Real Survey Data</span>
                        </div>`;
                        if (properties.survey_title && properties.survey_title !== 'Unknown') {
                            clickHtml += `<div style="margin-bottom: 6px;">
                                <span style="font-size:15px;">📄</span> <strong>Survey:</strong> ${properties.survey_title}
                            </div>`;
                        }
                        if (properties.survey_date) {
                            clickHtml += `<div style="margin-bottom: 6px;">
                                <span style="font-size:15px;">📅</span> <strong>Date:</strong> ${properties.survey_date}
                            </div>`;
                        }
                        if (properties.feature_type) {
                            clickHtml += `<div style="margin-bottom: 6px;">
                                <span style="font-size:15px;">🪨</span> <strong>Feature Type:</strong> ${properties.feature_type}
                            </div>`;
                        }
                        if (properties.elevation) {
                            clickHtml += `<div style="margin-bottom: 6px;">
                                <span style="font-size:15px;">⛰️</span> <strong>Elevation:</strong> ${properties.elevation} m
                            </div>`;
                        }
                        if (properties.soil_type && properties.soil_type !== 'unknown') {
                            clickHtml += `<div style="margin-bottom: 6px;">
                                <span style="font-size:15px;">🌱</span> <strong>Soil Type:</strong> ${properties.soil_type}
                            </div>`;
                        }
                        if (properties.minerals && Array.isArray(properties.minerals) && properties.minerals.length > 0) {
                            clickHtml += `<div style="margin-bottom: 6px;">
                                <span style="font-size:15px;">⛏️</span> <strong>Minerals:</strong> ${properties.minerals.join(', ')}
                            </div>`;
                        } else if (properties.minerals && typeof properties.minerals === 'string') {
                            clickHtml += `<div style="margin-bottom: 6px;">
                                <span style="font-size:15px;">⛏️</span> <strong>Minerals:</strong> ${properties.minerals}
                            </div>`;
                        }
                        if (typeof properties.gold_probability === 'number') {
                            clickHtml += `<div style="margin-bottom: 6px;">
                                <span style="font-size:15px;">🥇</span> <strong>Gold Probability:</strong> ${(properties.gold_probability * 100).toFixed(1)}%
                            </div>`;
                        }
                        if (typeof properties.confidence === 'number') {
                            clickHtml += `<div style="margin-bottom: 6px;">
                                <span style="font-size:15px;">✅</span> <strong>Confidence:</strong> ${(properties.confidence * 100).toFixed(1)}%
                            </div>`;
                        }
                        if (properties.description) {
                            clickHtml += `<hr style="margin: 12px 0; border: none; border-top: 1px solid #e5e7eb;">
                            <div style="margin-bottom: 6px;">
                                <span style="font-size:15px;">📝</span> <strong>Description:</strong>
                            </div>
                            <div style="font-size: 12px; color: #374151; line-height: 1.4; background: #f0f9ff; padding: 10px; border-radius: 6px; border-left: 4px solid #3b82f6;">
                                ${properties.description}
                            </div>`;
                        }
                        // Add survey metadata
                        clickHtml += `<hr style="margin: 12px 0; border: none; border-top: 1px solid #e5e7eb;">
                        <div style="margin-bottom: 6px;">
                            <span style="font-size:15px;">📁</span> <strong>Source Document:</strong> ${properties.source_file || 'Uploaded PDF'}
                        </div>
                        <div style="margin-bottom: 6px;">
                            <span style="font-size:15px;">🤖</span> <strong>Extraction Method:</strong> LLM text analysis
                        </div>`;
                        // Add soil analysis details if available
                        if (typeof properties.ph_level === 'number' || typeof properties.organic_content === 'number' || properties.mineral_content) {
                            clickHtml += `<div style="margin-top: 6px; font-size: 12px; color: #374151; line-height: 1.4; background: #ecfdf5; padding: 10px; border-radius: 6px; border-left: 4px solid #10b981;">
                                <strong>Soil Analysis:</strong><br>
                                ${typeof properties.ph_level === 'number' ? '• pH: ' + properties.ph_level.toFixed(1) + '<br>' : ''}
                                ${typeof properties.organic_content === 'number' ? '• Organic content: ' + properties.organic_content.toFixed(1) + '%<br>' : ''}
                                ${properties.mineral_content ? '• Mineral content: ' + properties.mineral_content + '<br>' : ''}
                            </div>`;
                        }
                    }
                    
                    clickHtml += '</div></div>';
                    
                    clickPopup.setHTML(clickHtml);
                    clickPopup.setLngLat(coordinates).addTo(map);
                });
            })
            .catch(error => {
                console.error('Error loading geological features:', error);
            });
    }

    // Global variables for trend line hover popup
    let hoveredTrendId = null;
    let trendPopup = null;
    
    // Global variables for map refresh
    let mapRefreshInterval = null;
    let lastRefreshTime = Date.now();
    
    // Create popup for trend line hover
    function createTrendLinePopup() {
        if (!trendPopup) {
            trendPopup = new mapboxgl.Popup({
                closeButton: false,
                maxWidth: '300px',
                className: 'trend-line-popup'
            });
        }
        return trendPopup;
    }
    
    // Show trend line hover popup
    function showTrendLineHoverPopup(e, map) {
        console.log('showTrendLineHoverPopup called');
        const feature = e.features[0];
        if (!feature) {
            console.log('No feature found');
            return;
        }
        
        const properties = feature.properties;
        console.log('Trend properties:', properties);
        
        // Get coordinates from the feature geometry instead of properties
        const coordinates = feature.geometry.coordinates || [];
        console.log('Trend coordinates:', coordinates);
        
        if (coordinates.length < 2) {
            console.log('Not enough coordinates');
            return;
        }
        
        // Calculate trend range and direction
        const startCoord = coordinates[0];
        const endCoord = coordinates[1];
        const distance = Math.sqrt(
            Math.pow(endCoord[0] - startCoord[0], 2) + 
            Math.pow(endCoord[1] - startCoord[1], 2)
        ) * 111; // Approximate km conversion
        
        // Calculate direction
        const angle = Math.atan2(endCoord[1] - startCoord[1], endCoord[0] - startCoord[0]) * 180 / Math.PI;
        const direction = angle >= -22.5 && angle < 22.5 ? 'E' :
                         angle >= 22.5 && angle < 67.5 ? 'NE' :
                         angle >= 67.5 && angle < 112.5 ? 'N' :
                         angle >= 112.5 && angle < 157.5 ? 'NW' :
                         angle >= 157.5 || angle < -157.5 ? 'W' :
                         angle >= -157.5 && angle < -112.5 ? 'SW' :
                         angle >= -112.5 && angle < -67.5 ? 'S' : 'SE';
        
        // Format coordinates
        const formatCoord = (coord) => {
            const lat = coord[1].toFixed(4);
            const lng = coord[0].toFixed(4);
            return `${lat}°N, ${lng}°W`;
        };
        
        // Create enhanced popup content similar to gold predictions
        let html = `<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 300px;">
            <div style="border-left: 4px solid ${properties.color}; padding-left: 8px; margin-bottom: 8px;">
                <strong style="color: ${properties.color}; font-size: 14px;">${properties.name}</strong>
            </div>
            <div style="font-size: 12px; line-height: 1.4;">
                <div style="margin-bottom: 4px;">
                    <strong>Type:</strong> ${properties.type}
                </div>
                <div style="margin-bottom: 4px;">
                    <strong>Direction:</strong> ${direction} (${distance.toFixed(1)} km)
                </div>
                <div style="margin-bottom: 4px;">
                    <strong>Confidence:</strong> <span style="color: ${properties.confidence > 0.7 ? '#22c55e' : properties.confidence > 0.4 ? '#eab308' : '#ef4444'};">${(properties.confidence * 100).toFixed(1)}%</span>
                </div>
                <div style="margin-bottom: 4px;">
                    <strong>Features:</strong> ${properties.feature_count} geological points
                </div>
                <div style="margin-bottom: 4px;">
                    <strong>Start:</strong> ${formatCoord(startCoord)}
                </div>
                <div style="margin-bottom: 4px;">
                    <strong>End:</strong> ${formatCoord(endCoord)}
                </div>`;
        
        // Add metadata if available
        const metadata = properties.metadata || {};
        if (metadata.formation_types && metadata.formation_types.length > 0) {
            html += `<div style="margin-bottom: 4px;">
                <strong>Formations:</strong> ${metadata.formation_types.slice(0, 3).join(', ')}${metadata.formation_types.length > 3 ? '...' : ''}
            </div>`;
        }
        
        if (metadata.mineral_types && metadata.mineral_types.length > 0) {
            html += `<div style="margin-bottom: 4px;">
                <strong>Minerals:</strong> ${metadata.mineral_types.slice(0, 3).join(', ')}${metadata.mineral_types.length > 3 ? '...' : ''}
            </div>`;
        }
        
        if (metadata.elevation_range) {
            html += `<div style="margin-bottom: 4px;">
                <strong>Elevation:</strong> ${metadata.elevation_range.avg.toFixed(0)}m (${metadata.elevation_range.min.toFixed(0)}-${metadata.elevation_range.max.toFixed(0)}m)
            </div>`;
        }
        
        // Add supporting features if available
        const supportingFeatures = properties.supporting_features || [];
        if (supportingFeatures.length > 0) {
            html += `<hr style="margin: 8px 0; border: none; border-top: 1px solid #e5e7eb;">
            <div style="margin-bottom: 4px;">
                <strong>Key Features:</strong>
            </div>`;
            
            supportingFeatures.slice(0, 2).forEach(feature => {
                html += `<div style="margin-bottom: 2px; padding: 2px 4px; background: #f3f4f6; border-radius: 3px; font-size: 11px;">
                    <strong>${feature.type}:</strong> ${feature.description}
                </div>`;
            });
            
            if (supportingFeatures.length > 2) {
                html += `<div style="font-size: 11px; color: #6b7280;">+${supportingFeatures.length - 2} more features</div>`;
            }
        }
        
        html += '</div></div>';
        
        // Create popup similar to gold predictions
        const popup = new mapboxgl.Popup({
            closeButton: false,
            closeOnClick: false,
            maxWidth: '320px'
        });
        
        popup.setHTML(html);
        popup.setLngLat(e.lngLat).addTo(map);
        
        // Change cursor
        map.getCanvas().style.cursor = 'pointer';
    }
    
    // Show popup for overlapping trends
    function showOverlappingTrendsPopup(e, map) {
        console.log('showOverlappingTrendsPopup called with', e.features.length, 'features');
        
        if (e.features.length === 0) return;
        
        // Create popup content for all overlapping trends
        let html = `<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 400px;">
            <div style="margin-bottom: 8px;">
                <strong style="font-size: 14px; color: #374151;">Overlapping Trends (${e.features.length})</strong>
            </div>
            <div style="max-height: 300px; overflow-y: auto;">`;
        
        e.features.forEach((feature, index) => {
            const properties = feature.properties;
            const coordinates = feature.geometry.coordinates || [];
            
            // Calculate direction and distance for line features
            let directionInfo = '';
            if (coordinates.length >= 2) {
                const startCoord = coordinates[0];
                const endCoord = coordinates[1];
                const distance = Math.sqrt(
                    Math.pow(endCoord[0] - startCoord[0], 2) + 
                    Math.pow(endCoord[1] - startCoord[1], 2)
                ) * 111; // Approximate km conversion
                
                const angle = Math.atan2(endCoord[1] - startCoord[1], endCoord[0] - startCoord[0]) * 180 / Math.PI;
                const direction = angle >= -22.5 && angle < 22.5 ? 'E' :
                                 angle >= 22.5 && angle < 67.5 ? 'NE' :
                                 angle >= 67.5 && angle < 112.5 ? 'N' :
                                 angle >= 112.5 && angle < 157.5 ? 'NW' :
                                 angle >= 157.5 || angle < -157.5 ? 'W' :
                                 angle >= -157.5 && angle < -112.5 ? 'SW' :
                                 angle >= -112.5 && angle < -67.5 ? 'S' : 'SE';
                
                directionInfo = ` • ${direction} (${distance.toFixed(1)} km)`;
            }
            
            html += `
                <div style="border-left: 4px solid ${properties.color}; padding: 8px; margin-bottom: 8px; background: #f9fafb; border-radius: 4px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                        <strong style="color: ${properties.color}; font-size: 13px;">${properties.name}</strong>
                        <span style="font-size: 11px; color: #6b7280;">#${index + 1}</span>
                    </div>
                    <div style="font-size: 11px; line-height: 1.3; color: #374151;">
                        <div><strong>Type:</strong> ${properties.type}${directionInfo}</div>
                        <div><strong>Confidence:</strong> <span style="color: ${properties.confidence > 0.7 ? '#22c55e' : properties.confidence > 0.4 ? '#eab308' : '#ef4444'};">${(properties.confidence * 100).toFixed(1)}%</span></div>
                        <div><strong>Features:</strong> ${properties.feature_count} geological points</div>`;
            
            // Add metadata if available
            const metadata = properties.metadata || {};
            if (metadata.formation_types && metadata.formation_types.length > 0) {
                html += `<div><strong>Formations:</strong> ${metadata.formation_types.slice(0, 2).join(', ')}${metadata.formation_types.length > 2 ? '...' : ''}</div>`;
            }
            
            if (metadata.mineral_types && metadata.mineral_types.length > 0) {
                html += `<div><strong>Minerals:</strong> ${metadata.mineral_types.slice(0, 2).join(', ')}${metadata.mineral_types.length > 2 ? '...' : ''}</div>`;
            }
            
            if (metadata.elevation_range) {
                html += `<div><strong>Elevation:</strong> ${metadata.elevation_range.avg.toFixed(0)}m</div>`;
            }
            
            html += `</div></div>`;
        });
        
        html += `</div>
            <div style="font-size: 10px; color: #6b7280; margin-top: 8px; text-align: center;">
                Hover over individual trends to see more details
            </div>
        </div>`;
        
        // Create popup
        const popup = new mapboxgl.Popup({
            closeButton: true,
            closeOnClick: false,
            maxWidth: '400px'
        });
        
        popup.setHTML(html);
        popup.setLngLat(e.lngLat).addTo(map);
        
        // Change cursor
        map.getCanvas().style.cursor = 'pointer';
    }
    
    // Hide trend line hover popup
    function hideTrendLineHoverPopup(map) {
        // Remove all popups (Mapbox automatically handles this)
        const popups = document.querySelectorAll('.mapboxgl-popup');
        popups.forEach(popup => popup.remove());
        map.getCanvas().style.cursor = '';
    }

    function loadMineralizationTrends(map) {
        console.log('loadMineralizationTrends called for map:', map);
        
        // Check if source already exists and remove it first
        if (map.getSource('mineralization-trends')) {
            map.removeLayer('mineralization-trends-points');
            map.removeLayer('mineralization-trends-labels');
            map.removeLayer('mineralization-trends-lines');
            map.removeSource('mineralization-trends');
        }
        
        // Add trend lines source
        map.addSource('mineralization-trends', {
            'type': 'geojson',
            'data': {
                'type': 'FeatureCollection',
                'features': []
            }
        });
        
        // Add trend lines layer
        map.addLayer({
            'id': 'mineralization-trends-lines',
            'type': 'line',
            'source': 'mineralization-trends',
            'paint': {
                'line-color': ['get', 'color'],
                'line-width': 6,  // Make lines thicker
                'line-opacity': 0.9,  // Make lines more visible
                'line-dasharray': [4, 4]  // Make dashed pattern more visible
            },
            'filter': ['==', ['get', 'visible'], true]
        });
        console.log('Added mineralization-trends-lines layer');
        
        // Add trend labels
        map.addLayer({
            'id': 'mineralization-trends-labels',
            'type': 'symbol',
            'source': 'mineralization-trends',
            'layout': {
                'text-field': ['get', 'name'],
                'text-font': ['Open Sans Bold'],
                'text-size': 12,
                'text-offset': [0, -1.5],
                'text-anchor': 'center',
                'text-allow-overlap': false,
                'text-ignore-placement': false
            },
            'paint': {
                'text-color': ['get', 'color'],
                'text-halo-color': '#ffffff',
                'text-halo-width': 1
            },
            'filter': ['==', ['get', 'visible'], true]
        });
        
        // Add trend points (for interaction) - make them invisible but interactive for hover
        map.addLayer({
            'id': 'mineralization-trends-points',
            'type': 'circle',
            'source': 'mineralization-trends',
            'paint': {
                'circle-radius': 0,  // Make points invisible
                'circle-color': ['get', 'color'],
                'circle-opacity': 0,  // Completely transparent
                'circle-stroke-width': 0,
                'circle-stroke-color': ['get', 'color'],
                'circle-stroke-opacity': 0
            },
            'filter': ['==', ['get', 'visible'], true]
        });
        console.log('Added mineralization-trends-points layer');
        
        // Add hover events for trend lines - handle overlapping trends
        map.on('mouseenter', 'mineralization-trends-lines', function(e) {
            console.log('Trend line hover detected:', e.features.length, 'features');
            if (e.features.length > 0) {
                // Show popup for all overlapping trends
                showOverlappingTrendsPopup(e, map);
                
                // Highlight all hovered trends
                const hoveredIds = e.features.map(f => f.properties.id);
                map.setPaintProperty('mineralization-trends-lines', 'line-width', 
                    ['case',
                        ['in', ['get', 'id'], ['literal', hoveredIds]], 6,
                        4
                    ]
                );
            }
        });
        console.log('Added mouseenter event listener for trend lines');
        
        map.on('mouseleave', 'mineralization-trends-lines', function() {
            hoveredTrendId = null;
            hideTrendLineHoverPopup(map);
            
            // Reset line width
            map.setPaintProperty('mineralization-trends-lines', 'line-width', 4);
        });
        
        // Add click handler for trend lines
        map.on('click', 'mineralization-trends-points', function(e) {
            const feature = e.features[0];
            if (feature) {
                showTrendDetails(feature.properties);
            }
        });
        
        // Enhanced hover for trend points - handle overlapping trends
        map.on('mouseenter', 'mineralization-trends-points', function(e) {
            console.log('Trend point hover detected:', e.features.length, 'features');
            if (e.features.length > 0) {
                // Show popup for all overlapping trends
                showOverlappingTrendsPopup(e, map);
            }
        });
        
        map.on('mouseleave', 'mineralization-trends-points', function() {
            // Remove popups
            const popups = document.querySelectorAll('.mapboxgl-popup');
            popups.forEach(popup => popup.remove());
            map.getCanvas().style.cursor = '';
        });
        
        // Load initial trends
        updateMineralizationTrends(map);
    }
    
    // Update mineralization trends
    function updateMineralizationTrends(map, trendType = 'all', confidence = 0.1) {
        const url = `/api/mineralization-trends/?type=${trendType}&confidence=${confidence}`;
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const trends = data.trends;
                    const features = trends.map((trend, index) => {
                        // Spread out overlapping trends by slightly offsetting coordinates
                        const offset = index * 0.001; // Small offset for each trend
                        const baseCoords = trend.coordinates;
                        
                        // Create slightly offset coordinates for overlapping trends
                        const offsetCoords = baseCoords.map(coord => [
                            coord[0] + offset,
                            coord[1] + offset
                        ]);
                        
                        return {
                            'type': 'Feature',
                            'geometry': {
                                'type': 'LineString',
                                'coordinates': offsetCoords
                            },
                            'properties': {
                                'id': trend.id,
                                'name': trend.name,
                                'type': trend.type,
                                'color': trend.color,
                                'confidence': trend.confidence,
                                'feature_count': trend.feature_count,
                                'supporting_features': trend.supporting_features,
                                'metadata': trend.metadata,
                                'visible': true,
                                'original_coordinates': baseCoords,
                                'offset_index': index
                            }
                        };
                    });
                    
                    // Update the source data
                    const source = map.getSource('mineralization-trends');
                    if (source) {
                        source.setData({
                            'type': 'FeatureCollection',
                            'features': features
                        });
                    }
                    
                    console.log(`Loaded ${trends.length} mineralization trends`);
                    console.log('Trend features:', features);
                    
                    // Show status message
                    const statusDiv = document.getElementById('trend-status');
                    if (statusDiv) {
                        statusDiv.innerHTML = `<span class="text-green-600">Loaded ${trends.length} mineralization trends from ${data.total_features_analyzed} geological features</span>`;
                    }
                    
                    // Debug: Check if layers exist
                    console.log('Trend layers exist:', {
                        'mineralization-trends-lines': map.getLayer('mineralization-trends-lines'),
                        'mineralization-trends-points': map.getLayer('mineralization-trends-points'),
                        'mineralization-trends-labels': map.getLayer('mineralization-trends-labels')
                    });
                    

                } else {
                    console.error('Error loading trends:', data.error);
                    const statusDiv = document.getElementById('trend-status');
                    if (statusDiv) {
                        statusDiv.innerHTML = `<span class="text-red-600">Error: ${data.error}</span>`;
                    }
                    

                }
            })
            .catch(error => {
                console.error('Error fetching trends:', error);
                const statusDiv = document.getElementById('trend-status');
                if (statusDiv) {
                    statusDiv.innerHTML = '<span class="text-red-600">Error loading trends</span>';
                }
            });
    }
    
    // Show trend details in a popup
    function showTrendDetails(trendProperties) {
        const popup = new mapboxgl.Popup({
            closeButton: true,
            maxWidth: '400px'
        });
        
        const supportingFeatures = trendProperties.supporting_features || [];
        const metadata = trendProperties.metadata || {};
        
        let popupContent = `
            <div class="trend-popup">
                <h3 class="font-bold text-lg mb-2" style="color: ${trendProperties.color};">${trendProperties.name}</h3>
                <div class="text-sm space-y-1">
                    <p><strong>Type:</strong> ${trendProperties.type}</p>
                    <p><strong>Confidence:</strong> ${(trendProperties.confidence * 100).toFixed(1)}%</p>
                    <p><strong>Features:</strong> ${trendProperties.feature_count}</p>
                </div>
        `;
        
        if (metadata.formation_types && metadata.formation_types.length > 0) {
            popupContent += `<p><strong>Formations:</strong> ${metadata.formation_types.join(', ')}</p>`;
        }
        
        if (metadata.mineral_types && metadata.mineral_types.length > 0) {
            popupContent += `<p><strong>Minerals:</strong> ${metadata.mineral_types.join(', ')}</p>`;
        }
        
        if (metadata.elevation_range) {
            popupContent += `<p><strong>Elevation:</strong> ${metadata.elevation_range.avg.toFixed(0)}m (${metadata.elevation_range.min.toFixed(0)}-${metadata.elevation_range.max.toFixed(0)}m)</p>`;
        }
        
        if (supportingFeatures.length > 0) {
            popupContent += `
                <div class="mt-3">
                    <h4 class="font-semibold mb-1">Supporting Features:</h4>
                    <div class="max-h-32 overflow-y-auto">
            `;
            
            supportingFeatures.forEach(feature => {
                popupContent += `
                    <div class="text-xs p-1 bg-gray-100 rounded mb-1">
                        <strong>${feature.type}:</strong> ${feature.description}<br>
                        <span class="text-gray-600">Confidence: ${(feature.confidence * 100).toFixed(1)}%</span>
                    </div>
                `;
            });
            
            popupContent += `
                    </div>
                </div>
            `;
        }
        
        popupContent += '</div>';
        
        popup.setHTML(popupContent);
        
        // Show popup at the center of the trend
        const center = trendProperties.center || trendProperties.coordinates[0];
        popup.setLngLat(center).addTo(currentMap);
    }

    // Clear mineralization trends
    window.clearMineralizationTrends = function(map) {
        const source = map.getSource('mineralization-trends');
        if (source) {
            source.setData({
                'type': 'FeatureCollection',
                'features': []
            });
        }
        

    };
    
    // Toggle mineralization trends visibility
    window.toggleMineralizationTrendsVisibility = function(map, visible) {
        const filter = visible ? ['==', ['get', 'visible'], true] : ['==', ['get', 'visible'], false];
        
        if (map.getLayer('mineralization-trends-lines')) {
            map.setFilter('mineralization-trends-lines', filter);
        }
        if (map.getLayer('mineralization-trends-labels')) {
            map.setFilter('mineralization-trends-labels', filter);
        }
        if (map.getLayer('mineralization-trends-points')) {
            map.setFilter('mineralization-trends-points', filter);
        }
    };
    

    
    // Highlight specific trend
    window.highlightTrend = function(trendId) {
        const map = window.currentMap || window.map2D;
        if (!map) return;
        
        // Reset all trends to normal opacity
        map.setPaintProperty('mineralization-trends-lines', 'line-opacity', 0.8);
        
        // Highlight the selected trend
        map.setFilter('mineralization-trends-lines', ['==', ['get', 'id'], trendId]);
        map.setPaintProperty('mineralization-trends-lines', 'line-opacity', 1.0);
        map.setPaintProperty('mineralization-trends-lines', 'line-width', 6);
        
        // Reset filter after 3 seconds
        setTimeout(() => {
            map.setFilter('mineralization-trends-lines', ['==', ['get', 'visible'], true]);
            map.setPaintProperty('mineralization-trends-lines', 'line-opacity', 0.8);
            map.setPaintProperty('mineralization-trends-lines', 'line-width', 4);
        }, 3000);
    };
    
    // Update mineralization trends with custom data
    window.updateMineralizationTrendsWithData = function(map, trends) {
        const features = trends.map((trend, index) => {
            // Spread out overlapping trends by slightly offsetting coordinates
            const offset = index * 0.001; // Small offset for each trend
            const baseCoords = trend.coordinates;
            
            // Create slightly offset coordinates for overlapping trends
            const offsetCoords = baseCoords.map(coord => [
                coord[0] + offset,
                coord[1] + offset
            ]);
            
            return {
                'type': 'Feature',
                'geometry': {
                    'type': 'LineString',
                    'coordinates': offsetCoords
                },
                'properties': {
                    'id': trend.id,
                    'name': trend.name,
                    'type': trend.type,
                    'color': trend.color,
                    'confidence': trend.confidence,
                    'feature_count': trend.feature_count,
                    'supporting_features': trend.supporting_features,
                    'metadata': trend.metadata,
                    'visible': true,
                    'original_coordinates': baseCoords,
                    'offset_index': index
                }
            };
        });
        
        const source = map.getSource('mineralization-trends');
        if (source) {
            source.setData({
                'type': 'FeatureCollection',
                'features': features
            });
        }
        

    };
    
    // Function to refresh all map data
    function refreshMapData(map) {
        console.log('🔄 Refreshing map data...');
        
        // Refresh gold predictions
        if (map.getSource('gold-predictions')) {
            loadGoldPredictions(map);
        }
        
        // Refresh geological features
        if (map.getSource('geological-features')) {
            loadGeologicalFeatures(map);
        }
        
        // Refresh mineralization trends
        if (map.getSource('mineralization-trends')) {
            updateMineralizationTrends(map);
        }
        
        lastRefreshTime = Date.now();
        console.log('✅ Map data refreshed');
    }
    
    // Function to start automatic map refresh
    function startMapAutoRefresh(map, intervalSeconds = 30) {
        if (mapRefreshInterval) {
            clearInterval(mapRefreshInterval);
        }
        
        mapRefreshInterval = setInterval(() => {
            refreshMapData(map);
        }, intervalSeconds * 1000);
        
        console.log(`🔄 Auto-refresh started (every ${intervalSeconds} seconds)`);
    }
    
    // Function to stop automatic map refresh
    function stopMapAutoRefresh() {
        if (mapRefreshInterval) {
            clearInterval(mapRefreshInterval);
            mapRefreshInterval = null;
            console.log('⏹️ Auto-refresh stopped');
        }
    }
    
    // Function to manually refresh map (can be called from other parts of the app)
    window.refreshMap = function() {
        if (map2D) {
            refreshMapData(map2D);
        }
        if (map3D) {
            refreshMapData(map3D);
        }
    };
    
    // Function to check for model training completion and refresh map
    function checkModelTrainingStatus() {
        fetch('/api/openai-training-status/')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.status.model_trained) {
                    // Model was recently trained, refresh map
                    console.log('🤖 Model training detected, refreshing map...');
                    refreshMapData(map2D);
                    refreshMapData(map3D);
                }
            })
            .catch(error => {
                console.error('Error checking model training status:', error);
            });
    }
    
    // Start auto-refresh for both maps after they're loaded
    setTimeout(() => {
        if (map2D) {
            startMapAutoRefresh(map2D, 30); // Refresh every 30 seconds
        }
        if (map3D) {
            startMapAutoRefresh(map3D, 30); // Refresh every 30 seconds
        }
        
        // Check for model training status every 60 seconds
        setInterval(checkModelTrainingStatus, 60000);
    }, 5000); // Start after 5 seconds to ensure maps are fully loaded

}); 