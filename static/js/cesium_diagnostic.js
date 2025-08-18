// Cesium Diagnostic Tool
document.addEventListener('DOMContentLoaded', function() {
    console.log('Cesium diagnostic tool initialized');
    
    // Check for Cesium script
    if (typeof Cesium === 'undefined') {
        console.error('Cesium is not defined! The script may not be loading correctly.');
        checkScriptLoading();
        return;
    }
    
    console.log('Cesium is defined in the global scope');
    console.log('Cesium version:', Cesium.VERSION);
    
    // Check WebGL support
    if (!window.WebGLRenderingContext) {
        console.error('WebGL is not supported in this browser!');
        displayError('WebGL not supported', 'Your browser does not support WebGL, which is required for 3D globe visualization.');
        return;
    }
    
    console.log('WebGL is supported in this browser');
    
    // Check if canvas is supported
    const canvas = document.createElement('canvas');
    if (!canvas || !canvas.getContext) {
        console.error('Canvas is not supported in this browser!');
        displayError('Canvas not supported', 'Your browser does not support the Canvas element, which is required for 3D visualization.');
        return;
    }
    
    // Try to get a WebGL context
    try {
        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (!gl) {
            throw new Error('WebGL context could not be initialized');
        }
        console.log('WebGL context successfully created');
        
        // Log WebGL capabilities
        console.log('WebGL vendor:', gl.getParameter(gl.VENDOR));
        console.log('WebGL renderer:', gl.getParameter(gl.RENDERER));
        console.log('WebGL version:', gl.getParameter(gl.VERSION));
        console.log('GLSL version:', gl.getParameter(gl.SHADING_LANGUAGE_VERSION));
        
        // Check for specific WebGL capabilities needed by Cesium
        const maxTextureSize = gl.getParameter(gl.MAX_TEXTURE_SIZE);
        console.log('Max texture size:', maxTextureSize);
        if (maxTextureSize < 4096) {
            console.warn('Max texture size is less than recommended (4096)');
        }
        
        // Check for CORS support
        const corsSupported = 'withCredentials' in new XMLHttpRequest();
        console.log('CORS support:', corsSupported ? 'Yes' : 'No');
        if (!corsSupported) {
            console.warn('CORS not supported, which may prevent loading external resources');
        }
        
    } catch (e) {
        console.error('WebGL context test failed:', e);
        displayError('WebGL initialization failed', 'Your browser supports WebGL, but it could not be initialized: ' + e.message);
        return;
    }
    
    // Check if Cesium container exists
    const cesiumContainer = document.getElementById('cesium-container');
    if (!cesiumContainer) {
        console.error('Cesium container element not found in the DOM');
        return;
    }
    
    console.log('Cesium container element found in the DOM');
    console.log('Container size:', cesiumContainer.offsetWidth, 'x', cesiumContainer.offsetHeight);
    
    // Check for container visibility
    const containerStyle = window.getComputedStyle(cesiumContainer);
    console.log('Container display:', containerStyle.display);
    console.log('Container visibility:', containerStyle.visibility);
    
    if (containerStyle.display === 'none') {
        console.warn('Cesium container is hidden (display: none)');
    }
    
    // All checks passed
    console.log('All diagnostic checks passed. Cesium should work properly.');
    
    // Helper function to check script loading
    function checkScriptLoading() {
        const scripts = document.getElementsByTagName('script');
        let cesiumScriptFound = false;
        
        for (let i = 0; i < scripts.length; i++) {
            const src = scripts[i].src;
            if (src.includes('Cesium.js') || src.includes('cesium')) {
                cesiumScriptFound = true;
                console.log('Found Cesium script:', src);
                
                // Check if the script loaded successfully
                if (scripts[i].readyState) {
                    console.log('Script readyState:', scripts[i].readyState);
                }
            }
        }
        
        if (!cesiumScriptFound) {
            console.error('No Cesium script found in the document!');
            displayError('Cesium not found', 'The Cesium library script was not found in the document. Please check your script includes.');
        }
    }
    
    // Helper function to display errors to the user
    function displayError(title, message) {
        const cesiumContainer = document.getElementById('cesium-container');
        if (cesiumContainer) {
            cesiumContainer.innerHTML = `
                <div class="cesium-error">
                    <h3>${title}</h3>
                    <p>${message}</p>
                    <p>Please check the browser console for more details.</p>
                </div>
            `;
        }
    }
}); 