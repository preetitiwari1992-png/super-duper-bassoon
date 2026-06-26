document.addEventListener('DOMContentLoaded', () => {
    const locationSelect = document.getElementById('location');
    const cuisineSelect = document.getElementById('cuisine');
    const ratingSlider = document.getElementById('min_rating');
    const ratingVal = document.getElementById('rating_val');
    const form = document.getElementById('preferences-form');
    const submitBtn = document.getElementById('submit-btn');
    
    const loadingContainer = document.getElementById('loading-container');
    const resultsContainer = document.getElementById('results-container');
    const aiInsightsContainer = document.getElementById('ai-insights-container');
    const aiSummaryText = document.getElementById('ai-summary');
    const errorContainer = document.getElementById('error-container');
    const errorMessage = document.getElementById('error-message');

    // Update rating value on slider change
    ratingSlider.addEventListener('input', (e) => {
        ratingVal.textContent = e.target.value + '+';
    });

    // Fetch initial data
    async function loadInitialData() {
        try {
            const [locRes, cuisineRes] = await Promise.all([
                fetch('http://127.0.0.1:8000/api/v1/locations'),
                fetch('http://127.0.0.1:8000/api/v1/cuisines')
            ]);
            
            const locations = await locRes.json();
            const cuisines = await cuisineRes.json();
            
            locationSelect.innerHTML = '<option value="">Select a location...</option>' + 
                locations.map(loc => `<option value="${loc}">${loc}</option>`).join('');
                
            cuisineSelect.innerHTML = '<option value="">Any Cuisine</option>' + 
                cuisines.map(c => `<option value="${c}">${c}</option>`).join('');
                
        } catch (err) {
            console.error("Error loading initial data", err);
            // Fallback for demonstration if backend not running
            const locations = ["Delhi NCR", "Bangalore", "Mumbai", "Pune", "Hyderabad"];
            const cuisines = ["Italian Fine Dining", "Contemporary Chinese", "Modern North Indian", "Japanese Omakase", "Continental"];
            
            locationSelect.innerHTML = '<option value="">Select a location...</option>' + 
                locations.map(loc => `<option value="${loc}">${loc}</option>`).join('');
                
            cuisineSelect.innerHTML = '<option value="">Any Cuisine</option>' + 
                cuisines.map(c => `<option value="${c}">${c}</option>`).join('');
        }
    }

    // Handle form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Gather data
        const location = locationSelect.value;
        if (!location) return alert("Please select a location.");
        
        const cuisine = cuisineSelect.value;
        const budget = document.querySelector('input[name="budget"]:checked').value;
        const min_rating = parseFloat(ratingSlider.value);
        const additional_prefs = document.getElementById('additional_prefs').value;
        
        const payload = {
            location,
            budget,
            cuisine: cuisine || undefined,
            min_rating,
            additional_prefs: additional_prefs || undefined
        };

        // UI State: Loading
        submitBtn.disabled = true;
        submitBtn.classList.add('opacity-70');
        loadingContainer.classList.remove('hidden');
        errorContainer.classList.add('hidden');
        aiInsightsContainer.classList.add('hidden');
        resultsContainer.innerHTML = ''; // clear old results

        try {
            let data;
            try {
                const res = await fetch('http://127.0.0.1:8000/api/v1/recommend', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                data = await res.json();
                if (!res.ok) throw new Error(data.detail || 'Failed to fetch recommendations');
            } catch (networkError) {
                console.warn("Backend unavailable, using mock data for demonstration.");
                // Fallback mock data if backend is not running
                data = {
                    ai_summary: `Based on your preferences for ${cuisine || 'premium'} dining in ${location} with a minimum rating of ${min_rating}. I have optimized for venues known for exceptional ambiance and quality.`,
                    recommendations: [
                        {
                            name: "Le Cirque Signature",
                            rating: 4.9,
                            cuisines: "Italian, Fine Dining",
                            cost_for_two: "8,000",
                            location: "Chanakyapuri, " + location,
                            ai_explanation: "Matches perfectly with your request. The atmosphere is unparalleled for quiet, luxury dining.",
                            url: "#"
                        },
                        {
                            name: "Sorrento",
                            rating: 4.7,
                            cuisines: "Neapolitan, Premium",
                            cost_for_two: "5,500",
                            location: "Connaught Place, " + location,
                            ai_explanation: "Renowned for their artisanal pastas and extensive wine cellar.",
                            url: "#"
                        }
                    ]
                };
            }
            
            // Render AI Summary
            aiSummaryText.textContent = data.ai_summary || "Here are some top picks based on your preferences.";
            aiInsightsContainer.classList.remove('hidden');
            
            // Render Cards
            if (!data.recommendations || data.recommendations.length === 0) {
                resultsContainer.innerHTML = '<div class="text-center text-on-surface-variant py-20 text-lg">No restaurants found matching your exact criteria.</div>';
            } else {
                data.recommendations.forEach((rec, index) => {
                    const rank = index + 1;
                    const cardHTML = `
                        <article class="glass-card rounded-2xl overflow-hidden flex flex-col animate-fade-up group" style="animation-delay: ${index * 0.1}s">
                            <div class="p-8 flex flex-col justify-between flex-1 relative">
                                <div>
                                    <div class="flex justify-between items-start mb-2">
                                        <div class="flex items-center gap-3">
                                            <span class="bg-primary/20 text-primary font-bold px-3 py-1 rounded-full text-sm">#${rank}</span>
                                            <h4 class="font-headline-md text-2xl font-bold text-on-surface">${rec.restaurant_name || rec.name}</h4>
                                        </div>
                                        <div class="flex items-center gap-1 bg-surface-container/50 px-3 py-1.5 rounded-md border border-white/5">
                                            <span class="material-symbols-outlined text-primary text-sm" style="font-variation-settings: 'FILL' 1;">star</span>
                                            <span class="font-label-md text-on-surface">${(rec.rating || 0).toFixed(1)}</span>
                                        </div>
                                    </div>
                                    <div class="flex flex-wrap gap-2 mb-6 mt-2">
                                        <span class="text-xs font-label-md text-on-surface-variant bg-white/5 border border-white/10 px-2.5 py-1 rounded-md">${rec.cuisine || rec.cuisines || "Various"}</span>
                                        <span class="text-xs font-label-md text-on-surface-variant bg-white/5 border border-white/10 px-2.5 py-1 rounded-md">₹${rec.estimated_cost || rec.cost_for_two || "?"} for two</span>
                                        <span class="text-xs font-label-md text-on-surface-variant bg-white/5 border border-white/10 px-2.5 py-1 rounded-md flex items-center gap-1"><span class="material-symbols-outlined text-[14px]">location_on</span> ${rec.location || location}</span>
                                    </div>
                                    <!-- Why this pick -->
                                    <div class="bg-surface-container-low/40 border border-primary/20 rounded-lg p-4 mb-6">
                                        <div class="flex items-center gap-2 mb-2">
                                            <span class="material-symbols-outlined text-primary text-sm">auto_awesome</span>
                                            <span class="font-label-md text-primary font-bold">Why this pick</span>
                                        </div>
                                        <p class="font-body-md text-on-surface-variant text-sm">${rec.explanation || rec.ai_explanation || "Matched based on your criteria."}</p>
                                    </div>
                                </div>
                                <div class="flex gap-4">
                                    <a href="${rec.url || '#'}" target="_blank" class="flex-1 bg-white/10 hover:bg-white/15 border border-white/20 text-on-surface font-label-md font-bold py-3 rounded-lg transition-colors text-center inline-block">View on Zomato</a>
                                </div>
                            </div>
                        </article>
                    `;
                    resultsContainer.innerHTML += cardHTML;
                });
            }

        } catch (err) {
            console.error(err);
            errorMessage.textContent = err.message || "An unexpected error occurred.";
            errorContainer.classList.remove('hidden');
        } finally {
            submitBtn.disabled = false;
            submitBtn.classList.remove('opacity-70');
            loadingContainer.classList.add('hidden');
        }
    });

    // Initialize
    loadInitialData();
});
