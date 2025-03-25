document.addEventListener('DOMContentLoaded', () => {
    // Debug log to verify the script is running
    console.log('Script loaded');

    document.querySelectorAll('.endpoint-item').forEach(item => {
        // Debug log to verify we found endpoint items
        console.log('Found endpoint item:', item.dataset);

        item.addEventListener('click', () => {
            // Get the data attributes
            const method = item.dataset.method;
            const server = item.dataset.server || '';  // Default to empty string if undefined
            const path = item.dataset.path;

            console.log('Clicked endpoint:', { method, server, path });

            // Update the method dropdown
            const methodSelect = document.getElementById('method');
            if (methodSelect) {
                methodSelect.value = method;
            }

            // Construct the full URL
            let fullUrl;
            try {
                // Handle cases where server might be a relative path
                if (server.startsWith('/')) {
                    // For relative paths, you might want to add your default domain
                    fullUrl = `https://your-domain.com${server}${path}`;
                } else if (!server.startsWith('http')) {
                    // If no protocol specified, assume https
                    fullUrl = `https://${server}${path}`;
                } else {
                    // Server includes protocol
                    fullUrl = `${server}${path}`;
                }

                console.log('Constructed URL:', fullUrl);

                // Update the URL input
                const urlInput = document.getElementById('url');
                if (urlInput) {
                    urlInput.value = fullUrl;
                }
            } catch (error) {
                console.error('Error constructing URL:', error);
            }
        });
    });
});

async function sendRequest() {
    // Get the current values
    const method = document.getElementById('method').value;
    const url = document.getElementById('url').value;
    let headers = {};
    let body = null;

    console.log('Sending request:', { method, url });

    // Validate URL
    if (!url) {
        document.getElementById('response').textContent = 'Error: No URL provided';
        return;
    }

    // Parse headers
    try {
        const headersText = document.getElementById('headers').value;
        if (headersText.trim()) {
            headers = JSON.parse(headersText);
        }
    } catch (error) {
        document.getElementById('response').textContent = `Error parsing headers: ${error.message}`;
        return;
    }

    // Parse body
    try {
        const bodyText = document.getElementById('body').value;
        if (bodyText.trim()) {
            body = bodyText;
        }
    } catch (error) {
        document.getElementById('response').textContent = `Error parsing body: ${error.message}`;
        return;
    }

    // Show loading state
    document.getElementById('response').textContent = 'Loading...';

    try {
        const response = await fetch('/test_endpoint', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                method,
                url,
                headers,
                body
            })
        });

        const data = await response.json();

        // Format the response nicely
        let formattedResponse = '';
        if (data.status === 'success') {
            formattedResponse = `Status Code: ${data.response.status_code}\n\n`;
            formattedResponse += 'Headers:\n';
            formattedResponse += JSON.stringify(data.response.headers, null, 2);
            formattedResponse += '\n\nBody:\n';
            formattedResponse += JSON.stringify(data.response.body, null, 2);
        } else {
            formattedResponse = `Error: ${JSON.stringify(data.error, null, 2)}`;
        }

        document.getElementById('response').textContent = formattedResponse;
    } catch (error) {
        document.getElementById('response').textContent = `Error: ${error.message}`;
    }
}