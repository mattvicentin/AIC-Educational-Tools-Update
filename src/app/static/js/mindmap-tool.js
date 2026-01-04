/**
 * Mind Map Tool Handler
 * Manages the mind map panel, generation, and display flow
 */

(function() {
    'use strict';

    const MINDMAP_PANEL_ID = 'mindmap-panel';
    const MINDMAP_STEPS = {
        CONFIG: 'mindmap-step-config',
        DISPLAY: 'mindmap-step-display'
    };

    let currentMindMap = null;
    let chatId = null;
    let tooltipElement = null;

    /**
     * Initialize mind map tool
     */
    function initMindMapTool() {
        // Get chat ID from URL or data attribute
        const chatMatch = window.location.pathname.match(/\/chat\/(\d+)/);
        chatId = chatMatch ? parseInt(chatMatch[1]) : null;
        
        if (!chatId) {
            const chatContainer = document.querySelector('.chat-container');
            chatId = chatContainer ? parseInt(chatContainer.dataset.chatId) : null;
        }

        if (!chatId) {
            console.warn('Mind Map tool: Could not determine chat ID');
            return;
        }

        // Setup event listeners
        setupEventListeners();
        
        // Setup context mode change handler
        const contextModeSelect = document.getElementById('mindmap-context-mode');
        if (contextModeSelect) {
            contextModeSelect.addEventListener('change', handleContextModeChange);
        }

        // Create tooltip element
        tooltipElement = document.getElementById('mindmap-tooltip');
        if (!tooltipElement) {
            tooltipElement = document.createElement('div');
            tooltipElement.id = 'mindmap-tooltip';
            tooltipElement.className = 'mindmap-tooltip hidden';
            document.body.appendChild(tooltipElement);
        }
    }

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // Close button
        const closeBtn = document.getElementById('mindmap-panel-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', closeMindMapPanel);
        }

        // Config form submit
        const configForm = document.getElementById('mindmap-config-form');
        if (configForm) {
            configForm.addEventListener('submit', handleConfigSubmit);
        }

        // Size buttons
        const sizeButtons = document.querySelectorAll('.mindmap-size-btn');
        sizeButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const size = btn.getAttribute('data-size');
                handleSizeSelection(size);
            });
        });

        // Library add button
        const libraryAddBtn = document.getElementById('mindmap-library-add-btn');
        if (libraryAddBtn) {
            libraryAddBtn.addEventListener('click', openLibraryUpload);
        }

        // Library file input
        const libraryFileInput = document.getElementById('mindmap-library-file-input');
        if (libraryFileInput) {
            libraryFileInput.addEventListener('change', handleMindMapLibraryUpload);
        }

        // Display actions
        const retryBtn = document.getElementById('mindmap-retry-btn');
        const sendToChatBtn = document.getElementById('mindmap-send-to-chat-btn');
        if (retryBtn) retryBtn.addEventListener('click', resetMindMap);
        if (sendToChatBtn) sendToChatBtn.addEventListener('click', sendToChat);

        // Error retry
        const errorRetryBtn = document.getElementById('mindmap-error-retry');
        if (errorRetryBtn) {
            errorRetryBtn.addEventListener('click', () => {
                hideError();
                showStep(MINDMAP_STEPS.CONFIG);
            });
        }

        // Close on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !isPanelHidden()) {
                closeMindMapPanel();
            }
        });

        // Close on backdrop click
        const backdrop = document.getElementById('mindmap-panel-backdrop');
        if (backdrop) {
            backdrop.addEventListener('click', (e) => {
                if (e.target === backdrop) {
                    closeMindMapPanel();
                }
            });
        }
    }

    /**
     * Handle size selection
     */
    function handleSizeSelection(size) {
        // Update button active states
        const buttons = document.querySelectorAll('.mindmap-size-btn');
        buttons.forEach(btn => {
            if (btn.getAttribute('data-size') === size) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // Update hidden input
        const hiddenInput = document.getElementById('mindmap-size');
        if (hiddenInput) {
            hiddenInput.value = size;
        }
    }

    /**
     * Handle context mode change
     */
    async function handleContextModeChange() {
        const contextMode = document.getElementById('mindmap-context-mode')?.value;
        const librarySection = document.getElementById('mindmap-library-section');
        
        if (!librarySection) return;

        if (contextMode === 'library' || contextMode === 'both') {
            librarySection.classList.remove('mindmap-config-field--hidden');
            await loadLibraryDocuments();
        } else {
            librarySection.classList.add('mindmap-config-field--hidden');
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
        const emptyEl = document.getElementById('mindmap-library-empty');
        const listEl = document.getElementById('mindmap-library-list');
        
        if (emptyEl) emptyEl.classList.remove('hidden');
        if (listEl) listEl.classList.add('hidden');
    }

    /**
     * Show library document list
     */
    function showLibraryList(documents) {
        const emptyEl = document.getElementById('mindmap-library-empty');
        const listEl = document.getElementById('mindmap-library-list');
        
        if (emptyEl) emptyEl.classList.add('hidden');
        if (listEl) {
            listEl.classList.remove('hidden');
            listEl.innerHTML = '';
            
            documents.forEach(doc => {
                const item = document.createElement('div');
                item.className = 'mindmap-library-item';
                
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.id = `mindmap-doc-${doc.id}`;
                checkbox.value = doc.id;
                checkbox.name = 'library_doc_ids';
                
                const label = document.createElement('label');
                label.className = 'mindmap-library-item-label';
                label.htmlFor = `mindmap-doc-${doc.id}`;
                label.textContent = doc.name;
                
                const meta = document.createElement('span');
                meta.className = 'mindmap-library-item-meta';
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
        const fileInput = document.getElementById('mindmap-library-file-input');
        if (fileInput) {
            fileInput.click();
        }
    }

    /**
     * Handle file upload for mind map panel
     */
    async function handleMindMapLibraryUpload(event) {
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

        const statusDiv = document.getElementById('mindmap-library-upload-status');
        
        if (statusDiv) {
            statusDiv.classList.remove('hidden');
            statusDiv.textContent = 'Uploading...';
            statusDiv.className = 'mindmap-library-upload-status';
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
                        statusDiv.className = 'mindmap-library-upload-status mindmap-library-upload-status--error';
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
                statusDiv.className = 'mindmap-library-upload-status mindmap-library-upload-status--success';
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
                statusDiv.className = 'mindmap-library-upload-status mindmap-library-upload-status--error';
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
        const contextMode = formData.get('context_mode');
        const size = formData.get('size') || 'medium';
        const instructions = formData.get('instructions') || '';
        
        // Get selected library documents
        const libraryDocIds = [];
        if (contextMode === 'library' || contextMode === 'both') {
            const checkboxes = document.querySelectorAll('#mindmap-library-list input[type="checkbox"]:checked');
            checkboxes.forEach(cb => libraryDocIds.push(parseInt(cb.value)));
            
            if (contextMode === 'library' && libraryDocIds.length === 0) {
                showError('Please select at least one library document');
                return;
            }
        }

        // Show loading
        showLoading('Generating mind map...');

        try {
            const response = await fetch('/api/mindmap/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    chat_id: chatId,
                    context_mode: contextMode,
                    size: size,
                    library_doc_ids: libraryDocIds,
                    instructions: instructions
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to generate mind map');
            }

            if (!data.success) {
                throw new Error(data.error || 'Mind map generation failed');
            }

            // Store mind map and display
            currentMindMap = data.mind_map;
            renderMindMap(currentMindMap.mind_map_data);
            showStep(MINDMAP_STEPS.DISPLAY);
            
        } catch (error) {
            console.error('Mind map generation error:', error);
            showError(error.message || 'Failed to generate mind map. Please try again.');
        }
    }

    /**
     * Render mind map visualization
     */
    function renderMindMap(mindMapData) {
        const container = document.getElementById('mindmap-display-container');
        if (!container) return;

        container.innerHTML = '';
        
        // Create SVG for connections
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('class', 'mindmap-visualization');
        svg.style.position = 'absolute';
        svg.style.top = '0';
        svg.style.left = '0';
        svg.style.width = '100%';
        svg.style.height = '100%';
        svg.style.pointerEvents = 'none';
        container.appendChild(svg);

        const root = mindMapData.root;
        if (!root) return;

        // Get container dimensions (account for padding)
        const containerRect = container.getBoundingClientRect();
        const containerWidth = container.offsetWidth || 800;
        const containerHeight = container.offsetHeight || 500;
        const padding = 60; // Padding from edges
        const availableWidth = containerWidth - (padding * 2);
        const availableHeight = containerHeight - (padding * 2);
        const centerX = containerWidth / 2;
        const centerY = containerHeight / 2;

        // Create temporary container for measuring all nodes first
        // Append to container to ensure same styling context
        const tempContainer = document.createElement('div');
        tempContainer.style.position = 'absolute';
        tempContainer.style.visibility = 'hidden';
        tempContainer.style.pointerEvents = 'none';
        tempContainer.style.top = '0';
        tempContainer.style.left = '0';
        tempContainer.style.width = containerWidth + 'px';
        tempContainer.style.height = containerHeight + 'px';
        container.appendChild(tempContainer);

        // Measure all nodes first
        const nodeSizes = new Map();
        const rootNode = createNode(root, 'root', 0, 0);
        tempContainer.appendChild(rootNode);
        // Force layout calculation
        void rootNode.offsetWidth;
        nodeSizes.set('root', { 
            width: Math.max(rootNode.offsetWidth || 150, 120), 
            height: Math.max(rootNode.offsetHeight || 50, 40)
        });
        tempContainer.removeChild(rootNode);

        const nodes = mindMapData.nodes || [];
        
        // Collect all nodes and measure them
        nodes.forEach(node => {
            const nodeEl = createNode(node, 'branch', 0, 0);
            tempContainer.appendChild(nodeEl);
            // Force layout calculation
            void nodeEl.offsetWidth;
            const width = Math.max(nodeEl.offsetWidth || 120, 100);
            const height = Math.max(nodeEl.offsetHeight || 40, 35);
            nodeSizes.set(node.id, { width, height });
            tempContainer.removeChild(nodeEl);
            
            // Measure children
            if (node.children) {
                node.children.forEach(child => {
                    const childEl = createNode(child, 'sub', 0, 0);
                    tempContainer.appendChild(childEl);
                    // Force layout calculation
                    void childEl.offsetWidth;
                    const childWidth = Math.max(childEl.offsetWidth || 100, 80);
                    const childHeight = Math.max(childEl.offsetHeight || 35, 30);
                    nodeSizes.set(child.id, { width: childWidth, height: childHeight });
                    tempContainer.removeChild(childEl);
                });
            }
        });
        
        container.removeChild(tempContainer);

        // Render root node at center (ensure it's within bounds)
        const rootSize = nodeSizes.get('root');
        const rootX = Math.max(padding + rootSize.width / 2, Math.min(centerX, containerWidth - padding - rootSize.width / 2));
        const rootY = Math.max(padding + rootSize.height / 2, Math.min(centerY, containerHeight - padding - rootSize.height / 2));
        rootNode.style.left = `${rootX}px`;
        rootNode.style.top = `${rootY}px`;
        container.appendChild(rootNode);
        
        // Update center position if root was adjusted
        const actualCenterX = rootX;
        const actualCenterY = rootY;

        // Store node positions for collision detection
        const nodePositions = new Map();
        nodePositions.set('root', { x: actualCenterX, y: actualCenterY });

        // Render branch nodes - distribute evenly to left and right sides
        const primaryBranches = nodes.filter(n => n.parent === 'root');
        
        // Count total nodes to estimate space needed
        let totalChildren = 0;
        primaryBranches.forEach(branch => {
            if (branch.children) totalChildren += branch.children.length;
        });
        
        // Calculate maximum vertical space needed
        const maxBranchesOnSide = Math.ceil(primaryBranches.length / 2);
        const maxChildrenPerBranch = Math.max(...primaryBranches.map(b => (b.children || []).length), 0);
        
        // Calculate optimal spacing to fit within container
        const maxVerticalSpace = availableHeight - rootSize.height;
        const verticalSpacing = Math.min(120, maxVerticalSpace / Math.max(maxBranchesOnSide + maxChildrenPerBranch, 1));
        
        // Calculate horizontal offset - ensure it fits with children
        const maxDepth = 2; // Primary + children (can extend to grandchildren)
        const estimatedMaxWidth = availableWidth / (maxDepth + 1);
        const horizontalOffset = Math.min(availableWidth * 0.25, estimatedMaxWidth);
        
        // Split branches between left and right sides
        const leftBranches = [];
        const rightBranches = [];
        primaryBranches.forEach((node, index) => {
            if (index % 2 === 0) {
                leftBranches.push(node);
            } else {
                rightBranches.push(node);
            }
        });
        
        // Position left branches
        const leftStartY = actualCenterY - ((leftBranches.length - 1) * verticalSpacing) / 2;
        leftBranches.forEach((node, index) => {
            const nodeSize = nodeSizes.get(node.id) || { width: 120, height: 40 };
            let y = leftStartY + (index * verticalSpacing);
            let x = actualCenterX - horizontalOffset;
            
            // Ensure node fits within boundaries
            y = Math.max(padding + nodeSize.height / 2, Math.min(y, containerHeight - padding - nodeSize.height / 2));
            x = Math.max(padding + nodeSize.width / 2, x);
            
            // Check for collisions and adjust if needed
            let finalX = x;
            let finalY = y;
            let attempts = 0;
            const maxAttempts = 20;
            
            while (attempts < maxAttempts) {
                let hasCollision = false;
                for (const [nodeId, pos] of nodePositions.entries()) {
                    const existingSize = nodeSizes.get(nodeId) || { width: 100, height: 40 };
                    const distance = Math.sqrt(Math.pow(finalX - pos.x, 2) + Math.pow(finalY - pos.y, 2));
                    const minDistance = (nodeSize.width / 2) + (existingSize.width / 2) + 40;
                    
                    if (distance < minDistance) {
                        hasCollision = true;
                        // Try moving left, but ensure it stays within bounds
                        const newX = finalX - 25;
                        if (newX >= padding + nodeSize.width / 2) {
                            finalX = newX;
                        } else {
                            // If can't move left, try vertical adjustment
                            finalY += (index % 2 === 0 ? -15 : 15);
                            finalY = Math.max(padding + nodeSize.height / 2, Math.min(finalY, containerHeight - padding - nodeSize.height / 2));
                        }
                        break;
                    }
                }
                
                if (!hasCollision) break;
                attempts++;
            }
            
            // Final boundary check
            finalX = Math.max(padding + nodeSize.width / 2, finalX);
            finalY = Math.max(padding + nodeSize.height / 2, Math.min(finalY, containerHeight - padding - nodeSize.height / 2));
            
            // Create and position node
            const nodeEl = createNode(node, 'branch', finalX, finalY);
            container.appendChild(nodeEl);
            nodePositions.set(node.id, { x: finalX, y: finalY });
            
            // Draw connection line from root to branch
            drawConnection(svg, actualCenterX, actualCenterY, finalX, finalY);
            
            // Render children extending further left
            if (node.children && node.children.length > 0) {
                // Calculate child spacing to fit within boundaries
                const maxChildSpacing = Math.max(0, finalX - padding - nodeSize.width / 2);
                const childSpacing = Math.min(140, maxChildSpacing);
                renderChildren(node.children, node.id, finalX, finalY, nodePositions, nodeSizes, svg, container, childSpacing, -1, containerWidth, containerHeight, padding); // -1 = left direction
            }
        });
        
        // Position right branches
        const rightStartY = actualCenterY - ((rightBranches.length - 1) * verticalSpacing) / 2;
        rightBranches.forEach((node, index) => {
            const nodeSize = nodeSizes.get(node.id) || { width: 120, height: 40 };
            let y = rightStartY + (index * verticalSpacing);
            let x = actualCenterX + horizontalOffset;
            
            // Ensure node fits within boundaries
            y = Math.max(padding + nodeSize.height / 2, Math.min(y, containerHeight - padding - nodeSize.height / 2));
            x = Math.min(containerWidth - padding - nodeSize.width / 2, x);
            
            // Check for collisions and adjust if needed
            let finalX = x;
            let finalY = y;
            let attempts = 0;
            const maxAttempts = 20;
            
            while (attempts < maxAttempts) {
                let hasCollision = false;
                for (const [nodeId, pos] of nodePositions.entries()) {
                    const existingSize = nodeSizes.get(nodeId) || { width: 100, height: 40 };
                    const distance = Math.sqrt(Math.pow(finalX - pos.x, 2) + Math.pow(finalY - pos.y, 2));
                    const minDistance = (nodeSize.width / 2) + (existingSize.width / 2) + 40;
                    
                    if (distance < minDistance) {
                        hasCollision = true;
                        // Try moving right, but ensure it stays within bounds
                        const newX = finalX + 25;
                        if (newX <= containerWidth - padding - nodeSize.width / 2) {
                            finalX = newX;
                        } else {
                            // If can't move right, try vertical adjustment
                            finalY += (index % 2 === 0 ? -15 : 15);
                            finalY = Math.max(padding + nodeSize.height / 2, Math.min(finalY, containerHeight - padding - nodeSize.height / 2));
                        }
                        break;
                    }
                }
                
                if (!hasCollision) break;
                attempts++;
            }
            
            // Final boundary check
            finalX = Math.min(containerWidth - padding - nodeSize.width / 2, finalX);
            finalY = Math.max(padding + nodeSize.height / 2, Math.min(finalY, containerHeight - padding - nodeSize.height / 2));
            
            // Create and position node
            const nodeEl = createNode(node, 'branch', finalX, finalY);
            container.appendChild(nodeEl);
            nodePositions.set(node.id, { x: finalX, y: finalY });
            
            // Draw connection line from root to branch
            drawConnection(svg, actualCenterX, actualCenterY, finalX, finalY);
            
            // Render children extending further right
            if (node.children && node.children.length > 0) {
                // Calculate child spacing to fit within boundaries
                const maxChildSpacing = Math.max(0, containerWidth - padding - finalX - nodeSize.width / 2);
                const childSpacing = Math.min(140, maxChildSpacing);
                renderChildren(node.children, node.id, finalX, finalY, nodePositions, nodeSizes, svg, container, childSpacing, 1, containerWidth, containerHeight, padding); // 1 = right direction
            }
        });

        // Initialize Lucide icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    /**
     * Render child nodes recursively with collision detection and boundary checking
     * direction: -1 for left, 1 for right
     */
    function renderChildren(children, parentId, parentX, parentY, nodePositions, nodeSizes, svg, container, childSpacing, direction, containerWidth, containerHeight, padding) {
        if (!children || children.length === 0) return;

        // Calculate vertical spacing for children - ensure they fit vertically
        const availableVerticalSpace = containerHeight - (padding * 2);
        const verticalSpacing = Math.min(90, availableVerticalSpace / Math.max(children.length, 1));
        const startY = parentY - ((children.length - 1) * verticalSpacing) / 2;
        
        children.forEach((child, index) => {
            const childSize = nodeSizes.get(child.id) || { width: 100, height: 35 };
            let y = startY + (index * verticalSpacing);
            let x = parentX + (direction * childSpacing); // Extend in the same direction as parent
            
            // Ensure node fits within boundaries
            y = Math.max(padding + childSize.height / 2, Math.min(y, containerHeight - padding - childSize.height / 2));
            if (direction === -1) {
                x = Math.max(padding + childSize.width / 2, x);
            } else {
                x = Math.min(containerWidth - padding - childSize.width / 2, x);
            }
            
            // Check for collisions and adjust if needed
            let finalX = x;
            let finalY = y;
            let attempts = 0;
            const maxAttempts = 20;
            
            while (attempts < maxAttempts) {
                let hasCollision = false;
                for (const [nodeId, pos] of nodePositions.entries()) {
                    const existingSize = nodeSizes.get(nodeId) || { width: 100, height: 40 };
                    const distance = Math.sqrt(Math.pow(finalX - pos.x, 2) + Math.pow(finalY - pos.y, 2));
                    const minDistance = (childSize.width / 2) + (existingSize.width / 2) + 35;
                    
                    if (distance < minDistance) {
                        hasCollision = true;
                        // Adjust position - move further in direction or adjust vertically
                        if (attempts % 2 === 0) {
                            const newX = finalX + (direction * 20);
                            // Check if new position is within bounds
                            if (direction === -1 && newX >= padding + childSize.width / 2) {
                                finalX = newX;
                            } else if (direction === 1 && newX <= containerWidth - padding - childSize.width / 2) {
                                finalX = newX;
                            } else {
                                // Can't move further, try vertical adjustment
                                finalY += (index % 2 === 0 ? -12 : 12);
                                finalY = Math.max(padding + childSize.height / 2, Math.min(finalY, containerHeight - padding - childSize.height / 2));
                            }
                        } else {
                            finalY += (index % 2 === 0 ? -12 : 12);
                            finalY = Math.max(padding + childSize.height / 2, Math.min(finalY, containerHeight - padding - childSize.height / 2));
                        }
                        break;
                    }
                }
                
                if (!hasCollision) break;
                attempts++;
            }
            
            // Final boundary check
            if (direction === -1) {
                finalX = Math.max(padding + childSize.width / 2, finalX);
            } else {
                finalX = Math.min(containerWidth - padding - childSize.width / 2, finalX);
            }
            finalY = Math.max(padding + childSize.height / 2, Math.min(finalY, containerHeight - padding - childSize.height / 2));
            
            // Create and position node
            const nodeEl = createNode(child, 'sub', finalX, finalY);
            container.appendChild(nodeEl);
            nodePositions.set(child.id, { x: finalX, y: finalY });
            
            // Draw connection line from parent to child
            drawConnection(svg, parentX, parentY, finalX, finalY);
            
            // Render grandchildren if any, continuing in same direction
            if (child.children && child.children.length > 0) {
                // Calculate spacing to fit within boundaries
                let maxGrandchildSpacing;
                if (direction === -1) {
                    maxGrandchildSpacing = Math.max(0, finalX - padding - childSize.width / 2);
                } else {
                    maxGrandchildSpacing = Math.max(0, containerWidth - padding - finalX - childSize.width / 2);
                }
                const grandchildSpacing = Math.min(120, maxGrandchildSpacing);
                renderChildren(child.children, child.id, finalX, finalY, nodePositions, nodeSizes, svg, container, grandchildSpacing, direction, containerWidth, containerHeight, padding);
            }
        });
    }

    /**
     * Create a node element
     */
    function createNode(nodeData, type, x, y) {
        const node = document.createElement('div');
        node.className = `mindmap-node-${type}`;
        node.textContent = nodeData.label;
        node.dataset.nodeId = nodeData.id;
        node.dataset.explanation = nodeData.explanation || '';
        
        // Position absolutely
        node.style.position = 'absolute';
        node.style.left = `${x}px`;
        node.style.top = `${y}px`;
        node.style.transform = 'translate(-50%, -50%)';
        
        // Add hover event listeners for tooltip
        node.addEventListener('mouseenter', (e) => showTooltip(e, nodeData.explanation));
        node.addEventListener('mouseleave', hideTooltip);
        node.addEventListener('mousemove', (e) => updateTooltipPosition(e));
        
        return node;
    }

    /**
     * Draw connection line between nodes
     */
    function drawConnection(svg, x1, y1, x2, y2) {
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', x1);
        line.setAttribute('y1', y1);
        line.setAttribute('x2', x2);
        line.setAttribute('y2', y2);
        line.setAttribute('class', 'mindmap-connection');
        svg.appendChild(line);
    }

    /**
     * Show tooltip with explanation
     */
    function showTooltip(event, explanation) {
        if (!tooltipElement || !explanation) return;
        
        tooltipElement.textContent = explanation;
        tooltipElement.classList.remove('hidden');
        updateTooltipPosition(event);
    }

    /**
     * Update tooltip position
     */
    function updateTooltipPosition(event) {
        if (!tooltipElement || tooltipElement.classList.contains('hidden')) return;
        
        const offset = 10;
        tooltipElement.style.left = `${event.pageX + offset}px`;
        tooltipElement.style.top = `${event.pageY + offset}px`;
    }

    /**
     * Hide tooltip
     */
    function hideTooltip() {
        if (tooltipElement) {
            tooltipElement.classList.add('hidden');
        }
    }

    /**
     * Send mind map to chat
     */
    async function sendToChat() {
        if (!currentMindMap || !chatId) {
            console.error('Cannot send mind map: missing mind map or chatId');
            return;
        }

        // Build structured text representation
        let mindMapText = `**Mind Map: ${currentMindMap.mind_map_data.root.label}**\n\n`;
        mindMapText += `Generated from ${currentMindMap.context_mode} context (${currentMindMap.size} size).\n\n`;
        
        // Add root
        mindMapText += `**Root:** ${currentMindMap.mind_map_data.root.label}\n`;
        if (currentMindMap.mind_map_data.root.explanation) {
            mindMapText += `*${currentMindMap.mind_map_data.root.explanation}*\n\n`;
        }
        
        // Add branches
        const nodes = currentMindMap.mind_map_data.nodes || [];
        nodes.forEach((node, index) => {
            mindMapText += `**Branch ${index + 1}:** ${node.label}\n`;
            if (node.explanation) {
                mindMapText += `*${node.explanation}*\n`;
            }
            
            // Add children
            if (node.children && node.children.length > 0) {
                node.children.forEach((child, childIndex) => {
                    mindMapText += `  - ${child.label}`;
                    if (child.explanation) {
                        mindMapText += `: ${child.explanation}`;
                    }
                    mindMapText += '\n';
                });
            }
            mindMapText += '\n';
        });

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
                    'content': mindMapText,
                    'ai_response': '0',
                    'csrf_token': csrfToken
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || 'Failed to send message to chat');
            }

            // Success - close panel and refresh messages
            closeMindMapPanel();
            
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
            console.error('Failed to send mind map to chat:', error);
            // Don't show alert, just log the error
        }
    }

    /**
     * Get CSRF token from meta tag or form
     */
    function getCsrfToken() {
        // Try meta tag first
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            return metaTag.getAttribute('content');
        }
        
        // Try form input
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
     * Open mind map panel
     */
    function openMindMapPanel() {
        const panel = document.getElementById(MINDMAP_PANEL_ID);
        const backdrop = document.getElementById('mindmap-panel-backdrop');
        if (!panel) {
            console.error('Mind map panel not found');
            return;
        }

        // Show backdrop first
        if (backdrop) {
            backdrop.classList.remove('hidden');
        }
        
        // Then show panel
        panel.classList.remove('hidden');
        showStep(MINDMAP_STEPS.CONFIG);
        resetMindMap();
        
        // Load library documents if needed
        handleContextModeChange();
        
        // Initialize Lucide icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    /**
     * Close mind map panel
     */
    function closeMindMapPanel() {
        const panel = document.getElementById(MINDMAP_PANEL_ID);
        const backdrop = document.getElementById('mindmap-panel-backdrop');
        
        if (panel) {
            panel.classList.add('hidden');
        }
        
        // Hide backdrop
        if (backdrop) {
            backdrop.classList.add('hidden');
        }
        
        resetMindMap();
    }

    /**
     * Check if panel is hidden
     */
    function isPanelHidden() {
        const panel = document.getElementById(MINDMAP_PANEL_ID);
        return !panel || panel.classList.contains('hidden');
    }

    /**
     * Show a specific step
     */
    function showStep(stepId) {
        Object.values(MINDMAP_STEPS).forEach(step => {
            const stepEl = document.getElementById(step);
            if (stepEl) {
                stepEl.classList.remove('mindmap-step--active');
                stepEl.classList.add('mindmap-step--hidden');
            }
        });

        const targetStep = document.getElementById(stepId);
        if (targetStep) {
            targetStep.classList.remove('mindmap-step--hidden');
            targetStep.classList.add('mindmap-step--active');
        }

        hideLoading();
        hideError();
    }

    /**
     * Reset mind map
     */
    function resetMindMap() {
        currentMindMap = null;
        
        const configForm = document.getElementById('mindmap-config-form');
        if (configForm) {
            configForm.reset();
            const sizeInput = document.getElementById('mindmap-size');
            if (sizeInput) sizeInput.value = 'medium';
        }
        
        // Reset size selection
        handleSizeSelection('medium');
        
        // Reset library section
        const librarySection = document.getElementById('mindmap-library-section');
        if (librarySection) {
            librarySection.classList.add('mindmap-config-field--hidden');
        }

        // Reset context mode
        const contextModeSelect = document.getElementById('mindmap-context-mode');
        if (contextModeSelect) {
            contextModeSelect.value = 'chat';
        }

        // Clear library list
        const libraryList = document.getElementById('mindmap-library-list');
        if (libraryList) {
            libraryList.innerHTML = '';
            libraryList.classList.add('hidden');
        }
        const libraryEmpty = document.getElementById('mindmap-library-empty');
        if (libraryEmpty) {
            libraryEmpty.classList.remove('hidden');
        }

        // Clear display
        const displayContainer = document.getElementById('mindmap-display-container');
        if (displayContainer) {
            displayContainer.innerHTML = '';
        }

        // Switch back to config step
        showStep(MINDMAP_STEPS.CONFIG);
        hideError();
        hideLoading();
    }

    /**
     * Show loading state
     */
    function showLoading(text = 'Loading...') {
        const loadingEl = document.getElementById('mindmap-loading');
        const loadingText = document.getElementById('mindmap-loading-text');
        
        if (loadingEl) loadingEl.classList.remove('hidden');
        if (loadingText) loadingText.textContent = text;
    }

    /**
     * Hide loading state
     */
    function hideLoading() {
        const loadingEl = document.getElementById('mindmap-loading');
        if (loadingEl) loadingEl.classList.add('hidden');
    }

    /**
     * Show error
     */
    function showError(message) {
        const errorEl = document.getElementById('mindmap-error');
        const errorText = document.getElementById('mindmap-error-text');
        
        if (errorEl) errorEl.classList.remove('hidden');
        if (errorText) errorText.textContent = message;
        
        hideLoading();
    }

    /**
     * Hide error
     */
    function hideError() {
        const errorEl = document.getElementById('mindmap-error');
        if (errorEl) errorEl.classList.add('hidden');
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initMindMapTool);
    } else {
        initMindMapTool();
    }

    // Export for external use
    window.mindMapTool = {
        open: openMindMapPanel,
        close: closeMindMapPanel
    };

})();
