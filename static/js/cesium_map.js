// Cesium 3D Map for GoldMine AI
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the cesium map page
    const cesiumContainer = document.getElementById('cesium-container');
    if (!cesiumContainer) {
        console.log('Cesium container not found, exiting initialization');
        return;
    }

    console.log('Initializing Cesium globe');
    
    try {
        // Your Cesium access token - using default token for development
        Cesium.Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiIxZDUyN2FmYy0xZmY4LTRhZTQtODI4Yy03ZGFjYWZjNDI1ODYiLCJpZCI6MzA1OTMyLCJpYXQiOjE3NDgxMDY2NzR9.1CBxE3hXUc4yVtK_84hrm_iBqfBpbw9wC35Q4F2P8Bw';
        
        // Create a basic Cesium viewer with default providers
        const viewer = new Cesium.Viewer('cesium-container', {
            // No imagery provider specified - use default
            baseLayerPicker: true, // Enable the layer picker so user can choose imagery
            geocoder: false,
            homeButton: true,
            sceneModePicker: true,
            navigationHelpButton: true,
            animation: false,
            timeline: false,
            fullscreenButton: true
        });

        console.log('Cesium viewer created successfully');
        
        // Remove default Cesium credit container
        viewer.cesiumWidget.creditContainer.style.display = "none";
        
        // Add custom zoom controls
        addZoomControls(viewer, cesiumContainer);
        
        // Store the last search query for use across functions
        let lastSearchQuery = '';
        
        // Connect search bar to globe
        connectSearchBar(viewer);
        
        // Add a highlight to Guyana/Potaro-Siparuni region
        // Coordinates for Potaro-Siparuni region, Guyana
        const POTARO_SIPARUNI_COORDINATES = {
            longitude: -59.2880, // Degrees
            latitude: 4.7856,    // Degrees
            height: 50000.0   // Meters
        };
        
        // Add a point for the Potaro-Siparuni region
        viewer.entities.add({
            position: Cesium.Cartesian3.fromDegrees(
                POTARO_SIPARUNI_COORDINATES.longitude, 
                POTARO_SIPARUNI_COORDINATES.latitude
            ),
            point: {
                pixelSize: 10,
                color: Cesium.Color.YELLOW,
                outlineColor: Cesium.Color.BLACK,
                outlineWidth: 10
            },
            label: {
                text: 'Potaro-Siparuni Region',
                font: '14pt sans-serif',
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                outlineWidth: 2,
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                pixelOffset: new Cesium.Cartesian2(0, -9)
            }
        });
        
        // Connect search bar to 3D globe
        function connectSearchBar(viewer) {
            const searchForm = document.getElementById('map-search-form');
            const searchInput = document.getElementById('map-search-input');
            
            if (!searchForm || !searchInput) {
                console.warn('Search form or input not found in the DOM');
                return;
            }
            
            // Create a search results entity for highlighting search results
            let searchResultEntity = null;
            
            // Add event listener for search form submission
            searchForm.addEventListener('submit', function(e) {
                e.preventDefault();
                const searchQuery = searchInput.value.trim();
                
                if (searchQuery) {
                    console.log('Searching for:', searchQuery);
                    lastSearchQuery = searchQuery; // Store the query
                    
                    // Only search if the globe view is currently active
                    if (document.getElementById('cesium-container').style.display === 'block') {
                        searchLocation(searchQuery, viewer);
                    }
                }
            });
            
            // Also listen for the custom search event that might be triggered by map_handler.js
            document.addEventListener('mapSearch', function(event) {
                if (event.detail && event.detail.query) {
                    console.log('Received map search event:', event.detail.query);
                    lastSearchQuery = event.detail.query; // Store the query
                    
                    // Only search if the globe view is currently active
                    if (document.getElementById('cesium-container').style.display === 'block') {
                        searchLocation(event.detail.query, viewer);
                    }
                }
            });
            
            // Listen for map view change to re-apply the last search when switching to globe view
            const mapViewSelector = document.getElementById('map-view-selector');
            if (mapViewSelector) {
                mapViewSelector.addEventListener('change', function() {
                    if (mapViewSelector.value === 'globe' && lastSearchQuery) {
                        // Wait a moment for the globe to be fully visible
                        setTimeout(() => {
                            searchLocation(lastSearchQuery, viewer);
                        }, 300);
                    }
                });
            }
            
            console.log('Search bar connected to 3D globe');
        }
        
        // Search for location and fly to it on the globe
        function searchLocation(query, viewer) {
            // First try to parse as coordinates
            const coordRegex = /^[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)$/;
            
            if (coordRegex.test(query)) {
                // It's coordinates, format: "latitude, longitude"
                const [lat, lng] = query.split(',').map(c => parseFloat(c.trim()));
                flyToLocation(lng, lat, viewer);
                addSearchMarker(lng, lat, `${lat}, ${lng}`, viewer);
                return;
            }
            
            // Otherwise search for location name using Nominatim (OpenStreetMap)
            // Add limit=1 to get only the best match and enhance performance
            fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`)
                .then(response => response.json())
                .then(data => {
                    if (data && data.length > 0) {
                        const location = data[0];
                        const lat = parseFloat(location.lat);
                        const lng = parseFloat(location.lon);
                        
                        console.log('Found location:', location.display_name);
                        flyToLocation(lng, lat, viewer);
                        addSearchMarker(lng, lat, location.display_name, viewer);
                    } else {
                        console.warn('Location not found in global search:', query);
                        
                        // Try a more specific search with additional parameters
                        fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1&addressdetails=1`)
                            .then(response => response.json())
                            .then(data => {
                                if (data && data.length > 0) {
                                    const location = data[0];
                                    const lat = parseFloat(location.lat);
                                    const lng = parseFloat(location.lon);
                                    
                                    console.log('Found location in detailed search:', location.display_name);
                                    flyToLocation(lng, lat, viewer);
                                    addSearchMarker(lng, lat, location.display_name, viewer);
                                } else {
                                    // Final fallback - try search limited to Guyana
                                    fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&countrycodes=gy&limit=1`)
                                        .then(response => response.json())
                                        .then(data => {
                                            if (data && data.length > 0) {
                                                const location = data[0];
                                                const lat = parseFloat(location.lat);
                                                const lng = parseFloat(location.lon);
                                                
                                                console.log('Found location in Guyana:', location.display_name);
                                                flyToLocation(lng, lat, viewer);
                                                addSearchMarker(lng, lat, location.display_name, viewer);
                                            } else {
                                                console.error('Location not found:', query);
                                                // Only show alert if globe view is active
                                                if (document.getElementById('cesium-container').style.display === 'block') {
                                                    alert('Location not found. Please try another search term or use coordinates.');
                                                }
                                            }
                                        })
                                        .catch(error => {
                                            console.error('Error searching location in Guyana:', error);
                                        });
                                }
                            })
                            .catch(error => {
                                console.error('Error in detailed search:', error);
                            });
                    }
                })
                .catch(error => {
                    console.error('Error searching location:', error);
                    // Only show alert if globe view is active
                    if (document.getElementById('cesium-container').style.display === 'block') {
                        alert('An error occurred during the search. Please try again.');
                    }
                });
        }
        
        // Add a marker for search results
        function addSearchMarker(longitude, latitude, name, viewer) {
            // Remove previous search result entity if it exists
            if (viewer.entities.getById('search-result')) {
                viewer.entities.removeById('search-result');
            }
            
            // Add a new marker at the search location
            viewer.entities.add({
                id: 'search-result',
                position: Cesium.Cartesian3.fromDegrees(longitude, latitude),
                billboard: {
                    image: createSearchMarkerImage(),
                    verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                    scale: 0.7, // Slightly larger
                    disableDepthTestDistance: Number.POSITIVE_INFINITY // Always draw on top
                },
                label: {
                    text: name,
                    font: '14pt sans-serif',
                    style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                    outlineWidth: 2,
                    verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                    pixelOffset: new Cesium.Cartesian2(0, -38),
                    fillColor: Cesium.Color.WHITE,
                    outlineColor: Cesium.Color.BLACK,
                    disableDepthTestDistance: Number.POSITIVE_INFINITY, // Always draw on top
                    showBackground: true,
                    backgroundColor: new Cesium.Color(0.1, 0.1, 0.1, 0.7) // Dark semi-transparent background
                },
                description: `<strong>Search Result</strong><br />
                            Coordinates: ${latitude.toFixed(6)}, ${longitude.toFixed(6)}<br />
                            Location: ${name}<br />
                            <em>Click to view details</em>`,
                // Add a pulsing circle to attract attention
                ellipse: {
                    semiMinorAxis: 500, // Size in meters
                    semiMajorAxis: 500, // Size in meters
                    height: 0,
                    material: new Cesium.MaterialProperty({
                        fabric: {
                            type: 'EllipsoidSurface',
                            uniforms: {
                                color: new Cesium.Color(1.0, 0.0, 0.0, 0.5),
                                glowPower: 0.25,
                                glowLimit: 0.6
                            },
                            source: `
                                czm_material czm_getMaterial(czm_materialInput materialInput) {
                                    czm_material material = czm_getDefaultMaterial(materialInput);
                                    float d = length(materialInput.st - 0.5) * 2.0;
                                    float t = fract(czm_frameNumber / 120.0) * 3.14159265 * 2.0;
                                    float alpha = pow(abs(sin(t)), 0.5) * (1.0 - d);
                                    material.alpha = alpha * 0.5;
                                    material.diffuse = color.rgb;
                                    return material;
                                }
                            `
                        }
                    })
                }
            });
            
            console.log('Search marker added at:', longitude, latitude);
        }
        
        // Create a search marker image (a red pin)
        function createSearchMarkerImage() {
            // Create a canvas for the pin
            const canvas = document.createElement('canvas');
            canvas.width = 64;
            canvas.height = 64;
            const context = canvas.getContext('2d');
            
            // Draw a pin
            context.beginPath();
            context.arc(32, 20, 12, 0, 2 * Math.PI);
            context.fillStyle = '#FF4136';
            context.fill();
            context.strokeStyle = '#FFFFFF';
            context.lineWidth = 2;
            context.stroke();
            
            // Draw the pointer
            context.beginPath();
            context.moveTo(32, 32);
            context.lineTo(32, 56);
            context.strokeStyle = '#FF4136';
            context.lineWidth = 4;
            context.stroke();
            
            // Draw a small circle at the bottom of the pointer
            context.beginPath();
            context.arc(32, 56, 2, 0, 2 * Math.PI);
            context.fillStyle = '#FF4136';
            context.fill();
            
            return canvas.toDataURL();
        }
        
        // Fly to a location on the globe with smooth animation
        function flyToLocation(longitude, latitude, viewer, height = 30000) {
            // Determine the appropriate height based on search text
            // For city names, get closer. For country names, stay higher
            const lowerQuery = lastSearchQuery ? lastSearchQuery.toLowerCase() : '';
            let flyHeight = height;
            
            // Adjust height based on query content - expanded range
            if (lowerQuery.includes('world') || lowerQuery.includes('earth') || lowerQuery.includes('globe')) {
                flyHeight = 10000000; // Global view (10,000 km)
            } else if (lowerQuery.includes('continent') || lowerQuery.includes('hemisphere')) {
                flyHeight = 5000000; // Continental view (5,000 km)
            } else if (lowerQuery.includes('country') || lowerQuery.includes('nation')) {
                flyHeight = 1000000; // Country level (1,000 km)
            } else if (lowerQuery.includes('region') || lowerQuery.includes('province') || lowerQuery.includes('state')) {
                flyHeight = 300000; // Region level (300 km)
            } else if (lowerQuery.includes('city') || lowerQuery.includes('town')) {
                flyHeight = 50000; // City level (50 km)
            } else if (lowerQuery.includes('district') || lowerQuery.includes('area') || lowerQuery.includes('neighborhood')) {
                flyHeight = 10000; // District level (10 km)
            } else if (lowerQuery.includes('street') || lowerQuery.includes('road')) {
                flyHeight = 1000; // Street level (1 km)
            } else if (lowerQuery.includes('building') || lowerQuery.includes('house') || lowerQuery.includes('address')) {
                flyHeight = 300; // Building level (300 m)
            }
            
            // Create a smooth flight animation
            viewer.camera.flyTo({
                destination: Cesium.Cartesian3.fromDegrees(longitude, latitude, flyHeight),
                orientation: {
                    heading: Cesium.Math.toRadians(0),
                    pitch: Cesium.Math.toRadians(-50),
                    roll: 0
                },
                duration: 3.0, // Slightly longer for smoother animation
                complete: function() {
                    console.log('Camera moved to search location at height:', flyHeight);
                    
                    // Create a short bounce effect after arrival for lower heights only
                    if (flyHeight < 100000) { // Only add bounce for close-up views
                        const currentHeight = viewer.camera.positionCartographic.height;
                        const bounceHeight = currentHeight * 0.95; // Slight bounce down
                        
                        setTimeout(() => {
                            viewer.camera.flyTo({
                                destination: Cesium.Cartesian3.fromDegrees(
                                    longitude, 
                                    latitude, 
                                    bounceHeight
                                ),
                                duration: 0.6,
                                easingFunction: Cesium.EasingFunction.QUADRATIC_IN_OUT
                            });
                        }, 100);
                    }
                }
            });
        }
        
        // Function to add custom zoom controls
        function addZoomControls(viewer, container) {
            // Create zoom controls container
            const zoomControls = document.createElement('div');
            zoomControls.className = 'cesium-zoom-controls';
            
            // Create zoom in button
            const zoomInButton = document.createElement('button');
            zoomInButton.className = 'cesium-zoom-button';
            zoomInButton.setAttribute('title', 'Zoom In');
            zoomInButton.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                    <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
                </svg>
            `;
            
            // Create zoom out button
            const zoomOutButton = document.createElement('button');
            zoomOutButton.className = 'cesium-zoom-button';
            zoomOutButton.setAttribute('title', 'Zoom Out');
            zoomOutButton.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                    <path d="M19 13H5v-2h14v2z"/>
                </svg>
            `;
            
            // Add zoom functionality
            zoomInButton.addEventListener('click', function() {
                zoomIn(viewer);
            });
            
            zoomOutButton.addEventListener('click', function() {
                zoomOut(viewer);
            });
            
            // Add buttons to container
            zoomControls.appendChild(zoomInButton);
            zoomControls.appendChild(zoomOutButton);
            
            // Add controls to the cesium container
            container.appendChild(zoomControls);
            
            console.log('Zoom controls added to globe');
        }
        
        // Zoom in function with adaptive zoom factor
        function zoomIn(viewer) {
            try {
                // Get current zoom level
                const currentHeight = viewer.camera.positionCartographic.height;
                
                // Use different zoom factors based on current height
                let zoomFactor;
                if (currentHeight > 5000000) {
                    zoomFactor = 0.5; // Zoom in faster from very high altitudes (50%)
                } else if (currentHeight > 1000000) {
                    zoomFactor = 0.6; // Faster zoom from high altitudes (40%)
                } else if (currentHeight > 100000) {
                    zoomFactor = 0.7; // Standard zoom (30%)
                } else if (currentHeight > 10000) {
                    zoomFactor = 0.8; // Slower zoom for mid altitudes (20%)
                } else {
                    zoomFactor = 0.9; // Very slow zoom for close-up views (10%)
                }
                
                // Calculate new height
                const newHeight = currentHeight * zoomFactor;
                
                // Get current camera position in lat/lon
                const position = viewer.camera.positionCartographic;
                const lat = Cesium.Math.toDegrees(position.latitude);
                const lon = Cesium.Math.toDegrees(position.longitude);
                
                // Maintain current view angle
                const heading = viewer.camera.heading;
                const pitch = viewer.camera.pitch;
                const roll = viewer.camera.roll;
                
                // Fly to same location but closer
                viewer.camera.flyTo({
                    destination: Cesium.Cartesian3.fromDegrees(lon, lat, newHeight),
                    orientation: {
                        heading: heading,
                        pitch: pitch,
                        roll: roll
                    },
                    duration: 0.5
                });
                
                console.log('Zooming in, new height:', newHeight);
            } catch (error) {
                console.error('Error during zoom in:', error);
            }
        }
        
        // Zoom out function with adaptive zoom factor
        function zoomOut(viewer) {
            try {
                // Get current zoom level
                const currentHeight = viewer.camera.positionCartographic.height;
                
                // Use different zoom factors based on current height
                let zoomFactor;
                if (currentHeight < 1000) {
                    zoomFactor = 2.0; // Zoom out faster from very low altitudes (100%)
                } else if (currentHeight < 10000) {
                    zoomFactor = 1.7; // Faster zoom from low altitudes (70%)
                } else if (currentHeight < 100000) {
                    zoomFactor = 1.5; // Standard zoom (50%)
                } else if (currentHeight < 1000000) {
                    zoomFactor = 1.3; // Slower zoom for high altitudes (30%)
                } else {
                    zoomFactor = 1.2; // Very slow zoom for very high altitudes (20%)
                }
                
                // Set a maximum height limit (just beyond Earth view)
                const maxHeight = 12000000; // 12,000 km
                
                // Calculate new height
                let newHeight = currentHeight * zoomFactor;
                if (newHeight > maxHeight) {
                    newHeight = maxHeight;
                }
                
                // Get current camera position in lat/lon
                const position = viewer.camera.positionCartographic;
                const lat = Cesium.Math.toDegrees(position.latitude);
                const lon = Cesium.Math.toDegrees(position.longitude);
                
                // Maintain current view angle
                const heading = viewer.camera.heading;
                const pitch = viewer.camera.pitch;
                const roll = viewer.camera.roll;
                
                // Fly to same location but further
                viewer.camera.flyTo({
                    destination: Cesium.Cartesian3.fromDegrees(lon, lat, newHeight),
                    orientation: {
                        heading: heading,
                        pitch: pitch,
                        roll: roll
                    },
                    duration: 0.5
                });
                
                console.log('Zooming out, new height:', newHeight);
            } catch (error) {
                console.error('Error during zoom out:', error);
            }
        }
        
        // Fly to Potaro-Siparuni region
        viewer.camera.flyTo({
            destination: Cesium.Cartesian3.fromDegrees(
                POTARO_SIPARUNI_COORDINATES.longitude, 
                POTARO_SIPARUNI_COORDINATES.latitude, 
                POTARO_SIPARUNI_COORDINATES.height
            ),
            orientation: {
                heading: Cesium.Math.toRadians(0.0),
                pitch: Cesium.Math.toRadians(-45.0),
                roll: 0.0
            },
            complete: function() {
                console.log('Camera moved to target position');
            }
        });
        
        // Add GeoJSON data if available
        async function loadGuyanaData() {
            try {
                // Load GeoJSON data for Guyana boundaries
                const response = await fetch('/static/data/potaro_siparuni_boundary.geojson');
                if (!response.ok) {
                    throw new Error(`Failed to fetch boundary data: ${response.status}`);
                }
                const geojsonData = await response.json();
                console.log('Boundary data loaded successfully');
                
                // Add the GeoJSON data as a data source
                const dataSource = await Cesium.GeoJsonDataSource.load(geojsonData, {
                    stroke: Cesium.Color.GOLD,
                    fill: Cesium.Color.GOLD.withAlpha(0.3),
                    strokeWidth: 3
                });
                
                viewer.dataSources.add(dataSource);
                console.log('Boundary data added to globe');
                
                // Load geological features
                loadGeologicalFeatures();
                
                // Load gold prediction data if available
                loadGoldPredictions();
                
            } catch (error) {
                console.error('Error loading Guyana data:', error);
                // Continue without boundary data
            }
        }
        
        // Load gold predictions data
        async function loadGoldPredictions() {
            try {
                // Load regular prediction data (excludes coordinates that overlap with geological features)
                const predictionResponse = await fetch('/api/enhanced-predictions/');
                if (!predictionResponse.ok) {
                    throw new Error(`Failed to fetch prediction data: ${predictionResponse.status}`);
                }
                const predictionData = await predictionResponse.json();
                console.log('Prediction data loaded successfully');
                
                // Create prediction entities
                predictionData.predictions.forEach(prediction => {
                    // Determine color based on probability
                    let color;
                    if (prediction.probability < 0.33) {
                        color = Cesium.Color.BLUE;
                    } else if (prediction.probability < 0.66) {
                        color = Cesium.Color.YELLOW;
                    } else {
                        color = Cesium.Color.RED;
                    }
                    
                    // Add entity to map
                    viewer.entities.add({
                        name: `Gold Prediction: ${prediction.probability.toFixed(2)}`,
                        position: Cesium.Cartesian3.fromDegrees(
                            prediction.longitude, 
                            prediction.latitude,
                            prediction.elevation || 0
                        ),
                        point: {
                            pixelSize: 10,
                            color: color,
                            outlineColor: Cesium.Color.WHITE,
                            outlineWidth: 2
                        },
                        description: `<strong>Gold Prediction</strong><br />
                                    Coordinates: ${prediction.latitude.toFixed(6)}, ${prediction.longitude.toFixed(6)}<br />
                                    Probability: ${(prediction.probability * 100).toFixed(1)}%<br />
                                    Confidence: ${(prediction.confidence * 100).toFixed(1)}%<br />
                                    Soil Type: ${prediction.soil_type}<br />
                                    Geological Formation: ${prediction.geological_formation}<br />
                                    Created: ${new Date(prediction.created_at).toLocaleDateString()}`
                    });
                });
                console.log('Regular prediction data added to globe');
                
                // Load intelligent coordinates (AI-generated) separately
                const intelligentResponse = await fetch('/api/intelligent-coordinates/');
                if (intelligentResponse.ok) {
                    const intelligentData = await intelligentResponse.json();
                    console.log('Intelligent coordinates loaded successfully');
                    
                    // Create intelligent coordinate entities with distinct styling
                    intelligentData.coordinates.forEach(coordinate => {
                        // Determine color based on probability (using distinct color scheme)
                        let color;
                        if (coordinate.gold_probability < 0.33) {
                            color = Cesium.Color.CYAN;
                        } else if (coordinate.gold_probability < 0.66) {
                            color = Cesium.Color.DARKORANGE;
                        } else {
                            color = Cesium.Color.MAGENTA;
                        }
                        
                        // Create description for intelligent coordinates
                        let description = `<strong>🤖 AI-Generated Exploration Point</strong><br />
                                        Coordinates: ${coordinate.latitude.toFixed(6)}, ${coordinate.longitude.toFixed(6)}<br />
                                        Gold Probability: ${(coordinate.gold_probability * 100).toFixed(1)}%<br />
                                        Confidence: ${(coordinate.confidence_score * 100).toFixed(1)}%<br />
                                        Priority: ${coordinate.exploration_priority.toUpperCase()}<br />
                                        Source: ${coordinate.source}<br />
                                        Feature Type: ${coordinate.feature_type}<br />
                                        Created: ${new Date(coordinate.created_at).toLocaleDateString()}`;
                        
                        // Add entity to map with distinct styling
                        viewer.entities.add({
                            name: `AI Exploration: ${coordinate.gold_probability.toFixed(2)}`,
                            position: Cesium.Cartesian3.fromDegrees(
                                coordinate.longitude, 
                                coordinate.latitude,
                                coordinate.elevation || 0
                            ),
                            point: {
                                pixelSize: 18, // Even larger size for intelligent coordinates
                                color: color,
                                outlineColor: Cesium.Color.BLACK,
                                outlineWidth: 4
                            },
                            description: description
                        });
                    });
                    console.log('Intelligent coordinates added to globe');
                } else {
                    console.warn('Intelligent coordinates not available');
                }
                
            } catch (error) {
                console.error('Error loading prediction data:', error);
                // Continue without prediction data
            }
        }
        
        // Load initial data
        loadGuyanaData().catch(error => {
            console.error('Failed to load initial data:', error);
        });
        
        // Remove any existing coordinate tooltips immediately
        const existingTooltips = document.querySelectorAll('.coordinate-tooltip, .cesium-coordinate-tooltip');
        existingTooltips.forEach(tooltip => {
            tooltip.remove();
            console.log('Removed existing coordinate tooltip');
        });

        // Create a legend
        createLegend();
        
        // Create floating coordinate tooltip after data is loaded (DISABLED)
        // setTimeout(() => {
        //     createCoordinateTooltip();
            
        //     // Add a test entity to verify hover functionality
        //     viewer.entities.add({
        //         name: 'Test Hover Point',
        //         position: Cesium.Cartesian3.fromDegrees(-59.3, 5.2, 1000),
        //         point: {
        //             pixelSize: 20,
        //             color: Cesium.Color.YELLOW,
        //             outlineColor: Cesium.Color.BLACK,
        //             outlineWidth: 3
        //         },
        //         description: 'Test point for hover functionality'
        //     });
            
        //     // Test tooltip manually
        //     setTimeout(() => {
        //         testTooltip();
        //     }, 500);
        // }, 1000);
        
        function createLegend() {
            const legendContainer = document.createElement('div');
            legendContainer.className = 'cesium-legend';
            legendContainer.innerHTML = `
                <h4>Map Legend</h4>
                
                <div class="legend-section" style="border: 2px solid #3288bd; border-radius: 8px; padding: 10px; margin-bottom: 15px; background-color: rgba(50, 136, 189, 0.1);">
                    <h5 style="color: #3288bd; margin: 0 0 10px 0; font-weight: bold;">📊 Gold Predictions</h5>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: #3288bd; width: 20px; height: 20px; border-radius: 50%; margin-right: 10px;"></div>
                        <span>Low Probability</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: #fee08b; width: 20px; height: 20px; border-radius: 50%; margin-right: 10px;"></div>
                        <span>Medium Probability</span>
                    </div>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: #d53e4f; width: 20px; height: 20px; border-radius: 50%; margin-right: 10px;"></div>
                        <span>High Probability</span>
                    </div>
                </div>
                
                <div class="legend-section" style="border: 2px solid #32cd32; border-radius: 8px; padding: 10px; margin-bottom: 15px; background-color: rgba(50, 205, 50, 0.1);">
                    <h5 style="color: #32cd32; margin: 0 0 10px 0; font-weight: bold;">📋 Geological Survey Data</h5>
                    <div class="legend-item">
                        <div class="legend-color" style="background-color: #32cd32; width: 20px; height: 20px; border-radius: 50%; margin-right: 10px;"></div>
                        <span>Real Survey Locations</span>
                    </div>
                </div>
            `;
            
            document.querySelector('.map-container').appendChild(legendContainer);
        }
        
        function createCoordinateTooltip() {
            // DISABLED: Coordinate tooltip creation
            console.log('Coordinate tooltip creation disabled');
            return;
            
            // Original code commented out below
            /*
            console.log('Creating coordinate tooltip...');
            
            const tooltip = document.createElement('div');
            tooltip.className = 'cesium-coordinate-tooltip';
            tooltip.innerHTML = `
                <div class="tooltip-header">Coordinates</div>
                <div class="tooltip-content">
                    <div class="tooltip-section">
                        <div class="tooltip-item">
                            <span class="tooltip-label">Latitude:</span>
                            <span class="tooltip-value" id="hover-lat">-</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Longitude:</span>
                            <span class="tooltip-value" id="hover-lon">-</span>
                        </div>
                        <div class="tooltip-item">
                            <span class="tooltip-label">Elevation:</span>
                            <span class="tooltip-value" id="hover-elev">-</span>
                        </div>
                    </div>
                </div>
            `;
            
            const mapContainer = document.querySelector('.map-container');
            if (mapContainer) {
                mapContainer.appendChild(tooltip);
                console.log('Coordinate tooltip added to map container');
                
                // Verify tooltip elements exist
                const latElement = document.getElementById('hover-lat');
                const lonElement = document.getElementById('hover-lon');
                const elevElement = document.getElementById('hover-elev');
                
                console.log('Tooltip elements found:', {
                    lat: !!latElement,
                    lon: !!lonElement,
                    elev: !!elevElement
                });
                
                // Add hover event handlers
                setupCoordinateHoverHandlers(viewer);
            } else {
                console.error('Map container not found');
            }
            */
        }
        
        function setupCoordinateHoverHandlers(viewer) {
            console.log('Setting up coordinate hover handlers...');
            
            // Track mouse movement over entities
            const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
            
            handler.setInputAction(function(movement) {
                console.log('Mouse movement detected at:', movement.endPosition.x, movement.endPosition.y);
                
                const pickedObject = viewer.scene.pick(movement.endPosition);
                console.log('Picked object:', pickedObject);
                
                if (Cesium.defined(pickedObject) && pickedObject.id) {
                    const entity = pickedObject.id;
                    console.log('Hovering over entity:', entity.name || entity.id);
                    
                    const position = entity.position.getValue(viewer.clock.currentTime);
                    
                    if (position) {
                        const cartographic = Cesium.Cartographic.fromCartesian(position);
                        const lat = Cesium.Math.toDegrees(cartographic.latitude);
                        const lon = Cesium.Math.toDegrees(cartographic.longitude);
                        const elev = cartographic.height;
                        
                        console.log('Entity coordinates:', lat, lon, elev);
                        
                        // Update coordinate tooltip
                        const latElement = document.getElementById('hover-lat');
                        const lonElement = document.getElementById('hover-lon');
                        const elevElement = document.getElementById('hover-elev');
                        
                        if (latElement && lonElement && elevElement) {
                            latElement.textContent = lat.toFixed(6);
                            lonElement.textContent = lon.toFixed(6);
                            elevElement.textContent = elev ? `${elev.toFixed(1)}m` : 'N/A';
                            console.log('Updated tooltip with coordinates');
                        } else {
                            console.error('Tooltip elements not found');
                        }
                        
                        // Show and position tooltip above cursor
                        const tooltip = document.querySelector('.cesium-coordinate-tooltip');
                        if (tooltip) {
                            tooltip.style.display = 'block';
                            
                            // Calculate position with offset
                            let left = movement.endPosition.x + 10;
                            let top = movement.endPosition.y - 10;
                            
                            // Ensure tooltip doesn't go off-screen
                            const tooltipRect = tooltip.getBoundingClientRect();
                            const windowWidth = window.innerWidth;
                            const windowHeight = window.innerHeight;
                            
                            // Adjust horizontal position if tooltip would go off-screen
                            if (left + tooltipRect.width > windowWidth) {
                                left = movement.endPosition.x - tooltipRect.width - 10;
                            }
                            
                            // Adjust vertical position if tooltip would go off-screen
                            if (top - tooltipRect.height < 0) {
                                top = movement.endPosition.y + 20; // Show below cursor instead
                            }
                            
                            tooltip.style.left = left + 'px';
                            tooltip.style.top = top + 'px';
                            console.log('Showing tooltip at:', left, top);
                        } else {
                            console.error('Tooltip element not found');
                        }
                    } else {
                        console.log('No position data for entity');
                    }
                } else {
                    console.log('No entity picked, hiding tooltip');
                    // Hide tooltip when not hovering over an entity
                    const tooltip = document.querySelector('.cesium-coordinate-tooltip');
                    if (tooltip) {
                        tooltip.style.display = 'none';
                    }
                }
            }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);
            
            console.log('Hover handlers set up successfully');
        }
        
        // Set resize handler to ensure Cesium renders correctly when displayed
        const mapViewSelector = document.getElementById('map-view-selector');
        if (mapViewSelector) {
            mapViewSelector.addEventListener('change', function() {
                if (mapViewSelector.value === 'globe') {
                    setTimeout(() => {
                        viewer.resize();
                        console.log('Cesium viewer resized');
                    }, 100);
                }
            });
        }
        
        // Load geological features data
        async function loadGeologicalFeatures() {
            try {
                const response = await fetch('/api/map-coordinates/');
                if (!response.ok) {
                    throw new Error(`Failed to fetch geological features: ${response.status}`);
                }
                const featureData = await response.json();
                console.log('Geological features loaded successfully');
                
                // Create geological feature entities
                featureData.coordinates.forEach(feature => {
                    // Use lime green color for geological features to match legend
                    const color = Cesium.Color.LIME;
                    
                    // Create description
                    let description = `<strong>📋 Geological Survey Data</strong><br />
                                    Coordinates: ${feature.latitude.toFixed(6)}, ${feature.longitude.toFixed(6)}<br />
                                    Type: ${feature.feature_type}<br />
                                    Confidence: ${(feature.confidence * 100).toFixed(1)}%<br />
                                    Soil Type: ${feature.soil_type}<br />
                                    Survey: ${feature.survey_title}<br />
                                    Description: ${feature.description}<br />
                                    <em>Real survey location from uploaded documents</em>`;
                    
                    // Add minerals if available
                    if (feature.minerals && feature.minerals.length > 0) {
                        description += `<br />Minerals: ${feature.minerals.join(', ')}`;
                    }
                    
                    // Add entity to map with different styling
                    viewer.entities.add({
                        name: `Survey Data: ${feature.feature_type}`,
                        position: Cesium.Cartesian3.fromDegrees(
                            feature.longitude, 
                            feature.latitude,
                            feature.elevation || 0
                        ),
                        point: {
                            pixelSize: 8, // Smaller size for features
                            color: color,
                            outlineColor: Cesium.Color.DARKGREEN,
                            outlineWidth: 2
                        },
                        description: description
                    });
                });
                console.log('Geological features added to globe');
                
            } catch (error) {
                console.error('Error loading geological features:', error);
                // Continue without geological features
            }
        }
        
        function testTooltip() {
            console.log('Testing tooltip...');
            const tooltip = document.querySelector('.cesium-coordinate-tooltip');
            if (tooltip) {
                console.log('Tooltip found, testing display...');
                tooltip.style.display = 'block';
                tooltip.style.left = '100px';
                tooltip.style.top = '100px';
                
                // Update with test coordinates
                const latElement = document.getElementById('hover-lat');
                const lonElement = document.getElementById('hover-lon');
                const elevElement = document.getElementById('hover-elev');
                
                if (latElement && lonElement && elevElement) {
                    latElement.textContent = '5.200000';
                    lonElement.textContent = '-59.300000';
                    elevElement.textContent = '1000.0m';
                    console.log('Test coordinates set');
                }
                
                // Hide after 3 seconds
                setTimeout(() => {
                    tooltip.style.display = 'none';
                    console.log('Test tooltip hidden');
                }, 3000);
            } else {
                console.error('Tooltip not found for testing');
            }
            
            // Test entity picking
            testEntityPicking();
        }
        
        function testEntityPicking() {
            console.log('Testing entity picking...');
            console.log('Total entities:', viewer.entities.values.length);
            
            viewer.entities.values.forEach((entity, index) => {
                console.log(`Entity ${index}:`, entity.name || entity.id);
            });
            
            // Test picking at center of screen
            const centerX = window.innerWidth / 2;
            const centerY = window.innerHeight / 2;
            const pickedObject = viewer.scene.pick(new Cesium.Cartesian2(centerX, centerY));
            console.log('Picking test at center:', pickedObject);
        }
        
    } catch (error) {
        console.error('Error initializing Cesium:', error);
        cesiumContainer.innerHTML = `
            <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.7); padding: 20px; border-radius: 10px; color: white; text-align: center;">
                <h3>Failed to initialize 3D Globe</h3>
                <p>Please check your internet connection and try again.</p>
                <p>Error: ${error.message}</p>
            </div>
        `;
    }
}); 