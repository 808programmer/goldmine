// Dark Mode Toggle
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded');
    
    // Get DOM elements with error checking
    const themeToggleDarkIcon = document.getElementById('theme-toggle-dark-icon');
    console.log('Dark icon found:', themeToggleDarkIcon !== null);
    
    const themeToggleLightIcon = document.getElementById('theme-toggle-light-icon');
    console.log('Light icon found:', themeToggleLightIcon !== null);
    
    const themeToggleBtn = document.getElementById('theme-toggle');
    console.log('Toggle button found:', themeToggleBtn !== null);

    // Check if elements exist
    if (!themeToggleDarkIcon || !themeToggleLightIcon || !themeToggleBtn) {
        console.error('Theme toggle elements not found');
        return;
    }

    console.log('Theme toggle initialized');
    
    // Set the initial theme based on localStorage or system preference
    function setTheme() {
        // First, make sure both icons are hidden
        themeToggleDarkIcon.classList.add('hidden');
        themeToggleLightIcon.classList.add('hidden');
        
        const isDarkMode = localStorage.getItem('color-theme') === 'dark' || 
            (!('color-theme' in localStorage) && 
             window.matchMedia('(prefers-color-scheme: dark)').matches);
        
        console.log('Should be dark mode?', isDarkMode);
        console.log('color-theme in localStorage:', localStorage.getItem('color-theme'));
        
        if (isDarkMode) {
            // Dark mode
            document.documentElement.classList.add('dark');
            themeToggleLightIcon.classList.remove('hidden'); // Show sun icon in dark mode
            console.log('Dark mode activated');
        } else {
            // Light mode
            document.documentElement.classList.remove('dark');
            themeToggleDarkIcon.classList.remove('hidden'); // Show moon icon in light mode
            console.log('Light mode activated');
        }
    }

    // Call initially to set the theme
    setTheme();

    // Toggle theme function
    function toggleTheme() {
        console.log('Toggle button clicked');
        
        // Get all elements that have dark mode variants
        const darkModeElements = document.querySelectorAll('[class*="dark:"]');
        
        // Toggle icons with a smooth fade
        themeToggleDarkIcon.style.transition = 'opacity 300ms ease';
        themeToggleLightIcon.style.transition = 'opacity 300ms ease';
        
        // Prepare the icons for transition
        if (document.documentElement.classList.contains('dark')) {
            // Switching to light mode
            themeToggleLightIcon.style.opacity = '0';
            themeToggleDarkIcon.style.opacity = '0';
            setTimeout(() => {
                themeToggleDarkIcon.classList.remove('hidden');
                themeToggleLightIcon.classList.add('hidden');
                setTimeout(() => {
                    themeToggleDarkIcon.style.opacity = '1';
                }, 50);
            }, 150);
        } else {
            // Switching to dark mode
            themeToggleDarkIcon.style.opacity = '0';
            themeToggleLightIcon.style.opacity = '0';
            setTimeout(() => {
                themeToggleLightIcon.classList.remove('hidden');
                themeToggleDarkIcon.classList.add('hidden');
                setTimeout(() => {
                    themeToggleLightIcon.style.opacity = '1';
                }, 50);
            }, 150);
        }
        
        // Check current theme and update with smooth transition
        // First, ensure all elements have transitions
        document.body.style.transition = 'background-color 500ms ease, color 500ms ease';
        darkModeElements.forEach(el => {
            if (!el.style.transition) {
                el.style.transition = 'background-color 500ms ease, color 500ms ease, border-color 500ms ease, opacity 500ms ease';
            }
        });
        
        // Apply the theme change
        if (document.documentElement.classList.contains('dark')) {
            document.documentElement.classList.remove('dark');
            localStorage.setItem('color-theme', 'light');
            console.log('Switched to light mode');
        } else {
            document.documentElement.classList.add('dark');
            localStorage.setItem('color-theme', 'dark');
            console.log('Switched to dark mode');
        }
    }

    // Event listener for theme toggle button
    if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', toggleTheme);
    } else {
        console.warn('Theme toggle button not found');
    }
    
    // ===== Page Transition Functionality =====
    console.log('Initializing page transitions');
    
    // Apply FOUC prevention classes
    document.body.classList.add('no-fouc', 'transition-ready', 'gpu-accelerated');
    
    // Create overlay for smoother transitions
    const transitionOverlay = document.createElement('div');
    transitionOverlay.className = 'page-transition-overlay';
    document.body.appendChild(transitionOverlay);
    
    // Apply initial fade-in effect with slide up
    document.body.style.opacity = '0';
    document.body.style.transform = 'translateY(20px)';
    document.body.style.transition = 'opacity 800ms cubic-bezier(0.19, 1, 0.22, 1), transform 800ms cubic-bezier(0.19, 1, 0.22, 1)';
    
    // Function to add overlay transition style to head
    function addOverlayStyle() {
        const styleEl = document.createElement('style');
        styleEl.textContent = `
            .page-transition-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: #d1d5db;
                z-index: 9999;
                opacity: 0;
                pointer-events: none;
                transition: opacity 600ms cubic-bezier(0.19, 1, 0.22, 1);
                will-change: opacity;
            }
            
            .dark .page-transition-overlay {
                background-color: #18181b;
            }
            
            .page-transition-overlay.visible {
                opacity: 1;
                pointer-events: all;
            }
            
            /* Prevent flickering by hiding content until we're ready */
            html.loading {
                visibility: hidden;
                opacity: 0;
            }
            
            /* Prevent scroll during transitions */
            html.transitioning {
                overflow: hidden;
                height: 100%;
            }
        `;
        document.head.appendChild(styleEl);
    }
    
    // Add the overlay style
    addOverlayStyle();
    
    // Mark as loading until ready
    document.documentElement.classList.add('loading');
    
    // Add a small script to the head to prevent flash of unstyled content
    function addInstantHideScript() {
        const script = document.createElement('script');
        script.textContent = `
            // Hide page immediately to prevent FOUC
            document.documentElement.classList.add('loading');
        `;
        // Add at the very beginning of head for immediate execution
        document.head.insertBefore(script, document.head.firstChild);
    }
    
    // Add instant hide script for future page loads
    addInstantHideScript();
    
    // Preload images for smoother experience
    function preloadImages() {
        const images = document.querySelectorAll('img');
        
        if (images.length > 0) {
            console.log(`Preloading ${images.length} images for smoother transitions`);
            
            // Create an array to track loaded images
            const imagePromises = [];
            
            images.forEach(img => {
                // Only preload images with src attribute
                if (img.src) {
                    const promise = new Promise((resolve, reject) => {
                        // If already loaded, resolve immediately
                        if (img.complete) {
                            resolve();
                            return;
                        }
                        
                        // Set up load and error handlers
                        img.onload = () => resolve();
                        img.onerror = () => resolve(); // Resolve anyway to continue
                    });
                    
                    imagePromises.push(promise);
                }
            });
            
            // When all critical images are loaded, fade in the page
            Promise.all(imagePromises)
                .then(() => {
                    console.log('Critical images loaded');
                    setTimeout(() => fadeInPage(), 100); // Small delay to ensure rendering is complete
                })
                .catch(() => {
                    console.log('Some images failed to load, fading in anyway');
                    setTimeout(() => fadeInPage(), 100);
                });
        } else {
            // No images to preload, fade in after a small delay to ensure page is ready
            setTimeout(() => fadeInPage(), 100);
        }
    }
    
    // Function to fade in the page
    function fadeInPage() {
        // First make page visible but still transparent
        document.documentElement.classList.remove('loading');
        
        // Remove FOUC prevention
        document.body.classList.remove('no-fouc');
        
        // Hide the overlay
        transitionOverlay.classList.remove('visible');
        
        // Fade in the page with a slight delay to ensure smooth transition
        setTimeout(() => {
            document.body.style.opacity = '1';
            document.body.style.transform = 'translateY(0)';
            console.log('Page fade-in complete');
        }, 50);
    }
    
    // Start preloading images after a small delay to ensure the DOM is ready
    setTimeout(() => preloadImages(), 50);
    
    // Get all internal links for smooth page transitions
    const internalLinks = document.querySelectorAll('a[href^="/"], a[href^="./"], a[href^="../"], a[href^="' + window.location.origin + '"]');
    
    // Track if navigation is in progress to prevent double-clicks
    let isNavigating = false;
    
    internalLinks.forEach(link => {
        // Skip links with target="_blank" or download attribute
        if (link.getAttribute('target') === '_blank' || link.hasAttribute('download')) {
            return;
        }
        
        link.addEventListener('click', function(e) {
            // Skip if already navigating
            if (isNavigating) {
                e.preventDefault();
                return;
            }
            
            // Skip for modifier keys
            if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) {
                return;
            }
            
            const href = this.getAttribute('href');
            
            // Skip for same-page anchors and JavaScript links
            if (href.startsWith('#') || href.startsWith('javascript:')) {
                return;
            }
            
            // Skip for external links
            if (href.indexOf('://') > 0 || href.indexOf('//') === 0) {
                return;
            }
            
            e.preventDefault();
            isNavigating = true;
            
            // Prevent scrolling during transition
            document.documentElement.classList.add('transitioning');
            
            // Preload the next page (optional if server allows)
            const prefetcher = document.createElement('link');
            prefetcher.rel = 'prefetch';
            prefetcher.href = href;
            document.head.appendChild(prefetcher);
            
            // First show the overlay
            transitionOverlay.classList.add('visible');
            
            // Then start the fade out animation
            setTimeout(() => {
                // Smoothly fade out the page
                document.body.style.opacity = '0';
                document.body.style.transform = 'translateY(20px)';
                
                // Store destination to localStorage for next page load
                localStorage.setItem('lastTransitionDestination', href);
                
                // Navigate after fade-out completes
                setTimeout(() => {
                    window.location.href = href;
                }, 400);
            }, 200);
        });
    });
    
    // Store the current scroll position before page unload
    window.addEventListener('beforeunload', function() {
        // Store scroll position for restoration after page load
        sessionStorage.setItem('scrollPosition', window.scrollY);
        
        // Mark document as loading (will be applied on next page)
        document.documentElement.classList.add('loading');
        
        // Show the overlay first for a smoother experience
        transitionOverlay.classList.add('visible');
        
        // Then fade out the content
        setTimeout(() => {
            document.body.style.opacity = '0';
            document.body.style.transform = 'translateY(20px)';
        }, 50);
    });
    
    // Detect if we came from another page via our transition
    const cameFromTransition = !!localStorage.getItem('lastTransitionDestination');
    if (cameFromTransition) {
        // Force the overlay to be immediately visible without transition
        transitionOverlay.style.transition = 'none';
        transitionOverlay.classList.add('visible');
        
        // Force a reflow to ensure the style is applied
        void transitionOverlay.offsetWidth;
        
        // Restore the transition
        setTimeout(() => {
            transitionOverlay.style.transition = '';
        }, 10);
        
        // Clear the flag
        localStorage.removeItem('lastTransitionDestination');
    }
    
    // Restore scroll position if available
    const savedScrollPosition = sessionStorage.getItem('scrollPosition');
    if (savedScrollPosition) {
        window.scrollTo(0, parseInt(savedScrollPosition));
        sessionStorage.removeItem('scrollPosition');
    }
});

// Historical Prospects Analysis
document.addEventListener('DOMContentLoaded', function() {
    const analyzeHistoricalBtn = document.getElementById('analyze-historical-btn');
    const historicalResults = document.getElementById('historical-results');
    const historicalLoading = document.getElementById('historical-loading');
    const historicalProspectsList = document.getElementById('historical-prospects-list');
    const historicalSummary = document.getElementById('historical-summary');

    if (analyzeHistoricalBtn) {
        analyzeHistoricalBtn.addEventListener('click', function() {
            analyzeHistoricalProspects();
        });
    }

    async function analyzeHistoricalProspects() {
        try {
            // Show loading state
            historicalLoading.classList.remove('hidden');
            historicalResults.classList.add('hidden');
            analyzeHistoricalBtn.disabled = true;
            analyzeHistoricalBtn.innerHTML = `
                <svg class="animate-spin w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Analyzing...
            `;

            const response = await fetch('/api/analyze-historical-prospects/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    query: 'Analyze historical geological documents for mining prospects'
                })
            });

            const data = await response.json();

            if (data.success) {
                displayHistoricalResults(data);
            } else {
                showHistoricalError(data.error || 'Failed to analyze historical prospects');
            }

        } catch (error) {
            console.error('Error analyzing historical prospects:', error);
            showHistoricalError('Network error occurred while analyzing historical prospects');
        } finally {
            // Hide loading state
            historicalLoading.classList.add('hidden');
            analyzeHistoricalBtn.disabled = false;
            analyzeHistoricalBtn.innerHTML = `
                <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                Analyze Historical Prospects
            `;
        }
    }

    function displayHistoricalResults(data) {
        // Display prospects
        historicalProspectsList.innerHTML = '';
        
        if (data.prospects && data.prospects.length > 0) {
            data.prospects.forEach((prospect, index) => {
                const prospectElement = document.createElement('div');
                prospectElement.className = 'bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3 border border-amber-200 dark:border-amber-600';
                prospectElement.innerHTML = `
                    <div class="font-mono text-sm whitespace-pre-line text-amber-800 dark:text-amber-200">${prospect}</div>
                `;
                historicalProspectsList.appendChild(prospectElement);
            });
        } else {
            historicalProspectsList.innerHTML = `
                <div class="text-amber-600 dark:text-amber-400 text-center py-4">
                    No prospects found in historical documents.
                </div>
            `;
        }

        // Display summary
        if (data.analysis_summary) {
            historicalSummary.innerHTML = `
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                    <div>
                        <div class="font-semibold text-amber-800 dark:text-amber-200">${data.total_prospects_found}</div>
                        <div class="text-xs">Total Prospects</div>
                    </div>
                    <div>
                        <div class="font-semibold text-amber-800 dark:text-amber-200">${data.documents_analyzed}</div>
                        <div class="text-xs">Documents Analyzed</div>
                    </div>
                    <div>
                        <div class="font-semibold text-amber-800 dark:text-amber-200">${data.analysis_summary.confidence_range}</div>
                        <div class="text-xs">Confidence Range</div>
                    </div>
                    <div>
                        <div class="font-semibold text-amber-800 dark:text-amber-200">${data.analysis_summary.average_confidence}</div>
                        <div class="text-xs">Avg Confidence</div>
                    </div>
                </div>
            `;
        }

        // Show results
        historicalResults.classList.remove('hidden');
    }

    function showHistoricalError(message) {
        historicalProspectsList.innerHTML = `
            <div class="text-red-600 dark:text-red-400 text-center py-4">
                <svg class="w-8 h-8 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                ${message}
            </div>
        `;
        historicalSummary.innerHTML = '';
        historicalResults.classList.remove('hidden');
    }

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
});
