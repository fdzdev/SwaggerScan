let endpointAnalysis = null;
let isTestingInProgress = false;
let shouldStopTests = false;

document.addEventListener('DOMContentLoaded', async () => {
    const docSelector = document.getElementById('docSelector');

    if (docSelector && docSelector.value) {
        await fetchEndpointsForDocumentation(docSelector.value);
    }
});

async function fetchEndpointsForDocumentation(docId) {
    console.log('Fetching endpoints for documentation:', docId);
    try {
        const response = await fetch(`/api/analyze_endpoints/${docId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        endpointAnalysis = data;
        updateCountsForDocumentation(docId);
    } catch (error) {
        console.error('Error fetching endpoints:', error);
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    console.log('Loading endpoints...');
    try {
        const response = await fetch('/api/analyze_endpoints');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        endpointAnalysis = data;

        // Initialize results container with 0 counts
        initializeResultsContainer();

        // Create parameter inputs
        const uniqueParams = new Set();
        data.endpoints.forEach(endpoint => {
            try {
                // Add path parameters
                if (endpoint.path_params) {
                    const pathParams = Array.isArray(endpoint.path_params)
                        ? endpoint.path_params
                        : (typeof endpoint.path_params === 'string'
                            ? JSON.parse(endpoint.path_params)
                            : []);
                    pathParams.forEach(param => uniqueParams.add(param.name));
                }
                // Add query parameters
                if (endpoint.query_params) {
                    const queryParams = Array.isArray(endpoint.query_params)
                        ? endpoint.query_params
                        : (typeof endpoint.query_params === 'string'
                            ? JSON.parse(endpoint.query_params)
                            : []);
                    queryParams.forEach(param => uniqueParams.add(param.name));
                }
            } catch (e) {
                console.error('Error processing parameters for endpoint:', endpoint, e);
            }
        });


        // Create parameter input fields
        const parameterInputs = document.getElementById('parameter-inputs');
        parameterInputs.innerHTML = ''; // Clear existing inputs
        uniqueParams.forEach(param => {
            const div = document.createElement('div');
            div.className = 'parameter-input';
            div.innerHTML = `
              <label for="${param}">{${param}}:</label>
              <input type="text" id="${param}" placeholder="Value for ${param}">
          `;
            parameterInputs.appendChild(div);
        });

        // Get the documentation selector
        const docSelector = document.getElementById('docSelector');
        if (docSelector) {
            docSelector.addEventListener('change', async function () {
                const selectedDocId = this.value;
                console.log('Documentation selected:', selectedDocId);
                if (selectedDocId) {
                    await fetchEndpointsForDocumentation(selectedDocId);
                }
            });

            // If there's already a selected documentation, update counts
            if (docSelector.value) {
                console.log('Initial documentation:', docSelector.value);
                updateCountsForDocumentation(docSelector.value);
            }
        }

    } catch (error) {
        console.error('Error during initialization:', error);
    }
});


function initializeResultsContainer() {
    const details = document.getElementById('results-details');
    details.innerHTML = `
        <div class="results-summary">
            <div class="summary-grid">
                <button class="filter-btn all active" onclick="filterResults('all')">
                    <div class="count-value" id="total-count">0</div>
                    <div class="count-label">Total Tests</div>
                </button>
                <button class="filter-btn completed" onclick="filterResults('completed')">
                    <div class="count-value" id="completed-count">0</div>
                    <div class="count-label">Completed</div>
                </button>
                <button class="filter-btn successful" onclick="filterResults('successful')">
                    <div class="count-value" id="success-count">0</div>
                    <div class="count-label">Successful</div>
                </button>
                <button class="filter-btn failed" onclick="filterResults('failed')">
                    <div class="count-value" id="failed-count">0</div>
                    <div class="count-label">Failed</div>
                </button>
                <button class="filter-btn attention" onclick="filterResults('attention')">
                    <div class="count-value" id="attention-count">0</div>
                    <div class="count-label">Needs Attention</div>
                </button>
            </div>
        </div>
        <div class="results-list"></div>
    `;
}

// Add this function to update the progress bar
function updateProgress(completed, total) {
    const progressPercent = (completed / total) * 100;
    const progressBar = document.getElementById('progress-indicator');
    if (progressBar) {
        progressBar.style.width = `${progressPercent}%`;
    }
}

// Make filterResults available globally
window.filterResults = function (filter) {
    // Update active button state
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`.filter-btn.${filter}`).classList.add('active');

    // Filter results
    const results = document.querySelectorAll('.endpoint-result');
    results.forEach(result => {
        const status = result.querySelector('.status');
        switch (filter) {
            case 'all':
                result.style.display = 'block';
                break;
            case 'completed':
                result.style.display = status.textContent !== 'Testing...' ? 'block' : 'none';
                break;
            case 'successful':
                result.style.display = status.classList.contains('success') ? 'block' : 'none';
                break;
            case 'failed':
                result.style.display = status.classList.contains('failed') ? 'block' : 'none';
                break;
            case 'attention':
                result.style.display = result.classList.contains('needs-attention') ? 'block' : 'none';
                break;
        }
    });
};

// Update counts when switching documentations
function updateCountsForDocumentation(docId) {
    if (!endpointAnalysis || !docId) {
        console.log('No endpoints or docId available');
        return;
    }
    // Filter endpoints for current documentation
    const currentEndpoints = endpointAnalysis.endpoints.filter(
        endpoint => endpoint.documentation_id === parseInt(docId)
    );

    // Update total count
    document.getElementById('total-count').textContent = currentEndpoints.length;

    // Reset other counts
    document.getElementById('completed-count').textContent = '0';
    document.getElementById('success-count').textContent = '0';
    document.getElementById('failed-count').textContent = '0';
    document.getElementById('attention-count').textContent = '0';
    document.querySelector('.results-list').innerHTML = '';

    // Clear results list
    document.querySelector('.results-list').innerHTML = '';

}

// Update counts during test execution
function updateCounters(counts) {
    document.getElementById('total-count').textContent = counts.total;
    document.getElementById('completed-count').textContent = counts.completed;
    document.getElementById('success-count').textContent = counts.successful;
    document.getElementById('failed-count').textContent = counts.failed;
    document.getElementById('attention-count').textContent = counts.needsAttention;
}

// Make stopTests available globally
window.stopTests = function () {
    shouldStopTests = true;
    document.getElementById('stop-btn').disabled = true;
    console.log('Tests stopped by user');
};

async function runMassiveTest() {
    if (isTestingInProgress) return;

    isTestingInProgress = true;
    shouldStopTests = false;

    // Get the current documentation ID
    const docSelector = document.getElementById('docSelector');
    const selectedDocId = docSelector?.value;

    if (!selectedDocId) {
        console.error('No documentation selected');
        alert('Please select a documentation first');
        return;
    }
    console.log('Starting tests for documentation:', selectedDocId);
    isTestingInProgress = true;
    shouldStopTests = false;

    // Update button states
    const stopBtn = document.getElementById('stop-btn');
    stopBtn.disabled = false;

    try {
        const testConfig = {
            headers: JSON.parse(document.getElementById('headers-config').value || '{}'),
            body: JSON.parse(document.getElementById('body-config').value || '{}')

        };
        const currentEndpoints = endpointAnalysis.endpoints.filter(
            endpoint => endpoint.documentation_id === parseInt(selectedDocId)
        );
        console.log(`Testing ${currentEndpoints.length} endpoints for documentation ${selectedDocId}`);


        // Add parameter values to config
        const paramInputs = document.querySelectorAll('.parameter-input input');
        paramInputs.forEach(input => {
            testConfig[input.id] = input.value || `test_${input.id}`;
        });

        // Reset counters
        let counts = {
            total: endpointAnalysis.endpoints.length,
            completed: 0,
            successful: 0,
            failed: 0,
            needsAttention: 0
        };
        updateCounters(counts);
        updateProgress(0, counts.total)

        // Clear previous results
        const resultsList = document.querySelector('.results-list');
        resultsList.innerHTML = '';

        // Test each endpoint
        for (const endpoint of endpointAnalysis.endpoints) {
            if (shouldStopTests) {
                console.log('Testing stopped by user');
                break;
            }

            // Create result container for this endpoint
            const resultDiv = document.createElement('div');
            resultDiv.className = 'endpoint-result';

            // Construct the full path for display
            const displayPath = `${endpoint.base_path || ''}${endpoint.path}`;

            resultDiv.innerHTML = `
                <div class="endpoint-header">
                    <span class="method ${endpoint.method.toLowerCase()}">${endpoint.method}</span>
                    <span class="path">${displayPath}</span>
                    <span class="status">Testing...</span>
                </div>
                <div class="endpoint-details" style="display: none;"></div>
            `;
            resultsList.appendChild(resultDiv);

            try {
                const response = await fetch('/api/run_massive_test', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        endpoints: [endpoint],
                        testConfig: testConfig
                    })
                });

                const result = await response.json();
                // const testResult = result.results[0];
                console.log('Test result:', result);

                // Get the first result from the results array
                const testResult = result.results[0];

                // Update UI with result
                updateEndpointResult(resultDiv, testResult);

                // Update counters
                counts.completed++;
                if (testResult.success) counts.successful++;
                else counts.failed++;
                if (testResult.needs_attention) counts.needsAttention++;
                updateCounters(counts);
                updateProgress(counts.completed, counts.total);  // Fixed: using counts.total

            } catch (error) {
                console.error('Error testing endpoint:', error);
                updateEndpointResult(resultDiv, {
                    success: false,
                    error: error.message,
                    needs_attention: true
                });

                // Update counters
                counts.completed++;
                counts.failed++;
                counts.needsAttention++;
                updateCounters(counts);
                updateProgress(counts.completed, counts.total);  // Fixed: using counts.total

            }
        }
    } catch (error) {
        console.error('Error running tests:', error);
    } finally {
        isTestingInProgress = false;
        stopBtn.disabled = true;
    }
}

// Make runMassiveTest available globally
window.runMassiveTest = runMassiveTest;
window.updateProgress = updateProgress;

function updateEndpointResult(resultDiv, result) {
    const header = resultDiv.querySelector('.endpoint-header');
    const status = header.querySelector('.status');
    const details = resultDiv.querySelector('.endpoint-details');

    // Update status
    status.textContent = result.success ? 'Success' : 'Failed';
    status.className = `status ${result.success ? 'success' : 'failed'}`;

    // Add needs-attention class to the main div if needed
    if (result.needs_attention) {
        resultDiv.classList.add('needs-attention');
        status.textContent += ' ⚠️';
    }

    // Update details
    details.innerHTML = `
        <div class="details-grid">
            <div class="detail-item">
                <span class="detail-label">Full URL:</span>
                <span class="detail-value url">${result.test_url}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Response Time:</span>
                <span class="detail-value">${result.response_time || 'N/A'}ms</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Status Code:</span>
                <span class="detail-value status-code ${result.needs_attention ? 'attention' : ''}">${result.status_code || 'N/A'}</span>
            </div>
        </div>
        ${result.error ? `
            <div class="error-container">
                <span class="detail-label">Error:</span>
                <span class="error">${result.error}</span>
            </div>
        ` : ''}
        <div class="response-container">
            <span class="detail-label">Response:</span>
            <pre class="response">${JSON.stringify(result.response || {}, null, 2)}</pre>
        </div>
    `;

    // Show/hide details on header click
    header.onclick = () => {
        details.style.display = details.style.display === 'none' ? 'block' : 'none';
    };
}
window.runMassiveTest = runMassiveTest;

window.fillRandomValues = function () {
    // Fill all parameter inputs with "1"
    document.querySelectorAll('.parameter-input input').forEach(input => {
        input.value = "1";
    });

    // Fill headers and body with basic JSON
    document.getElementById('headers-config').value = JSON.stringify({
        "Content-Type": "application/json"
    }, null, 2);

    document.getElementById('body-config').value = JSON.stringify({
        "test": "1"
    }, null, 2);
};