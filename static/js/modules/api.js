/**
 * API Client Module
 * Handles all API communication with the backend
 */
class APIClient {
    constructor(baseURL = '') {
        this.baseURL = baseURL;
        this.defaultHeaders = {
            'Content-Type': 'application/json',
        };
        this.sessionId = this.generateSessionId();
    }

    /**
     * Generate a unique session ID for conversation tracking
     * @returns {string} - Unique session ID
     */
    generateSessionId() {
        // Try to get existing session ID from localStorage
        let sessionId = localStorage.getItem('goldmine_session_id');
        
        if (!sessionId) {
            // Generate new session ID
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('goldmine_session_id', sessionId);
        }
        
        return sessionId;
    }

    /**
     * Get current session ID
     * @returns {string} - Current session ID
     */
    getSessionId() {
        return this.sessionId;
    }

    /**
     * Clear session ID (for new chat)
     */
    clearSession() {
        localStorage.removeItem('goldmine_session_id');
        this.sessionId = this.generateSessionId();
    }

    /**
     * Make an API request
     * @param {string} endpoint - API endpoint
     * @param {Object} options - Request options
     * @returns {Promise} - Response promise
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: { ...this.defaultHeaders, ...options.headers },
            ...options
        };

        console.log('API request - URL:', url); // Debug log
        console.log('API request - config:', config); // Debug log

        try {
            console.log('API request - making fetch request...'); // Debug log
            const response = await fetch(url, config);
            console.log('API request - response received:', response.status, response.statusText); // Debug log
            
            const data = await response.json();
            console.log('API request - response data:', data); // Debug log

            if (!response.ok) {
                console.error('API request - response not ok:', response.status, data); // Debug log
                throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            return data;
        } catch (error) {
            console.error(`API request failed: ${endpoint}`, error);
            throw error;
        }
    }

    /**
     * Get CSRF token from cookies
     * @returns {string} - CSRF token
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

    // Chat and Conversation API Methods

    /**
     * Send a chat message with intelligent analysis integration
     * @param {string} message - User message
     * @param {Array} conversationHistory - Previous conversation messages
     * @returns {Promise} - Chat response
     */
    async sendChatMessage(message, conversationHistory = []) {
        // Use the unified chat endpoint for all queries
        console.log('Using Unified Chat System for all queries');
        return this.request('/api/unified-chat/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({
                message: message,
                conversation_history: conversationHistory,
                session_id: this.sessionId
            })
        });
    }

    /**
     * Detect if a message should use intelligent geological analysis
     * @param {string} message - User message
     * @returns {boolean} - True if geological analysis should be used
     */
    shouldUseIntelligentAnalysis(message) {
        const geologicalKeywords = [
            'gold', 'mining', 'geological', 'geology', 'mineral', 'deposit', 'ore',
            'exploration', 'prospecting', 'survey', 'formation', 'rock', 'vein',
            'quarry', 'mine', 'extraction', 'drilling', 'sampling', 'assay',
            'copper', 'iron', 'diamond', 'bauxite', 'manganese', 'nickel', 'zinc',
            'lead', 'uranium', 'coal', 'oil', 'gas', 'silver', 'platinum',
            'granite', 'schist', 'gneiss', 'limestone', 'sandstone', 'shale',
            'fault', 'fold', 'intrusion', 'metamorphism', 'sedimentary', 'igneous',
            'basin', 'anticline', 'syncline', 'outcrop', 'bedrock', 'overburden',
            'placer', 'lode', 'contact', 'stratigraphy', 'lithology'
        ];

        const messageLower = message.toLowerCase();
        return geologicalKeywords.some(keyword => messageLower.includes(keyword));
    }

    /**
     * Detect the type of geological query for better analysis
     * @param {string} message - User message
     * @returns {string} - Query type for intelligent analysis
     */
    detectQueryType(message) {
        const messageLower = message.toLowerCase();
        
        if (messageLower.includes('where') || messageLower.includes('location') || 
            messageLower.includes('coordinates') || messageLower.includes('map') || 
            messageLower.includes('area') || messageLower.includes('region')) {
            return 'location';
        }
        

        
        if (messageLower.includes('gold') || messageLower.includes('mineral') || 
            messageLower.includes('deposit') || messageLower.includes('ore') || 
            messageLower.includes('grade') || messageLower.includes('concentration')) {
            return 'mineral';
        }
        
        if (messageLower.includes('formation') || messageLower.includes('rock') || 
            messageLower.includes('geological') || messageLower.includes('structure') || 
            messageLower.includes('fault') || messageLower.includes('fold')) {
            return 'technical';
        }
        
        if (messageLower.includes('exploration') || messageLower.includes('prospecting') || 
            messageLower.includes('mining') || messageLower.includes('extraction') || 
            messageLower.includes('economic') || messageLower.includes('commercial')) {
            return 'economic';
        }
        
        if (messageLower.includes('history') || messageLower.includes('timeline') || 
            messageLower.includes('development') || messageLower.includes('past') || 
            messageLower.includes('previous') || messageLower.includes('earlier')) {
            return 'historical';
        }
        
        return 'general';
    }

    /**
     * Submit user feedback for a conversation message
     * @param {string} messageId - Message ID
     * @param {number} rating - User rating (1-5)
     * @param {string} feedback - Optional text feedback
     * @returns {Promise} - Feedback submission result
     */


    /**
     * Get conversation history for current session
     * @returns {Promise} - Conversation history
     */
    async getConversationHistory() {
        return this.request(`/api/unified-chat/history/${this.sessionId}/`);
    }



    /**
     * Clear conversation history for current session
     * @returns {Promise} - Clear result
     */
    async clearConversationHistory() {
        const result = await this.request(`/api/unified-chat/clear/${this.sessionId}/`);
        if (result.success) {
            this.clearSession(); // Generate new session ID
        }
        return result;
    }

    // Machine Learning API Methods

    /**
     * Train the ML model
     * @param {Object} params - Training parameters
     * @returns {Promise} - Training result
     */
    async trainModel(params = {}) {
        return this.request('/train-model/', {
            method: 'POST',
            body: JSON.stringify(params)
        });
    }

    /**
     * Make a prediction
     * @param {Object} features - Prediction features
     * @returns {Promise} - Prediction result
     */
    async makePrediction(features) {
        return this.request('/make-prediction/', {
            method: 'POST',
            body: JSON.stringify(features)
        });
    }

    /**
     * Get prediction history
     * @param {Object} params - Query parameters
     * @returns {Promise} - Predictions list
     */
    async getPredictions(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const endpoint = queryString ? `/api/enhanced-predictions/?${queryString}` : '/api/enhanced-predictions/';
        return this.request(endpoint);
    }

    /**
     * Get geological features
     * @param {Object} params - Query parameters
     * @returns {Promise} - Features list
     */
    async getGeologicalFeatures(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const endpoint = queryString ? `/api/map-coordinates/?${queryString}` : '/api/map-coordinates/';
        return this.request(endpoint);
    }

    // PDF Processing API Methods

    /**
     * Upload a PDF file
     * @param {File} file - File to upload
     * @param {string} documentType - Type of document ('geological_survey' or 'mining_map')
     * @returns {Promise} - Upload result
     */
    async uploadFile(file, documentType = 'geological_survey') {
        console.log('API uploadFile called - documentType:', documentType); // Debug log
        console.log('API uploadFile - file:', file.name, 'size:', file.size); // Debug log
        
        const formData = new FormData();
        formData.append('files', file); // Changed from 'file' to 'files' to match upload_multiple_files
        formData.append('document_type', documentType);

        console.log('API uploadFile - FormData created, making request...'); // Debug log

        try {
            // Use the upload_multiple_files endpoint which processes files immediately
            const result = await this.request('/pdfocr/upload-multiple/', {
                method: 'POST',
                headers: {}, // Let browser set Content-Type for FormData
                body: formData
            });
            
            console.log('API uploadFile - request successful, result:', result); // Debug log
            
            // The upload_multiple_files endpoint returns a different structure
            // We need to extract the first uploaded file from the response
            if (result.success && result.uploaded_files && result.uploaded_files.length > 0) {
                const uploadedFile = result.uploaded_files[0];
                return {
                    success: true,
                    upload_id: uploadedFile.upload_id,
                    filename: uploadedFile.filename,
                    status: uploadedFile.status,
                    created_at: uploadedFile.created_at
                };
            } else {
                throw new Error(result.error || 'Upload failed');
            }
        } catch (error) {
            console.error('API uploadFile - request failed:', error); // Debug log
            throw error;
        }
    }

    /**
     * Upload multiple PDF files
     * @param {FileList|Array} files - Files to upload
     * @param {string} documentType - Type of document ('geological_survey' or 'mining_map')
     * @returns {Promise} - Upload result
     */
    async uploadMultipleFiles(files, documentType = 'geological_survey') {
        console.log('API uploadMultipleFiles called - documentType:', documentType); // Debug log
        console.log('API uploadMultipleFiles - files count:', files.length); // Debug log
        
        const formData = new FormData();
        
        // Add all files to FormData
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }
        formData.append('document_type', documentType);

        console.log('API uploadMultipleFiles - FormData created, making request...'); // Debug log

        try {
            const result = await this.request('/pdfocr/upload-multiple/', {
                method: 'POST',
                headers: {}, // Let browser set Content-Type for FormData
                body: formData
            });
            
            console.log('API uploadMultipleFiles - request successful, result:', result); // Debug log
            return result;
        } catch (error) {
            console.error('API uploadMultipleFiles - request failed:', error); // Debug log
            throw error;
        }
    }

    /**
     * Process an uploaded file
     * @param {string} uploadId - Upload ID of the file to process
     * @returns {Promise<Object>} - Processing result
     */
    async processFile(uploadId) {
        try {
            console.log('API: Processing file with uploadId:', uploadId);
            
            const response = await fetch(`/pdfocr/process-file/${uploadId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const result = await response.json();
            console.log('API: Process file response:', result);
            
            return result;
        } catch (error) {
            console.error('API: Process file error:', error);
            throw new Error(`Failed to process file: ${error.message}`);
        }
    }

    /**
     * Get all uploaded files
     * @returns {Promise} - Files list
     */
    async getFiles() {
        return this.request('/get-files/');
    }

    /**
     * Delete an uploaded file
     * @param {number} uploadId - Upload ID
     * @returns {Promise} - Deletion result
     */
    async deleteFile(uploadId) {
        return this.request(`/delete-file/${uploadId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': this.getCSRFToken()
            }
        });
    }

    /**
     * Get file processing status
     * @param {string} uploadId - Upload ID
     * @returns {Promise} - Status result
     */
    async getFileStatus(uploadId) {
        return this.request(`/api/file-status/${uploadId}/`);
    }

    /**
     * Get file status with retry logic
     * @param {string} uploadId - Upload ID
     * @param {number} maxRetries - Maximum retry attempts
     * @returns {Promise} - Status result
     */
    async getFileStatusWithRetry(uploadId, maxRetries = 3) {
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                const status = await this.getFileStatus(uploadId);
                return status;
            } catch (error) {
                if (attempt === maxRetries) {
                    throw error;
                }
                // Wait before retrying (exponential backoff)
                await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
            }
        }
    }

    /**
     * Track file progress with real-time updates
     * @param {string} uploadId - Upload ID
     * @param {Function} onProgress - Progress callback
     * @param {Function} onComplete - Completion callback
     * @param {Function} onError - Error callback
     * @returns {Function} - Function to stop tracking
     */
    async trackFileProgress(uploadId, onProgress, onComplete, onError) {
        let isTracking = true;
        let lastProgress = 0;
        let consecutiveErrors = 0;
        const maxConsecutiveErrors = 3;

        const pollStatus = async () => {
            if (!isTracking) return;

            try {
                const status = await this.getFileStatus(uploadId);
                
                if (status.success) {
                    consecutiveErrors = 0; // Reset error count on success
                    
                    // Call progress callback
                    if (onProgress) {
                        onProgress(status);
                    }

                    // Check if processing is complete
                    if (status.status === 'processed' || status.status === 'completed' || status.status === 'failed') {
                        isTracking = false;
                        if (onComplete) {
                            onComplete(status);
                        }
                        return;
                    }

                    // Continue polling based on status
                    const pollInterval = this.getPollInterval(status.status, status.progress);
                    setTimeout(pollStatus, pollInterval);
                } else {
                    throw new Error(status.error || 'Failed to get file status');
                }
            } catch (error) {
                consecutiveErrors++;
                console.error(`Error tracking file progress (attempt ${consecutiveErrors}):`, error);
                
                if (consecutiveErrors >= maxConsecutiveErrors) {
                    isTracking = false;
                    if (onError) {
                        onError(error);
                    }
                    return;
                }

                // Retry with exponential backoff
                const retryDelay = Math.min(1000 * Math.pow(2, consecutiveErrors - 1), 10000);
                setTimeout(pollStatus, retryDelay);
            }
        };

        // Start polling
        pollStatus();

        // Return function to stop tracking
        return () => {
            isTracking = false;
        };
    }

    /**
     * Get appropriate polling interval based on status and progress
     * @param {string} status - File status
     * @param {number} progress - Current progress percentage
     * @returns {number} - Polling interval in milliseconds
     */
    getPollInterval(status, progress) {
        // Adjust polling frequency based on status and progress
        switch (status) {
            case 'uploaded':
                return 2000; // Poll every 2 seconds for uploaded files
            case 'pending':
                return 3000; // Poll every 3 seconds for pending files
            case 'processing':
                if (progress < 50) {
                    return 2000; // More frequent updates during text extraction
                } else {
                    return 3000; // Less frequent updates during data processing
                }
            default:
                return 5000; // Default 5 second interval
        }
    }

    /**
     * Track multiple files simultaneously
     * @param {Array} uploadIds - Array of upload IDs
     * @param {Function} onProgress - Progress callback for individual files
     * @param {Function} onComplete - Completion callback for all files
     * @param {Function} onError - Error callback
     * @returns {Function} - Function to stop all tracking
     */
    async trackMultipleFiles(uploadIds, onProgress, onComplete, onError) {
        const trackers = [];
        const results = new Map();
        let completedCount = 0;

        const checkAllComplete = () => {
            if (completedCount === uploadIds.length) {
                if (onComplete) {
                    onComplete(Array.from(results.values()));
                }
            }
        };

        for (const uploadId of uploadIds) {
            const stopTracking = await this.trackFileProgress(
                uploadId,
                (status) => {
                    results.set(uploadId, status);
                    if (onProgress) {
                        onProgress(uploadId, status, results);
                    }
                },
                (status) => {
                    results.set(uploadId, status);
                    completedCount++;
                    checkAllComplete();
                },
                (error) => {
                    results.set(uploadId, { error, status: 'error' });
                    completedCount++;
                    if (onError) {
                        onError(uploadId, error);
                    }
                    checkAllComplete();
                }
            );
            trackers.push(stopTracking);
        }

        // Return function to stop all tracking
        return () => {
            trackers.forEach(stop => stop());
        };
    }

    /**
     * Retry processing for a failed file
     * @param {string} uploadId - Upload ID
     * @param {string} modelType - Model type
     * @returns {Promise} - Retry result
     */
    async retryProcessing(uploadId, modelType) {
        return this.request(`/api/retry-processing/${uploadId}/`, {
            method: 'POST',
            body: JSON.stringify({ model_type: modelType })
        });
    }

    /**
     * Cancel processing for a file
     * @param {string} uploadId - Upload ID
     * @param {string} modelType - Model type
     * @returns {Promise} - Cancel result
     */
    async cancelProcessing(uploadId, modelType) {
        return this.request(`/api/cancel-processing/${uploadId}/`, {
            method: 'POST',
            body: JSON.stringify({ model_type: modelType })
        });
    }

    // Utility methods for progress tracking
    /**
     * Format file size for display
     * @param {number} bytes - File size in bytes
     * @returns {string} - Formatted file size
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Format progress message with emoji
     * @param {string} status - File status
     * @param {number} progress - Progress percentage
     * @param {string} message - Status message
     * @returns {string} - Formatted message
     */
    formatProgressMessage(status, progress, message) {
        const progressPercent = Math.round(progress);
        const statusEmoji = this.getStatusEmoji(status);
        return `${statusEmoji} ${message} (${progressPercent}%)`;
    }

    /**
     * Get emoji for file status
     * @param {string} status - File status
     * @returns {string} - Status emoji
     */
    getStatusEmoji(status) {
        switch (status) {
            case 'uploaded': return '📤';
            case 'pending': return '⏳';
            case 'processing': return '🔄';
            case 'processed':
            case 'completed': return '✅';
            case 'failed': return '❌';
            case 'unprocessed': return '📄';
            default: return '❓';
        }
    }
}

// Export for use in other modules
window.APIClient = APIClient; 