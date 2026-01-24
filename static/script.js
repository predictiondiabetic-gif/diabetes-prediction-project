// Handle form submission
document.getElementById('predictionForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const loading = document.getElementById('loading');
    const resultContainer = document.getElementById('resultContainer');
    const predictBtn = document.getElementById('predictBtn');
    
    // Show loading
    loading.style.display = 'flex';
    predictBtn.disabled = true;
    resultContainer.style.display = 'none';
    
    // Get form data
    const formData = {
        hba1c: parseFloat(document.getElementById('hba1c').value),
        diagnosed_diabetes: parseInt(document.getElementById('diagnosed_diabetes').value),
        glucose_fasting: parseFloat(document.getElementById('glucose_fasting').value),
        glucose_postprandial: parseFloat(document.getElementById('glucose_postprandial').value),
        family_history_diabetes: parseInt(document.getElementById('family_history_diabetes').value),
        diabetes_risk_score: parseFloat(document.getElementById('diabetes_risk_score').value),
        hypertension_history: parseInt(document.getElementById('hypertension_history').value)
    };
    
    try {
        // Make prediction request
        const response = await fetch('/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            displayResult(data);
        } else {
            alert('Error: ' + (data.error || 'Unknown error occurred'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error making prediction: ' + error.message);
    } finally {
        loading.style.display = 'none';
        predictBtn.disabled = false;
    }
});

// Display prediction result
function displayResult(data) {
    const resultContainer = document.getElementById('resultContainer');
    const predictionBadge = document.getElementById('predictionBadge');
    const predictionText = document.getElementById('predictionText');
    const probabilitiesDiv = document.getElementById('probabilities');
    
    // Set prediction badge
    const prediction = data.prediction;
    predictionBadge.textContent = prediction;
    predictionBadge.className = 'prediction-badge';
    
    if (prediction === 'Type 2') {
        predictionBadge.classList.add('type2');
    } else if (prediction === 'Pre-Diabetes') {
        predictionBadge.classList.add('pre');
    } else {
        predictionBadge.classList.add('no');
    }
    
    predictionText.textContent = `Predicted Stage: ${prediction}`;
    
    // Display probabilities
    probabilitiesDiv.innerHTML = '';
    const sortedProbs = Object.entries(data.probabilities)
        .sort((a, b) => b[1] - a[1]);
    
    sortedProbs.forEach(([label, prob]) => {
        const probItem = document.createElement('div');
        probItem.className = 'prob-item';
        
        const probLabel = document.createElement('span');
        probLabel.className = 'prob-label';
        probLabel.textContent = label;
        
        const probBarContainer = document.createElement('div');
        probBarContainer.className = 'prob-bar-container';
        
        const probBar = document.createElement('div');
        probBar.className = 'prob-bar';
        probBar.style.width = (prob * 100) + '%';
        probBar.textContent = (prob * 100).toFixed(1) + '%';
        
        probBarContainer.appendChild(probBar);
        
        const probValue = document.createElement('span');
        probValue.className = 'prob-value';
        probValue.textContent = (prob * 100).toFixed(2) + '%';
        
        probItem.appendChild(probLabel);
        probItem.appendChild(probBarContainer);
        probItem.appendChild(probValue);
        
        probabilitiesDiv.appendChild(probItem);
    });
    
    resultContainer.style.display = 'block';
    
    // Scroll to result
    resultContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Handle Analyze Dashboard button
document.getElementById('analyzeBtn').addEventListener('click', () => {
    // Redirect to Tableau dashboard
    window.location.href = '/dashboard';
});

