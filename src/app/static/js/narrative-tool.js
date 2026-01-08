/**
 * Narrative Tool Handler
 * Manages the narrative panel, generation, and display flow
 */

(function() {
    'use strict';

    const NARRATIVE_PANEL_ID = 'narrative-panel';
    const NARRATIVE_STEPS = {
        CONFIG: 'narrative-step-config',
        DISPLAY: 'narrative-step-display',
        REFLECTION: 'narrative-step-reflection',
        FEEDBACK: 'narrative-step-feedback',
        SEND: 'narrative-step-send'
    };

    // Reflection prompts (hard-coded)
    const REFLECTION_PROMPTS = {
        linear: "Reflect on the narrative you just read. What concepts from the course materials did you recognize? How did the story help you understand these concepts? Can you think of real-world situations where these concepts apply?",
        interactive: "Reflect on your experience with this interactive narrative. What decisions did you make and why? How did your choices connect to the concepts from the course materials? What would have happened differently if you had made other choices? How does this relate to real-world decision-making?"
    };

    let currentNarrative = null;
    let currentNarrativeType = null;
    let currentComplexity = null;
    let currentContextParts = null;
    let currentNodeId = null;
    let visitedNodes = [];
    let reflectionText = null;
    let feedbackContent = null;
    let chatId = null;

    /**
     * Initialize narrative tool
     */
    function initNarrativeTool() {
        // Get chat ID from URL or data attribute
        const chatMatch = window.location.pathname.match(/\/chat\/(\d+)/);
        chatId = chatMatch ? parseInt(chatMatch[1]) : null;
        
        if (!chatId) {
            const chatContainer = document.querySelector('.chat-container');
            chatId = chatContainer ? parseInt(chatContainer.dataset.chatId) : null;
        }

        if (!chatId) {
            console.warn('Narrative tool: Could not determine chat ID');
            return;
        }

        // Setup event listeners
        setupEventListeners();
        
        // Setup context mode change handler
        const contextModeSelect = document.getElementById('narrative-context-mode');
        if (contextModeSelect) {
            contextModeSelect.addEventListener('change', handleContextModeChange);
            // Initialize library section visibility on load
            handleContextModeChange();
        }

        // Setup narrative type change handler
        const narrativeTypeSelect = document.getElementById('narrative-type');
        if (narrativeTypeSelect) {
            narrativeTypeSelect.addEventListener('change', handleNarrativeTypeChange);
            // Initialize complexity field visibility on load
            handleNarrativeTypeChange();
        }
    }

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // Close button
        const closeBtn = document.getElementById('narrative-panel-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', closeNarrativePanel);
        }

        // Config form submit
        const configForm = document.getElementById('narrative-config-form');
        if (configForm) {
            configForm.addEventListener('submit', handleConfigSubmit);
        }

        // Library add button
        const libraryAddBtn = document.getElementById('narrative-library-add-btn');
        if (libraryAddBtn) {
            libraryAddBtn.addEventListener('click', openLibraryUpload);
        }

        // Library file input
        const libraryFileInput = document.getElementById('narrative-library-file-input');
        if (libraryFileInput) {
            libraryFileInput.addEventListener('change', handleNarrativeLibraryUpload);
        }

        // Continue button (linear)
        const continueBtn = document.getElementById('narrative-continue-btn');
        if (continueBtn) {
            continueBtn.addEventListener('click', showReflectionStep);
        }

        // Continue button (interactive)
        const interactiveContinueBtn = document.getElementById('narrative-interactive-continue-btn');
        if (interactiveContinueBtn) {
            interactiveContinueBtn.addEventListener('click', showReflectionStep);
        }

        // Submit reflection button
        const submitReflectionBtn = document.getElementById('narrative-submit-reflection-btn');
        if (submitReflectionBtn) {
            submitReflectionBtn.addEventListener('click', handleReflectionSubmit);
        }

        // Get feedback button
        const getFeedbackBtn = document.getElementById('narrative-get-feedback-btn');
        if (getFeedbackBtn) {
            getFeedbackBtn.addEventListener('click', generateFeedback);
        }

        // Skip feedback button (also acts as Continue after feedback is shown)
        const skipFeedbackBtn = document.getElementById('narrative-skip-feedback-btn');
        if (skipFeedbackBtn) {
            skipFeedbackBtn.addEventListener('click', () => {
                skipFeedback();
            });
        }

        // Send to chat button
        const sendToChatBtn = document.getElementById('narrative-send-to-chat-btn');
        if (sendToChatBtn) {
            sendToChatBtn.addEventListener('click', sendToChat);
        }

        // Error retry
        const errorRetryBtn = document.getElementById('narrative-error-retry');
        if (errorRetryBtn) {
            errorRetryBtn.addEventListener('click', () => {
                hideError();
                showStep(NARRATIVE_STEPS.CONFIG);
            });
        }

        // Close on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !isPanelHidden()) {
                closeNarrativePanel();
            }
        });

        // Close on backdrop click
        const backdrop = document.getElementById('narrative-panel-backdrop');
        if (backdrop) {
            backdrop.addEventListener('click', (e) => {
                if (e.target === backdrop) {
                    closeNarrativePanel();
                }
            });
        }
    }

    /**
     * Handle context mode change
     */
    async function handleContextModeChange() {
        const contextMode = document.getElementById('narrative-context-mode')?.value;
        const librarySection = document.getElementById('narrative-library-section');
        
        if (!librarySection) return;

        if (contextMode === 'library' || contextMode === 'both') {
            librarySection.classList.remove('narrative-config-field--hidden');
            await loadLibraryDocuments();
        } else {
            librarySection.classList.add('narrative-config-field--hidden');
        }
    }

    /**
     * Handle narrative type change
     */
    function handleNarrativeTypeChange() {
        const narrativeType = document.getElementById('narrative-type')?.value;
        const complexityField = document.getElementById('narrative-complexity-field');
        const complexitySelect = document.getElementById('narrative-complexity');
        
        if (!complexityField || !complexitySelect) return;

        if (narrativeType === 'interactive') {
            // Show with smooth transition
            complexityField.classList.remove('narrative-config-field--hidden');
            complexitySelect.required = true;
        } else {
            // Hide with smooth transition
            complexityField.classList.add('narrative-config-field--hidden');
            complexitySelect.required = false;
        }
    }

    /**
     * Load library documents
     */
    async function loadLibraryDocuments() {
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
        const emptyEl = document.getElementById('narrative-library-empty');
        const listEl = document.getElementById('narrative-library-list');
        
        if (emptyEl) emptyEl.classList.remove('hidden');
        if (listEl) listEl.classList.add('hidden');
    }

    /**
     * Show library document list
     */
    function showLibraryList(documents) {
        const emptyEl = document.getElementById('narrative-library-empty');
        const listEl = document.getElementById('narrative-library-list');
        
        if (emptyEl) emptyEl.classList.add('hidden');
        if (listEl) {
            listEl.classList.remove('hidden');
            listEl.innerHTML = '';
            
            documents.forEach(doc => {
                const item = document.createElement('div');
                item.className = 'narrative-library-item';
                
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.id = `narrative-doc-${doc.id}`;
                checkbox.value = doc.id;
                checkbox.name = 'library_doc_ids';
                
                const label = document.createElement('label');
                label.className = 'narrative-library-item-label';
                label.htmlFor = `narrative-doc-${doc.id}`;
                label.textContent = doc.name;
                
                const meta = document.createElement('span');
                meta.className = 'narrative-library-item-meta';
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
        const fileInput = document.getElementById('narrative-library-file-input');
        if (fileInput) {
            fileInput.click();
        }
    }

    /**
     * Handle file upload for narrative panel
     */
    async function handleNarrativeLibraryUpload(event) {
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

        const statusDiv = document.getElementById('narrative-library-upload-status');
        
        if (statusDiv) {
            statusDiv.classList.remove('hidden');
            statusDiv.textContent = 'Uploading...';
            statusDiv.className = 'narrative-library-upload-status';
        }

        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch(`/api/library/upload?room_id=${roomId}`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Upload failed');
            }

            if (statusDiv) {
                statusDiv.textContent = '✓ Upload successful';
                statusDiv.className = 'narrative-library-upload-status narrative-library-upload-status--success';
            }

            // Reload library documents
            await loadLibraryDocuments();
            
            // Clear file input
            event.target.value = '';
            
            setTimeout(() => {
                if (statusDiv) statusDiv.classList.add('hidden');
            }, 3000);
            
        } catch (error) {
            console.error('Upload error:', error);
            if (statusDiv) {
                statusDiv.textContent = `✗ ${error.message || 'Upload failed'}`;
                statusDiv.className = 'narrative-library-upload-status narrative-library-upload-status--error';
            }
            event.target.value = '';
        }
    }

    /**
     * Handle config form submit
     */
    async function handleConfigSubmit(e) {
        e.preventDefault();
        
        if (!chatId) {
            showError('Chat ID not available. Please refresh the page.');
            return;
        }

        const formData = new FormData(e.target);
        const contextMode = formData.get('context_mode');
        const narrativeType = formData.get('narrative_type');
        const complexity = formData.get('complexity');
        const instructions = formData.get('instructions') || '';
        
        // Validation
        if (!narrativeType) {
            showError('Please select a narrative type');
            return;
        }

        if (narrativeType === 'interactive' && !complexity) {
            showError('Please select a complexity level for interactive narratives');
            return;
        }
        
        // Get selected library documents
        const libraryDocIds = [];
        if (contextMode === 'library' || contextMode === 'both') {
            const checkboxes = document.querySelectorAll('#narrative-library-list input[type="checkbox"]:checked');
            checkboxes.forEach(cb => libraryDocIds.push(parseInt(cb.value)));
            
            if (contextMode === 'library' && libraryDocIds.length === 0) {
                showError('Please select at least one library document');
                return;
            }
        }

        // Show loading
        showLoading('Generating narrative...');

        try {
            const response = await fetch('/api/narrative/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    chat_id: chatId,
                    context_mode: contextMode,
                    library_doc_ids: libraryDocIds,
                    narrative_type: narrativeType,
                    complexity: complexity,
                    instructions: instructions
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to generate narrative');
            }

            if (!data.success) {
                throw new Error(data.error || 'Narrative generation failed');
            }

            // Store narrative data
            currentNarrative = data.narrative;
            currentNarrativeType = data.narrative_type;
            currentComplexity = data.complexity || null;
            
            // Validate interactive narrative structure
            if (currentNarrativeType === 'interactive') {
                if (!currentNarrative || !currentNarrative.nodes || !Array.isArray(currentNarrative.nodes)) {
                    throw new Error('Invalid interactive narrative structure: missing nodes array');
                }
                if (!currentNarrative.startNodeId) {
                    throw new Error('Invalid interactive narrative structure: missing startNodeId');
                }
                // Verify start node exists
                const startNodeExists = currentNarrative.nodes.some(n => n.id === currentNarrative.startNodeId);
                if (!startNodeExists) {
                    console.error('Start node validation failed:', {
                        startNodeId: currentNarrative.startNodeId,
                        availableNodes: currentNarrative.nodes.map(n => n.id)
                    });
                    throw new Error(`Invalid interactive narrative: start node "${currentNarrative.startNodeId}" not found in nodes`);
                }
                // Log for debugging
                console.log('Interactive narrative loaded:', {
                    nodeCount: currentNarrative.nodes.length,
                    nodeIds: currentNarrative.nodes.map(n => n.id),
                    startNodeId: currentNarrative.startNodeId
                });
            }
            
            // Store context parts for feedback generation
            currentContextParts = {
                chat: null,
                library: null
            };
            // Note: We'd need to fetch context parts separately if needed for feedback
            // For now, we'll pass what we have

            // Display narrative
            if (currentNarrativeType === 'linear') {
                displayLinearNarrative(currentNarrative);
            } else {
                displayInteractiveNarrative(currentNarrative);
            }
            
        } catch (error) {
            console.error('Narrative generation error:', error);
            showError(error.message || 'Failed to generate narrative. Please try again.');
        }
    }

    /**
     * Display linear narrative
     */
    function displayLinearNarrative(narrativeText) {
        hideLoading();
        
        const linearContainer = document.getElementById('narrative-linear-container');
        const linearContent = document.getElementById('narrative-linear-content');
        const interactiveContainer = document.getElementById('narrative-interactive-container');
        
        if (linearContainer && linearContent) {
            // Format text with paragraphs
            const formattedText = narrativeText.split('\n\n').map(para => {
                return `<p>${para.replace(/\n/g, '<br>')}</p>`;
            }).join('');
            
            linearContent.innerHTML = formattedText;
            linearContainer.classList.remove('hidden');
            interactiveContainer.classList.add('hidden');
            
            showStep(NARRATIVE_STEPS.DISPLAY);
        }
    }

    /**
     * Display interactive narrative
     */
    function displayInteractiveNarrative(narrativeData) {
        hideLoading();
        
        const linearContainer = document.getElementById('narrative-linear-container');
        const interactiveContainer = document.getElementById('narrative-interactive-container');
        
        if (interactiveContainer) {
            linearContainer.classList.add('hidden');
            interactiveContainer.classList.remove('hidden');
            
            // Store narrative data
            currentNarrative = narrativeData;
            
            // Start at the beginning
            currentNodeId = narrativeData.startNodeId;
            visitedNodes = [];
            
            // Render initial node
            renderInteractiveNode(currentNodeId);
            
            showStep(NARRATIVE_STEPS.DISPLAY);
        }
    }

    /**
     * Render interactive node
     */
    function renderInteractiveNode(nodeId) {
        if (!currentNarrative || !currentNarrative.nodes) {
            console.error('Narrative data is invalid:', currentNarrative);
            alert('Error: Narrative data is corrupted. Please try generating a new narrative.');
            return;
        }

        const nodeIdStr = String(nodeId).trim();
        
        // Try exact match first
        let node = currentNarrative.nodes.find(n => String(n.id).trim() === nodeIdStr);
        
        // If not found, try case-insensitive match as fallback
        if (!node) {
            node = currentNarrative.nodes.find(n => String(n.id).trim().toLowerCase() === nodeIdStr.toLowerCase());
        }
        
        if (!node) {
            // Debug: Log available node IDs
            const availableNodeIds = currentNarrative.nodes.map(n => String(n.id).trim());
            console.error('Node not found in renderInteractiveNode:', {
                lookingFor: nodeIdStr,
                lookingForType: typeof nodeId,
                availableNodes: availableNodeIds,
                nodeIdTypes: currentNarrative.nodes.map(n => typeof n.id),
                allNodes: currentNarrative.nodes.map(n => ({ id: n.id, idType: typeof n.id }))
            });
            alert(`Error: Story node not found (looking for: "${nodeIdStr}"). Available nodes: ${availableNodeIds.join(', ')}. Please try generating a new narrative.`);
            return;
        }

        const nodeContentEl = document.getElementById('narrative-node-content');
        const choicesContainerEl = document.getElementById('narrative-choices-container');
        const continueBtn = document.getElementById('narrative-interactive-continue-btn');
        
        if (!nodeContentEl || !choicesContainerEl) return;

        // Format and display node content
        const formattedContent = node.content.split('\n\n').map(para => {
            return `<p>${para.replace(/\n/g, '<br>')}</p>`;
        }).join('');
        nodeContentEl.innerHTML = formattedContent;

        // Mark node as visited
        if (!visitedNodes.includes(nodeId)) {
            visitedNodes.push(nodeId);
        }

        // Display choices if not an ending
        if (node.isEnding) {
            choicesContainerEl.innerHTML = '';
            if (continueBtn) {
                continueBtn.classList.remove('hidden');
            }
        } else {
            if (continueBtn) {
                continueBtn.classList.add('hidden');
            }
            
            choicesContainerEl.innerHTML = '';
            node.choices.forEach((choice, index) => {
                const choiceBtn = document.createElement('button');
                choiceBtn.type = 'button';
                choiceBtn.className = 'narrative-choice-btn';
                choiceBtn.textContent = choice.text;
                choiceBtn.addEventListener('click', () => handleChoiceClick(choice));
                choicesContainerEl.appendChild(choiceBtn);
            });
        }
    }

    /**
     * Handle choice click
     */
    function handleChoiceClick(choice) {
        if (!choice || !choice.nextNode) {
            console.error('Invalid choice:', choice);
            alert('Invalid choice. Please try again.');
            return;
        }

        // Disable all choice buttons
        const choiceButtons = document.querySelectorAll('.narrative-choice-btn');
        choiceButtons.forEach(btn => {
            btn.disabled = true;
        });

        // Validate that next node exists
        if (!currentNarrative || !currentNarrative.nodes) {
            console.error('Narrative data is invalid:', currentNarrative);
            alert('Error: Narrative data is corrupted. Please try generating a new narrative.');
            return;
        }

        const nextNodeId = String(choice.nextNode).trim();
        
        // Try exact match first
        let nextNode = currentNarrative.nodes.find(n => String(n.id).trim() === nextNodeId);
        
        // If not found, try case-insensitive match as fallback
        if (!nextNode) {
            nextNode = currentNarrative.nodes.find(n => String(n.id).trim().toLowerCase() === nextNodeId.toLowerCase());
        }
        
        if (!nextNode) {
            // Debug: Log available node IDs
            const availableNodeIds = currentNarrative.nodes.map(n => String(n.id).trim());
            console.error('Next node not found:', {
                lookingFor: nextNodeId,
                lookingForType: typeof nextNodeId,
                availableNodes: availableNodeIds,
                nodeIdTypes: currentNarrative.nodes.map(n => typeof n.id),
                allNodes: currentNarrative.nodes.map(n => ({ id: n.id, idType: typeof n.id })),
                currentNarrative: currentNarrative
            });
            alert(`Error: Next part of the story not found (looking for: "${nextNodeId}"). Available nodes: ${availableNodeIds.join(', ')}. Please try generating a new narrative.`);
            return;
        }

        // Navigate to next node
        currentNodeId = nextNodeId;
        renderInteractiveNode(currentNodeId);
    }

    /**
     * Show reflection step
     */
    function showReflectionStep() {
        const promptEl = document.getElementById('narrative-reflection-prompt');
        const reflectionTextarea = document.getElementById('narrative-reflection-text');
        
        if (promptEl) {
            promptEl.textContent = REFLECTION_PROMPTS[currentNarrativeType] || REFLECTION_PROMPTS.linear;
        }
        
        if (reflectionTextarea) {
            reflectionTextarea.value = '';
        }
        
        showStep(NARRATIVE_STEPS.REFLECTION);
    }

    /**
     * Handle reflection submit
     */
    function handleReflectionSubmit() {
        const reflectionTextarea = document.getElementById('narrative-reflection-text');
        if (!reflectionTextarea) return;

        const text = reflectionTextarea.value.trim();
        if (!text) {
            alert('Please write your reflection before submitting.');
            return;
        }

        reflectionText = text;
        showStep(NARRATIVE_STEPS.FEEDBACK);
    }

    /**
     * Generate feedback
     */
    async function generateFeedback() {
        if (!reflectionText) {
            alert('No reflection text available.');
            return;
        }

        showLoading('Generating feedback...');

        try {
            // Prepare narrative content for feedback
            let narrativeContentForFeedback;
            if (currentNarrativeType === 'linear') {
                narrativeContentForFeedback = currentNarrative;
            } else {
                // For interactive, send the full structure (backend will use it to understand decision logic)
                narrativeContentForFeedback = currentNarrative;
            }

            const response = await fetch('/api/narrative/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    narrative_type: currentNarrativeType,
                    narrative_content: narrativeContentForFeedback,
                    reflection_text: reflectionText,
                    context_parts: currentContextParts || {},
                    complexity: currentComplexity
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to generate feedback');
            }

            if (!data.success) {
                throw new Error(data.error || 'Feedback generation failed');
            }

            feedbackContent = data.feedback;
            displayFeedback(data.feedback);
            
        } catch (error) {
            console.error('Feedback generation error:', error);
            hideLoading();
            alert('Failed to generate feedback: ' + error.message);
        }
    }

    /**
     * Display feedback
     */
    function displayFeedback(feedback) {
        hideLoading();
        
        // Make sure we're on the feedback step
        showStep(NARRATIVE_STEPS.FEEDBACK);
        
        const feedbackContentEl = document.getElementById('narrative-feedback-content');
        const getFeedbackBtn = document.getElementById('narrative-get-feedback-btn');
        const skipFeedbackBtn = document.getElementById('narrative-skip-feedback-btn');
        
        if (!feedbackContentEl) return;

        let html = '';
        
        if (feedback.conceptual_understanding) {
            html += '<div class="narrative-feedback-section">';
            html += '<h3 class="narrative-feedback-section-title">Conceptual Understanding</h3>';
            html += `<div class="narrative-feedback-section-content">${feedback.conceptual_understanding.replace(/\n/g, '<br>')}</div>`;
            html += '</div>';
        }
        
        if (feedback.decision_reasoning && currentNarrativeType === 'interactive') {
            html += '<div class="narrative-feedback-section">';
            html += '<h3 class="narrative-feedback-section-title">Decision Reasoning</h3>';
            html += `<div class="narrative-feedback-section-content">${feedback.decision_reasoning.replace(/\n/g, '<br>')}</div>`;
            html += '</div>';
        }
        
        if (feedback.transfer_application) {
            html += '<div class="narrative-feedback-section">';
            html += '<h3 class="narrative-feedback-section-title">Transfer Application</h3>';
            html += `<div class="narrative-feedback-section-content">${feedback.transfer_application.replace(/\n/g, '<br>')}</div>`;
            html += '</div>';
        }

        // If no feedback sections were generated, show a message
        if (!html) {
            html = '<div class="narrative-feedback-section">';
            html += '<div class="narrative-feedback-section-content">No feedback content available.</div>';
            html += '</div>';
        }

        feedbackContentEl.innerHTML = html;
        feedbackContentEl.classList.remove('hidden');
        
        // Hide Get Feedback button, show Skip button (but change text to "Continue")
        if (getFeedbackBtn) getFeedbackBtn.classList.add('hidden');
        if (skipFeedbackBtn) {
            skipFeedbackBtn.classList.remove('hidden');
            skipFeedbackBtn.textContent = 'Continue';
        }
    }

    /**
     * Skip feedback
     */
    function skipFeedback() {
        // If feedback was already generated, this button acts as "Continue"
        if (feedbackContent) {
            showStep(NARRATIVE_STEPS.SEND);
        } else {
            // Otherwise, skip generating feedback
            feedbackContent = null;
            showStep(NARRATIVE_STEPS.SEND);
        }
    }

    /**
     * Send to chat
     */
    async function sendToChat() {
        if (!chatId) {
            alert('Chat ID not available. Please refresh the page.');
            return;
        }

        // Assemble content
        let content = '=== Narrative Experience ===\n\n';
        content += `Narrative Type: ${currentNarrativeType === 'linear' ? 'Linear Narrative' : 'Interactive Narrative'}\n`;
        if (currentComplexity) {
            content += `Complexity: ${currentComplexity.charAt(0).toUpperCase() + currentComplexity.slice(1)}\n`;
        }
        content += '\n--- Narrative ---\n';
        
        if (currentNarrativeType === 'linear') {
            content += currentNarrative;
        } else {
            // For interactive, show the path taken
            content += 'Interactive Narrative Path:\n';
            visitedNodes.forEach((nodeId, index) => {
                const node = currentNarrative.nodes.find(n => n.id === nodeId);
                if (node) {
                    content += `\n[Step ${index + 1}]\n${node.content}\n`;
                }
            });
        }
        
        content += '\n--- Reflection ---\n';
        content += reflectionText || 'No reflection provided.';
        
        content += '\n--- AI Feedback ---\n';
        if (feedbackContent) {
            if (feedbackContent.conceptual_understanding) {
                content += '\nConceptual Understanding:\n' + feedbackContent.conceptual_understanding + '\n';
            }
            if (feedbackContent.decision_reasoning) {
                content += '\nDecision Reasoning:\n' + feedbackContent.decision_reasoning + '\n';
            }
            if (feedbackContent.transfer_application) {
                content += '\nTransfer Application:\n' + feedbackContent.transfer_application + '\n';
            }
        } else {
            content += 'Feedback skipped.\n';
        }
        
        content += `\n---\nGenerated on: ${new Date().toLocaleString()}`;

        try {
            // Get CSRF token
            const csrfToken = getCsrfToken();
            if (!csrfToken) {
                throw new Error('CSRF token not found');
            }

            // Post message to chat
            const response = await fetch(`/chat/${chatId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    'content': content,
                    'ai_response': '0',
                    'csrf_token': csrfToken
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || 'Failed to send message to chat');
            }

            // Success - close panel and refresh messages
            closeNarrativePanel();
            
            // Refresh chat messages if function exists
            if (typeof pollNewMessages === 'function') {
                pollNewMessages();
            } else {
                // Fallback: reload page to show new message
                setTimeout(() => {
                    window.location.reload();
                }, 500);
            }
            
        } catch (error) {
            console.error('Failed to send narrative to chat:', error);
            alert('Failed to send to chat: ' + error.message);
        }
    }

    /**
     * Get CSRF token from meta tag or form
     */
    function getCsrfToken() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            return metaTag.getAttribute('content');
        }
        
        const form = document.querySelector('form[method="POST"]');
        if (form) {
            const csrfInput = form.querySelector('input[name="csrf_token"]');
            if (csrfInput) {
                return csrfInput.value;
            }
        }
        
        return null;
    }

    /**
     * Open narrative panel
     */
    function openNarrativePanel() {
        const panel = document.getElementById(NARRATIVE_PANEL_ID);
        const backdrop = document.getElementById('narrative-panel-backdrop');
        
        if (!panel || !backdrop) {
            console.warn('Narrative panel elements not found');
            return;
        }

        // Reset state
        resetPanel();
        
        // Show panel and backdrop
        panel.classList.remove('hidden');
        backdrop.classList.remove('hidden');
        
        // Initialize Lucide icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    /**
     * Close narrative panel
     */
    function closeNarrativePanel() {
        const panel = document.getElementById(NARRATIVE_PANEL_ID);
        const backdrop = document.getElementById('narrative-panel-backdrop');
        
        if (panel) panel.classList.add('hidden');
        if (backdrop) backdrop.classList.add('hidden');
        
        // Reset state
        resetPanel();
    }

    /**
     * Reset panel to initial state
     */
    function resetPanel() {
        currentNarrative = null;
        currentNarrativeType = null;
        currentComplexity = null;
        currentContextParts = null;
        currentNodeId = null;
        visitedNodes = [];
        reflectionText = null;
        feedbackContent = null;
        
        // Reset form
        const form = document.getElementById('narrative-config-form');
        if (form) form.reset();
        
        // Reset complexity field visibility
        handleNarrativeTypeChange();
        
        // Clear displays
        const linearContent = document.getElementById('narrative-linear-content');
        const nodeContent = document.getElementById('narrative-node-content');
        const choicesContainer = document.getElementById('narrative-choices-container');
        const reflectionTextarea = document.getElementById('narrative-reflection-text');
        const feedbackContentEl = document.getElementById('narrative-feedback-content');
        const getFeedbackBtn = document.getElementById('narrative-get-feedback-btn');
        const skipFeedbackBtn = document.getElementById('narrative-skip-feedback-btn');
        const continueBtn = document.getElementById('narrative-interactive-continue-btn');
        
        if (linearContent) linearContent.innerHTML = '';
        if (nodeContent) nodeContent.innerHTML = '';
        if (choicesContainer) choicesContainer.innerHTML = '';
        if (reflectionTextarea) reflectionTextarea.value = '';
        if (feedbackContentEl) {
            feedbackContentEl.innerHTML = '';
            feedbackContentEl.classList.add('hidden');
        }
        if (getFeedbackBtn) getFeedbackBtn.classList.remove('hidden');
        if (skipFeedbackBtn) skipFeedbackBtn.classList.add('hidden');
        if (continueBtn) continueBtn.classList.add('hidden');
        
        // Show config step
        showStep(NARRATIVE_STEPS.CONFIG);
        hideLoading();
        hideError();
    }

    /**
     * Show step
     */
    function showStep(stepId) {
        const steps = Object.values(NARRATIVE_STEPS);
        steps.forEach(step => {
            const stepEl = document.getElementById(step);
            if (stepEl) {
                if (step === stepId) {
                    stepEl.classList.remove('narrative-step--hidden');
                    stepEl.classList.add('narrative-step--active');
                } else {
                    stepEl.classList.remove('narrative-step--active');
                    stepEl.classList.add('narrative-step--hidden');
                }
            }
        });
    }

    /**
     * Show loading state
     */
    function showLoading(message) {
        const loadingEl = document.getElementById('narrative-loading');
        const loadingTextEl = document.getElementById('narrative-loading-text');
        
        if (loadingEl) {
            loadingEl.classList.remove('hidden');
            if (loadingTextEl) loadingTextEl.textContent = message || 'Loading...';
        }
        
        // Hide all steps
        Object.values(NARRATIVE_STEPS).forEach(step => {
            const stepEl = document.getElementById(step);
            if (stepEl) stepEl.classList.add('narrative-step--hidden');
        });
    }

    /**
     * Hide loading state
     */
    function hideLoading() {
        const loadingEl = document.getElementById('narrative-loading');
        if (loadingEl) {
            loadingEl.classList.add('hidden');
        }
    }

    /**
     * Show error state
     */
    function showError(message) {
        const errorEl = document.getElementById('narrative-error');
        const errorTextEl = document.getElementById('narrative-error-text');
        
        if (errorEl) {
            errorEl.classList.remove('hidden');
            if (errorTextEl) errorTextEl.textContent = message || 'An error occurred';
        }
        
        hideLoading();
    }

    /**
     * Hide error state
     */
    function hideError() {
        const errorEl = document.getElementById('narrative-error');
        if (errorEl) {
            errorEl.classList.add('hidden');
        }
    }

    /**
     * Check if panel is hidden
     */
    function isPanelHidden() {
        const panel = document.getElementById(NARRATIVE_PANEL_ID);
        return panel ? panel.classList.contains('hidden') : true;
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initNarrativeTool);
    } else {
        initNarrativeTool();
    }

    // Export for external use
    window.narrativeTool = {
        open: openNarrativePanel,
        close: closeNarrativePanel
    };

})();
