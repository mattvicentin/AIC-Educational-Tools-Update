/**
 * Library Tool - Document Upload and Search Functionality
 * Railway PostgreSQL version with room scoping
 */

// File upload handler
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('library-file-input');
    if (fileInput) {
        fileInput.addEventListener('change', handleFileUpload);
    }
    
    // Allow Enter key to search
    const searchInput = document.getElementById('library-search-input');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchLibraryDocuments();
            }
        });
    }
    
    // Load documents on page load
    refreshLibraryDocuments();
    
    // Load storage stats on page load
    updateStorageIndicator();
});

/**
 * Get room_id from page context
 * Canonical source: data-room-id attribute on container div
 */
function getRoomId() {
    // Try to get from data attribute (canonical source)
    const container = document.querySelector('[data-room-id]');
    if (container) {
        const roomId = container.getAttribute('data-room-id');
        if (roomId) {
            return parseInt(roomId, 10);
        }
    }
    
    // Fallback: Try to get from URL or other sources
    // This should not happen if template is correct
    console.warn('room_id not found in data-room-id attribute');
    return null;
}

/**
 * Update storage indicator with current usage
 */
async function updateStorageIndicator() {
    const roomId = getRoomId();
    if (!roomId) {
        console.error('Cannot update storage: room_id not available');
        return;
    }
    
    try {
        const response = await fetch(`/api/library/storage/stats?room_id=${roomId}`);
        
        if (!response.ok) {
            console.error('Failed to fetch storage stats');
            return;
        }
        
        const stats = await response.json();
        
        // Update percentage
        const percentageEl = document.getElementById('storage-percentage');
        if (percentageEl) {
            percentageEl.textContent = `${Math.round(stats.percentage)}%`;
        }
        
        // Update storage bar width and gradient color
        const storageBar = document.getElementById('storage-bar');
        if (storageBar) {
            storageBar.style.width = `${Math.min(stats.percentage, 100)}%`;
            storageBar.style.background = getStorageGradient(stats.percentage);
        }
        
        // Show/hide warning and disable/enable upload button
        const warningEl = document.getElementById('storage-warning');
        const uploadButton = document.querySelector('button[onclick*="library-file-input"]');
        const fileInput = document.getElementById('library-file-input');
        
        if (stats.percentage >= 100) {
            // Storage full
            if (warningEl) warningEl.classList.remove('hidden');
            if (uploadButton) {
                uploadButton.disabled = true;
                uploadButton.classList.add('opacity-50', 'cursor-not-allowed');
                uploadButton.classList.remove('hover:bg-primary/20');
            }
            if (fileInput) fileInput.disabled = true;
        } else {
            // Storage available
            if (warningEl) warningEl.classList.add('hidden');
            if (uploadButton) {
                uploadButton.disabled = false;
                uploadButton.classList.remove('opacity-50', 'cursor-not-allowed');
                uploadButton.classList.add('hover:bg-primary/20');
            }
            if (fileInput) fileInput.disabled = false;
        }
        
    } catch (error) {
        console.error('Error updating storage indicator:', error);
    }
}

/**
 * Get gradient color based on storage percentage
 * Light Green (0-50%) → Yellow (50-75%) → Orange (75-90%) → Red (90-100%)
 */
function getStorageGradient(percentage) {
    // Define color stops - lighter, more vibrant colors
    const colors = {
        green: '#b4e380',    // Light lime green (like in the image)
        yellow: '#fde047',   // Light yellow
        orange: '#fb923c',   // Light orange
        red: '#f87171'       // Light red
    };
    
    if (percentage <= 50) {
        // 0-50%: Pure light green
        return colors.green;
    } else if (percentage <= 75) {
        // 50-75%: Light green to Yellow
        const position = ((percentage - 50) / 25) * 100;
        return `linear-gradient(to right, ${colors.green}, ${colors.yellow} ${position}%)`;
    } else if (percentage <= 90) {
        // 75-90%: Yellow to Orange
        const position = ((percentage - 75) / 15) * 100;
        return `linear-gradient(to right, ${colors.yellow}, ${colors.orange} ${position}%)`;
    } else {
        // 90-100%: Orange to Red
        const position = ((percentage - 90) / 10) * 100;
        return `linear-gradient(to right, ${colors.orange}, ${colors.red} ${position}%)`;
    }
}

async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const roomId = getRoomId();
    if (!roomId) {
        alert('Error: Room ID not available. Please refresh the page.');
        event.target.value = ''; // Clear file input
        return;
    }
    
    const statusDiv = document.getElementById('library-upload-status');
    const listDiv = document.getElementById('library-documents-list');
    
    // VALIDATION: Check file size against available storage
    const STORAGE_LIMIT_BYTES = 10 * 1024 * 1024; // 10 MB
    const fileSizeBytes = file.size;
    const fileSizeMB = (fileSizeBytes / (1024 * 1024)).toFixed(2);
    
    try {
        // Get current storage usage
        const statsResponse = await fetch(`/api/library/storage/stats?room_id=${roomId}`);
        if (statsResponse.ok) {
            const stats = await statsResponse.json();
            const currentUsageBytes = stats.used_bytes;
            const availableBytes = STORAGE_LIMIT_BYTES - currentUsageBytes;
            const availableMB = (availableBytes / (1024 * 1024)).toFixed(2);
            
            // Check if file would exceed storage limit
            if (fileSizeBytes > availableBytes) {
                alert(`❌ File size (${fileSizeMB} MB) exceeds available storage (${availableMB} MB).\n\nPlease delete some documents to free up space before uploading or choose a smaller document.`);
                event.target.value = ''; // Clear file input
                return; // Stop upload
            }
        }
    } catch (error) {
        console.error('Error checking storage:', error);
        // Continue with upload if we can't check storage (graceful degradation)
    }
    
    // Generate temporary ID for this upload
    const tempId = 'uploading-' + Date.now();
    
    // Immediately add document to list in "uploading" state
    addUploadingDocument(tempId, file.name, listDiv);
    
    // Hide status div, we're showing progress in the list now
    statusDiv.classList.add('hidden');
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        // Update to "processing" stage
        updateUploadProgress(tempId, 'extracting', 33);
        
        // Include room_id in query parameter
        const response = await fetch(`/api/library/upload?room_id=${roomId}`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Upload failed');
        }
        
        // Update to "finalizing" stage
        updateUploadProgress(tempId, 'indexing', 90);
        
        const result = await response.json();
        
        // Complete - show success briefly then refresh
        updateUploadProgress(tempId, 'complete', 100);
        
        // Clear file input
        event.target.value = '';
        
        // Wait a moment to show completion, then refresh to show real document
        setTimeout(() => {
            refreshLibraryDocuments();
            updateStorageIndicator();
        }, 1000);
        
    } catch (error) {
        // Show error state
        updateUploadProgress(tempId, 'error', 0, error.message);
        console.error('Upload error:', error);
        
        // Remove failed upload after 5 seconds
        setTimeout(() => {
            const uploadElement = document.getElementById(tempId);
            if (uploadElement) {
                uploadElement.remove();
                // Refresh to show current state
                refreshLibraryDocuments();
                updateStorageIndicator();
            }
        }, 5000);
    }
}

function addUploadingDocument(tempId, fileName, listDiv) {
    // Remove "no documents" placeholder if present
    const placeholder = listDiv.querySelector('.text-muted-foreground');
    if (placeholder && placeholder.textContent.includes('No documents')) {
        placeholder.remove();
    }
    
    const uploadHtml = `
        <div id="${tempId}" class="relative p-2 rounded text-xs border border-primary/50 overflow-hidden bg-muted/10">
            <!-- Background progress fill -->
            <div class="upload-progress-bg absolute inset-0 bg-blue-500/40 transition-all duration-500" style="width: 10%; transform-origin: left;"></div>
            
            <!-- Content layer (above progress background) -->
            <div class="relative z-10 flex items-start gap-2">
                <div class="flex-1 min-w-0">
                    <div class="font-medium text-foreground truncate flex items-center gap-1" title="${escapeHtml(fileName)}">
                        <i data-lucide="upload" class="w-3 h-3"></i>
                        <span>${escapeHtml(fileName)}</span>
                    </div>
                    <div class="upload-status text-muted-foreground mt-1 flex items-center gap-2">
                        <span>Uploading...</span>
                        <span class="upload-percentage font-medium">10%</span>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Add to top of list
    listDiv.insertAdjacentHTML('afterbegin', uploadHtml);
    
    // Re-initialize lucide icons
    if (window.lucide) {
        window.lucide.createIcons();
    }
}

function updateUploadProgress(tempId, stage, percentage, errorMessage = null) {
    const uploadElement = document.getElementById(tempId);
    if (!uploadElement) return;
    
    const progressBg = uploadElement.querySelector('.upload-progress-bg');
    const statusText = uploadElement.querySelector('.upload-status');
    const percentageText = uploadElement.querySelector('.upload-percentage');
    
    if (errorMessage) {
        // Error state - fill entire background with red
        uploadElement.classList.remove('border-primary/50');
        uploadElement.classList.add('border-red-600/50');
        progressBg.classList.remove('bg-blue-500/40');
        progressBg.classList.add('bg-red-600/40');
        progressBg.style.width = '100%';
        statusText.innerHTML = `<span class="text-red-600 font-medium">✗ ${errorMessage}</span>`;
        if (percentageText) percentageText.remove();
        return;
    }
    
    // Update background fill width
    progressBg.style.width = `${percentage}%`;
    
    // Update percentage display
    if (percentageText) {
        percentageText.textContent = `${percentage}%`;
    }
    
    // Update status text based on stage
    const stageMessages = {
        'uploading': 'Uploading file...',
        'extracting': 'Extracting text...',
        'chunking': 'Processing content...',
        'indexing': 'Indexing chunks...',
        'complete': '✓ Complete!'
    };
    
    const messageSpan = statusText.querySelector('span:first-child') || statusText;
    messageSpan.textContent = stageMessages[stage] || 'Processing...';
    
    if (stage === 'complete') {
        // Success state - green background fill
        uploadElement.classList.remove('border-primary/50');
        uploadElement.classList.add('border-green-600/50');
        progressBg.classList.remove('bg-blue-500/40');
        progressBg.classList.add('bg-green-600/50');
        statusText.classList.add('text-green-600', 'font-medium');
    }
}

async function refreshLibraryDocuments() {
    const roomId = getRoomId();
    if (!roomId) {
        console.error('Cannot refresh documents: room_id not available');
        return;
    }
    
    const listDiv = document.getElementById('library-documents-list');
    
    // Show loading state
    listDiv.innerHTML = `
        <div class="flex items-center gap-2 text-xs text-muted-foreground p-2">
            <div class="animate-spin rounded-full h-3 w-3 border-b-2 border-primary"></div>
            Loading documents...
        </div>
    `;
    
    try {
        const response = await fetch(`/api/library/documents?room_id=${roomId}`, {
            method: 'GET'
        });
        
        if (!response.ok) {
            throw new Error('Failed to fetch documents');
        }
        
        const data = await response.json();
        displayDocumentsList(data.documents);
        
    } catch (error) {
        listDiv.innerHTML = `
            <div class="text-xs text-muted-foreground p-2">
                💡 Upload a document to get started!
            </div>
        `;
        console.error('Fetch documents error:', error);
    }
}

function displayDocumentsList(documents) {
    const listDiv = document.getElementById('library-documents-list');
    
    if (!documents || documents.length === 0) {
        listDiv.innerHTML = `
            <div class="text-xs text-muted-foreground p-2">
                💡 No documents uploaded yet.<br>
                Upload a document to get started!
            </div>
        `;
        return;
    }
    
    const roomId = getRoomId();
    
    const documentsHTML = documents.map(doc => {
        const uploadDate = new Date(doc.uploaded_at);
        const formattedDate = uploadDate.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric',
            year: uploadDate.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined
        });
        
        return `
            <div class="p-2 bg-muted rounded text-xs border border-border hover:border-primary transition-colors group">
                <div class="flex items-start justify-between gap-2">
                    <div class="flex-1 min-w-0">
                        <div class="font-medium text-foreground truncate" title="${escapeHtml(doc.name)}">
                            <i data-lucide="file-text" class="w-3 h-3 inline mr-1"></i>
                            ${escapeHtml(doc.name)}
                        </div>
                        <div class="text-muted-foreground mt-1">
                            <span>${formattedDate}</span>
                        </div>
                    </div>
                    <button 
                        onclick="deleteDocument('${doc.file_id}', '${escapeHtml(doc.name)}', ${roomId})"
                        class="opacity-0 group-hover:opacity-100 transition-opacity text-red-600 hover:text-red-800 p-1"
                        title="Delete document"
                    >
                        <i data-lucide="trash-2" class="w-3 h-3"></i>
                    </button>
                </div>
            </div>
        `;
    }).join('');
    
    listDiv.innerHTML = documentsHTML;
    
    // Re-initialize lucide icons for the new content
    if (window.lucide) {
        window.lucide.createIcons();
    }
}

async function deleteDocument(fileId, fileName, roomId) {
    if (!confirm(`Are you sure you want to delete "${fileName}"?`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/library/clear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ids: [fileId],
                room_id: roomId
            })
        });
        
        if (!response.ok) {
            throw new Error('Delete failed');
        }
        
        // Refresh the list and update storage
        refreshLibraryDocuments();
        updateStorageIndicator();
        
    } catch (error) {
        alert(`Failed to delete document: ${error.message}`);
        console.error('Delete error:', error);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Export functions for inline onclick handlers
window.refreshLibraryDocuments = refreshLibraryDocuments;
window.deleteDocument = deleteDocument;

