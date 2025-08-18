// Gold Price Tracker Widget
document.addEventListener('DOMContentLoaded', function() {
    // Check if at least one of the gold price elements exists on the page
    const hasGoldWidget = document.getElementById('gold-price-widget') !== null;
    const hasSmallGoldWidget = document.getElementById('gold-price-widget-small') !== null;
    
    if (!hasGoldWidget && !hasSmallGoldWidget) {
        console.log('No gold price widgets found on this page, skipping initialization');
        return;
    }
    
    console.log('Initializing gold price tracker');
    
    // Initialize the gold price tracker
    initGoldPriceTracker();
    
    // Set up the refresh button event if it exists
    const refreshButton = document.getElementById('refresh-gold-price');
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            fetchGoldPrices();
            // Add rotation animation to refresh icon
            const refreshIcon = document.querySelector('#refresh-gold-price svg');
            if (refreshIcon) {
                refreshIcon.classList.add('animate-spin');
                setTimeout(() => {
                    refreshIcon.classList.remove('animate-spin');
                }, 1000);
            }
        });
    }
    
    // Store the price in sessionStorage so it's available across pages
    // Check if we already have a recent price in sessionStorage
    const storedPriceData = sessionStorage.getItem('goldPriceData');
    const storedTimestamp = sessionStorage.getItem('goldPriceTimestamp');
    
    if (storedPriceData && storedTimestamp) {
        const now = new Date().getTime();
        const timestamp = parseInt(storedTimestamp);
        const fiveMinutes = 5 * 60 * 1000;
        
        // If the stored price is less than 5 minutes old, use it
        if (now - timestamp < fiveMinutes) {
            console.log('Using stored gold price from sessionStorage');
            const priceData = JSON.parse(storedPriceData);
            updateWidgetUI(priceData);
            
            // Update last updated text if element exists
            const lastUpdatedElement = document.getElementById('gold-price-last-updated');
            if (lastUpdatedElement) {
                const updateTime = new Date(timestamp).toLocaleTimeString();
                lastUpdatedElement.textContent = `Last updated: ${updateTime}${priceData.isApiData ? '' : ' (simulated data)'}`;
            }
        } else {
            // Data is stale, fetch new data
            fetchGoldPrices();
        }
    } else {
        // No stored data, fetch new data
        fetchGoldPrices();
    }
    
    // Auto refresh every 5 minutes (300000 ms)
    setInterval(fetchGoldPrices, 300000);
});

// Initialize the gold price tracker widget
function initGoldPriceTracker() {
    // Create the initial widget with loading state
    updateWidgetUI({
        price: null,
        currency: 'USD',
        change: null,
        changePercent: null,
        loading: true
    });
}

// Fetch gold prices from API
async function fetchGoldPrices() {
    console.log('Fetching gold prices...');
    
    try {
        // Show loading state
        updateWidgetUI({
            price: null,
            currency: 'USD',
            change: null,
            changePercent: null,
            loading: true
        });
        
        // Try to fetch from our backend API endpoint
        let price = null;
        let isApiData = false;
        
        try {
            // Use our backend API endpoint which securely handles the external API call
            const response = await fetch('/api/gold-price/', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log('Backend gold price API response:', data);
                
                if (data.success && data.price !== null) {
                    price = data.price;
                    isApiData = data.isApiData;
                    console.log('Gold price from backend API:', price);
                } else {
                    throw new Error(data.error || 'Invalid response from backend API');
                }
            } else {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(`Backend API failed: ${response.status} - ${errorData.error || 'Unknown error'}`);
            }
        } catch (apiError) {
            console.warn('Backend gold price API failed:', apiError);
            // Continue to fallback
        }
        
        // If API failed, use simulated price
        if (price === null) {
            price = getSimulatedGoldPrice();
            console.log('Using simulated gold price (in grams):', price);
        }
        
        // Calculate change data
        let previousPrice = localStorage.getItem('previousGoldPrice');
        
        // If there's no previous price in localStorage, just use current price
        if (!previousPrice) {
            previousPrice = price;
            localStorage.setItem('previousGoldPrice', price);
        } else {
            previousPrice = parseFloat(previousPrice);
        }
        
        const change = price - previousPrice;
        const changePercent = (change / previousPrice) * 100;
        
        // Save current price for next comparison
        localStorage.setItem('previousGoldPrice', price);
        
        // Create data object
        const priceData = {
            price: price,
            currency: 'USD',
            change: change,
            changePercent: changePercent,
            loading: false,
            isApiData: isApiData
        };
        
        // Store in sessionStorage for use across pages
        sessionStorage.setItem('goldPriceData', JSON.stringify(priceData));
        sessionStorage.setItem('goldPriceTimestamp', new Date().getTime().toString());
        
        // Update the widget with the fetched data
        updateWidgetUI(priceData);
        
        // Also store the last updated time
        const now = new Date();
        const lastUpdatedElement = document.getElementById('gold-price-last-updated');
        if (lastUpdatedElement) {
            lastUpdatedElement.textContent = `Last updated: ${now.toLocaleTimeString()}${isApiData ? '' : ' (simulated data)'}`;
        }
        
        console.log('Gold price widget updated successfully');
        
    } catch (error) {
        console.error('Error updating gold price widget:', error);
        
        // Use fallback price
        const fallbackPrice = getSimulatedGoldPriceInGrams();
        console.log('Using fallback gold price after error:', fallbackPrice);
        
        // Get previous price from localStorage or use fallback
        const previousPrice = parseFloat(localStorage.getItem('previousGoldPrice') || fallbackPrice);
        const change = fallbackPrice - previousPrice;
        const changePercent = (change / previousPrice) * 100;
        
        // Save fallback price for next comparison
        localStorage.setItem('previousGoldPrice', fallbackPrice);
        
        // Create fallback data object
        const fallbackData = {
            price: fallbackPrice,
            currency: 'USD',
            change: change,
            changePercent: changePercent,
            loading: false,
            isApiData: false
        };
        
        // Store in sessionStorage for use across pages
        sessionStorage.setItem('goldPriceData', JSON.stringify(fallbackData));
        sessionStorage.setItem('goldPriceTimestamp', new Date().getTime().toString());
        
        // Update the widget with the fallback data
        updateWidgetUI(fallbackData);
        
        // Also store the last updated time
        const now = new Date();
        const lastUpdatedElement = document.getElementById('gold-price-last-updated');
        if (lastUpdatedElement) {
            lastUpdatedElement.textContent = `Last updated: ${now.toLocaleTimeString()} (estimated)`;
        }
    }
}

// Get a realistic simulated gold price based on actual recent market prices (in grams)
function getSimulatedGoldPrice() {
    return getSimulatedGoldPriceInGrams();
}

// Get a realistic simulated gold price in grams
function getSimulatedGoldPriceInGrams() {
    // Current realistic base price (as of May 2024) - per gram
    // Gold is around $2337.40 per troy ounce, which is around $75.15 per gram
    const basePrice = 75.15;
    
    // Add some variation to simulate market movement
    // Use a combination of:
    // - Day of month for consistent daily change
    // - Current hour for intraday changes
    // - Current minute to add small fluctuations
    const today = new Date();
    const day = today.getDate();
    const hour = today.getHours();
    const minute = today.getMinutes();
    
    // Day-to-day variation (±1.5%)
    const dailyFactor = 1 + ((day % 30) - 15) / 1000;
    
    // Hour-to-hour variation (±0.5%)
    const hourFactor = 1 + ((hour % 24) - 12) / 2400;
    
    // Minute-to-minute variation (±0.1%)
    const minuteFactor = 1 + ((minute % 60) - 30) / 30000;
    
    // Calculate final price with all factors
    const simulatedPrice = basePrice * dailyFactor * hourFactor * minuteFactor;
    
    // Round to 2 decimal places
    return Math.round(simulatedPrice * 100) / 100;
}

// Fallback function in case of complete failure
function getFallbackGoldPrice() {
    // Just use the simulated price as fallback
    return getSimulatedGoldPriceInGrams();
}

// Update the widget UI based on the gold price data
function updateWidgetUI(data) {
    console.log('Updating widget UI with data:', data);
    
    const priceElement = document.getElementById('gold-price-value');
    const changeElement = document.getElementById('gold-price-change');
    const widgetElement = document.getElementById('gold-price-widget');
    const smallPriceElement = document.getElementById('gold-price-value-small');
    const dataSourceElement = document.getElementById('data-source-indicator');
    
    // Update the main widget if it exists
    if (priceElement) {
        if (data.loading) {
            // Show loading state
            priceElement.innerHTML = '<div class="animate-pulse">Loading...</div>';
        } else if (data.error) {
            // Show error state
            priceElement.innerHTML = 'Failed to load';
        } else {
            // Format price with 2 decimal places
            const formattedPrice = data.price.toFixed(2);
            priceElement.textContent = `$${formattedPrice}`;
        }
    }
    
    // Update change element if it exists
    if (changeElement) {
        if (data.loading) {
            changeElement.innerHTML = '';
        } else if (data.error) {
            changeElement.innerHTML = '<span class="text-red-500">Try again later</span>';
        } else {
            // Format change amount and percent
            const isPositive = data.change >= 0;
            const changeSymbol = isPositive ? '+' : '';
            const changeClass = isPositive ? 'text-green-500' : 'text-red-500';
            
            changeElement.innerHTML = `
                <span class="${changeClass}">
                    ${changeSymbol}$${Math.abs(data.change).toFixed(2)} (${changeSymbol}${Math.abs(data.changePercent).toFixed(2)}%)
                    ${isPositive ? '▲' : '▼'}
                </span>
            `;
        }
    }
    
    // Update small widget in navbar if it exists
    if (smallPriceElement) {
        if (data.loading) {
            smallPriceElement.innerHTML = '<div class="animate-pulse">...</div>';
        } else if (data.error) {
            smallPriceElement.textContent = 'Error';
        } else {
            // Format price with 2 decimal places
            const formattedPrice = data.price.toFixed(2);
            smallPriceElement.textContent = `$${formattedPrice}/g`;
        }
        
        // Add background effect for price changes in small widget
        if (!data.loading && !data.error && data.change !== 0) {
            const smallWidget = document.getElementById('gold-price-widget-small');
            if (smallWidget) {
                const isPositive = data.change >= 0;
                smallWidget.classList.add(isPositive ? 'price-up' : 'price-down');
                setTimeout(() => {
                    smallWidget.classList.remove('price-up', 'price-down');
                }, 1000);
            }
        }
    }
    
    // Update data source indicator if it exists
    if (dataSourceElement && !data.loading && !data.error) {
        dataSourceElement.textContent = data.isApiData ? 
            'Using real-time market data' : 
            'Using simulated data based on recent market prices';
        
        dataSourceElement.className = data.isApiData ? 
            'text-xs text-green-600 dark:text-green-400 mt-1 font-medium' : 
            'text-xs text-amber-600 dark:text-amber-400 mt-1 font-medium';
    }
    
    // Add background pulse animation if price changed and widget exists
    if (widgetElement && !data.loading && !data.error && data.change !== 0) {
        const isPositive = data.change >= 0;
        const bgClass = isPositive ? 'bg-green-100' : 'bg-red-100';
        widgetElement.classList.add(bgClass);
        setTimeout(() => {
            widgetElement.classList.remove(bgClass);
        }, 1000);
    }
} 