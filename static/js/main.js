// KidsKlassiks Main JavaScript
console.log('KidsKlassiks JS loaded');

// HTMX Configuration
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, configuring HTMX');
    
    // Configure HTMX
    htmx.config.globalViewTransitions = true;
    htmx.config.timeout = 30000; // 30 second timeout
    
    // Handle HTMX requests
    document.body.addEventListener('htmx:beforeRequest', function(evt) {
        console.log('HTMX request starting:', evt.detail.requestConfig.path);
        showProcessingModal();
    });
    
    document.body.addEventListener('htmx:afterRequest', function(evt) {
        console.log('HTMX request completed:', evt.detail.xhr.status);
        hideProcessingModal();
        
        if (evt.detail.xhr.status !== 200) {
            showError('Request failed. Please try again.');
        }
    });
    
    document.body.addEventListener('htmx:responseError', function(evt) {
        console.error('HTMX error:', evt.detail);
        hideProcessingModal();
        showError('Server error occurred. Please try again.');
    });
    
    document.body.addEventListener('htmx:timeout', function(evt) {
        console.error('HTMX timeout:', evt.detail);
        hideProcessingModal();
        showError('Request timed out. Please try again.');
    });
});

// Processing Modal Functions
function showProcessingModal() {
    const modal = document.getElementById('processing-modal');
    if (modal) {
        modal.style.display = 'flex';
        console.log('Processing modal shown');
    } else {
        // Create modal if it doesn't exist
        const modalHtml = `
            <div id="processing-modal" class="modal" style="display: flex;">
                <div class="modal-content">
                    <div class="spinner"></div>
                    <p>Processing...</p>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        console.log('Processing modal created and shown');
    }
}

function hideProcessingModal() {
    const modal = document.getElementById('processing-modal');
    if (modal) {
        modal.style.display = 'none';
        console.log('Processing modal hidden');
    }
}

function showError(message) {
    hideProcessingModal();
    
    // Remove existing error
    const existingError = document.getElementById('error-alert');
    if (existingError) {
        existingError.remove();
    }
    
    // Show error
    const errorHtml = `
        <div id="error-alert" class="alert error" style="position: fixed; top: 20px; right: 20px; z-index: 10000;">
            ❌ ${message}
            <button onclick="this.parentElement.remove()" style="margin-left: 10px;">×</button>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', errorHtml);
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        const alert = document.getElementById('error-alert');
        if (alert) alert.remove();
    }, 5000);
}

// Navigation Functions
function navigateToLibrary() {
    console.log('Navigating to library');
    htmx.ajax('GET', '/books/library', {target: '#main-content', swap: 'innerHTML'});
}

function navigateToImport() {
    console.log('Navigating to import');
    htmx.ajax('GET', '/books/import', {target: '#main-content', swap: 'innerHTML'});
}

// File Upload Handler
function handleFileUpload(input) {
    const file = input.files[0];
    if (file) {
        console.log('File selected:', file.name);
        const fileInfo = document.getElementById('file-info');
        if (fileInfo) {
            fileInfo.textContent = `Selected: ${file.name}`;
        }
    }
}

// Form Submission
function submitImportForm() {
    const form = document.getElementById('import-form');
    if (form) {
        console.log('Submitting import form');
        showProcessingModal();
        
        const formData = new FormData(form);
        
        fetch('/books/import', {
            method: 'POST',
            body: formData
        })
        .then(response => response.text())
        .then(html => {
            hideProcessingModal();
            document.getElementById('import-result').innerHTML = html;
        })
        .catch(error => {
            console.error('Import error:', error);
            hideProcessingModal();
            showError('Import failed. Please try again.');
        });
    }
}

console.log('KidsKlassiks JS setup complete');