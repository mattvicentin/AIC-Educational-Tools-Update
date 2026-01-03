/**
 * Flashcards Tool Handler
 * Manages the flashcards panel, generation, and display flow
 */

(function() {
    'use strict';
    
    // #region agent log
    console.error('[DEBUG] Flashcards tool IIFE STARTED');
    fetch('http://127.0.0.1:7242/ingest/08dfd7f6-3013-4e1c-b3fe-d590be4d1bee',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'flashcards-tool.js:9',message:'IIFE execution started',data:{timestamp:Date.now()},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch((e)=>{console.error('[DEBUG] Fetch failed:',e);});
    // #endregion
    console.log('Flashcards tool script loading...');

    const FLASHCARDS_PANEL_ID = 'flashcards-panel';
    const FLASHCARDS_STEPS = {
        CONFIG: 'flashcards-step-config',
        GRID: 'flashcards-step-grid',
        SINGLE: 'flashcards-step-single'
    };

    let currentFlashcards = [];
    let currentSessionId = null;
    let currentCursor = null;
    let currentDisplayMode = null;
    let currentGridSize = null;
    let currentCardIndex = 0;
    let seenHashes = new Set();
    let chatId = null;
    let savedConfig = null; // Store configuration for "Generate More"

    /**
     * Initialize flashcards tool
     */
    function initFlashcardsTool() {
        // Get chat ID from URL or data attribute
        const chatMatch = window.location.pathname.match(/\/chat\/(\d+)/);
        chatId = chatMatch ? parseInt(chatMatch[1]) : null;
        
        if (!chatId) {
            const chatContainer = document.querySelector('.chat-container');
            chatId = chatContainer ? parseInt(chatContainer.dataset.chatId) : null;
        }

        if (!chatId) {
            console.warn('Flashcards tool: Could not determine chat ID');
            return;
        }

        // Setup event listeners
        setupEventListeners();
        
        // Setup context mode change handler
        const contextModeSelect = document.getElementById('flashcards-context-mode');
        if (contextModeSelect) {
            contextModeSelect.addEventListener('change', handleContextModeChange);
        }
    }

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // Close button
        const closeBtn = document.getElementById('flashcards-panel-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', closeFlashcardsPanel);
        }

        // Config form submit
        const configForm = document.getElementById('flashcards-config-form');
        if (configForm) {
            configForm.addEventListener('submit', handleConfigSubmit);
        }

        // Display mode change
        const displayModeSelect = document.getElementById('flashcards-display-mode');
        if (displayModeSelect) {
            displayModeSelect.addEventListener('change', handleDisplayModeChange);
        }

        // Library add button
        const libraryAddBtn = document.getElementById('flashcards-library-add-btn');
        if (libraryAddBtn) {
            libraryAddBtn.addEventListener('click', openLibraryUpload);
        }

        // Library file input
        const libraryFileInput = document.getElementById('flashcards-library-file-input');
        if (libraryFileInput) {
            libraryFileInput.addEventListener('change', handleFlashcardsLibraryUpload);
        }

        // Close buttons (grid and single card views)
        const closeBtnGrid = document.getElementById('flashcards-close-btn');
        const closeSingleBtn = document.getElementById('flashcards-close-single-btn');
        if (closeBtnGrid) closeBtnGrid.addEventListener('click', closeFlashcardsPanel);
        if (closeSingleBtn) closeSingleBtn.addEventListener('click', closeFlashcardsPanel);

        // Next card button
        const nextBtn = document.getElementById('flashcards-next-btn');
        if (nextBtn) {
            nextBtn.addEventListener('click', goToNextCard);
        }

        // Error retry
        const errorRetryBtn = document.getElementById('flashcards-error-retry');
        if (errorRetryBtn) {
            errorRetryBtn.addEventListener('click', () => {
                hideError();
                showStep(FLASHCARDS_STEPS.CONFIG);
            });
        }

        // Close on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !isPanelHidden()) {
                closeFlashcardsPanel();
            }
        });

        // Close on backdrop click
        const backdrop = document.getElementById('flashcards-panel-backdrop');
        if (backdrop) {
            backdrop.addEventListener('click', (e) => {
                if (e.target === backdrop) {
                    closeFlashcardsPanel();
                }
            });
        }
    }

    /**
     * Handle display mode change
     */
    function handleDisplayModeChange() {
        const displayMode = document.getElementById('flashcards-display-mode').value;
        const gridSizeField = document.getElementById('flashcards-grid-size-field');
        const cardCountField = document.getElementById('flashcards-card-count-field');

        if (displayMode === 'grid') {
            gridSizeField.classList.remove('flashcards-config-field--hidden');
            cardCountField.classList.add('flashcards-config-field--hidden');
        } else {
            gridSizeField.classList.add('flashcards-config-field--hidden');
            cardCountField.classList.remove('flashcards-config-field--hidden');
        }
    }


    /**
     * Handle context mode change
     */
    async function handleContextModeChange() {
        const contextMode = document.getElementById('flashcards-context-mode')?.value;
        const librarySection = document.getElementById('flashcards-library-section');
        
        if (!librarySection) return;

        if (contextMode === 'library' || contextMode === 'both') {
            librarySection.classList.remove('flashcards-config-field--hidden');
            await loadLibraryDocuments();
        } else {
            librarySection.classList.add('flashcards-config-field--hidden');
        }
    }

    /**
     * Load library documents
     */
    async function loadLibraryDocuments() {
        if (!chatId) return;

        try {
            const chatContainer = document.querySelector('.chat-container');
            const roomId = chatContainer ? parseInt(chatContainer.dataset.roomId) : null;
            
            if (!roomId) {
                showLibraryEmpty();
                return;
            }

            const docsResponse = await fetch(`/api/library/documents?room_id=${roomId}`);
            const docsData = await docsResponse.json();
            
            const documents = docsData.documents || [];
            
            if (documents.length === 0) {
                showLibraryEmpty();
            } else {
                showLibraryList(documents);
            }
        } catch (error) {
            console.error('Failed to load library documents:', error);
            showLibraryEmpty();
        }
    }

    /**
     * Show library empty state
     */
    function showLibraryEmpty() {
        const emptyEl = document.getElementById('flashcards-library-empty');
        const listEl = document.getElementById('flashcards-library-list');
        
        if (emptyEl) emptyEl.classList.remove('hidden');
        if (listEl) listEl.classList.add('hidden');
    }

    /**
     * Show library document list
     */
    function showLibraryList(documents) {
        const emptyEl = document.getElementById('flashcards-library-empty');
        const listEl = document.getElementById('flashcards-library-list');
        
        if (emptyEl) emptyEl.classList.add('hidden');
        if (listEl) {
            listEl.classList.remove('hidden');
            listEl.innerHTML = '';
            
            documents.forEach(doc => {
                const item = document.createElement('div');
                item.className = 'flashcards-library-item';
                
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.id = `flashcards-doc-${doc.id}`;
                checkbox.value = doc.id;
                checkbox.name = 'library_doc_ids';
                
                const label = document.createElement('label');
                label.className = 'flashcards-library-item-label';
                label.htmlFor = `flashcards-doc-${doc.id}`;
                label.textContent = doc.name;
                
                const meta = document.createElement('span');
                meta.className = 'flashcards-library-item-meta';
                const sizeKB = doc.file_size ? Math.round(doc.file_size / 1024) : 0;
                const uploadedDate = doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : '';
                meta.textContent = `${sizeKB} KB • ${uploadedDate}`;
                
                item.appendChild(checkbox);
                item.appendChild(label);
                item.appendChild(meta);
                listEl.appendChild(item);
            });
        }
    }

    /**
     * Open library upload
     */
    function openLibraryUpload() {
        const fileInput = document.getElementById('flashcards-library-file-input');
        if (fileInput) {
            fileInput.click();
        }
    }

    /**
     * Handle file upload for flashcards panel
     */
    async function handleFlashcardsLibraryUpload(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        if (!chatId) {
            showError('Chat ID not available. Please refresh the page.');
            event.target.value = '';
            return;
        }

        const chatContainer = document.querySelector('.chat-container');
        const roomId = chatContainer ? parseInt(chatContainer.dataset.roomId) : null;
        
        if (!roomId) {
            showError('Room ID not available. Please refresh the page.');
            event.target.value = '';
            return;
        }

        const statusDiv = document.getElementById('flashcards-library-upload-status');
        
        if (statusDiv) {
            statusDiv.classList.remove('hidden');
            statusDiv.textContent = 'Uploading...';
            statusDiv.className = 'flashcards-library-upload-status';
        }

        const STORAGE_LIMIT_BYTES = 10 * 1024 * 1024; // 10 MB
        const fileSizeBytes = file.size;
        const fileSizeMB = (fileSizeBytes / (1024 * 1024)).toFixed(2);
        
        try {
            const statsResponse = await fetch(`/api/library/storage/stats?room_id=${roomId}`);
            if (statsResponse.ok) {
                const stats = await statsResponse.json();
                const currentUsageBytes = stats.used_bytes;
                const availableBytes = STORAGE_LIMIT_BYTES - currentUsageBytes;
                const availableMB = (availableBytes / (1024 * 1024)).toFixed(2);
                
                if (fileSizeBytes > availableBytes) {
                    if (statusDiv) {
                        statusDiv.textContent = `❌ File size (${fileSizeMB} MB) exceeds available storage (${availableMB} MB)`;
                        statusDiv.className = 'flashcards-library-upload-status flashcards-library-upload-status--error';
                    }
                    event.target.value = '';
                    setTimeout(() => {
                        if (statusDiv) statusDiv.classList.add('hidden');
                    }, 5000);
                    return;
                }
            }
        } catch (error) {
            console.error('Error checking storage:', error);
        }

        const formData = new FormData();
        formData.append('file', file);
        
        try {
            if (statusDiv) {
                statusDiv.textContent = 'Processing...';
            }

            const response = await fetch(`/api/library/upload?room_id=${roomId}`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Upload failed');
            }
            
            const result = await response.json();
            
            if (statusDiv) {
                statusDiv.textContent = '✓ Upload successful!';
                statusDiv.className = 'flashcards-library-upload-status flashcards-library-upload-status--success';
            }
            
            event.target.value = '';
            await loadLibraryDocuments();
            
            setTimeout(() => {
                if (statusDiv) statusDiv.classList.add('hidden');
            }, 2000);
            
        } catch (error) {
            console.error('Upload error:', error);
            if (statusDiv) {
                statusDiv.textContent = `❌ ${error.message || 'Upload failed'}`;
                statusDiv.className = 'flashcards-library-upload-status flashcards-library-upload-status--error';
            }
            event.target.value = '';
            setTimeout(() => {
                if (statusDiv) statusDiv.classList.add('hidden');
            }, 5000);
        }
    }

    /**
     * Handle config form submit
     */
    async function handleConfigSubmit(e) {
        e.preventDefault();
        
        if (!chatId) {
            showError('Chat ID not found');
            return;
        }

        const formData = new FormData(e.target);
        const displayMode = formData.get('display_mode');
        const contextMode = formData.get('context_mode');
        const instructions = formData.get('instructions') || '';
        
        let cardCount = null;
        let gridSize = null;

        if (displayMode === 'grid') {
            gridSize = formData.get('grid_size');
            // Card count is calculated from grid size
            cardCount = calculateCardCountFromGrid(gridSize);
        } else {
            cardCount = parseInt(formData.get('card_count'));
            if (!cardCount || cardCount < 1) {
                showError('Please enter a valid card count');
                return;
            }
        }
        
        // Get selected library documents
        const libraryDocIds = [];
        if (contextMode === 'library' || contextMode === 'both') {
            const checkboxes = document.querySelectorAll('#flashcards-library-list input[type="checkbox"]:checked');
            checkboxes.forEach(cb => libraryDocIds.push(parseInt(cb.value)));
            
            if (contextMode === 'library' && libraryDocIds.length === 0) {
                showError('Please select at least one library document');
                return;
            }
        }

        // Show loading
        showLoading('Generating flashcards...');

        try {
            const response = await fetch('/api/flashcards/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    chat_id: chatId,
                    context_mode: contextMode,
                    library_doc_ids: libraryDocIds,
                    display_mode: displayMode,
                    grid_size: gridSize,
                    card_count: cardCount,
                    instructions: instructions
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.message || data.error || 'Failed to generate flashcards');
            }

            // Handle response status
            if (data.status === 'insufficient_context') {
                showWarning(data.message || 'Context insufficient for requested count');
                if (data.cards && data.cards.length > 0) {
                    handleFlashcardsResponse(data, displayMode, gridSize);
                } else {
                    hideLoading();
                    showStep(FLASHCARDS_STEPS.CONFIG);
                }
                return;
            }

            if (data.status !== 'ok') {
                throw new Error(data.message || 'Flashcard generation failed');
            }

            // Store configuration for "Generate More" functionality
            savedConfig = {
                contextMode: contextMode,
                libraryDocIds: libraryDocIds,
                displayMode: displayMode,
                gridSize: gridSize,
                cardCount: cardCount,
                instructions: instructions
            };

            handleFlashcardsResponse(data, displayMode, gridSize);
            
        } catch (error) {
            console.error('Flashcard generation error:', error);
            showError(error.message || 'Failed to generate flashcards. Please try again.');
        }
    }

    /**
     * Calculate card count from grid size
     */
    function calculateCardCountFromGrid(gridSize) {
        const parts = gridSize.split('x');
        return parseInt(parts[0]) * parseInt(parts[1]);
    }

    /**
     * Handle flashcards response
     */
    function handleFlashcardsResponse(data, displayMode, gridSize) {
        currentFlashcards = data.cards || [];
        currentDisplayMode = displayMode;
        currentGridSize = gridSize;
        currentCardIndex = 0;

        // Track seen hashes
        currentFlashcards.forEach(card => {
            if (card.hash) {
                seenHashes.add(card.hash);
            }
        });

        // Show appropriate display
        if (displayMode === 'grid') {
            renderGridCards(currentFlashcards, gridSize);
            showStep(FLASHCARDS_STEPS.GRID);
            // Show "Generate More" button in grid mode
            const generateMoreBtn = document.getElementById('flashcards-generate-more-btn');
            if (generateMoreBtn) {
                generateMoreBtn.style.display = 'block';
            }
        } else {
            renderSingleCard(currentFlashcards[0], 0, currentFlashcards.length);
            showStep(FLASHCARDS_STEPS.SINGLE);
            // Hide "Generate More" button in single card mode
            const generateMoreBtn = document.getElementById('flashcards-generate-more-btn');
            if (generateMoreBtn) {
                generateMoreBtn.style.display = 'none';
            }
        }

        hideLoading();
    }

    /**
     * Render grid cards
     */
    function renderGridCards(cards, gridSize) {
        const container = document.getElementById('flashcards-grid-container');
        if (!container) return;

        container.innerHTML = '';
        container.setAttribute('data-grid', gridSize);

        cards.forEach((card, index) => {
            const cardEl = createCardElement(card, index);
            container.appendChild(cardEl);
        });

        // Initialize Lucide icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    /**
     * Render single card
     */
    function renderSingleCard(card, index, total) {
        const wrapper = document.getElementById('flashcards-single-card-wrapper');
        const progress = document.getElementById('flashcards-progress');
        const nextBtn = document.getElementById('flashcards-next-btn');

        if (!wrapper) return;

        wrapper.innerHTML = '';
        const cardEl = createCardElement(card, index);
        wrapper.appendChild(cardEl);

        // Update progress
        if (progress) {
            progress.textContent = `Card ${index + 1} of ${total}`;
        }

        // Update next button
        if (nextBtn) {
            if (index >= total - 1) {
                nextBtn.disabled = true;
            } else {
                nextBtn.disabled = false;
            }
        }

        // Initialize Lucide icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    /**
     * Create card element
     */
    function createCardElement(card, index) {
        const cardWrapper = document.createElement('div');
        cardWrapper.className = 'flashcard-card';
        cardWrapper.dataset.cardIndex = index;

        const inner = document.createElement('div');
        inner.className = 'flashcard-inner';

        const front = document.createElement('div');
        front.className = 'flashcard-front';
        front.textContent = card.front || '';

        const back = document.createElement('div');
        back.className = 'flashcard-back';
        back.textContent = card.back || '';

        inner.appendChild(front);
        inner.appendChild(back);
        cardWrapper.appendChild(inner);

        // Add click handler for flip
        cardWrapper.addEventListener('click', () => {
            flipCard(cardWrapper);
        });

        return cardWrapper;
    }

    /**
     * Flip card
     */
    function flipCard(cardElement) {
        cardElement.classList.toggle('flipped');
    }

    /**
     * Go to next card (single mode)
     */
    function goToNextCard() {
        if (currentCardIndex >= currentFlashcards.length - 1) {
            return;
        }

        currentCardIndex++;
        renderSingleCard(currentFlashcards[currentCardIndex], currentCardIndex, currentFlashcards.length);
    }

    /**
     * Generate more cards using saved configuration (grid mode only)
     */
    async function generateMoreCards() {
        if (!savedConfig || savedConfig.displayMode !== 'grid') {
            showError('Configuration not available');
            return;
        }

        if (!chatId) {
            showError('Chat ID not found');
            return;
        }

        showLoading('Generating more flashcards...');

        try {
            const response = await fetch('/api/flashcards/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    chat_id: chatId,
                    context_mode: savedConfig.contextMode,
                    library_doc_ids: savedConfig.libraryDocIds,
                    display_mode: savedConfig.displayMode,
                    grid_size: savedConfig.gridSize,
                    card_count: savedConfig.cardCount,
                    instructions: savedConfig.instructions
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.message || data.error || 'Failed to generate more flashcards');
            }

            // Handle response status
            if (data.status === 'insufficient_context') {
                showWarning(data.message || 'No more cards can be generated');
                hideLoading();
                return;
            }

            if (data.status !== 'ok') {
                throw new Error(data.message || 'Failed to generate more flashcards');
            }

            // Filter duplicates and add new cards
            const newCards = (data.cards || []).filter(card => {
                if (card.hash && seenHashes.has(card.hash)) {
                    return false;
                }
                if (card.hash) {
                    seenHashes.add(card.hash);
                }
                return true;
            });

            if (newCards.length === 0) {
                showWarning('No new unique cards could be generated');
                hideLoading();
                return;
            }

            // Add to current flashcards
            currentFlashcards.push(...newCards);

            // Re-render grid with all cards
            renderGridCards(currentFlashcards, savedConfig.gridSize);
            hideLoading();

        } catch (error) {
            console.error('Generate more error:', error);
            showError(error.message || 'Failed to generate more flashcards');
        }
    }

    /**
     * Open flashcards panel
     */
    function openFlashcardsPanel() {
        const panel = document.getElementById(FLASHCARDS_PANEL_ID);
        const backdrop = document.getElementById('flashcards-panel-backdrop');
        if (!panel) {
            console.error('Flashcards panel not found');
            return;
        }

        // Show backdrop first
        if (backdrop) {
            backdrop.classList.remove('hidden');
        }
        
        // Then show panel
        panel.classList.remove('hidden');
        showStep(FLASHCARDS_STEPS.CONFIG);
        resetFlashcards();
        
        // Load library documents if needed
        handleContextModeChange();
        
        // Initialize Lucide icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    /**
     * Close flashcards panel
     */
    function closeFlashcardsPanel() {
        const panel = document.getElementById(FLASHCARDS_PANEL_ID);
        const backdrop = document.getElementById('flashcards-panel-backdrop');
        
        if (panel) {
            panel.classList.add('hidden');
        }
        
        if (backdrop) {
            backdrop.classList.add('hidden');
        }
        
        resetFlashcards();
    }

    /**
     * Check if panel is hidden
     */
    function isPanelHidden() {
        const panel = document.getElementById(FLASHCARDS_PANEL_ID);
        return !panel || panel.classList.contains('hidden');
    }

    /**
     * Show a specific step
     */
    function showStep(stepId) {
        Object.values(FLASHCARDS_STEPS).forEach(step => {
            const stepEl = document.getElementById(step);
            if (stepEl) {
                stepEl.classList.remove('flashcards-step--active');
                stepEl.classList.add('flashcards-step--hidden');
            }
        });

        const targetStep = document.getElementById(stepId);
        if (targetStep) {
            targetStep.classList.remove('flashcards-step--hidden');
            targetStep.classList.add('flashcards-step--active');
        }

        hideLoading();
        hideError();
    }

    /**
     * Reset flashcards
     */
    function resetFlashcards() {
        currentFlashcards = [];
        currentSessionId = null;
        currentCursor = null;
        currentDisplayMode = null;
        currentGridSize = null;
        currentCardIndex = 0;
        seenHashes.clear();
        savedConfig = null;
        
        const configForm = document.getElementById('flashcards-config-form');
        if (configForm) {
            configForm.reset();
        }

        // Reset display mode visibility
        handleDisplayModeChange();
        
        // Reset library section
        const librarySection = document.getElementById('flashcards-library-section');
        if (librarySection) {
            librarySection.classList.add('flashcards-config-field--hidden');
        }

        // Reset context mode
        const contextModeSelect = document.getElementById('flashcards-context-mode');
        if (contextModeSelect) {
            contextModeSelect.value = 'chat';
        }

        // Clear library list
        const libraryList = document.getElementById('flashcards-library-list');
        if (libraryList) {
            libraryList.innerHTML = '';
            libraryList.classList.add('hidden');
        }
        const libraryEmpty = document.getElementById('flashcards-library-empty');
        if (libraryEmpty) {
            libraryEmpty.classList.remove('hidden');
        }

        showStep(FLASHCARDS_STEPS.CONFIG);
        hideError();
        hideLoading();
    }

    /**
     * Show loading state
     */
    function showLoading(text = 'Loading...') {
        const loadingEl = document.getElementById('flashcards-loading');
        const loadingText = document.getElementById('flashcards-loading-text');
        
        if (loadingEl) loadingEl.classList.remove('hidden');
        if (loadingText) loadingText.textContent = text;
    }

    /**
     * Hide loading state
     */
    function hideLoading() {
        const loadingEl = document.getElementById('flashcards-loading');
        if (loadingEl) loadingEl.classList.add('hidden');
    }

    /**
     * Show error
     */
    function showError(message) {
        const errorEl = document.getElementById('flashcards-error');
        const errorText = document.getElementById('flashcards-error-text');
        
        if (errorEl) errorEl.classList.remove('hidden');
        if (errorText) errorText.textContent = message;
        
        hideLoading();
    }

    /**
     * Show warning
     */
    function showWarning(message) {
        // For now, use error display but could be styled differently
        const errorEl = document.getElementById('flashcards-error');
        const errorText = document.getElementById('flashcards-error-text');
        
        if (errorEl) {
            errorEl.classList.remove('hidden');
            errorEl.style.borderColor = '#f59e0b';
            errorEl.style.background = '#fef3c7';
        }
        if (errorText) {
            errorText.textContent = message;
            errorText.style.color = '#92400e';
        }
        
        hideLoading();
    }

    /**
     * Hide error
     */
    function hideError() {
        const errorEl = document.getElementById('flashcards-error');
        if (errorEl) {
            errorEl.classList.add('hidden');
            errorEl.style.borderColor = '';
            errorEl.style.background = '';
        }
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initFlashcardsTool);
    } else {
        initFlashcardsTool();
    }

    // Export for external use
    // Export for external use
    // #region agent log
    console.error('[DEBUG] About to export flashcardsTool, openFlashcardsPanel type:', typeof openFlashcardsPanel);
    fetch('http://127.0.0.1:7242/ingest/08dfd7f6-3013-4e1c-b3fe-d590be4d1bee',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'flashcards-tool.js:947',message:'About to export flashcardsTool',data:{openFlashcardsPanelExists:typeof openFlashcardsPanel,closeFlashcardsPanelExists:typeof closeFlashcardsPanel},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch((e)=>{console.error('[DEBUG] Fetch failed:',e);});
    // #endregion
    window.flashcardsTool = {
        open: openFlashcardsPanel,
        close: closeFlashcardsPanel
    };
    // #region agent log
    console.error('[DEBUG] flashcardsTool exported, exists:', !!window.flashcardsTool);
    fetch('http://127.0.0.1:7242/ingest/08dfd7f6-3013-4e1c-b3fe-d590be4d1bee',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'flashcards-tool.js:952',message:'flashcardsTool exported',data:{flashcardsToolExists:!!window.flashcardsTool,hasOpen:!!window.flashcardsTool?.open,hasClose:!!window.flashcardsTool?.close},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch((e)=>{console.error('[DEBUG] Fetch failed:',e);});
    // #endregion
    console.log('Flashcards tool exported:', window.flashcardsTool);

})();
