// Support Chat Bot Functionality
document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');
    const footerModal = document.getElementById('footer-modal');
    const supportButton = document.querySelector('[data-modal-target="footer-modal"]');
    const closeModalButton = document.querySelector('[data-modal-hide="footer-modal"]');

    // Add pulse effect to support button
    if (supportButton) {
        supportButton.querySelector('img').classList.add('support-pulse');
    }

    // Predefined responses for common questions
    const responses = {
        'greeting': [
            "Hello! How can I help you today?",
            "Hi there! What can I assist you with?",
            "Welcome to GoldMine AI support! How may I help you?"
        ],
        'about': [
            "GoldMine AI is a platform that uses artificial intelligence to predict potential gold deposits based on geological data. Our system analyzes various factors such as soil type, terrain, and historical mining data to provide accurate predictions."
        ],
        'features': [
            "GoldMine AI offers several features including: 2D and 3D maps for visualization, predictive AI models for gold deposit identification, real-time gold price tracking, and data upload capabilities for your own datasets."
        ],
        'price': [
            "You can check current gold prices on our homepage. We provide real-time gold price data per gram with historical trends. The data is updated every 5 minutes from reliable market sources."
        ],
        'account': [
            "You can create an account by clicking the 'Sign in' button in the top right corner and then selecting 'Create account'. This will allow you to save your predictions and access more advanced features."
        ],
        'upload': [
            "To upload your data, click on the upload button in the navigation bar. We accept CSV, Excel, and PDF formats. Your data will be processed and analyzed by our AI model."
        ],
        'map': [
            "Our platform offers three map views: 2D satellite view, 3D terrain view, and 3D globe view. You can switch between these views using the dropdown selector on the maps page."
        ],
        'predict': [
            "To get a prediction, navigate to the 'Predict' page, input your geological data (or upload a dataset), and our AI model will analyze the information to generate a prediction of gold deposit probability."
        ],
        'contact': [
            "You can contact our team at support@goldmineai.com or through this chat. We typically respond within 24 hours on business days."
        ],
        'fallback': [
            "Contact tech support at support@goldmineai.com",
            "I'm not sure I understand. Could you please provide more details or ask a different question?",
            "I'm still learning! Could you rephrase your question?",
            "I don't have information on that topic yet. Would you like to know about our features, maps, or prediction capabilities instead?"
        ]
    };

    // Initialize the chat
    function initChat() {
        // Event listeners
        if (chatForm) {
            chatForm.addEventListener('submit', handleSubmit);
        }
        
        if (supportButton) {
            supportButton.addEventListener('click', openChat);
        }
        
        if (closeModalButton) {
            closeModalButton.addEventListener('click', closeChat);
        }
        
        // Add resize handler to keep modal positioned correctly
        window.addEventListener('resize', handleResize);
    }

    // Handle form submission
    function handleSubmit(e) {
        e.preventDefault();
        const message = userInput.value.trim();
        
        if (message === '') return;
        
        // Check if this is a geological query
        const isGeologicalQuery = shouldUseIntelligentAnalysis(message);
        
        // Show/hide analysis indicator
        const analysisIndicator = document.getElementById('analysis-indicator');
        if (analysisIndicator) {
            if (isGeologicalQuery) {
                analysisIndicator.classList.remove('hidden');
            } else {
                analysisIndicator.classList.add('hidden');
            }
        }
        
        // Add user message to chat
        addMessage(message, 'user');
        
        // Clear input
        userInput.value = '';
        
        // Show typing indicator
        showTypingIndicator();
        
        // Use intelligent analysis for geological queries
        if (isGeologicalQuery) {
            processIntelligentQuery(message);
        } else {
            // Generate response after a slight delay to simulate thinking
            setTimeout(() => {
                const response = generateResponse(message);
                
                // Remove typing indicator
                removeTypingIndicator();
                
                // Add bot response
                addMessage(response, 'bot');
                
                // Scroll to bottom
                scrollToBottom();
            }, 1000 + Math.random() * 1000); // Random delay between 1-2 seconds
        }
    }

    // Check if message should use intelligent analysis
    function shouldUseIntelligentAnalysis(message) {
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

    // Process intelligent geological query
    async function processIntelligentQuery(message) {
        try {
            // Check if APIClient is available
            if (typeof APIClient === 'undefined') {
                console.error('APIClient not available, falling back to basic response');
                const response = generateResponse(message);
                removeTypingIndicator();
                addMessage(response, 'bot');
                scrollToBottom();
                return;
            }

            const apiClient = new APIClient();
            
            // Send query to intelligent analysis system
            const data = await apiClient.sendChatMessage(message, []);
            
            if (data.success) {
                removeTypingIndicator();
                
                // Display intelligent analysis response
                displayIntelligentResponse(data);
            } else {
                // Handle error
                removeTypingIndicator();
                addMessage('Sorry, I encountered an error processing your geological query. Please try again.', 'bot');
                console.error('Intelligent query error:', data.error);
            }
            
            scrollToBottom();
            
        } catch (error) {
            console.error('Error processing intelligent query:', error);
            removeTypingIndicator();
            addMessage('Sorry, I encountered an error. Please try again.', 'bot');
            scrollToBottom();
        }
    }

    // Display intelligent analysis response
    function displayIntelligentResponse(data) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chat-message bot mb-3';
        
        let html = `
            <div class="flex items-start">
                <div class="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-600 flex items-center justify-center mr-2">
                    <svg class="w-5 h-5 text-blue-600 dark:text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"></path>
                    </svg>
                </div>
                <div class="ml-2 py-2 px-3 bg-blue-100 dark:bg-blue-600 rounded-lg rounded-tl-none max-w-md">
                    <div class="space-y-3">
                        <!-- Main Response -->
                        <div class="text-gray-800 dark:text-gray-200">
                            ${data.response.replace(/\n/g, '<br>')}
                        </div>
                        

                        
                        <!-- Generated Coordinates Section -->
                        ${data.coordinates && data.coordinates.length > 0 ? `
                        <div class="mt-3 p-2 bg-green-50 dark:bg-green-800 rounded border border-green-200 dark:border-green-700">
                            <div class="flex items-center mb-2">
                                <svg class="w-4 h-4 text-green-600 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clip-rule="evenodd"></path>
                                </svg>
                                <span class="text-xs text-green-700 dark:text-green-300 font-medium">Generated Exploration Targets</span>
                            </div>
                            
                            <div class="space-y-2">
                                ${data.coordinates.map((coord, index) => `
                                    <div class="text-xs space-y-1">
                                        <div class="font-medium text-green-800 dark:text-green-200">
                                            ${index + 1}. ${coord.area_name}
                                        </div>
                                        <div class="text-green-600 dark:text-green-300">
                                            📍 ${coord.latitude.toFixed(4)}°N, ${Math.abs(coord.longitude).toFixed(4)}°W
                                        </div>
                                        <div class="text-green-600 dark:text-green-300">
                                            🏔️ ${coord.elevation.value} ${coord.elevation.unit} (${coord.elevation.confidence})
                                        </div>
                                        <div class="text-green-600 dark:text-green-300">
                                            🎯 Confidence: ${(coord.confidence * 100).toFixed(0)}%
                                        </div>
                                        <div class="text-green-500 dark:text-green-400 text-xs">
                                            ${coord.description}
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                        ` : ''}
                        
                        <!-- AI Analysis Badge -->
                        <div class="flex justify-center">
                            <div class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-200">
                                <svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                                </svg>
                                AI Geological Analysis
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        messageDiv.innerHTML = html;
        chatMessages.appendChild(messageDiv);
    }

    // Add a message to the chat
    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${sender} mb-3`;
        
        let html = '';
        if (sender === 'user') {
            html = `
                <div class="flex items-start">
                    <div class="ml-2 py-2 px-3 bg-blue-100 dark:bg-blue-600 rounded-lg rounded-tl-none">
                        <p class="text-gray-800 dark:text-gray-200">${text}</p>
                    </div>
                    <div class="w-8 h-8 rounded-full bg-zinc-100 dark:bg-zinc-700 flex items-center justify-center ml-2">
                        <svg class="w-4 h-4 text-zinc-600 dark:text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
                        </svg>
                    </div>
                </div>
            `;
        } else {
            html = `
                <div class="flex items-start">
                    <div class="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-600 flex items-center justify-center mr-2">
                        <svg class="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"></path>
                        </svg>
                    </div>
                    <div class="ml-2 py-2 px-3 bg-blue-100 dark:bg-blue-600 rounded-lg rounded-tl-none">
                        <p class="text-gray-800 dark:text-gray-200">${text}</p>
                    </div>
                </div>
            `;
        }
        
        messageDiv.innerHTML = html;
        chatMessages.appendChild(messageDiv);
        scrollToBottom();
    }

    // Show typing indicator
    function showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'chat-message bot typing mb-3';
        typingDiv.id = 'typing-indicator';
        
        const html = `
            <div class="flex items-start">
                <div class="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-600 flex items-center justify-center mr-2">
                    <svg class="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"></path>
                    </svg>
                </div>
                <div class="ml-2 py-2 px-3 bg-blue-100 dark:bg-blue-600 rounded-lg rounded-tl-none">
                    <div class="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        `;
        
        typingDiv.innerHTML = html;
        chatMessages.appendChild(typingDiv);
        scrollToBottom();
    }

    // Remove typing indicator
    function removeTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    // Generate a response based on user input
    function generateResponse(message) {
        message = message.toLowerCase();
        
        // Check for greetings
        if (message.match(/^(hi|hello|hey|greetings|sup|what's up).*/i)) {
            return getRandomResponse('greeting');
        }
        
        // Check for about inquiries
        if (message.match(/.*(what is|about|tell me about|info about|information on|what's|whats).*(goldmine|gold mine|this site|this website|this platform|this application).*/i)) {
            return getRandomResponse('about');
        }
        
        // Check for feature inquiries
        if (message.match(/.*(what|which|tell me about|list|show).*(features|functions|capabilities|options).*/i)) {
            return getRandomResponse('features');
        }
        
        // Check for price inquiries
        if (message.match(/.*(gold|price|market|value|rates|cost).*/i)) {
            return getRandomResponse('price');
        }
        
        // Check for account inquiries
        if (message.match(/.*(account|sign up|register|login|log in|signin|sign in).*/i)) {
            return getRandomResponse('account');
        }
        
        // Check for upload inquiries
        if (message.match(/.*(upload|file|dataset|data|csv|excel).*/i)) {
            return getRandomResponse('upload');
        }
        
        // Check for map inquiries
        if (message.match(/.*(map|maps|view|2d|3d|globe|terrain|satellite).*/i)) {
            return getRandomResponse('map');
        }
        
        // Check for prediction inquiries
        if (message.match(/.*(predict|prediction|analysis|analyze|ai|model|forecast).*/i)) {
            return getRandomResponse('predict');
        }
        
        // Check for contact inquiries
        if (message.match(/.*(contact|email|phone|reach|support|help|team).*/i)) {
            return getRandomResponse('contact');
        }
        
        // Fallback
        return getRandomResponse('fallback');
    }

    // Get a random response from a category
    function getRandomResponse(category) {
        const responseArray = responses[category] || responses['fallback'];
        const randomIndex = Math.floor(Math.random() * responseArray.length);
        return responseArray[randomIndex];
    }

    // Scroll chat to bottom
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Open chat
    function openChat() {
        // First remove hidden class to make the element in the DOM
        footerModal.classList.remove('hidden');
        
        // Force a reflow to ensure the CSS transition works properly
        void footerModal.offsetWidth;
        
        // Make sure the modal is properly positioned
        footerModal.style.position = 'fixed';
        footerModal.style.bottom = window.innerWidth < 768 ? '16px' : '32px';  
        footerModal.style.right = window.innerWidth < 768 ? '16px' : '32px';
        
        // Add show class for the animation
        footerModal.classList.add('show');
        
        // Add a subtle entrance animation for the chat messages
        const messages = chatMessages.querySelectorAll('.chat-message');
        messages.forEach((message, index) => {
            message.style.opacity = '0';
            message.style.transform = 'translateY(10px)';
            message.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            
            setTimeout(() => {
                message.style.opacity = '1';
                message.style.transform = 'translateY(0)';
            }, 300 + (index * 100));
        });
        
        // Focus on input field after animation completes
        setTimeout(() => {
            userInput.focus();
        }, 400);
    }

    // Close chat
    function closeChat() {
        // First remove the show class for the animation
        footerModal.classList.remove('show');
        
        // Add hidden class after transition completes
        setTimeout(() => {
            footerModal.classList.add('hidden');
            
            // Reset message animations for next opening
            const messages = chatMessages.querySelectorAll('.chat-message');
            messages.forEach(message => {
                message.style.opacity = '';
                message.style.transform = '';
                message.style.transition = '';
            });
        }, 400); // Match this with the CSS transition duration
    }

    // Handle window resize
    function handleResize() {
        if (footerModal && footerModal.classList.contains('show')) {
            footerModal.style.bottom = window.innerWidth < 768 ? '16px' : '32px';
            footerModal.style.right = window.innerWidth < 768 ? '16px' : '32px';
            
            // Adjust height if needed
            const maxHeight = window.innerHeight * 0.8;
            const modalContent = footerModal.querySelector('.bg-white, .dark\\:bg-zinc-800');
            if (modalContent) {
                modalContent.style.maxHeight = `${maxHeight}px`;
            }
        }
    }

    // Initialize the chat
    initChat();
}); 