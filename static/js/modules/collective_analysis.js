/**
 * Collective Text Analysis Module
 * Handles collective analysis of multiple extracted text files
 */

class CollectiveAnalysis {
    constructor() {
        this.isAnalyzing = false;
        this.apiEndpoint = '/api/analyze-collective-texts/';
    }

    /**
     * Start collective analysis of text files
     * @param {Object} options - Analysis options
     * @param {number} options.limit - Maximum number of files to analyze
     * @param {boolean} options.reprocess - Whether to reprocess already processed files
     * @param {string} options.apiKey - OpenAI API key (optional)
     * @param {string} options.model - OpenAI model to use
     * @param {Function} options.onProgress - Progress callback
     * @param {Function} options.onSuccess - Success callback
     * @param {Function} options.onError - Error callback
     */
    async startAnalysis(options = {}) {
        if (this.isAnalyzing) {
            throw new Error('Analysis already in progress');
        }

        this.isAnalyzing = true;

        try {
            // Prepare request data
            const requestData = {
                limit: options.limit || null,
                reprocess: options.reprocess || false,
                model: options.model || 'gpt-4o-mini'
            };

            if (options.apiKey) {
                requestData.api_key = options.apiKey;
            }

            // Call progress callback
            if (options.onProgress) {
                options.onProgress('Starting collective analysis...');
            }

            // Make API request
            const response = await fetch(this.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();

            if (result.success) {
                // Call success callback
                if (options.onSuccess) {
                    options.onSuccess(result);
                }
            } else {
                throw new Error(result.error || 'Analysis failed');
            }

        } catch (error) {
            console.error('Collective analysis error:', error);
            
            // Call error callback
            if (options.onError) {
                options.onError(error.message);
            }
        } finally {
            this.isAnalyzing = false;
        }
    }

    /**
     * Get CSRF token from cookies
     * @returns {string} CSRF token
     */
    getCSRFToken() {
        const name = 'csrftoken';
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

    /**
     * Display analysis results in a formatted way
     * @param {Object} result - Analysis result
     * @param {HTMLElement} container - Container to display results
     */
    displayResults(result, container) {
        if (!container) {
            console.error('Container element not provided');
            return;
        }

        const analysisResult = result.analysis_result;
        const summary = analysisResult.__summary_statistics__ || {};

        // Create results HTML
        const html = `
            <div class="collective-analysis-results">
                <h3>📊 Collective Analysis Results</h3>
                
                <div class="results-summary">
                    <div class="summary-item">
                        <span class="label">Files Analyzed:</span>
                        <span class="value">${result.files_analyzed}</span>
                    </div>
                    <div class="summary-item">
                        <span class="label">Total Text Length:</span>
                        <span class="value">${result.total_text_length.toLocaleString()} characters</span>
                    </div>
                    <div class="summary-item">
                        <span class="label">Coordinates Found:</span>
                        <span class="value">${summary.total_coordinates || 0}</span>
                    </div>
                    <div class="summary-item">
                        <span class="label">Geological Formations:</span>
                        <span class="value">${summary.total_geological_formations || 0}</span>
                    </div>
                    <div class="summary-item">
                        <span class="label">Gold Indicators:</span>
                        <span class="value">${summary.total_gold_indicators || 0}</span>
                    </div>
                    <div class="summary-item">
                        <span class="label">Minerals:</span>
                        <span class="value">${summary.total_minerals || 0}</span>
                    </div>
                    <div class="summary-item">
                        <span class="label">Cross-Document Insights:</span>
                        <span class="value">${summary.cross_document_insights_count || 0}</span>
                    </div>
                    <div class="summary-item">
                        <span class="label">Data Completeness:</span>
                        <span class="value">${((summary.data_completeness || 0) * 100).toFixed(1)}%</span>
                    </div>
                </div>

                ${this.renderCoordinates(analysisResult.coordinates || [])}
                ${this.renderCrossInsights(analysisResult.cross_document_insights || [])}
                ${this.renderGeologicalFormations(analysisResult.geological_formations || [])}
                ${this.renderGoldIndicators(analysisResult.gold_indicators || [])}
                ${this.renderMinerals(analysisResult.minerals || [])}
            </div>
        `;

        container.innerHTML = html;
    }

    /**
     * Render coordinates section
     * @param {Array} coordinates - Coordinates array
     * @returns {string} HTML string
     */
    renderCoordinates(coordinates) {
        if (!coordinates.length) return '';

        return `
            <div class="results-section">
                <h4>🗺️ Coordinates Found (${coordinates.length})</h4>
                <div class="coordinates-list">
                    ${coordinates.slice(0, 10).map((coord, index) => `
                        <div class="coordinate-item">
                            <div class="coord-header">
                                <span class="coord-number">#${index + 1}</span>
                                <span class="coord-coords">${coord.latitude}, ${coord.longitude}</span>
                                <span class="coord-confidence">Confidence: ${(coord.confidence * 100).toFixed(1)}%</span>
                            </div>
                            <div class="coord-context">${coord.context || 'No context provided'}</div>
                            ${coord.elevation ? `<div class="coord-elevation">Elevation: ${coord.elevation}m</div>` : ''}
                        </div>
                    `).join('')}
                </div>
                ${coordinates.length > 10 ? `<div class="more-items">... and ${coordinates.length - 10} more coordinates</div>` : ''}
            </div>
        `;
    }

    /**
     * Render cross-document insights section
     * @param {Array} insights - Cross-document insights array
     * @returns {string} HTML string
     */
    renderCrossInsights(insights) {
        if (!insights.length) return '';

        return `
            <div class="results-section">
                <h4>🔍 Cross-Document Insights (${insights.length})</h4>
                <div class="insights-list">
                    ${insights.slice(0, 5).map((insight, index) => `
                        <div class="insight-item">
                            <div class="insight-header">
                                <span class="insight-number">#${index + 1}</span>
                                <span class="insight-type">${insight.type}</span>
                                <span class="insight-confidence">Confidence: ${(insight.confidence * 100).toFixed(1)}%</span>
                            </div>
                            <div class="insight-text">${insight.insight}</div>
                        </div>
                    `).join('')}
                </div>
                ${insights.length > 5 ? `<div class="more-items">... and ${insights.length - 5} more insights</div>` : ''}
            </div>
        `;
    }

    /**
     * Render geological formations section
     * @param {Array} formations - Geological formations array
     * @returns {string} HTML string
     */
    renderGeologicalFormations(formations) {
        if (!formations.length) return '';

        return `
            <div class="results-section">
                <h4>🏔️ Geological Formations (${formations.length})</h4>
                <div class="formations-list">
                    ${formations.slice(0, 5).map((formation, index) => `
                        <div class="formation-item">
                            <div class="formation-header">
                                <span class="formation-number">#${index + 1}</span>
                                <span class="formation-type">${formation.type}</span>
                                <span class="formation-potential">Gold Potential: ${formation.gold_potential}</span>
                            </div>
                            <div class="formation-description">${formation.description || 'No description provided'}</div>
                        </div>
                    `).join('')}
                </div>
                ${formations.length > 5 ? `<div class="more-items">... and ${formations.length - 5} more formations</div>` : ''}
            </div>
        `;
    }

    /**
     * Render gold indicators section
     * @param {Array} indicators - Gold indicators array
     * @returns {string} HTML string
     */
    renderGoldIndicators(indicators) {
        if (!indicators.length) return '';

        return `
            <div class="results-section">
                <h4>🥇 Gold Indicators (${indicators.length})</h4>
                <div class="indicators-list">
                    ${indicators.slice(0, 5).map((indicator, index) => `
                        <div class="indicator-item">
                            <div class="indicator-header">
                                <span class="indicator-number">#${index + 1}</span>
                                <span class="indicator-name">${indicator.indicator}</span>
                                <span class="indicator-confidence">Confidence: ${(indicator.confidence * 100).toFixed(1)}%</span>
                            </div>
                            <div class="indicator-context">${indicator.context || 'No context provided'}</div>
                        </div>
                    `).join('')}
                </div>
                ${indicators.length > 5 ? `<div class="more-items">... and ${indicators.length - 5} more indicators</div>` : ''}
            </div>
        `;
    }

    /**
     * Render minerals section
     * @param {Array} minerals - Minerals array
     * @returns {string} HTML string
     */
    renderMinerals(minerals) {
        if (!minerals.length) return '';

        return `
            <div class="results-section">
                <h4>💎 Minerals (${minerals.length})</h4>
                <div class="minerals-list">
                    ${minerals.slice(0, 5).map((mineral, index) => `
                        <div class="mineral-item">
                            <div class="mineral-header">
                                <span class="mineral-number">#${index + 1}</span>
                                <span class="mineral-name">${mineral.name}</span>
                                <span class="mineral-concentration">${mineral.concentration}</span>
                            </div>
                            <div class="mineral-details">
                                ${mineral.depth ? `Depth: ${mineral.depth}` : ''}
                                ${mineral.association_with_gold ? ` | Gold Association: ${mineral.association_with_gold}` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
                ${minerals.length > 5 ? `<div class="more-items">... and ${minerals.length - 5} more minerals</div>` : ''}
            </div>
        `;
    }
}

/**
 * Enhanced Progress Tracking Module
 * Provides real-time progress updates and status tracking for file processing
 */
class ProgressTracker {
    constructor() {
        this.api = new APIClient();
        this.activeTrackers = new Map();
        this.progressCallbacks = new Map();
        this.isAutoRefreshEnabled = true;
        this.autoRefreshInterval = null;
        this.processingFiles = new Set();
    }

    /**
     * Initialize progress tracking for the upload management page
     */
    init() {
        this.setupAutoRefresh();
        this.initializeProgressBars();
        this.startTrackingProcessingFiles();
        this.setupEventListeners();
    }

    /**
     * Setup auto-refresh functionality
     */
    setupAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }

        this.autoRefreshInterval = setInterval(() => {
            if (this.isAutoRefreshEnabled && this.processingFiles.size > 0) {
                this.refreshProcessingStatus();
            }
        }, 5000); // Refresh every 5 seconds if files are processing
    }

    /**
     * Initialize progress bars for existing processing files
     */
    initializeProgressBars() {
        const processingRows = document.querySelectorAll('.upload-row[data-status="processing"], .upload-row[data-status="pending"]');
        
        processingRows.forEach(row => {
            const uploadId = row.getAttribute('data-upload-id');
            if (uploadId) {
                this.processingFiles.add(uploadId);
                this.startTrackingFile(uploadId, row);
            }
        });

        this.updateProcessingIndicator();
    }

    /**
     * Start tracking a specific file
     * @param {string} uploadId - Upload ID
     * @param {HTMLElement} row - Table row element
     */
    startTrackingFile(uploadId, row) {
        if (!this.activeTrackers || !this.activeTrackers.has) {
            console.error('activeTrackers is not properly initialized');
            this.activeTrackers = new Map(); // Reinitialize if corrupted
        }

        if (this.activeTrackers.has(uploadId)) {
            return; // Already tracking this file
        }

        try {
            const stopTracking = this.api.trackFileProgress(
                uploadId,
                (status) => this.onFileProgress(uploadId, status, row),
                (status) => this.onFileComplete(uploadId, status, row),
                (error) => this.onFileError(uploadId, error, row)
            );

            // Validate that stopTracking is a function
            if (typeof stopTracking === 'function') {
                this.activeTrackers.set(uploadId, stopTracking);
                this.processingFiles.add(uploadId);
                console.log(`Started tracking file: ${uploadId}`);
            } else {
                console.error(`trackFileProgress did not return a function for ${uploadId}`);
            }
        } catch (error) {
            console.error(`Error starting file tracking for ${uploadId}:`, error);
        }
    }

    /**
     * Handle file progress updates
     * @param {string} uploadId - Upload ID
     * @param {Object} status - Status object
     * @param {HTMLElement} row - Table row element
     */
    onFileProgress(uploadId, status, row) {
        console.log(`Progress update for ${uploadId}:`, status);
        
        // Update progress bar
        const progressBar = row.querySelector('.processing-progress-bar');
        const progressText = row.querySelector('.processing-progress-text');
        const processingStep = row.querySelector('.processing-step');
        const statusBadge = row.querySelector('.status-badge');

        if (progressBar) {
            progressBar.style.width = status.progress + '%';
        }
        if (progressText) {
            progressText.textContent = Math.round(status.progress) + '%';
        }
        if (processingStep) {
            // Show more detailed progress messages
            let stepMessage = status.message;
            if (status.progress < 20) {
                stepMessage = '📤 File uploaded, starting processing...';
            } else if (status.progress < 40) {
                stepMessage = '🔄 Extracting text from PDF...';
            } else if (status.progress < 70) {
                stepMessage = '📝 Processing extracted text...';
            } else if (status.progress < 90) {
                stepMessage = '🔍 Analyzing content...';
            } else if (status.progress < 100) {
                stepMessage = '✨ Finalizing processing...';
            } else {
                stepMessage = '✅ Processing complete!';
            }
            processingStep.textContent = stepMessage;
        }
        if (statusBadge) {
            statusBadge.textContent = this.getStatusDisplayText(status.status);
            statusBadge.className = `status-badge status-${status.status} px-2 inline-flex text-xs leading-5 font-semibold rounded-full`;
        }

        // Update row status
        row.setAttribute('data-status', status.status);

        // Show processing indicator if not already visible
        const progressContainer = row.querySelector('.processing-progress-container');
        if (progressContainer && progressContainer.classList.contains('hidden')) {
            progressContainer.classList.remove('hidden');
        }

        // Call any registered callbacks
        if (this.progressCallbacks.has(uploadId)) {
            this.progressCallbacks.get(uploadId).forEach(callback => callback(status));
        }

        this.updateProcessingIndicator();
    }

    /**
     * Handle file completion
     * @param {string} uploadId - Upload ID
     * @param {Object} status - Status object
     * @param {HTMLElement} row - Table row element
     */
    onFileComplete(uploadId, status, row) {
        console.log(`File completed: ${uploadId}`, status);
        
        this.onFileProgress(uploadId, status, row);

        // Stop tracking this file with better error handling
        try {
            if (this.activeTrackers && this.activeTrackers.has && this.activeTrackers.has(uploadId)) {
                const stopTracking = this.activeTrackers.get(uploadId);
                if (typeof stopTracking === 'function') {
                    stopTracking();
                }
                this.activeTrackers.delete(uploadId);
            }
        } catch (trackingError) {
            console.error('Error stopping file tracking:', trackingError);
        }

        this.processingFiles.delete(uploadId);

        // Show completion message
        const processingStep = row.querySelector('.processing-step');
        if (processingStep) {
            if (status.status === 'processed' || status.status === 'completed') {
                processingStep.textContent = '✅ Processing complete! File ready for analysis.';
            } else if (status.status === 'failed') {
                processingStep.textContent = '❌ Processing failed. Click retry to try again.';
            }
        }

        // Hide progress bar after a delay
        setTimeout(() => {
            const progressContainer = row.querySelector('.processing-progress-container');
            if (progressContainer) {
                progressContainer.classList.add('hidden');
            }
        }, 3000);

        // Show completion notification
        this.showNotification(
            `File "${status.filename}" processing ${status.status === 'processed' ? 'complete' : 'failed'}!`,
            status.status === 'processed' ? 'success' : 'error'
        );

        this.updateProcessingIndicator();
        this.updateStatistics();
        
        // Refresh the uploads list to ensure the file appears in the correct section
        setTimeout(() => {
            if (typeof refreshUploadsList === 'function') {
                refreshUploadsList();
            }
        }, 1000);
    }

    /**
     * Handle file processing errors
     * @param {string} uploadId - Upload ID
     * @param {Error} error - Error object
     * @param {HTMLElement} row - Table row element
     */
    onFileError(uploadId, error, row) {
        console.error(`Error tracking file ${uploadId}:`, error);

        // Stop tracking this file with better error handling
        try {
            if (this.activeTrackers && this.activeTrackers.has && this.activeTrackers.has(uploadId)) {
                const stopTracking = this.activeTrackers.get(uploadId);
                if (typeof stopTracking === 'function') {
                    stopTracking();
                }
                this.activeTrackers.delete(uploadId);
            }
        } catch (trackingError) {
            console.error('Error stopping file tracking:', trackingError);
        }

        this.processingFiles.delete(uploadId);

        // Update row to show error state
        const statusBadge = row.querySelector('.status-badge');
        if (statusBadge) {
            statusBadge.textContent = 'Error';
            statusBadge.className = 'status-badge status-failed px-2 inline-flex text-xs leading-5 font-semibold rounded-full';
        }

        row.setAttribute('data-status', 'failed');

        // Show error notification
        this.showNotification(
            `Error tracking file progress: ${error.message}`,
            'error'
        );

        this.updateProcessingIndicator();
    }

    /**
     * Start tracking all currently processing files
     */
    startTrackingProcessingFiles() {
        const processingRows = document.querySelectorAll('.upload-row[data-status="processing"], .upload-row[data-status="pending"]');
        
        processingRows.forEach(row => {
            const uploadId = row.getAttribute('data-upload-id');
            if (uploadId && !this.activeTrackers.has(uploadId)) {
                this.startTrackingFile(uploadId, row);
            }
        });
    }

    /**
     * Refresh processing status for all files
     */
    async refreshProcessingStatus() {
        const processingRows = document.querySelectorAll('.upload-row[data-status="processing"], .upload-row[data-status="pending"]');
        
        for (const row of processingRows) {
            const uploadId = row.getAttribute('data-upload-id');
            if (uploadId) {
                try {
                    const status = await this.api.getFileStatus(uploadId);
                    if (status.success) {
                        this.onFileProgress(uploadId, status, row);
                        
                        // If file is complete, handle completion
                        if (status.status === 'processed' || status.status === 'completed' || status.status === 'failed') {
                            this.onFileComplete(uploadId, status, row);
                        }
                    }
                } catch (error) {
                    console.error(`Error refreshing status for ${uploadId}:`, error);
                }
            }
        }
    }

    /**
     * Update the processing indicator
     */
    updateProcessingIndicator() {
        const processingIndicator = document.getElementById('processing-indicator');
        const processingCount = document.getElementById('processing-count');
        
        if (this.processingFiles.size > 0) {
            if (processingIndicator) {
                processingIndicator.classList.remove('hidden');
            }
            if (processingCount) {
                processingCount.textContent = `${this.processingFiles.size} file${this.processingFiles.size > 1 ? 's' : ''}`;
            }
        } else {
            if (processingIndicator) {
                processingIndicator.classList.add('hidden');
            }
        }
    }

    /**
     * Update statistics display
     */
    updateStatistics() {
        // This would typically refresh the statistics cards
        // For now, we'll trigger a page refresh to get updated stats
        // In a production environment, you'd want to update this via AJAX
        setTimeout(() => {
            window.location.reload();
        }, 2000);
    }

    /**
     * Setup event listeners for user interactions
     */
    setupEventListeners() {
        // Manual refresh button
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                refreshBtn.classList.add('animate-spin');
                this.refreshProcessingStatus();
                setTimeout(() => {
                    refreshBtn.classList.remove('animate-spin');
                }, 1000);
            });
        }

        // Cancel processing buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('.processing-indicator-container')) {
                const container = e.target.closest('.processing-indicator-container');
                const uploadId = container.getAttribute('data-upload-id');
                const modelType = container.getAttribute('data-model-type');
                
                if (uploadId && confirm('Are you sure you want to cancel processing this file?')) {
                    this.cancelFileProcessing(uploadId, modelType, container);
                }
            }
        });

        // Retry buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('.retry-btn')) {
                const btn = e.target.closest('.retry-btn');
                const uploadId = btn.getAttribute('data-upload-id');
                const modelType = btn.getAttribute('data-model-type');
                
                if (uploadId) {
                    this.retryFileProcessing(uploadId, modelType, btn);
                }
            }
        });
    }

    /**
     * Cancel file processing
     * @param {string} uploadId - Upload ID
     * @param {string} modelType - Model type
     * @param {HTMLElement} container - Cancel button container
     */
    async cancelFileProcessing(uploadId, modelType, container) {
        try {
            container.style.pointerEvents = 'none';
            container.innerHTML = '<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-red-600 dark:border-red-400"></div>';
            
            const result = await this.api.cancelProcessing(uploadId, modelType);
            
            if (result.success) {
                const row = container.closest('.upload-row');
                if (row) {
                    const statusBadge = row.querySelector('.status-badge');
                    if (statusBadge) {
                        statusBadge.textContent = 'Cancelled';
                        statusBadge.className = 'status-badge status-failed px-2 inline-flex text-xs leading-5 font-semibold rounded-full';
                    }
                    row.setAttribute('data-status', 'failed');
                }
                
                this.showNotification('Processing cancelled successfully', 'success');
            } else {
                throw new Error(result.error || 'Failed to cancel processing');
            }
        } catch (error) {
            console.error('Error cancelling processing:', error);
            this.showNotification('Failed to cancel processing: ' + error.message, 'error');
            
            // Restore original state
            container.style.pointerEvents = 'auto';
            container.innerHTML = `
                <div class="loading-spinner animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 dark:border-blue-400 absolute inset-0 transition-opacity duration-300"></div>
                <div class="cancel-x opacity-0 absolute inset-0 z-10 bg-white dark:bg-zinc-800 rounded-full transition-opacity duration-300">
                    <svg class="h-4 w-4 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </div>
            `;
        }
    }

    /**
     * Retry file processing
     * @param {string} uploadId - Upload ID
     * @param {string} modelType - Model type
     * @param {HTMLElement} btn - Retry button
     */
    async retryFileProcessing(uploadId, modelType, btn) {
        try {
            btn.disabled = true;
            btn.textContent = 'Retrying...';
            
            const result = await this.api.retryProcessing(uploadId, modelType);
            
            if (result.success) {
                this.showNotification('Processing retry initiated successfully', 'success');
                
                // Start tracking the file again
                const row = btn.closest('.upload-row');
                if (row) {
                    this.startTrackingFile(uploadId, row);
                }
            } else {
                throw new Error(result.error || 'Failed to retry processing');
            }
        } catch (error) {
            console.error('Error retrying processing:', error);
            this.showNotification('Failed to retry processing: ' + error.message, 'error');
            
            // Restore button state
            btn.disabled = false;
            btn.textContent = 'Retry';
        }
    }

    /**
     * Get display text for status
     * @param {string} status - Status string
     * @returns {string} - Display text
     */
    getStatusDisplayText(status) {
        switch (status) {
            case 'pending': return 'Processing';
            case 'processing': return 'Processing';
            case 'processed': return 'Processed';
            case 'completed': return 'Completed';
            case 'failed': return 'Failed';
            case 'unprocessed': return 'Unprocessed';
            case 'uploaded': return 'Uploaded';
            default: return status.charAt(0).toUpperCase() + status.slice(1);
        }
    }

    /**
     * Show notification
     * @param {string} message - Notification message
     * @param {string} type - Notification type (success, error, info, warning)
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 max-w-sm ${
            type === 'success' ? 'bg-green-500 text-white' :
            type === 'error' ? 'bg-red-500 text-white' :
            type === 'warning' ? 'bg-yellow-500 text-white' :
            'bg-blue-500 text-white'
        }`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Remove notification after 3 seconds
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    /**
     * Register a callback for file progress updates
     * @param {string} uploadId - Upload ID
     * @param {Function} callback - Progress callback function
     */
    onProgress(uploadId, callback) {
        if (!this.progressCallbacks.has(uploadId)) {
            this.progressCallbacks.set(uploadId, []);
        }
        this.progressCallbacks.get(uploadId).push(callback);
    }

    /**
     * Clean up resources
     */
    destroy() {
        // Stop all active trackers
        this.activeTrackers.forEach(stopTracking => stopTracking());
        this.activeTrackers.clear();
        
        // Clear intervals
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
        
        // Clear callbacks
        this.progressCallbacks.clear();
        
        // Clear processing files set
        this.processingFiles.clear();
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CollectiveAnalysis;
} else {
    // Make available globally
    window.CollectiveAnalysis = CollectiveAnalysis;
} 