/**
 * Upload Handler Module
 * Handles file uploads and processing with improved error handling
 */
class UploadHandler {
    constructor() {
        this.api = new APIClient();
        this.ui = new UIUtils();
        this.uploadedFiles = new Map();
        this.selectedDocumentType = 'geological_survey'; // Default document type
        this.isProcessing = false;
        this.lastProcessTime = 0; // Track last processing time for rate limiting
        
        this.initializeEventListeners();
    }

    /**
     * Initialize event listeners
     */
    initializeEventListeners() {
        // File input change
        const fileInput = document.getElementById('uploadFile1');
        if (fileInput) {
            fileInput.addEventListener('change', async (e) => {
                this.selectedFiles = Array.from(e.target.files);
                this.showUploadModal(); // Show modal immediately on file select
                await this.handleFileSelection(this.selectedFiles); // Upload files and show process buttons
            });
        }

        // Document type radio button changes
        const documentTypeRadios = document.querySelectorAll('input[name="document_type"]');
        documentTypeRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.selectedDocumentType = e.target.value;
                console.log('Document type changed to:', this.selectedDocumentType); // Debug log
            });
        });

        // File selection automatically triggers upload (no upload button needed)
        // Upload happens immediately when files are selected

        // Modal close button
        const cancelBtn = document.getElementById('cancel-upload');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                this.closeUploadModal();
            });
        }

        // Success modal close
        const closeSuccessBtn = document.getElementById('close-success');
        if (closeSuccessBtn) {
            closeSuccessBtn.addEventListener('click', () => {
                this.closeSuccessModal();
            });
        }

        // Copy text button
        const copyTextBtn = document.getElementById('copy-text-btn');
        if (copyTextBtn) {
            copyTextBtn.addEventListener('click', () => {
                this.copyExtractedText();
            });
        }

        // View predictions button
        const viewPredictionsBtn = document.getElementById('view-predictions-btn');
        if (viewPredictionsBtn) {
            viewPredictionsBtn.addEventListener('click', () => {
                window.location.href = '/predict/';
            });
        }
    }

    /**
     * Populate the modal with the selected files
     */
    populateModalFileList() {
        const filesList = document.getElementById('uploaded-files-list');
        const emptyMessage = document.getElementById('uploaded-files-empty');
        if (!filesList) return;
        filesList.innerHTML = '';
        if (this.selectedFiles && this.selectedFiles.length > 0) {
            if (emptyMessage) emptyMessage.style.display = 'none';
            this.selectedFiles.forEach(file => {
                const fileItem = document.createElement('div');
                fileItem.className = 'flex items-center justify-between p-2 mb-2 bg-white dark:bg-zinc-700 rounded border border-zinc-200 dark:border-zinc-600';
                fileItem.innerHTML = `<span class="text-sm font-medium text-zinc-900 dark:text-white">${file.name}</span><span class="text-xs text-zinc-500 dark:text-zinc-400">${this.formatFileSize(file.size)}</span>`;
                filesList.appendChild(fileItem);
            });
        } else {
            if (emptyMessage) emptyMessage.style.display = 'block';
        }
    }

    /**
     * Handle file selection
     * @param {FileList} files - Selected files
     */
    async handleFileSelection(files) {
        console.log('[DEBUG] handleFileSelection called with files:', files);
        if (files.length === 0) return;

        try {
            // Use the new uploadMultipleFiles method for better efficiency
            console.log('[DEBUG] Uploading all files at once...');
            
            // Add status update for all files
            for (const file of files) {
                this.addUploadStatus(file.name, 'Preparing for upload...', 'info');
            }
            
            const result = await this.api.uploadMultipleFiles(files, this.selectedDocumentType);
            console.log('[DEBUG] Upload result:', result);
            
            if (result.success) {
                // Add success status for all uploaded files
                for (const uploadedFile of result.uploaded_files) {
                    this.addUploadStatus(uploadedFile.filename, 'Upload successful', 'success');
                    
                    // Store uploaded file info
                    this.uploadedFiles.set(uploadedFile.upload_id, {
                        ...uploadedFile,
                        status: uploadedFile.status || 'uploaded'
                    });
                }
                
                // Add error status for any failed files
                if (result.errors && result.errors.length > 0) {
                    for (const error of result.errors) {
                        this.addUploadStatus('Unknown file', error, 'error');
                    }
                }
                
                console.log('[DEBUG] All files processed successfully');
                this.populateUploadedFilesList();
            } else {
                throw new Error(result.error || 'Upload failed');
            }
            
        } catch (error) {
            console.error('[DEBUG] Upload failed in handleFileSelection:', error);
            this.ui.showToast('Upload failed: ' + error.message, 'error');
            
            // Add error status for all files
            for (const file of files) {
                this.addUploadStatus(file.name, `Upload failed: ${error.message}`, 'error');
            }
        }
    }

    // Progress bar functions removed - using simpler modal structure from index4.html

    /**
     * Update progress in the modal
     * @param {string} text - Progress text
     * @param {number} percentage - Progress percentage
     */
    updateModalProgress(text, percentage) {
        console.log(`[DEBUG] updateModalProgress: ${text} (${percentage}%)`);
        const progressText = document.getElementById('progress-text');
        const progressPercentage = document.getElementById('progress-percentage');
        const progressBar = document.getElementById('progress-bar');
        if (!progressText || !progressPercentage || !progressBar) {
            console.warn('[DEBUG] updateModalProgress: Progress bar elements not found');
        }
        if (progressText) progressText.textContent = text;
        if (progressPercentage) progressPercentage.textContent = `${Math.round(percentage)}%`;
        if (progressBar) progressBar.style.width = `${percentage}%`;
    }

    /**
     * Add status item to the upload progress
     * @param {string} filename - File name
     * @param {string} status - Status message
     * @param {string} type - Status type (success, error, info)
     */
    addUploadStatus(filename, status, type = 'info') {
        const statusContainer = document.getElementById('upload-status');
        if (!statusContainer) return;
        
        const statusItem = document.createElement('div');
        statusItem.className = 'flex items-center justify-between p-2 rounded border';
        
        let bgColor = 'bg-zinc-100 dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700';
        let textColor = 'text-zinc-700 dark:text-zinc-300';
        
        if (type === 'success') {
            bgColor = 'bg-green-100 dark:bg-green-900 border-green-200 dark:border-green-700';
            textColor = 'text-green-700 dark:text-green-300';
        } else if (type === 'error') {
            bgColor = 'bg-red-100 dark:bg-red-900 border-red-200 dark:border-red-700';
            textColor = 'text-red-700 dark:text-red-300';
        }
        
        statusItem.className = `flex items-center justify-between p-2 rounded border ${bgColor}`;
        
        statusItem.innerHTML = `
            <span class="text-sm font-medium ${textColor}">${filename}</span>
            <span class="text-xs ${textColor}">${status}</span>
        `;
        
        statusContainer.appendChild(statusItem);
        statusContainer.scrollTop = statusContainer.scrollHeight;
    }

    /**
     * Show upload complete state (simplified for index4.html structure)
     */
    showUploadComplete() {
        // Show success message
        const modalContent = document.getElementById('upload-modal-content');
        if (modalContent) {
            // Create success message if it doesn't exist
            let successMessage = document.getElementById('upload-success-message');
            if (!successMessage) {
                successMessage = document.createElement('div');
                successMessage.id = 'upload-success-message';
                successMessage.className = 'mb-4 p-3 bg-green-100 dark:bg-green-900 rounded-lg border border-green-200 dark:border-green-700';
                successMessage.innerHTML = `
                    <div class="flex items-center">
                        <svg class="w-5 h-5 text-green-600 dark:text-green-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                        </svg>
                        <span class="text-green-700 dark:text-green-300">All files uploaded successfully!</span>
                    </div>
                `;
                
                // Insert after the radio buttons section
                const radioSection = modalContent.querySelector('.mb-6');
                if (radioSection) {
                    radioSection.insertAdjacentElement('afterend', successMessage);
                }
            }
        }
        
        // Populate the uploaded files list
        this.populateUploadedFilesList();
    }

    /**
     * Show upload error state
     * @param {string} errorMessage - Error message to display
     */
    showUploadError(errorMessage) {
        const modalContent = document.getElementById('upload-modal-content');
        if (!modalContent) return;
        
        modalContent.innerHTML = `
            <h3 class="text-xl font-bold text-zinc-900 dark:text-white mb-4">Upload Failed</h3>
            
            <div class="mb-6 p-4 bg-red-100 dark:bg-red-900 rounded-lg border border-red-200 dark:border-red-700">
                <div class="flex items-center">
                    <svg class="w-5 h-5 text-red-600 dark:text-red-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                    <span class="text-red-700 dark:text-red-300">${errorMessage}</span>
                </div>
            </div>
            
            <div class="mt-6 flex justify-end">
                <button id="retry-upload" class="text-white bg-blue-600 hover:bg-blue-700 rounded-lg text-sm px-4 py-2 mr-2">Retry</button>
                <button id="close-upload" class="text-zinc-600 bg-transparent hover:bg-zinc-200 hover:text-zinc-900 rounded-lg text-sm px-4 py-2 dark:text-zinc-200 dark:hover:bg-zinc-800 dark:hover:text-white">Close</button>
            </div>
        `;
        
        // Re-bind buttons
        const retryBtn = document.getElementById('retry-upload');
        const closeBtn = document.getElementById('close-upload');
        
        if (retryBtn) {
            retryBtn.addEventListener('click', () => {
                this.handleFileSelection(this.selectedFiles);
            });
        }
        
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.closeUploadModal();
            });
        }
    }

    /**
     * Populate the uploaded files list with process buttons
     */
    populateUploadedFilesList() {
        const filesList = document.getElementById('uploaded-files-list');
        if (!filesList) return;
        
        filesList.innerHTML = '';
        
        if (this.uploadedFiles.size === 0) {
            filesList.innerHTML = '<div class="text-center text-zinc-400 dark:text-zinc-500">No files uploaded.</div>';
            return;
        }
        
        this.uploadedFiles.forEach((fileInfo, uploadId) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'flex flex-col mb-2 p-2 rounded bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700';
            fileItem.id = `file-${uploadId}`;
            
            fileItem.innerHTML = `
                <div class='flex justify-between items-center'>
                    <span class='font-medium text-zinc-900 dark:text-white'>${fileInfo.filename || fileInfo.file_name || 'Unknown file'}</span>
                    <button class='process-btn text-white bg-blue-600 hover:bg-blue-700 rounded px-3 py-1 text-xs' data-upload-id='${uploadId}'>Process</button>
                </div>
                <div class='text-xs text-zinc-400 mt-1'>Status: <span class='file-status'>${fileInfo.status || 'uploaded'}</span></div>
                <div class='progress-container hidden mt-2'>
                    <div class='flex justify-between text-xs text-zinc-600 dark:text-zinc-400 mb-1'>
                        <span class='progress-text'>Ready to process</span>
                        <span class='progress-percentage'>0%</span>
                    </div>
                    <div class='w-full bg-zinc-200 dark:bg-zinc-700 rounded-full h-2'>
                        <div class='progress-bar bg-blue-600 h-2 rounded-full transition-all duration-500' style='width: 0%'></div>
                    </div>
                </div>
                <div class='file-result text-xs mt-1'></div>
            `;
            
            filesList.appendChild(fileItem);
            
            // Add event listener to the Process button
            fileItem.querySelector('.process-btn').addEventListener('click', (e) => {
                const uploadId = e.target.getAttribute('data-upload-id');
                this.processFile(uploadId, fileItem);
            });
        });
    }

    /**
     * Upload a single file (upload only, no processing)
     * @param {File} file - File to upload
     */
    async uploadSingleFile(file) {
        try {
            console.log('uploadSingleFile called for:', file.name); // Debug log
            
            // Add status update
            this.addUploadStatus(file.name, 'Validating file...', 'info');
            
            // Validate file
            this.validateFile(file);
            console.log('File validation passed'); // Debug log
            
            // Add status update
            this.addUploadStatus(file.name, 'Validation passed', 'success');
            
            // Use stored document type
            console.log('Using document type for upload:', this.selectedDocumentType); // Debug log
            
            // Add status update
            this.addUploadStatus(file.name, 'Uploading to server...', 'info');
                
            // Upload file (upload only, no processing)
            console.log('Calling API uploadFile...'); // Debug log
            const result = await this.api.uploadFile(file, this.selectedDocumentType);
            console.log('API uploadFile result:', result); // Debug log
            
            if (result.success) {
                console.log('Upload successful, result:', result); // Debug log
                
                // Add success status
                this.addUploadStatus(file.name, 'Upload successful', 'success');
                
                // Handle duplicate detection
                if (result.is_duplicate) {
                    console.log('Duplicate detected, handling...'); // Debug log
                    this.addUploadStatus(file.name, 'Duplicate detected - review needed', 'info');
                    this.handleDuplicateDetection(result, file);
                }
                
                // Store uploaded file info (no processing yet)
                const uploadId = result.upload_id || result.pdf_id;
                this.uploadedFiles.set(uploadId, {
                    ...result,
                    file: file,
                    status: result.status || 'uploaded' // Use status from server response
                });
                
                console.log('File added to list successfully'); // Debug log
            } else {
                console.log('Upload failed, result:', result); // Debug log
                // Add error status
                this.addUploadStatus(file.name, `Upload failed: ${result.error || 'Unknown error'}`, 'error');
                
                // Check if it's a duplicate rejection
                if (result.duplicate_info && result.duplicate_info.overall_severity === 'high') {
                    this.handleDuplicateRejection(result, file);
                    return; // Don't throw error for duplicates
                }
                throw new Error(result.error || 'Upload failed');
            }
        } catch (error) {
            console.error('Upload error in uploadSingleFile:', error); // Debug log
            this.addUploadStatus(file.name, `Error: ${error.message}`, 'error');
            this.ui.showToast(`Failed to upload ${file.name}: ${error.message}`, 'error');
            throw error;
        }
    }
    
    /**
     * Handle duplicate detection warning
     * @param {Object} result - Upload result
     * @param {File} file - Uploaded file
     */
    handleDuplicateDetection(result, file) {
        const duplicateInfo = result.duplicate_info;
        const severity = duplicateInfo.overall_severity;
        
        let message = '';
        let type = 'warning';
        
        if (severity === 'high') {
            message = `Exact duplicate detected: ${duplicateInfo.message}`;
            type = 'error';
        } else if (severity === 'medium') {
            message = `Similar document detected: ${duplicateInfo.message}`;
            type = 'warning';
        } else {
            message = `Possible duplicate: ${duplicateInfo.message}`;
            type = 'info';
        }
        
        this.ui.showToast(message, type);
        
        // Log duplicate details for debugging
        if (result.duplicate_details && result.duplicate_details.length > 0) {
            console.log('Duplicate details:', result.duplicate_details);
        }
    }
    
    /**
     * Handle duplicate rejection
     * @param {Object} result - Upload result
     * @param {File} file - Uploaded file
     */
    handleDuplicateRejection(result, file) {
        const duplicateInfo = result.duplicate_info;
        const message = `Upload rejected: ${duplicateInfo.message}`;
        
        this.ui.showToast(message, 'error');
        
        // Show detailed duplicate information
        if (result.duplicate_details && result.duplicate_details.length > 0) {
            this.showDuplicateDetails(result.duplicate_details, file.name);
        }
    }
    
    /**
     * Show detailed duplicate information
     * @param {Array} duplicateDetails - Duplicate details
     * @param {string} filename - Original filename
     */
    showDuplicateDetails(duplicateDetails, filename) {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white dark:bg-zinc-800 rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-semibold text-red-600">Duplicate Document Detected</h3>
                    <button class="text-gray-500 hover:text-gray-700 text-xl" onclick="this.closest('.fixed').remove()">&times;</button>
                </div>
                <div class="mb-4">
                    <p class="text-sm text-gray-600 dark:text-gray-400 mb-2">
                        The file <strong>${filename}</strong> appears to be a duplicate of existing documents.
                    </p>
                </div>
                <div class="space-y-3">
                    ${duplicateDetails.map(dup => `
                        <div class="border border-gray-200 dark:border-gray-700 rounded p-3">
                            <div class="flex justify-between items-start mb-2">
                                <span class="font-medium text-sm">${dup.reason}</span>
                                <span class="text-xs px-2 py-1 rounded ${
                                    dup.severity === 'high' ? 'bg-red-100 text-red-800' :
                                    dup.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                                    'bg-blue-100 text-blue-800'
                                }">${dup.severity}</span>
                            </div>
                            <div class="text-xs text-gray-600 dark:text-gray-400">
                                <div>Existing file: ${dup.document.filename}</div>
                                <div>Uploaded: ${new Date(dup.document.created_at).toLocaleDateString()}</div>
                            </div>
                        </div>
                    `).join('')}
                </div>
                <div class="mt-4 text-center">
                    <button class="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded text-sm" 
                            onclick="this.closest('.fixed').remove()">
                        Close
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }

    /**
     * Validate uploaded file
     * @param {File} file - File to validate
     */
    validateFile(file) {
                // Check file size (max 100MB)
        const maxSize = 100 * 1024 * 1024;
        if (file.size > maxSize) {
            throw new Error(`File size exceeds maximum limit of 100MB`);
        }

        // Check file extension
        const allowedExtensions = ['.pdf'];
        const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
        
        if (!allowedExtensions.includes(fileExtension)) {
            throw new Error(`File type not allowed. Only PDF files are supported`);
        }

        // Check if file is empty
        if (file.size === 0) {
            throw new Error('File is empty');
        }
            }
            
    /**
     * Add file to the uploaded files list with a process button
     * @param {Object} result - Upload result
     */
    addFileToList(result) {
        const filesList = document.getElementById('uploaded-files-list');
        const emptyMessage = document.getElementById('uploaded-files-empty');
        
        if (emptyMessage) {
            emptyMessage.style.display = 'none';
        }

        const fileItem = document.createElement('div');
        fileItem.className = 'flex flex-col mb-2 p-2 rounded bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700';
        fileItem.id = `file-${result.upload_id || result.pdf_id}`;
        
        fileItem.innerHTML = `
            <div class='flex justify-between items-center'>
                <span class='font-medium text-zinc-900 dark:text-white'>${result.filename || result.file_name || 'Unknown file'}</span>
                <button class='process-btn text-white bg-blue-600 hover:bg-blue-700 rounded px-3 py-1 text-xs' data-upload-id='${result.upload_id || result.pdf_id}'>Process</button>
            </div>
            <div class='text-xs text-zinc-400 mt-1'>Status: <span class='file-status'>${result.status || 'uploaded'}</span></div>
            <div class='progress-container hidden mt-2'>
                <div class='flex justify-between text-xs text-zinc-600 dark:text-zinc-400 mb-1'>
                    <span class='progress-text'>Ready to process</span>
                    <span class='progress-percentage'>0%</span>
                </div>
                <div class='w-full bg-zinc-200 dark:bg-zinc-700 rounded-full h-2'>
                    <div class='progress-bar bg-blue-600 h-2 rounded-full transition-all duration-500' style='width: 0%'></div>
                </div>
            </div>
            <div class='file-result text-xs mt-1'></div>
        `;
        
        filesList.appendChild(fileItem);
        
        // Add event listener to the Process button
        fileItem.querySelector('.process-btn').addEventListener('click', (e) => {
            const uploadId = e.target.getAttribute('data-upload-id');
            this.processFile(uploadId, fileItem);
        });
    }

    /**
     * Process a specific file with enhanced progress tracking
     * @param {string} uploadId - Upload ID of the file to process
     * @param {HTMLElement} item - File item element
     */
    async processFile(uploadId, item) {
        const statusSpan = item.querySelector('.file-status');
        const resultDiv = item.querySelector('.file-result');
        const progressContainer = item.querySelector('.progress-container');
        const progressBar = item.querySelector('.progress-bar');
        const progressText = item.querySelector('.progress-text');
        const progressPercentage = item.querySelector('.progress-percentage');
        const processBtn = item.querySelector('.process-btn');
        
        // Check if already processing
        if (processBtn.disabled && processBtn.textContent === 'Processing...') {
            return;
        }
        
        // Rate limiting: Wait at least 30 seconds between processing attempts
        const now = Date.now();
        const timeSinceLastProcess = now - this.lastProcessTime;
        if (timeSinceLastProcess < 30000) { // 30 seconds
            const waitTime = Math.ceil((30000 - timeSinceLastProcess) / 1000);
            this.ui.showToast(`Please wait ${waitTime} seconds before processing another file (Adobe API rate limit)`, 'warning');
            return;
        }
        
        // Show progress bar and update initial state
        progressContainer.classList.remove('hidden');
        statusSpan.textContent = 'processing';
        processBtn.disabled = true;
        processBtn.textContent = 'Processing...';
        
        try {
            // More detailed progress stages with realistic timing
            this.updateProgress(progressBar, progressText, progressPercentage, 5, 'Initializing...');
            await this.sleep(200);
            
            this.updateProgress(progressBar, progressText, progressPercentage, 10, 'Authenticating with Adobe...');
            await this.sleep(300);
            
            this.updateProgress(progressBar, progressText, progressPercentage, 20, 'Preparing file upload...');
            await this.sleep(200);
            
            this.updateProgress(progressBar, progressText, progressPercentage, 30, 'Uploading to Adobe servers...');
            await this.sleep(400);
            
            this.updateProgress(progressBar, progressText, progressPercentage, 45, 'Creating OCR extraction job...');
            await this.sleep(300);
            
            this.updateProgress(progressBar, progressText, progressPercentage, 55, 'Starting OCR processing...');
            await this.sleep(200);
            
            this.updateProgress(progressBar, progressText, progressPercentage, 65, 'Processing OCR (may take several minutes)...');
            progressText.classList.add('pulse-animation');
            
            // Start the actual processing request
            const startTime = Date.now();
            this.lastProcessTime = startTime; // Update last process time
            const data = await this.api.processFile(uploadId);
            
            const processingTime = Math.round((Date.now() - startTime) / 1000);
            
            progressText.classList.remove('pulse-animation');
            
            if (data.success) {
                this.updateProgress(progressBar, progressText, progressPercentage, 85, 'Downloading extraction results...');
                await this.sleep(300);
                
                this.updateProgress(progressBar, progressText, progressPercentage, 95, 'Parsing extracted text...');
                await this.sleep(200);
                
                this.updateProgress(progressBar, progressText, progressPercentage, 100, `Complete! (${processingTime}s)`);
                statusSpan.textContent = 'completed';
                
                setTimeout(() => {
                    progressContainer.classList.add('hidden');
                    processBtn.textContent = 'Processed ✓';
                    processBtn.classList.add('bg-green-600', 'hover:bg-green-700');
                    processBtn.classList.remove('bg-blue-600', 'hover:bg-blue-700');
                }, 2000);
                
                if (data.extracted_text && data.extracted_text.trim()) {
                    resultDiv.innerHTML = `
                        <div class='mt-2 p-2 bg-green-50 dark:bg-green-900/20 rounded border border-green-200 dark:border-green-800'>
                            <p class='text-green-800 dark:text-green-200 text-sm'>✓ Text extracted successfully (${data.extracted_text.length} characters)</p>
                        </div>
                    `;
                } else {
                    resultDiv.innerHTML = `
                        <div class='mt-2 p-2 bg-yellow-50 dark:bg-yellow-900/20 rounded border border-yellow-200 dark:border-yellow-800'>
                            <p class='text-yellow-800 dark:text-yellow-200 text-sm'>Processed successfully, but no text was extracted.</p>
                        </div>
                    `;
                }
            } else {
                throw new Error(data.error || 'Processing failed');
            }
        } catch (err) {
            progressText.classList.remove('pulse-animation');
            this.updateProgress(progressBar, progressText, progressPercentage, 0, 'Processing failed');
            progressBar.classList.remove('bg-blue-600');
            progressBar.classList.add('bg-red-600');
            statusSpan.textContent = 'failed';
            
            // Check for rate limit error
            const isRateLimitError = err.message.toLowerCase().includes('rate limit') || 
                                   err.message.toLowerCase().includes('429') ||
                                   err.message.toLowerCase().includes('too many requests');
            
            let errorMessage = err.message;
            let errorType = 'Processing Failed';
            
            if (isRateLimitError) {
                errorType = 'Rate Limit Reached';
                errorMessage = 'Adobe API rate limit reached. Please wait 5-10 minutes before trying again.';
            }
            
            resultDiv.innerHTML = `
                <div class='mt-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800'>
                    <div class='flex items-center mb-1'>
                        <svg class='w-4 h-4 text-red-600 mr-2' fill='currentColor' viewBox='0 0 20 20'>
                            <path fill-rule='evenodd' d='M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z' clip-rule='evenodd'></path>
                        </svg>
                        <strong class='text-red-800 dark:text-red-200'>${errorType}</strong>
                    </div>
                    <p class='text-sm text-red-700 dark:text-red-300'>${errorMessage}</p>
                    ${isRateLimitError ? '<p class="text-xs text-red-600 mt-1">💡 Tip: Try again in 5-10 minutes</p>' : ''}
                </div>
            `;
            
            // Reset button for retry
            setTimeout(() => {
                processBtn.disabled = false;
                processBtn.textContent = 'Retry';
                progressContainer.classList.add('hidden');
                progressBar.classList.remove('bg-red-600');
                progressBar.classList.add('bg-blue-600');
            }, 3000);
        }
    }

    /**
     * Poll file status for real-time progress updates
     * @param {string} uploadId - Upload ID
     * @param {HTMLElement} item - File item element
     * @param {HTMLElement} progressBar - Progress bar element
     * @param {HTMLElement} progressText - Progress text element
     * @param {HTMLElement} progressPercentage - Progress percentage element
     * @param {HTMLElement} statusSpan - Status span element
     * @param {HTMLElement} resultDiv - Result div element
     * @param {HTMLElement} processBtn - Process button element
     * @param {HTMLElement} progressContainer - Progress container element
     */
    async pollFileStatus(uploadId, item, progressBar, progressText, progressPercentage, statusSpan, resultDiv, processBtn, progressContainer) {
        const maxAttempts = 120; // 10 minutes max (polling every 5 seconds)
        let attempts = 0;
        let interval;

        const poll = async () => {
            try {
                attempts++;
                console.log(`Polling attempt ${attempts} for upload ID: ${uploadId}`);
                
                const statusResult = await this.api.getFileStatus(uploadId);
                console.log('Status result:', statusResult);
                
                if (statusResult.success) {
                    const { status, progress, message } = statusResult;
                    console.log(`Status: ${status}, Progress: ${progress}%, Message: ${message}`);
                    
                    // Update progress bar
                    this.updateProgress(progressBar, progressText, progressPercentage, progress, message);
                    
                    if (status === 'processed') {
                        // Processing completed successfully
                        console.log('Processing completed successfully');
                        clearInterval(interval);
                        statusSpan.textContent = 'completed';
                        processBtn.textContent = 'Processed ✓';
                        processBtn.classList.add('bg-green-600', 'hover:bg-green-700');
                        processBtn.classList.remove('bg-blue-600', 'hover:bg-blue-700');

                        // Get final result and show success message
                        const finalResult = await this.api.processFile(uploadId);
                        if (finalResult.success) {
                            this.showSuccessMessage(finalResult, item);
                        }

                        // Hide progress after delay
                        setTimeout(() => {
                            progressContainer.classList.add('hidden');
                        }, 2000);
                        
                    } else if (status === 'failed') {
                        // Processing failed
                        console.log('Processing failed on server');
                        clearInterval(interval);
                        throw new Error('Processing failed on server');
                        
                    } else if (status === 'processing' || status === 'uploaded') {
                        // Still processing, continue polling
                        console.log(`Still processing (${status}), continuing to poll...`);
                        if (attempts >= maxAttempts) {
                            clearInterval(interval);
                            throw new Error('Processing timed out');
                        }
                    } else {
                        // Unknown status, log it and continue polling
                        console.log(`Unknown status: ${status}, continuing to poll...`);
                        if (attempts >= maxAttempts) {
                            clearInterval(interval);
                            throw new Error('Processing timed out');
                        }
                    }
                } else {
                    // Status check failed
                    console.log('Status check failed:', statusResult.error);
                    if (attempts >= maxAttempts) {
                        clearInterval(interval);
                        throw new Error('Failed to get processing status');
                    }
                }
            } catch (error) {
                console.error('Polling error:', error);
                if (attempts >= maxAttempts) {
                    clearInterval(interval);
                    throw error;
                }
            }
        };

        // Start polling every 5 seconds
        interval = setInterval(poll, 5000);
        
        // Initial poll
        await poll();
    }

    /**
     * Simulate processing progress with enhanced steps
     * @param {HTMLElement} progressBar - Progress bar element
     * @param {HTMLElement} progressText - Progress text element
     * @param {HTMLElement} progressPercentage - Progress percentage element
     * @param {string} documentType - Type of document being processed
     */
    async simulateProgress(progressBar, progressText, progressPercentage, documentType) {
        const steps = [
            { progress: 10, text: 'Uploading file...', duration: 500 },
            { progress: 20, text: 'Extracting text with Adobe OCR...', duration: 1000 },
            { progress: 35, text: 'Running OpenAI geological analysis...', duration: 2000 },
            { progress: 50, text: 'Extracting coordinates and features...', duration: 1000 },
            { progress: 65, text: 'Creating geological features...', duration: 1000 },
            { progress: 80, text: 'Generating training dataset...', duration: 1000 },
            { progress: 90, text: 'Saving analysis results...', duration: 500 },
            { progress: 100, text: 'Processing complete!', duration: 500 }
        ];

        for (const step of steps) {
            progressBar.style.width = `${step.progress}%`;
            progressPercentage.textContent = `${step.progress}%`;
            progressText.textContent = step.text;
            
            await new Promise(resolve => setTimeout(resolve, step.duration));
        }
    }

    /**
     * Update progress bar
     * @param {HTMLElement} progressBar - Progress bar element
     * @param {HTMLElement} progressText - Progress text element
     * @param {HTMLElement} progressPercentage - Progress percentage element
     * @param {number} percentage - Progress percentage
     * @param {string} text - Progress text
     */
    updateProgress(progressBar, progressText, progressPercentage, percentage, text) {
        console.log(`Updating progress: ${percentage}% - ${text}`);
        console.log('Progress elements:', { progressBar, progressText, progressPercentage });
        
        if (progressBar) {
            progressBar.style.width = percentage + '%';
        } else {
            console.error('Progress bar element not found!');
        }
        
        if (progressText) {
            progressText.textContent = text;
        } else {
            console.error('Progress text element not found!');
        }
        
        if (progressPercentage) {
            progressPercentage.textContent = percentage + '%';
        } else {
            console.error('Progress percentage element not found!');
        }
        
        // Add visual feedback based on progress
        if (progressBar) {
            if (percentage === 100) {
                progressBar.classList.remove('bg-blue-600', 'bg-yellow-600');
                progressBar.classList.add('bg-green-600');
            } else if (percentage >= 50) {
                progressBar.classList.remove('bg-blue-600', 'bg-green-600');
                progressBar.classList.add('bg-yellow-600');
            } else {
                progressBar.classList.remove('bg-yellow-600', 'bg-green-600');
                progressBar.classList.add('bg-blue-600');
            }
        }
    }
    
    /**
     * Handle processing error
     * @param {Error} error - Error object
     * @param {HTMLElement} progressBar - Progress bar element
     * @param {HTMLElement} progressText - Progress text element
     * @param {HTMLElement} progressPercentage - Progress percentage element
     * @param {HTMLElement} statusSpan - Status span element
     * @param {HTMLElement} resultDiv - Result div element
     * @param {HTMLElement} processBtn - Process button element
     * @param {HTMLElement} progressContainer - Progress container element
     */
    handleProcessingError(error, progressBar, progressText, progressPercentage, statusSpan, resultDiv, processBtn, progressContainer) {
        progressText.classList.remove('pulse-animation');
        this.updateProgress(progressBar, progressText, progressPercentage, 0, 'Processing failed');
        progressBar.classList.remove('bg-blue-600');
        progressBar.classList.add('bg-red-600');
        statusSpan.textContent = 'failed';

        resultDiv.innerHTML = `
            <div class='mt-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800'>
                <div class='flex items-center mb-1'>
                    <svg class='w-4 h-4 text-red-600 mr-2' fill='currentColor' viewBox='0 0 20 20'>
                        <path fill-rule='evenodd' d='M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z' clip-rule='evenodd'></path>
                    </svg>
                    <strong class='text-red-800 dark:text-red-200'>Processing Failed</strong>
                </div>
                <p class='text-sm text-red-700 dark:text-red-300'>${error.message}</p>
            </div>
        `;

        // Reset button for retry
        setTimeout(() => {
            processBtn.disabled = false;
            processBtn.textContent = 'Retry';
            progressContainer.classList.add('hidden');
            progressBar.classList.remove('bg-red-600');
            progressBar.classList.add('bg-blue-600');
        }, 3000);
    }
    
    /**
     * Show success message
     * @param {Object} result - Processing result
     * @param {HTMLElement} item - File item element
     */
    showSuccessMessage(result, item) {
        const resultDiv = item.querySelector('.file-result');

        if (result.extracted_text) {
            const textLength = result.extracted_text.length;
            const wordCount = result.extracted_text.split(/\s+/).filter(word => word.length > 0).length;

            // Build OpenAI analysis results section
            let openaiResults = '';
            if (result.openai_analysis_completed) {
                openaiResults = `
                    <div class='mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800'>
                        <div class='flex items-center mb-2'>
                            <svg class='w-4 h-4 text-blue-600 mr-2' fill='currentColor' viewBox='0 0 20 20'>
                                <path fill-rule='evenodd' d='M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z' clip-rule='evenodd'></path>
                            </svg>
                            <strong class='text-blue-800 dark:text-blue-200'>OpenAI Analysis Complete</strong>
                        </div>
                        <div class='grid grid-cols-2 gap-2 text-xs'>
                            ${result.coordinates_found ? `<div class='text-blue-700 dark:text-blue-300'>📍 Coordinates: ${result.coordinates_found}</div>` : ''}
                            ${result.geological_formations ? `<div class='text-blue-700 dark:text-blue-300'>🪨 Formations: ${result.geological_formations}</div>` : ''}
                            ${result.minerals_found ? `<div class='text-blue-700 dark:text-blue-300'>💎 Minerals: ${result.minerals_found}</div>` : ''}
                            ${result.gold_indicators ? `<div class='text-blue-700 dark:text-blue-300'>🥇 Gold Indicators: ${result.gold_indicators}</div>` : ''}
                            ${result.elevations ? `<div class='text-blue-700 dark:text-blue-300'>🏔️ Elevations: ${result.elevations}</div>` : ''}
                            ${result.soil_types ? `<div class='text-blue-700 dark:text-blue-300'>🌱 Soil Types: ${result.soil_types}</div>` : ''}
                        </div>
                        ${result.analysis_filename ? `<div class='mt-2 text-xs text-blue-600'>📄 Analysis saved: ${result.analysis_filename}</div>` : ''}
                    </div>
                `;
            }

            resultDiv.innerHTML = `
                <div class='mt-2 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800'>
                    <div class='flex items-center mb-2'>
                        <svg class='w-4 h-4 text-green-600 mr-2' fill='currentColor' viewBox='0 0 20 20'>
                            <path fill-rule='evenodd' d='M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z' clip-rule='evenodd'></path>
                        </svg>
                        <strong class='text-green-800 dark:text-green-200'>Extraction Complete</strong>
                    </div>
                    <p class='text-sm text-green-700 dark:text-green-300 mb-2'>
                        ${textLength.toLocaleString()} characters, ${wordCount.toLocaleString()} words extracted
                        ${result.processing_method ? `<br><span class="text-xs text-blue-600">Processed using: ${result.processing_method}</span>` : ''}
                        ${result.processing_method && result.processing_method.includes('Placeholder') ? `<br><span class="text-xs text-yellow-600">⚠️ OCR extraction failed - using placeholder data</span>` : ''}
                        ${result.dataset_generated ? `<br><span class="text-xs text-green-600">✅ Dataset generated (${result.rows_count || 0} rows)</span>` : ''}
                        ${result.geological_features_created ? `<br><span class="text-xs text-green-600">✅ ${result.geological_features_created} geological features created</span>` : ''}
                    </p>
                    <div class='max-h-32 overflow-y-auto bg-white dark:bg-zinc-800 p-2 rounded border'>
                        <pre class='whitespace-pre-wrap text-xs text-zinc-800 dark:text-zinc-200'>${result.extracted_text.substring(0, 500)}${result.extracted_text.length > 500 ? '\n\n... (truncated)' : ''}</pre>
                    </div>
                    ${openaiResults}
                </div>
            `;
        } else {
            resultDiv.innerHTML = `
                <div class='mt-2 p-2 bg-yellow-50 dark:bg-yellow-900/20 rounded border border-yellow-200 dark:border-yellow-800'>
                    <p class='text-yellow-800 dark:text-yellow-200 text-sm'>Processed successfully, but no text was extracted.</p>
                </div>
            `;
        }
    }

    /**
     * Show upload modal
     */
    showUploadModal() {
        console.log('showUploadModal called'); // Debug log
        const modal = document.getElementById('upload-modal');
        console.log('showUploadModal - modal element:', modal); // Debug log
        
        if (modal) {
            console.log('showUploadModal - showing modal'); // Debug log
            modal.classList.remove('hidden');
            modal.classList.add('flex');
            
            // Initialize document type from UI when modal is shown
            this.selectedDocumentType = this.getSelectedDocumentType();
            console.log('Modal shown - initialized document type:', this.selectedDocumentType); // Debug log
        } else {
            console.error('showUploadModal - modal element not found!'); // Debug log
            console.error('Available elements with "upload" in ID:', 
                Array.from(document.querySelectorAll('[id*="upload"]')).map(el => el.id)); // Debug log
        }
    }
    
    /**
     * Close upload modal (simplified for index4.html structure)
     */
    closeUploadModal() {
        const modal = document.getElementById('upload-modal');
        const fileInput = document.getElementById('uploadFile1');
        
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        }
        
        if (fileInput) {
            fileInput.value = '';
        }
        
        // Remove success message if it exists
        const successMessage = document.getElementById('upload-success-message');
        if (successMessage) {
            successMessage.remove();
        }
        
        // Reset selected files
        this.selectedFiles = [];
        
        // Clear the files list and show empty message
        const filesList = document.getElementById('uploaded-files-list');
        if (filesList) {
            filesList.innerHTML = '<div id="uploaded-files-empty" class="text-center text-zinc-400 dark:text-zinc-500">No files uploaded yet.</div>';
        }
    }

    /**
     * Close success modal
     */
    closeSuccessModal() {
        const modal = document.getElementById('success-modal');
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        }
    }

    /**
     * Copy extracted text to clipboard
     */
    async copyExtractedText() {
        const textDisplay = document.getElementById('extracted-text-display');
        if (textDisplay) {
            await this.ui.copyToClipboard(textDisplay.textContent);
        }
    }

    /**
     * Sleep utility function
     * @param {number} ms - Milliseconds to sleep
     * @returns {Promise} - Promise that resolves after delay
     */
        sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    /**
     * Get the selected document type from the UI
     * @returns {string} - Selected document type
     */
    getSelectedDocumentType() {
        const selectedRadio = document.querySelector('input[name="document_type"]:checked');
        const documentType = selectedRadio ? selectedRadio.value : 'geological_survey';
        console.log('getSelectedDocumentType - selectedRadio:', selectedRadio); // Debug log
        console.log('getSelectedDocumentType - documentType:', documentType); // Debug log
        return documentType;
    }

    /**
     * Format file size in bytes to a human-readable string
     * @param {number} bytes - File size in bytes
     * @returns {string} - Formatted file size
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Get CSRF token from cookies
     * @param {string} name - Cookie name
     * @returns {string|null} Cookie value
     */
    getCookie(name) {
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
}

// Initialize upload handler when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.uploadHandler = new UploadHandler();
}); 