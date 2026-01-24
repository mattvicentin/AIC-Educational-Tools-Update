/**
 * Mind Map Tool Handler
 * Manages the mind map panel, generation, and display flow
 */

console.log('[Mind Map] Script loading...');

(function() {
    'use strict';

    console.log('[Mind Map] IIFE executing...');

    // Export stub immediately to ensure it's always available
    // This will be replaced with real functions once they're defined
    window.mindMapTool = {
        open: function() {
            console.warn('[Mind Map] Tool functions not yet initialized, retrying...');
            // Try to call the real function if it exists now
            if (typeof openMindMapPanel === 'function') {
                openMindMapPanel();
            } else {
                console.error('[Mind Map] openMindMapPanel function still not available');
            }
        },
        close: function() {
            if (typeof closeMindMapPanel === 'function') {
                closeMindMapPanel();
            }
        }
    };
    console.log('[Mind Map] Initial stub exported', window.mindMapTool);

    const MINDMAP_PANEL_ID = 'mindmap-panel';
    const MINDMAP_STEPS = {
        CONFIG: 'mindmap-step-config',
        DISPLAY: 'mindmap-step-display'
    };

    let currentMindMap = null;
    let chatId = null;
    let tooltipElement = null;
    
    // Edit Mode is always enabled (View Mode removed)
    let editMode = true;
    let originalPositions = new Map(); // Store original ELK positions
    let customPositions = new Map(); // Store user-modified positions
    let manualConnections = []; // Store manually created connections
    let originalConnections = []; // Store original hierarchical connections
    let contentEdits = new Map(); // Store edited node content
    let isConnecting = false; // Track connection drawing state
    let connectionSource = null; // Track source node for connection
    let connectionSourceAnchor = null; // Track source anchor side
    let connectionPreviewLine = null; // Preview line element during connection drawing
    let draggedNode = null; // Currently dragged node
    let dragOffset = { x: 0, y: 0 }; // Offset for dragging
    let layoutTransform = { scale: 1, tx: 0, ty: 0 }; // World transform for layout fit
    let layoutPadding = 20; // Layout padding inside viewport

    function screenToWorld(x, y) {
        const scale = layoutTransform.scale || 1;
        return {
            x: (x - layoutTransform.tx) / scale,
            y: (y - layoutTransform.ty) / scale
        };
    }

    function worldToScreen(x, y) {
        const scale = layoutTransform.scale || 1;
        return {
            x: (x * scale) + layoutTransform.tx,
            y: (y * scale) + layoutTransform.ty
        };
    }

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
            console.warn('Mind Map tool: Could not determine chat ID, but tool is still available');
            // Don't return - allow initialization to continue so the tool can still be opened
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
        const exportBtn = document.getElementById('mindmap-export-btn');
        if (retryBtn) retryBtn.addEventListener('click', resetMindMap);
        if (sendToChatBtn) sendToChatBtn.addEventListener('click', sendToChat);
        if (exportBtn) exportBtn.addEventListener('click', exportMindMap);

        // Reset layout button
        const resetLayoutBtn = document.getElementById('mindmap-reset-layout-btn');
        if (resetLayoutBtn) resetLayoutBtn.addEventListener('click', handleResetLayout);
        
        // Initialize Edit Mode features (always enabled)
        initializeEditMode();

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
            try {
                await renderMindMap(currentMindMap.mind_map_data);
                showStep(MINDMAP_STEPS.DISPLAY);
                // Initialize Edit Mode after rendering
                initializeEditMode();
            } catch (renderError) {
                console.error('Mind map rendering error:', renderError);
                showError('Failed to render mind map: ' + renderError.message);
            }
            
        } catch (error) {
            console.error('Mind map generation error:', error);
            showError(error.message || 'Failed to generate mind map. Please try again.');
        }
    }

    /**
     * Render mind map visualization using deterministic mind map layout
     */
    async function renderMindMap(mindMapData) {
        const container = document.getElementById('mindmap-display-container');
        if (!container) return;

        container.innerHTML = '';
        
        const root = mindMapData.root;
        if (!root) return;

        // Get container dimensions
        const containerWidth = container.offsetWidth || 800;
        const containerHeight = container.offsetHeight || 500;
        const computedStyle = getComputedStyle(container);
        const paddingLeft = parseFloat(computedStyle.paddingLeft) || 0;
        const paddingRight = parseFloat(computedStyle.paddingRight) || 0;
        const paddingTop = parseFloat(computedStyle.paddingTop) || 0;
        const paddingBottom = parseFloat(computedStyle.paddingBottom) || 0;
        // Increased padding to prevent nodes from being cut off
        const padding = Math.max(paddingLeft, paddingRight, paddingTop, paddingBottom, 40);
        layoutPadding = padding;
        
        // Get size from current mind map to adjust scaling
        const size = currentMindMap?.size || 'medium';
        const sizeMultipliers = {
            'small': 1.4,   // 40% larger than fit for small
            'medium': 1.5,  // 50% larger than fit for medium
            'large': 1.6    // 60% larger than fit for large
        };
        const sizeMultiplier = sizeMultipliers[size] || 1.5;
        
        // Build viewport/world layers (single transform)
        const viewport = document.createElement('div');
        viewport.id = 'mindmap-viewport';
        viewport.style.position = 'relative';
        viewport.style.width = '100%';
        viewport.style.height = '100%';
        viewport.style.overflow = 'hidden';
        container.appendChild(viewport);

        const world = document.createElement('div');
        world.id = 'mindmap-world';
        world.style.position = 'absolute';
        world.style.left = '0';
        world.style.top = '0';
        world.style.transformOrigin = '0 0';
        viewport.appendChild(world);

        const worldSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        worldSvg.id = 'mindmap-edges';
        worldSvg.style.position = 'absolute';
        worldSvg.style.left = '0';
        worldSvg.style.top = '0';
        worldSvg.style.pointerEvents = 'none';
        worldSvg.style.overflow = 'visible';
        world.appendChild(worldSvg);

        const nodesContainer = document.createElement('div');
        nodesContainer.id = 'mindmap-nodes';
        nodesContainer.style.position = 'absolute';
        nodesContainer.style.left = '0';
        nodesContainer.style.top = '0';
        world.appendChild(nodesContainer);

        // Measure all nodes first
        const tempContainer = document.createElement('div');
        tempContainer.style.position = 'absolute';
        tempContainer.style.visibility = 'hidden';
        tempContainer.style.pointerEvents = 'none';
        tempContainer.style.top = '0';
        tempContainer.style.left = '0';
        tempContainer.style.width = containerWidth + 'px';
        tempContainer.style.height = containerHeight + 'px';
        container.appendChild(tempContainer);

        const nodeSizes = new Map();
        const nodeTypes = new Map();
        
        // Measure root
        const rootNode = createNode(root, 'root', 0, 0);
        tempContainer.appendChild(rootNode);
        void rootNode.offsetWidth;
        nodeSizes.set('root', { 
            width: Math.max(rootNode.offsetWidth || 150, 120), 
            height: Math.max(rootNode.offsetHeight || 50, 40)
        });
        nodeTypes.set('root', 'root');
        tempContainer.removeChild(rootNode);

        // Measure all other nodes
        const nodes = mindMapData.nodes || [];
        const branchNodes = nodes.length > 0 ? nodes : (root.children || []);
        
        function measureNode(node, type) {
            if (nodeSizes.has(node.id)) return;
            
            const nodeEl = createNode(node, type, 0, 0);
            tempContainer.appendChild(nodeEl);
            void nodeEl.offsetWidth;
            const width = Math.max(nodeEl.offsetWidth || 120, 100);
            const height = Math.max(nodeEl.offsetHeight || 40, 35);
            nodeSizes.set(node.id, { width, height });
            nodeTypes.set(node.id, type);
            tempContainer.removeChild(nodeEl);
            
            if (node.children) {
                node.children.forEach(child => {
                    measureNode(child, 'sub');
                });
            }
        }
        
        branchNodes.forEach(node => measureNode(node, 'branch'));
        container.removeChild(tempContainer);

        // Determine top-level branches
        let primaryBranches = nodes.filter(n => n.parent === 'root');
        if (primaryBranches.length === 0) {
            primaryBranches = nodes.length > 0 ? nodes : (root.children || []);
        }

        // Compute spacing based on node sizes
        let maxWidth = 120;
        let maxHeight = 40;
        nodeSizes.forEach(size => {
            maxWidth = Math.max(maxWidth, size.width);
            maxHeight = Math.max(maxHeight, size.height);
        });
        const horizontalGap = Math.max(60, maxWidth * 0.6);
        const levelGap = Math.max(140, maxHeight * 2.2);

        const subtreeWidths = new Map();
        function computeSubtreeWidth(node) {
            if (subtreeWidths.has(node.id)) return subtreeWidths.get(node.id);
            const size = nodeSizes.get(node.id) || { width: 120, height: 40 };
            const children = node.children || [];
            if (children.length === 0) {
                subtreeWidths.set(node.id, size.width);
                return size.width;
            }
            let totalChildren = 0;
            children.forEach(child => {
                totalChildren += computeSubtreeWidth(child);
            });
            totalChildren += horizontalGap * (children.length - 1);
            const total = Math.max(size.width, totalChildren);
            subtreeWidths.set(node.id, total);
            return total;
        }

        const nodePositions = new Map();
        const nodeElements = new Map();

        // Root will be positioned after we calculate the layout bounds
        // We'll center it vertically based on the total layout height
        nodePositions.set('root', { x: 0, y: 0 });

        function layoutSubtree(node, centerX, depth) {
            const y = depth * levelGap;
            nodePositions.set(node.id, { x: centerX, y });

            const children = node.children || [];
            if (children.length === 0) return;

            let totalWidth = 0;
            children.forEach(child => {
                totalWidth += computeSubtreeWidth(child);
            });
            totalWidth += horizontalGap * (children.length - 1);

            let cursorX = centerX - (totalWidth / 2);
            children.forEach(child => {
                const childWidth = computeSubtreeWidth(child);
                const childCenterX = cursorX + (childWidth / 2);
                layoutSubtree(child, childCenterX, depth + 1);
                cursorX += childWidth + horizontalGap;
            });
        }

        if (primaryBranches.length > 0) {
            let totalWidth = 0;
            primaryBranches.forEach(child => {
                totalWidth += computeSubtreeWidth(child);
            });
            totalWidth += horizontalGap * (primaryBranches.length - 1);
            // Center the primary branches horizontally around the root (x=0)
            let cursorX = -totalWidth / 2;
            primaryBranches.forEach(child => {
                const childWidth = computeSubtreeWidth(child);
                const childCenterX = cursorX + (childWidth / 2);
                layoutSubtree(child, childCenterX, 1);
                cursorX += childWidth + horizontalGap;
            });
        }

        // Removed expandHorizontalToFill() to preserve horizontal centering of primary branches
        // The primary branches are already centered around the root (x=0)

        // Calculate layout bounds to determine centering (both horizontal and vertical)
        const tempBounds = computeLayoutBounds(nodePositions, nodeSizes);
        const layoutCenterX = (tempBounds.minX + tempBounds.maxX) / 2;
        const layoutCenterY = (tempBounds.minY + tempBounds.maxY) / 2;
        
        // Shift all nodes so the layout center is at (0, 0)
        // This ensures the layout is centered both horizontally and vertically in world space
        for (const [nodeId, pos] of nodePositions.entries()) {
            pos.x = pos.x - layoutCenterX;
            pos.y = pos.y - layoutCenterY;
        }

        function renderTree(node, depth) {
            const pos = nodePositions.get(node.id);
            if (!pos) return;
            const type = depth === 1 ? 'branch' : 'sub';
            const nodeEl = createNode(node, type, pos.x, pos.y);
            nodesContainer.appendChild(nodeEl);
            nodeElements.set(node.id, nodeEl);
            if (node.children) {
                node.children.forEach(child => renderTree(child, depth + 1));
            }
        }

        // Render root first
        const rootPos = nodePositions.get('root');
        if (rootPos) {
            const rootEl = createNode(root, 'root', rootPos.x, rootPos.y);
            nodesContainer.appendChild(rootEl);
            nodeElements.set('root', rootEl);
        }

        // Then render primary branches
        primaryBranches.forEach(node => renderTree(node, 1));

        // Reset edit data on new render
        customPositions.clear();
        manualConnections = [];
        contentEdits.clear();
        originalConnections = [];

        // Store original positions
        originalPositions.clear();
        for (const [nodeId, pos] of nodePositions.entries()) {
            originalPositions.set(nodeId, { x: pos.x, y: pos.y });
        }

        // Store original connections data structure (for reference, but don't render lines)
        function storeConnectionData(nodeData, parentId = 'root') {
            if (nodeData.children) {
                nodeData.children.forEach(child => {
                    const parentPos = nodePositions.get(parentId);
                    const childPos = nodePositions.get(child.id);
                    
                    if (parentPos && childPos) {
                        const downwards = childPos.y >= parentPos.y;
                        originalConnections.push({
                            id: `orig-${parentId}-${child.id}`,
                            source: parentId,
                            sourceAnchor: downwards ? 'bottom' : 'top',
                            target: child.id,
                            targetAnchor: downwards ? 'top' : 'bottom',
                            isManual: false
                        });
                    }
                    
                    storeConnectionData(child, child.id);
                });
            }
        }
        
        storeConnectionData(root);
        primaryBranches.forEach(node => storeConnectionData(node, node.id));

        // Fit world to viewport
        const bounds = computeLayoutBounds(nodePositions, nodeSizes);
        applyWorldTransform(world, worldSvg, bounds, containerWidth, containerHeight, padding, sizeMultiplier);

        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    function computeLayoutBounds(nodePositions, nodeSizes) {
        let minX = Infinity;
        let maxX = -Infinity;
        let minY = Infinity;
        let maxY = -Infinity;
        for (const [nodeId, pos] of nodePositions.entries()) {
            const size = nodeSizes.get(nodeId) || { width: 120, height: 40 };
            const halfW = size.width / 2;
            const halfH = size.height / 2;
            minX = Math.min(minX, pos.x - halfW);
            maxX = Math.max(maxX, pos.x + halfW);
            minY = Math.min(minY, pos.y - halfH);
            maxY = Math.max(maxY, pos.y + halfH);
        }
        if (!isFinite(minX) || !isFinite(maxX)) {
            minX = 0;
            maxX = 1;
        }
        if (!isFinite(minY) || !isFinite(maxY)) {
            minY = 0;
            maxY = 1;
        }
        return {
            minX,
            maxX,
            minY,
            maxY,
            width: Math.max(1, maxX - minX),
            height: Math.max(1, maxY - minY)
        };
    }

    function applyWorldTransform(worldEl, svgEl, bounds, containerWidth, containerHeight, padding, sizeMultiplier = 1.5) {
        // Calculate scale to fit, then apply multiplier
        const availableW = Math.max(1, containerWidth - (padding * 2));
        const availableH = Math.max(1, containerHeight - (padding * 2));
        let scale = Math.min(availableW / bounds.width, availableH / bounds.height);
        if (!isFinite(scale) || scale <= 0) scale = 1;
        
        // Apply size multiplier (can be > 1.0 to fill more space)
        scale = scale * sizeMultiplier;

        // Calculate center of bounds
        const centerX = (bounds.minX + bounds.maxX) / 2;
        const centerY = (bounds.minY + bounds.maxY) / 2;
        
        // Calculate translation to center the scaled layout
        // Account for the scaled center point to ensure proper centering
        const scaledCenterX = centerX * scale;
        const scaledCenterY = centerY * scale;
        
        // Shift significantly more to the right by offsetting the center calculation
        // Use a larger offset to move the map more to the right
        const rightwardOffset = containerWidth * 0.15; // 15% shift to the right
        let tx = (containerWidth / 2) - scaledCenterX + rightwardOffset;
        let ty = (containerHeight / 2) - scaledCenterY;
        
        // Ensure we don't shift too far left (prevent cutoff)
        // Calculate the leftmost point after scaling
        const scaledLeft = (bounds.minX * scale) + tx;
        const scaledRight = (bounds.maxX * scale) + tx;
        const scaledTop = (bounds.minY * scale) + ty;
        const scaledBottom = (bounds.maxY * scale) + ty;
        
        // Adjust translation if nodes would be cut off
        const minMargin = 20; // Minimum margin from edges
        if (scaledLeft < minMargin) {
            // Shift right to prevent left cutoff
            const adjustment = minMargin - scaledLeft;
            tx += adjustment;
        }
        if (scaledRight > containerWidth - minMargin) {
            // Shift left to prevent right cutoff
            const adjustment = (containerWidth - minMargin) - scaledRight;
            tx += adjustment;
        }
        if (scaledTop < minMargin) {
            // Shift down to prevent top cutoff
            const adjustment = minMargin - scaledTop;
            ty += adjustment;
        }
        if (scaledBottom > containerHeight - minMargin) {
            // Shift up to prevent bottom cutoff
            const adjustment = (containerHeight - minMargin) - scaledBottom;
            ty += adjustment;
        }

        worldEl.style.transform = `translate(${tx}px, ${ty}px) scale(${scale})`;
        layoutTransform = { scale, tx, ty };

        if (svgEl) {
            svgEl.setAttribute('viewBox', `${bounds.minX} ${bounds.minY} ${bounds.width} ${bounds.height}`);
            svgEl.setAttribute('width', bounds.width.toString());
            svgEl.setAttribute('height', bounds.height.toString());
        }
    }

    /**
     * Simple fallback layout when ELK fails
     */
    function renderSimpleLayout(mindMapData, nodeSizes, nodeTypes, container, svg, containerWidth, containerHeight, padding, nodes) {
        const root = mindMapData.root;
        const centerX = containerWidth / 2;
        const centerY = containerHeight / 2;
        
        // Render root
        const rootEl = createNode(root, 'root', centerX, centerY);
        container.appendChild(rootEl);
        
        // Simple two-sided layout
        const primaryBranches = nodes.filter(n => n.parent === 'root');
        const horizontalSpacing = 200;
        const verticalSpacing = 100;
        
        primaryBranches.forEach((node, index) => {
            const side = index % 2 === 0 ? -1 : 1;
            const x = centerX + (side * horizontalSpacing);
            const y = centerY + ((Math.floor(index / 2) - (primaryBranches.length - 1) / 4) * verticalSpacing);
            
            const nodeEl = createNode(node, 'branch', x, y);
            container.appendChild(nodeEl);
            
            // Draw connection
            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            const dx = Math.max(40, Math.abs(x - centerX) * 0.35);
            path.setAttribute('d',
                `M ${centerX} ${centerY} ` +
                `C ${centerX + dx * side} ${centerY}, ` +
                `${x - dx * side} ${y}, ` +
                `${x} ${y}`
            );
            path.setAttribute('fill', 'none');
            path.setAttribute('stroke', '#93c5fd');
            path.setAttribute('stroke-width', '2');
            path.setAttribute('class', 'mindmap-connection');
            svg.appendChild(path);
            
            // Render children
            if (node.children) {
                node.children.forEach((child, childIndex) => {
                    const childX = x + (side * horizontalSpacing * 0.7);
                    const childY = y + ((childIndex - (node.children.length - 1) / 2) * verticalSpacing * 0.8);
                    const childEl = createNode(child, 'sub', childX, childY);
                    container.appendChild(childEl);
                    
                    // Draw child connection
                    const childPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                    const childDx = Math.max(30, Math.abs(childX - x) * 0.3);
                    childPath.setAttribute('d',
                        `M ${x} ${y} ` +
                        `C ${x + childDx * side} ${y}, ` +
                        `${childX - childDx * side} ${childY}, ` +
                        `${childX} ${childY}`
                    );
                    childPath.setAttribute('fill', 'none');
                    childPath.setAttribute('stroke', '#93c5fd');
                    childPath.setAttribute('stroke-width', '2');
                    childPath.setAttribute('class', 'mindmap-connection');
                    svg.appendChild(childPath);
                });
            }
        });
        
        // Initialize Lucide icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    /**
     * Convert mind map data structure to ELK graph format for one side
     */
    function convertToElkGraphSide(mindMapData, nodeSizes, sideBranches, direction) {
        const nodeMap = new Map();
        
        // Create ELK node
        function createElkNode(nodeData) {
            if (nodeMap.has(nodeData.id)) return nodeMap.get(nodeData.id);
            
            const elkNode = {
                id: nodeData.id,
                width: nodeSizes.get(nodeData.id)?.width || 120,
                height: nodeSizes.get(nodeData.id)?.height || 40,
                children: []
            };
            nodeMap.set(nodeData.id, elkNode);
            return elkNode;
        }
        
        // Build hierarchical structure
        function buildHierarchy(nodeData) {
            const elkNode = createElkNode(nodeData);
            
            if (nodeData.children && nodeData.children.length > 0) {
                nodeData.children.forEach(childData => {
                    const childElkNode = buildHierarchy(childData);
                    elkNode.children.push(childElkNode);
                });
            }
            
            return elkNode;
        }
        
        // Build ELK nodes for all branches on this side
        const elkBranches = sideBranches.map(branch => buildHierarchy(branch));
        
        return {
            id: 'side-root',
            children: elkBranches,
            layoutOptions: {
                'elk.algorithm': 'layered',
                'elk.direction': direction,
                'elk.spacing.nodeNode': '60',
                'elk.spacing.edgeNode': '40',
                'elk.layered.spacing.nodeNodeBetweenLayers': '120',
                'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLE',
                'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP',
            }
        };
    }

    /**
     * Get node center coordinates
     */
    function getNodeCenter(n) {
        return { cx: n.x + n.width / 2, cy: n.y + n.height / 2 };
    }

    /**
     * Compute root-anchored offset to center root in viewport
     */
    function computeRootAnchoredOffset(rootNode, viewportW, viewportH) {
        const { cx, cy } = getNodeCenter(rootNode);
        return {
            dx: (viewportW / 2) - cx,
            dy: (viewportH / 2) - cy
        };
    }

    /**
     * Get anchor point on right side of node
     */
    function anchorRight(n) {
        return { x: n.x + n.width, y: n.y + n.height / 2 };
    }

    /**
     * Get anchor point on left side of node
     */
    function anchorLeft(n) {
        return { x: n.x, y: n.y + n.height / 2 };
    }

    /**
     * Create bezier path between two points
     */
    function bezierPath(p, c) {
        const dx = Math.max(60, Math.abs(c.x - p.x) * 0.35);
        const side = c.x >= p.x ? 1 : -1;
        return `M ${p.x} ${p.y} C ${p.x + dx * side} ${p.y}, ${c.x - dx * side} ${c.y}, ${c.x} ${c.y}`;
    }

    /**
     * Calculate bounding box of ELK graph
     */
    function calculateBounds(node) {
        let minX = node.x || 0;
        let maxX = (node.x || 0) + (node.width || 0);
        let minY = node.y || 0;
        let maxY = (node.y || 0) + (node.height || 0);
        
        function traverse(n) {
            if (n.x !== undefined) {
                minX = Math.min(minX, n.x);
                maxX = Math.max(maxX, n.x + (n.width || 0));
            }
            if (n.y !== undefined) {
                minY = Math.min(minY, n.y);
                maxY = Math.max(maxY, n.y + (n.height || 0));
            }
            if (n.children) {
                n.children.forEach(child => traverse(child));
            }
        }
        
        if (node.children) {
            node.children.forEach(child => traverse(child));
        }
        
        return {
            x: minX,
            y: minY,
            width: maxX - minX,
            height: maxY - minY
        };
    }

    /**
     * Resolve collisions by pushing overlapping nodes apart
     * Implements a relaxation pass as recommended by GPT
     * Checks both vertical and horizontal overlaps
     */
    function resolveCollisions(nodePositions, nodeSizes, containerWidth, containerHeight, padding) {
        const minSpacing = 20; // Minimum space between node edges
        const maxIterations = 10;
        
        for (let iteration = 0; iteration < maxIterations; iteration++) {
            let hasCollisions = false;
            
            // Check all pairs of nodes for collisions
            const nodeIds = Array.from(nodePositions.keys());
            
            for (let i = 0; i < nodeIds.length; i++) {
                for (let j = i + 1; j < nodeIds.length; j++) {
                    const nodeId1 = nodeIds[i];
                    const nodeId2 = nodeIds[j];
                    const pos1 = nodePositions.get(nodeId1);
                    const pos2 = nodePositions.get(nodeId2);
                    const size1 = nodeSizes.get(nodeId1) || { width: 120, height: 40 };
                    const size2 = nodeSizes.get(nodeId2) || { width: 120, height: 40 };
                    
                    if (!pos1 || !pos2) continue;
                    
                    // Skip root node collisions (it's centered)
                    if (nodeId1 === 'root' || nodeId2 === 'root') continue;
                    
                    // Calculate distances
                    const distanceX = Math.abs(pos1.x - pos2.x);
                    const distanceY = Math.abs(pos1.y - pos2.y);
                    const minDistanceX = (size1.width / 2) + (size2.width / 2) + minSpacing;
                    const minDistanceY = (size1.height / 2) + (size2.height / 2) + minSpacing;
                    
                    // Check if nodes overlap
                    if (distanceX < minDistanceX && distanceY < minDistanceY) {
                        hasCollisions = true;
                        
                        // Calculate overlap amounts
                        const overlapX = minDistanceX - distanceX;
                        const overlapY = minDistanceY - distanceY;
                        
                        // Determine push direction based on relative positions
                        const pushX = overlapX / 2;
                        const pushY = overlapY / 2;
                        
                        // Determine which direction to push (away from each other)
                        const dirX = pos1.x < pos2.x ? -1 : 1;
                        const dirY = pos1.y < pos2.y ? -1 : 1;
                        
                        // Calculate new positions
                        let newX1 = pos1.x + (dirX * pushX);
                        let newY1 = pos1.y + (dirY * pushY);
                        let newX2 = pos2.x - (dirX * pushX);
                        let newY2 = pos2.y - (dirY * pushY);
                        
                        // Ensure nodes stay within bounds
                        const finalX1 = Math.max(
                            padding + size1.width / 2,
                            Math.min(newX1, containerWidth - padding - size1.width / 2)
                        );
                        const finalY1 = Math.max(
                            padding + size1.height / 2,
                            Math.min(newY1, containerHeight - padding - size1.height / 2)
                        );
                        const finalX2 = Math.max(
                            padding + size2.width / 2,
                            Math.min(newX2, containerWidth - padding - size2.width / 2)
                        );
                        const finalY2 = Math.max(
                            padding + size2.height / 2,
                            Math.min(newY2, containerHeight - padding - size2.height / 2)
                        );
                        
                        // Update positions
                        nodePositions.set(nodeId1, { x: finalX1, y: finalY1 });
                        nodePositions.set(nodeId2, { x: finalX2, y: finalY2 });
                        
                        // Update DOM
                        const el1 = document.querySelector(`[data-node-id="${nodeId1}"]`);
                        const el2 = document.querySelector(`[data-node-id="${nodeId2}"]`);
                        if (el1) {
                            el1.style.left = `${finalX1}px`;
                            el1.style.top = `${finalY1}px`;
                        }
                        if (el2) {
                            el2.style.left = `${finalX2}px`;
                            el2.style.top = `${finalY2}px`;
                        }
                    }
                }
            }
            
            if (!hasCollisions) break;
        }
    }

    /**
     * Center the entire mind map by computing bounding box of all nodes
     * This ensures the root stays centered even if the map is unbalanced
     */
    function centerMindMapByBoundingBox(nodePositions, containerWidth, containerHeight, padding) {
        if (nodePositions.size === 0) return;
        
        // Find bounding box of all nodes (accounting for actual node sizes)
        let minX = Infinity, maxX = -Infinity;
        let minY = Infinity, maxY = -Infinity;
        
        for (const [nodeId, pos] of nodePositions.entries()) {
            const nodeEl = document.querySelector(`[data-node-id="${nodeId}"]`);
            if (nodeEl) {
                const nodeWidth = nodeEl.offsetWidth || 120;
                const nodeHeight = nodeEl.offsetHeight || 40;
                // Account for node size when calculating bounds
                minX = Math.min(minX, pos.x - nodeWidth / 2);
                maxX = Math.max(maxX, pos.x + nodeWidth / 2);
                minY = Math.min(minY, pos.y - nodeHeight / 2);
                maxY = Math.max(maxY, pos.y + nodeHeight / 2);
            } else {
                // Fallback
                minX = Math.min(minX, pos.x);
                maxX = Math.max(maxX, pos.x);
                minY = Math.min(minY, pos.y);
                maxY = Math.max(maxY, pos.y);
            }
        }
        
        // Calculate center of current layout
        const currentCenterX = (minX + maxX) / 2;
        const currentCenterY = (minY + maxY) / 2;
        
        // Calculate desired center
        const desiredCenterX = containerWidth / 2;
        const desiredCenterY = containerHeight / 2;
        
        // Calculate offset needed
        const offsetX = desiredCenterX - currentCenterX;
        const offsetY = desiredCenterY - currentCenterY;
        
        // Apply offset to all nodes
        const adjustedPositions = new Map();
        for (const [nodeId, pos] of nodePositions.entries()) {
            const nodeEl = document.querySelector(`[data-node-id="${nodeId}"]`);
            if (nodeEl) {
                const newX = pos.x + offsetX;
                const newY = pos.y + offsetY;
                
                // Get node dimensions
                const nodeWidth = nodeEl.offsetWidth || 120;
                const nodeHeight = nodeEl.offsetHeight || 40;
                
                // Ensure node stays within bounds
                const finalX = Math.max(
                    padding + nodeWidth / 2,
                    Math.min(newX, containerWidth - padding - nodeWidth / 2)
                );
                const finalY = Math.max(
                    padding + nodeHeight / 2,
                    Math.min(newY, containerHeight - padding - nodeHeight / 2)
                );
                
                nodeEl.style.left = `${finalX}px`;
                nodeEl.style.top = `${finalY}px`;
                adjustedPositions.set(nodeId, { x: finalX, y: finalY });
            }
        }
        
        // Update positions map
        nodePositions.clear();
        for (const [nodeId, pos] of adjustedPositions.entries()) {
            nodePositions.set(nodeId, pos);
        }
    }

    // Align nodePositions with rendered DOM centers
    function syncPositionsWithDom(nodePositions, container) {
        const containerRect = container.getBoundingClientRect();
        const updated = new Map();
        for (const [nodeId] of nodePositions.entries()) {
            const el = container.querySelector(`[data-node-id="${nodeId}"]`);
            if (!el) continue;
            const rect = el.getBoundingClientRect();
            updated.set(nodeId, {
                x: rect.left - containerRect.left + rect.width / 2,
                y: rect.top - containerRect.top + rect.height / 2
            });
        }
        nodePositions.clear();
        for (const [id, pos] of updated.entries()) {
            nodePositions.set(id, pos);
        }
    }

    // Draw all connections with bezier paths
    function drawAllConnections(svg, mindMapData, nodePositions, container) {
        const rootPos = nodePositions.get('root');
        if (!rootPos) return;
        const nodes = mindMapData.nodes || [];

        // Helper to get DOM rect info
        function getRect(nodeId) {
            const el = container.querySelector(`[data-node-id="${nodeId}"]`);
            if (!el) return null;
            const cRect = container.getBoundingClientRect();
            const r = el.getBoundingClientRect();
            return {
                left: r.left - cRect.left,
                right: r.right - cRect.left,
                top: r.top - cRect.top,
                bottom: r.bottom - cRect.top,
                cx: r.left - cRect.left + r.width / 2,
                cy: r.top - cRect.top + r.height / 2
            };
        }

        function drawEdge(parentId, childId) {
            const p = getRect(parentId);
            const c = getRect(childId);
            if (!p || !c) return;
            const side = c.cx >= p.cx ? 1 : -1;
            const parentAnchor = side === 1 ? { x: p.right, y: p.cy } : { x: p.left, y: p.cy };
            const childAnchor = side === 1 ? { x: c.left, y: c.cy } : { x: c.right, y: c.cy };
            const dx = Math.max(40, Math.abs(childAnchor.x - parentAnchor.x) * 0.35);
            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('d', `M ${parentAnchor.x} ${parentAnchor.y} C ${parentAnchor.x + dx * side} ${parentAnchor.y}, ${childAnchor.x - dx * side} ${childAnchor.y}, ${childAnchor.x} ${childAnchor.y}`);
            path.setAttribute('fill', 'none');
            path.setAttribute('stroke', '#93c5fd');
            path.setAttribute('stroke-width', '2');
            path.setAttribute('class', 'mindmap-connection');
            svg.appendChild(path);
        }

        nodes.filter(n => n.parent === 'root').forEach(node => {
            drawEdge('root', node.id);
            drawChildEdges(node);
        });

        function drawChildEdges(parentNode) {
            if (!parentNode.children) return;
            parentNode.children.forEach(child => {
                drawEdge(parentNode.id, child.id);
                drawChildEdges(child);
            });
        }
    }

    /**
     * Redraw all connections after nodes are repositioned
     */
    function redrawConnections(svg, mindMapData, nodePositions) {
        const rootPos = nodePositions.get('root');
        if (!rootPos) return;
        
        const nodes = mindMapData.nodes || [];
        
        // Draw connections from root to primary branches
        nodes.filter(n => n.parent === 'root').forEach(node => {
            const nodePos = nodePositions.get(node.id);
            if (nodePos) {
                drawConnection(svg, rootPos.x, rootPos.y, nodePos.x, nodePos.y);
                
                // Draw connections to children recursively
                drawChildConnections(svg, node, nodePos, nodePositions);
            }
        });
    }

    /**
     * Recursively draw connections for children
     */
    function drawChildConnections(svg, parentNode, parentPos, nodePositions) {
        if (!parentNode.children || parentNode.children.length === 0) return;
        
        parentNode.children.forEach(child => {
            const childPos = nodePositions.get(child.id);
            if (childPos) {
                drawConnection(svg, parentPos.x, parentPos.y, childPos.x, childPos.y);
                // Recursively draw grandchildren
                drawChildConnections(svg, child, childPos, nodePositions);
            }
        });
    }

    /**
     * Create a node element
     */
    function createNode(nodeData, type, x, y) {
        const node = document.createElement('div');
        node.className = `mindmap-node-${type}`;
        
        // Apply content edits if any
        const displayLabel = contentEdits.get(nodeData.id) || nodeData.label;
        node.textContent = displayLabel;
        node.dataset.nodeId = nodeData.id;
        node.dataset.explanation = nodeData.explanation || '';
        node.dataset.editable = 'true';
        
        // Position absolutely - check for custom position first
        const nodeId = nodeData.id;
        const customPos = customPositions.get(nodeId);
        const finalX = customPos ? customPos.x : x;
        const finalY = customPos ? customPos.y : y;
        
        node.style.position = 'absolute';
        node.style.left = `${finalX}px`;
        node.style.top = `${finalY}px`;
        node.style.transform = 'translate(-50%, -50%)';
        
        // Add hover event listeners for Edit Mode features
        node.addEventListener('mouseenter', (e) => {
            // Show anchors and delete button
            showConnectionAnchors(node);
            showDeleteButton(node);
            // Show tooltip with explanation if available
            const explanation = node.dataset.explanation;
            if (explanation) {
                showTooltip(e, explanation);
            }
        });
        node.addEventListener('mouseleave', (e) => {
            hideConnectionAnchors(node);
            hideDeleteButton(node);
            // Hide tooltip
            hideTooltip();
        });
        // Update tooltip position on mouse move
        node.addEventListener('mousemove', (e) => {
            const explanation = node.dataset.explanation;
            if (explanation && tooltipElement && !tooltipElement.classList.contains('hidden')) {
                updateTooltipPosition(e);
            }
        });
        
        // Add anchor points (hidden by default)
        addConnectionAnchors(node);
        
        return node;
    }

    /**
     * Add connection anchors to a node
     */
    function addConnectionAnchors(node) {
        const anchors = ['left', 'right', 'top', 'bottom'];
        anchors.forEach(side => {
            const anchor = document.createElement('div');
            anchor.className = 'mindmap-anchor';
            anchor.dataset.anchorSide = side;
            anchor.dataset.nodeId = node.getAttribute('data-node-id');
            anchor.setAttribute('aria-label', `Connect from ${side} side`);
            node.appendChild(anchor);
        });
    }

    /**
     * Show connection anchors on node hover
     */
    function showConnectionAnchors(node) {
        if (isConnecting) return;
        keepAnchorsVisible(node);
    }

    /**
     * Hide connection anchors
     */
    function hideConnectionAnchors(node) {
        if (isConnecting) return; // Keep visible while connecting
        const anchors = node.querySelectorAll('.mindmap-anchor');
        anchors.forEach(anchor => {
            anchor.classList.remove('mindmap-anchor--visible');
            anchor.removeEventListener('click', handleAnchorClick);
        });
    }

    /**
     * Ensure anchors stay visible and attached to their node
     */
    function keepAnchorsVisible(nodeOrId) {
        const node = typeof nodeOrId === 'string'
            ? document.querySelector(`[data-node-id="${nodeOrId}"]`)
            : nodeOrId;
        if (!node) return;
        const anchors = node.querySelectorAll('.mindmap-anchor');
        anchors.forEach(anchor => {
            anchor.classList.add('mindmap-anchor--visible');
            anchor.removeEventListener('click', handleAnchorClick);
            anchor.addEventListener('click', handleAnchorClick);
        });
    }

    /**
     * Get anchor position in SVG coordinate system
     * Gets the actual rendered position of the anchor element and converts to SVG coordinates
     */
    function getAnchorPosition(nodeId, anchorSide) {
        const container = document.getElementById('mindmap-display-container');
        if (!container) return null;
        
        const node = container.querySelector(`[data-node-id="${nodeId}"]`);
        if (!node) return null;
        
        // Get the SVG element for coordinate transformation
        const svg = document.getElementById('mindmap-edges');
        if (!svg) return null;
        
        // Get the actual anchor element if it exists
        const anchor = node.querySelector(`[data-anchor-side="${anchorSide}"]`);
        
        // Get bounding rects - these account for all CSS transforms
        const elementRect = anchor ? anchor.getBoundingClientRect() : node.getBoundingClientRect();
        
        // Calculate the point we want to connect to
        let viewportX, viewportY;
        
        if (anchor) {
            // Use anchor center
            viewportX = elementRect.left + elementRect.width / 2;
            viewportY = elementRect.top + elementRect.height / 2;
        } else {
            // Fallback: calculate from node edges
            const nodeRect = node.getBoundingClientRect();
            const nodeCenterX = nodeRect.left + nodeRect.width / 2;
            const nodeCenterY = nodeRect.top + nodeRect.height / 2;
            
            switch(anchorSide) {
                case 'left':
                    viewportX = nodeRect.left;
                    viewportY = nodeCenterY;
                    break;
                case 'right':
                    viewportX = nodeRect.right;
                    viewportY = nodeCenterY;
                    break;
                case 'top':
                    viewportX = nodeCenterX;
                    viewportY = nodeRect.top;
                    break;
                case 'bottom':
                    viewportX = nodeCenterX;
                    viewportY = nodeRect.bottom;
                    break;
                default:
                    viewportX = nodeCenterX;
                    viewportY = nodeCenterY;
            }
        }
        
        // Convert viewport coordinates to SVG coordinates using SVG's built-in transformation
        // This properly handles all CSS transforms on both the SVG and the DOM elements
        try {
            const svgPoint = svg.createSVGPoint();
            svgPoint.x = viewportX;
            svgPoint.y = viewportY;
            
            // Get the inverse of the screen CTM to convert from screen to SVG coordinates
            const ctm = svg.getScreenCTM();
            if (!ctm) {
                // Fallback to manual calculation if getScreenCTM fails
                return screenToWorld(viewportX - container.getBoundingClientRect().left, 
                                    viewportY - container.getBoundingClientRect().top);
            }
            
            const inverseCTM = ctm.inverse();
            const svgCoords = svgPoint.matrixTransform(inverseCTM);
            
            return { x: svgCoords.x, y: svgCoords.y };
        } catch (e) {
            // Fallback to manual calculation if SVG transformation fails
            console.warn('SVG coordinate transformation failed, using fallback:', e);
            const containerRect = container.getBoundingClientRect();
            return screenToWorld(viewportX - containerRect.left, viewportY - containerRect.top);
        }
    }

    /**
     * Handle anchor click to start connection
     */
    function handleAnchorClick(e) {
        e.stopPropagation();
        
        const anchor = e.currentTarget;
        const nodeId = anchor.getAttribute('data-node-id');
        const anchorSide = anchor.getAttribute('data-anchor-side');
        
        // If already connecting, treat this as the target anchor
        if (isConnecting && connectionSource && nodeId !== connectionSource) {
            completeConnection(nodeId, anchorSide);
            return;
        }
        
        startConnection(nodeId, anchorSide);
    }

    /**
     * Show edit button on node hover
     */
    function showEditButton(node) {
        
        let editBtn = node.querySelector('.mindmap-edit-btn');
        if (!editBtn) {
            editBtn = document.createElement('button');
            editBtn.className = 'mindmap-edit-btn';
            editBtn.setAttribute('aria-label', 'Edit node content');
            editBtn.innerHTML = '<i data-lucide="pencil" class="w-4 h-4"></i>';
            editBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const nodeId = node.getAttribute('data-node-id');
                editNodeContent(nodeId);
            });
            node.appendChild(editBtn);
        }
        editBtn.classList.add('mindmap-edit-btn--visible');
    }

    /**
     * Hide edit button
     */
    function hideEditButton(node) {
        const editBtn = node.querySelector('.mindmap-edit-btn');
        if (editBtn) {
            editBtn.classList.remove('mindmap-edit-btn--visible');
        }
    }

    /**
     * Show delete button on node hover
     */
    function showDeleteButton(node) {
        // Don't allow deleting the root node
        const nodeId = node.getAttribute('data-node-id');
        if (nodeId === 'root') return;
        
        let deleteBtn = node.querySelector('.mindmap-delete-btn');
        if (!deleteBtn) {
            deleteBtn = document.createElement('button');
            deleteBtn.className = 'mindmap-delete-btn';
            deleteBtn.setAttribute('aria-label', 'Delete node');
            deleteBtn.innerHTML = '<i data-lucide="x" class="w-4 h-4"></i>';
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const nodeId = node.getAttribute('data-node-id');
                deleteNode(nodeId);
            });
            node.appendChild(deleteBtn);
        }
        deleteBtn.classList.add('mindmap-delete-btn--visible');
    }

    /**
     * Hide delete button
     */
    function hideDeleteButton(node) {
        const deleteBtn = node.querySelector('.mindmap-delete-btn');
        if (deleteBtn) {
            deleteBtn.classList.remove('mindmap-delete-btn--visible');
        }
    }

    /**
     * Delete a node
     */
    function deleteNode(nodeId) {
        if (nodeId === 'root') {
            alert('Cannot delete the root node');
            return;
        }
        
        if (!confirm('Are you sure you want to delete this node? This will also remove all connections to it.')) {
            return;
        }
        
        const container = document.getElementById('mindmap-display-container');
        if (!container) return;
        
        // Remove node from DOM
        const node = container.querySelector(`[data-node-id="${nodeId}"]`);
        if (node) {
            node.remove();
        }
        
        // Remove all connections involving this node
        manualConnections = manualConnections.filter(conn => 
            conn.source !== nodeId && conn.target !== nodeId
        );
        
        // Remove from custom positions and content edits
        customPositions.delete(nodeId);
        contentEdits.delete(nodeId);
        originalPositions.delete(nodeId);
        
        // Re-render connections to remove deleted ones
        const svg = container.querySelector('#mindmap-edges');
        if (svg && currentMindMap && currentMindMap.mind_map_data) {
            updateConnectionRendering();
        }
        
        // Re-initialize Lucide icons for any remaining buttons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    /**
     * Start connection drawing from an anchor
     */
    function startConnection(nodeId, anchorSide) {
        
        isConnecting = true;
        connectionSource = nodeId;
        connectionSourceAnchor = anchorSide;
        
        // Change cursor
        document.body.style.cursor = 'crosshair';

        // Keep source anchors visible so user can start additional lines without re-hover
        keepAnchorsVisible(nodeId);
        
        // Create preview line
        const container = document.getElementById('mindmap-display-container');
        if (!container) return;
        
        const svg = container.querySelector('#mindmap-edges') || 
                   container.querySelector('.mindmap-visualization');
        if (!svg) return;
        
        connectionPreviewLine = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        connectionPreviewLine.setAttribute('class', 'mindmap-connection-preview');
        connectionPreviewLine.setAttribute('fill', 'none');
        connectionPreviewLine.setAttribute('stroke', '#f59e0b');
        connectionPreviewLine.setAttribute('stroke-width', '2');
        svg.appendChild(connectionPreviewLine);
        
        // Add mouse move and click handlers
        container.addEventListener('mousemove', drawConnectionPreview);
        container.addEventListener('click', handleConnectionTargetClick);
        container.addEventListener('mouseleave', cancelConnectionDrawing);
        
        // Add ESC key handler
        document.addEventListener('keydown', handleConnectionKeyDown);
    }

    /**
     * Draw connection preview line
     */
    function drawConnectionPreview(e) {
        if (!isConnecting || !connectionSource) return;
        
        const container = document.getElementById('mindmap-display-container');
        if (!container || !connectionPreviewLine) return;
        
        const containerRect = container.getBoundingClientRect();
        
        // Get source anchor position using helper function
        const sourceAnchorPos = getAnchorPosition(connectionSource, connectionSourceAnchor);
        if (!sourceAnchorPos) return;
        
        const sourceAnchorX = sourceAnchorPos.x;
        const sourceAnchorY = sourceAnchorPos.y;
        
        // If hovering an anchor (not on the source node), snap to that anchor; otherwise follow the mouse
        const hoveredAnchor = e.target.classList?.contains('mindmap-anchor') ? e.target : null;
        const hoveredNodeId = hoveredAnchor?.getAttribute('data-node-id');
        const mouseScreenX = e.clientX - containerRect.left;
        const mouseScreenY = e.clientY - containerRect.top;
        const mouseWorld = screenToWorld(mouseScreenX, mouseScreenY);
        let targetX = mouseWorld.x;
        let targetY = mouseWorld.y;
        
        if (hoveredAnchor && hoveredNodeId && hoveredNodeId !== connectionSource) {
            const hoverAnchorSide = hoveredAnchor.getAttribute('data-anchor-side');
            const hoverPos = getAnchorPosition(hoveredNodeId, hoverAnchorSide);
            if (hoverPos) {
                targetX = hoverPos.x;
                targetY = hoverPos.y;
            }
        }
        
        // Calculate bezier curve control points
        const side = targetX >= sourceAnchorX ? 1 : -1;
        const dx = Math.max(60, Math.abs(targetX - sourceAnchorX) * 0.35);
        
        const pathData = `M ${sourceAnchorX} ${sourceAnchorY} ` +
            `C ${sourceAnchorX + dx * side} ${sourceAnchorY}, ` +
            `${targetX - dx * side} ${targetY}, ` +
            `${targetX} ${targetY}`;
        
        connectionPreviewLine.setAttribute('d', pathData);
        
        // Highlight valid drop targets
        const targetNode = e.target.closest('[data-node-id]');
        if (targetNode && targetNode.getAttribute('data-node-id') !== connectionSource) {
            targetNode.classList.add('mindmap-node--drop-target');
        } else {
            // Remove highlight from other nodes
            const nodes = container.querySelectorAll('[data-node-id]');
            nodes.forEach(node => {
                if (node.getAttribute('data-node-id') !== connectionSource) {
                    node.classList.remove('mindmap-node--drop-target');
                }
            });
        }
    }

    /**
     * Handle click on target node to complete connection
     */
    function handleConnectionTargetClick(e) {
        if (!isConnecting) return;
        
        // If clicking directly on an anchor, use that anchor as the target
        const targetAnchorEl = e.target.classList?.contains('mindmap-anchor') ? e.target : null;
        const targetNode = targetAnchorEl ? targetAnchorEl.closest('[data-node-id]') : e.target.closest('[data-node-id]');
        if (!targetNode) {
            // Clicked outside, cancel
            cancelConnectionDrawing();
            return;
        }
        
        const targetNodeId = targetNode.getAttribute('data-node-id');
        if (targetNodeId === connectionSource) {
            // Can't connect to self
            cancelConnectionDrawing();
            return;
        }
        
        // Determine target anchor based on relative position from source anchor
        const container = document.getElementById('mindmap-display-container');
        if (!container) {
            cancelConnectionDrawing();
            return;
        }
        
        // Get source anchor position
        const sourceAnchorPos = getAnchorPosition(connectionSource, connectionSourceAnchor);
        if (!sourceAnchorPos) {
            cancelConnectionDrawing();
            return;
        }
        
        // If an anchor was clicked, use that anchor side; otherwise choose closest anchor to the click
        let targetAnchor = targetAnchorEl?.getAttribute('data-anchor-side');
        if (!targetAnchor) {
            const targetRect = targetNode.getBoundingClientRect();
            const containerRect = container.getBoundingClientRect();
            const clickScreenX = e.clientX - containerRect.left;
            const clickScreenY = e.clientY - containerRect.top;
            const clickWorld = screenToWorld(clickScreenX, clickScreenY);
            
            const clickX = clickWorld.x;
            const clickY = clickWorld.y;
            
            // Choose anchor based on closest distance to click point
            const anchorSides = ['left', 'right', 'top', 'bottom'];
            let closestSide = 'left';
            let closestDist = Infinity;
            anchorSides.forEach(side => {
                const pos = getAnchorPosition(targetNodeId, side);
                if (!pos) return;
                const dist = Math.hypot(pos.x - clickX, pos.y - clickY);
                if (dist < closestDist) {
                    closestDist = dist;
                    closestSide = side;
                }
            });
            targetAnchor = closestSide;
        }
        
        completeConnection(targetNodeId, targetAnchor);
    }

    /**
     * Complete connection drawing
     */
    function completeConnection(targetNodeId, targetAnchor) {
        if (!isConnecting || !connectionSource) return;
        
        // Check for duplicate connection
        const isDuplicate = manualConnections.some(conn => 
            conn.source === connectionSource && 
            conn.target === targetNodeId &&
            conn.sourceAnchor === connectionSourceAnchor &&
            conn.targetAnchor === targetAnchor
        );
        
        if (!isDuplicate) {
            // Create new connection
            const connectionId = `manual-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
            manualConnections.push({
                id: connectionId,
                source: connectionSource,
                sourceAnchor: connectionSourceAnchor,
                target: targetNodeId,
                targetAnchor: targetAnchor,
                isManual: true
            });
            
            // Re-render connections
            const container = document.getElementById('mindmap-display-container');
            if (container) {
                const svg = container.querySelector('#mindmap-edges') || 
                           container.querySelector('.mindmap-visualization');
                if (svg) {
                    // Remove preview and re-render all
                    if (connectionPreviewLine && connectionPreviewLine.parentNode) {
                        connectionPreviewLine.parentNode.removeChild(connectionPreviewLine);
                    }
                    updateConnectionRendering();
                }
                // Keep anchors visible on both ends so user can draw again
                keepAnchorsVisible(connectionSource);
                keepAnchorsVisible(targetNodeId);
            }
        }
        
        // Clean up
        cancelConnectionDrawing();
    }

    /**
     * Handle keydown during connection drawing
     */
    function handleConnectionKeyDown(e) {
        if (e.key === 'Escape' && isConnecting) {
            cancelConnectionDrawing();
        }
    }

    /**
     * Delete a manual connection
     */
    function deleteConnection(connectionId) {
        // Edit Mode is always enabled
        
        // Remove from manual connections array
        const index = manualConnections.findIndex(conn => conn.id === connectionId);
        if (index !== -1) {
            manualConnections.splice(index, 1);
            
            // Remove from DOM
            const container = document.getElementById('mindmap-display-container');
            if (container) {
                const svg = container.querySelector('#mindmap-edges') || 
                           container.querySelector('.mindmap-visualization');
                if (svg) {
                    // Remove the path
                    const path = svg.querySelector(`[data-connection-id="${connectionId}"]`);
                    if (path) {
                        path.remove();
                    }
                    // Remove the delete button
                    const deleteBtn = svg.querySelector(`.mindmap-connection-delete[data-connection-id="${connectionId}"]`);
                    if (deleteBtn) {
                        deleteBtn.remove();
                    }
                }
            }
        }
    }

    /**
     * Enable content editing for nodes
     */
    function enableContentEditing() {
        const container = document.getElementById('mindmap-display-container');
        if (!container) return;
        
        const nodes = container.querySelectorAll('[data-node-id][data-editable="true"]');
        nodes.forEach(node => {
            // Add double-click handler
            node.addEventListener('dblclick', (e) => {
                e.stopPropagation();
                const nodeId = node.getAttribute('data-node-id');
                editNodeContent(nodeId);
            });
        });
    }

    /**
     * Disable content editing
     */
    function disableContentEditing() {
        const container = document.getElementById('mindmap-display-container');
        if (!container) return;
        
        const nodes = container.querySelectorAll('[data-node-id]');
        nodes.forEach(node => {
            // Remove double-click handlers (they'll be re-added if needed)
            const newNode = node.cloneNode(true);
            node.parentNode.replaceChild(newNode, node);
        });
    }

    /**
     * Edit node content
     */
    function editNodeContent(nodeId) {
        // Edit Mode is always enabled
        
        const container = document.getElementById('mindmap-display-container');
        if (!container) return;
        
        const node = container.querySelector(`[data-node-id="${nodeId}"]`);
        if (!node) return;
        
        // Get original content
        const originalContent = contentEdits.get(nodeId) || 
                              (currentMindMap && currentMindMap.mind_map_data ? 
                               (currentMindMap.mind_map_data.root.id === nodeId ? 
                                currentMindMap.mind_map_data.root.label :
                                (currentMindMap.mind_map_data.nodes || []).find(n => n.id === nodeId)?.label) : 
                               node.textContent.trim());
        
        // Create input element
        const input = document.createElement('input');
        input.type = 'text';
        input.value = originalContent;
        input.className = 'mindmap-node-editor';
        input.style.position = 'absolute';
        input.style.left = '0';
        input.style.top = '0';
        input.style.width = '100%';
        input.style.height = '100%';
        input.style.border = '2px solid #3b82f6';
        input.style.borderRadius = 'inherit';
        input.style.padding = 'inherit';
        input.style.fontSize = 'inherit';
        input.style.fontWeight = 'inherit';
        input.style.textAlign = 'center';
        input.style.background = 'white';
        input.style.zIndex = '1000';
        
        // Replace node content with input
        const originalText = node.textContent;
        node.textContent = '';
        node.appendChild(input);
        input.focus();
        input.select();
        
        // Handle save
        const saveEdit = () => {
            const newContent = input.value.trim();
            if (newContent && newContent !== originalContent) {
                contentEdits.set(nodeId, newContent);
                node.textContent = newContent;
                // Re-measure node size if needed
                // Node will auto-resize based on content
            } else {
                node.textContent = originalText;
            }
            input.remove();
        };
        
        // Handle cancel
        const cancelEdit = () => {
            node.textContent = originalText;
            input.remove();
        };
        
        input.addEventListener('blur', saveEdit);
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                saveEdit();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                cancelEdit();
            }
        });
    }

    /**
     * Save node content (called from edit handler)
     */
    function saveNodeContent(nodeId, newContent) {
        contentEdits.set(nodeId, newContent);
        
        // Update node display
        const container = document.getElementById('mindmap-display-container');
        if (!container) return;
        
        const node = container.querySelector(`[data-node-id="${nodeId}"]`);
        if (node) {
            node.textContent = newContent;
        }
    }

    /**
     * Reset layout to original state
     */
    function handleResetLayout() {
        if (!confirm('Reset layout to original positions? This will clear all custom positions, manual connections, and content edits.')) {
            return;
        }
        
        resetLayout();
    }

    /**
     * Reset layout to original state
     */
    function resetLayout() {
        const container = document.getElementById('mindmap-display-container');
        if (!container) return;
        
        // Clear custom positions
        customPositions.clear();
        
        // Clear manual connections
        manualConnections = [];
        
        // Clear content edits
        contentEdits.clear();
        
        // Restore original positions
        const nodes = container.querySelectorAll('[data-node-id]');
        nodes.forEach(node => {
            const nodeId = node.getAttribute('data-node-id');
            const originalPos = originalPositions.get(nodeId);
            
            if (originalPos) {
                node.style.left = `${originalPos.x}px`;
                node.style.top = `${originalPos.y}px`;
            }
            
            // Restore original content
            if (currentMindMap && currentMindMap.mind_map_data) {
                const root = currentMindMap.mind_map_data.root;
                const nodesData = currentMindMap.mind_map_data.nodes || [];
                let originalLabel = root.id === nodeId ? root.label : 
                                  nodesData.find(n => n.id === nodeId)?.label ||
                                  nodesData.flatMap(n => n.children || []).find(c => c.id === nodeId)?.label;
                
                if (originalLabel) {
                    node.textContent = originalLabel;
                }
            }
        });
        
        // Re-render connections (only original ones)
        updateConnectionRendering();
        
        // Cancel any ongoing operations
        cancelConnectionDrawing();
    }

    /**
     * Draw connection line between nodes
     */
    function drawConnection(svg, x1, y1, x2, y2) {
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', x1.toString());
        line.setAttribute('y1', y1.toString());
        line.setAttribute('x2', x2.toString());
        line.setAttribute('y2', y2.toString());
        line.setAttribute('stroke', '#93c5fd');
        line.setAttribute('stroke-width', '2');
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
     * Export mind map as image
     */
    async function exportMindMap() {
        if (!currentMindMap) {
            console.error('Cannot export: no mind map available');
            alert('No mind map to export. Please generate a mind map first.');
            return;
        }

        const container = document.getElementById('mindmap-display-container');
        if (!container) {
            console.error('Cannot export: container not found');
            return;
        }

        try {
            // Check if html2canvas is available
            if (typeof html2canvas === 'undefined') {
                // Try to load html2canvas dynamically
                await loadHtml2Canvas();
            }

            if (typeof html2canvas === 'undefined') {
                alert('Export functionality requires html2canvas library. Please contact support.');
                return;
            }

            // Show loading indicator
            const exportBtn = document.getElementById('mindmap-export-btn');
            const originalText = exportBtn ? exportBtn.textContent : 'Export';
            if (exportBtn) {
                exportBtn.disabled = true;
                exportBtn.textContent = 'Exporting...';
            }

            // Capture the container
            const canvas = await html2canvas(container, {
                backgroundColor: '#ffffff',
                scale: 2, // Higher resolution for better quality
                logging: false,
                useCORS: true,
                allowTaint: true,
                width: container.scrollWidth,
                height: container.scrollHeight
            });
            
            // Convert to blob and download
            canvas.toBlob((blob) => {
                if (blob) {
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = `mindmap-${Date.now()}.png`;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    URL.revokeObjectURL(url);
                }
                
                // Restore button
                if (exportBtn) {
                    exportBtn.disabled = false;
                    exportBtn.textContent = originalText;
                }
            }, 'image/png', 0.95); // High quality

        } catch (error) {
            console.error('Failed to export mind map:', error);
            alert('Failed to export mind map. Please try again.');
            
            // Restore button
            const exportBtn = document.getElementById('mindmap-export-btn');
            if (exportBtn) {
                exportBtn.disabled = false;
                exportBtn.textContent = 'Export';
            }
        }
    }

    /**
     * Load html2canvas library dynamically
     */
    function loadHtml2Canvas() {
        return new Promise((resolve, reject) => {
            // Check if already loaded
            if (typeof html2canvas !== 'undefined') {
                resolve();
                return;
            }

            // Try to load from unpkg.com (allowed in CSP)
            const script = document.createElement('script');
            script.src = 'https://unpkg.com/html2canvas@1.4.1/dist/html2canvas.min.js';
            script.onload = resolve;
            script.onerror = () => {
                // Fallback: try alternative CDN
                const fallbackScript = document.createElement('script');
                fallbackScript.src = 'https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js';
                fallbackScript.onload = resolve;
                fallbackScript.onerror = reject;
                document.head.appendChild(fallbackScript);
            };
            document.head.appendChild(script);
        });
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

    // Replace stub with real functions once they're defined
    window.mindMapTool = {
        open: openMindMapPanel,
        close: closeMindMapPanel
    };
    console.log('[Mind Map] Tool functions replaced with real implementations');

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

    /**
     * Initialize Edit Mode (always enabled)
     */
    function initializeEditMode() {
        editMode = true;
        const container = document.getElementById('mindmap-display-container');
        if (!container) return;

        // Always show edit mode styling
        container.classList.add('mindmap-edit-mode');
        
        // Show reset layout button
        const resetLayoutBtn = document.getElementById('mindmap-reset-layout-btn');
        if (resetLayoutBtn) resetLayoutBtn.style.display = 'block';

        // Enable dragging and content editing
        enableDragging();
        enableContentEditing();

        // Re-render connections to show edit controls
        if (currentMindMap && currentMindMap.mind_map_data) {
            updateConnectionRendering();
        }
    }

    /**
     * Cancel connection drawing
     */
    function cancelConnectionDrawing() {
        isConnecting = false;
        connectionSource = null;
        connectionSourceAnchor = null;
        
        if (connectionPreviewLine && connectionPreviewLine.parentNode) {
            connectionPreviewLine.parentNode.removeChild(connectionPreviewLine);
            connectionPreviewLine = null;
        }
        
        document.body.style.cursor = '';
        
        // Remove event listeners
        const container = document.getElementById('mindmap-display-container');
        if (container) {
            container.removeEventListener('mousemove', drawConnectionPreview);
            container.removeEventListener('click', handleConnectionTargetClick);
            container.removeEventListener('mouseleave', cancelConnectionDrawing);
        }
        document.removeEventListener('keydown', handleConnectionKeyDown);
        
        // Remove drop target highlights
        const nodes = container ? container.querySelectorAll('[data-node-id]') : [];
        nodes.forEach(node => node.classList.remove('mindmap-node--drop-target'));

        // Keep anchors visible on the node under the cursor (if any) so user can reconnect quickly
        const hoveredNode = container ? container.querySelector(':hover')?.closest?.('[data-node-id]') : null;
        if (hoveredNode) {
            keepAnchorsVisible(hoveredNode);
        }
    }

    /**
     * Hide all connection anchors
     */
    function hideAllAnchors() {
        const anchors = document.querySelectorAll('.mindmap-anchor');
        anchors.forEach(anchor => anchor.classList.remove('mindmap-anchor--visible'));
    }

    /**
     * Ensure no node overlaps (prevent piling up)
     */
    function ensureNoOverlaps(nodePositions, nodeSizes, nodeElements, containerWidth, containerHeight, padding) {
        const minSpacing = 50; // Minimum space between node edges (increased to prevent piling up)
        const maxIterations = 30; // More iterations to ensure all overlaps are resolved
        
        for (let iteration = 0; iteration < maxIterations; iteration++) {
            let hasOverlaps = false;
            const nodeIds = Array.from(nodePositions.keys());
            
            for (let i = 0; i < nodeIds.length; i++) {
                for (let j = i + 1; j < nodeIds.length; j++) {
                    const nodeId1 = nodeIds[i];
                    const nodeId2 = nodeIds[j];
                    const pos1 = nodePositions.get(nodeId1);
                    const pos2 = nodePositions.get(nodeId2);
                    const size1 = nodeSizes.get(nodeId1) || { width: 120, height: 40 };
                    const size2 = nodeSizes.get(nodeId2) || { width: 120, height: 40 };
                    
                    if (!pos1 || !pos2) continue;
                    
                    // Calculate distance between node centers
                    const dx = Math.abs(pos1.x - pos2.x);
                    const dy = Math.abs(pos1.y - pos2.y);
                    
                    // Calculate minimum required distance (half widths + half heights + spacing)
                    const minDx = (size1.width / 2) + (size2.width / 2) + minSpacing;
                    const minDy = (size1.height / 2) + (size2.height / 2) + minSpacing;
                    
                    // Check if nodes overlap
                    if (dx < minDx && dy < minDy) {
                        hasOverlaps = true;
                        
                        // Calculate overlap amounts
                        const overlapX = minDx - dx;
                        const overlapY = minDy - dy;
                        
                        // Determine push direction
                        const dirX = pos1.x < pos2.x ? -1 : 1;
                        const dirY = pos1.y < pos2.y ? -1 : 1;
                        
                        // Push nodes apart
                        let newX1 = pos1.x + (dirX * overlapX / 2);
                        let newY1 = pos1.y + (dirY * overlapY / 2);
                        let newX2 = pos2.x - (dirX * overlapX / 2);
                        let newY2 = pos2.y - (dirY * overlapY / 2);
                        
                        // Ensure nodes stay within bounds
                        newX1 = Math.max(padding + size1.width / 2, Math.min(newX1, containerWidth - padding - size1.width / 2));
                        newY1 = Math.max(padding + size1.height / 2, Math.min(newY1, containerHeight - padding - size1.height / 2));
                        newX2 = Math.max(padding + size2.width / 2, Math.min(newX2, containerWidth - padding - size2.width / 2));
                        newY2 = Math.max(padding + size2.height / 2, Math.min(newY2, containerHeight - padding - size2.height / 2));
                        
                        // Update positions
                        nodePositions.set(nodeId1, { x: newX1, y: newY1 });
                        nodePositions.set(nodeId2, { x: newX2, y: newY2 });
                        
                        // Update DOM
                        const el1 = nodeElements.get(nodeId1);
                        const el2 = nodeElements.get(nodeId2);
                        if (el1) {
                            el1.style.left = `${newX1}px`;
                            el1.style.top = `${newY1}px`;
                        }
                        if (el2) {
                            el2.style.left = `${newX2}px`;
                            el2.style.top = `${newY2}px`;
                        }
                    }
                }
            }
            
            if (!hasOverlaps) break;
        }
    }


    /**
     * Render all connections (manual only - no original connections rendered)
     */
    function renderAllConnections(svg, mindMapData) {
        if (!svg) return;
        
        const container = svg.closest('#mindmap-display-container') || 
                         document.getElementById('mindmap-display-container');
        if (!container) return;
        
        // Don't render original connections - only manual ones
        // Original connections are stored for reference but not displayed
        
        // Render manual connections only
        manualConnections.forEach(conn => {
            const sourceNode = container.querySelector(`[data-node-id="${conn.source}"]`);
            const targetNode = container.querySelector(`[data-node-id="${conn.target}"]`);
            
            if (sourceNode && targetNode) {
                // Get anchor positions using helper function
                const sourceAnchorPos = getAnchorPosition(conn.source, conn.sourceAnchor);
                const targetAnchorPos = getAnchorPosition(conn.target, conn.targetAnchor);
                
                if (!sourceAnchorPos || !targetAnchorPos) return;
                
                const sourceAnchorX = sourceAnchorPos.x;
                const sourceAnchorY = sourceAnchorPos.y;
                const targetAnchorX = targetAnchorPos.x;
                const targetAnchorY = targetAnchorPos.y;
                
                const side = targetAnchorX >= sourceAnchorX ? 1 : -1;
                const dx = Math.max(60, Math.abs(targetAnchorX - sourceAnchorX) * 0.35);
                
                // Create a wrapper group for the path and delete button
                const connectionGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                connectionGroup.setAttribute('class', 'mindmap-connection-group');
                connectionGroup.setAttribute('data-connection-id', conn.id);
                
                const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                path.setAttribute('d',
                    `M ${sourceAnchorX} ${sourceAnchorY} ` +
                    `C ${sourceAnchorX + dx * side} ${sourceAnchorY}, ` +
                    `${targetAnchorX - dx * side} ${targetAnchorY}, ` +
                    `${targetAnchorX} ${targetAnchorY}`
                );
                path.setAttribute('fill', 'none');
                path.setAttribute('stroke', '#f59e0b');
                path.setAttribute('stroke-width', '2');
                path.setAttribute('class', 'mindmap-connection mindmap-connection--manual');
                path.setAttribute('data-connection-id', conn.id);
                
                // Add delete handler for manual connections (always enabled)
                path.addEventListener('contextmenu', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    deleteConnection(conn.id);
                });
                
                // Create delete button for connection
                const deleteBtn = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                deleteBtn.setAttribute('class', 'mindmap-connection-delete');
                deleteBtn.setAttribute('data-connection-id', conn.id);
                deleteBtn.style.opacity = '0';
                deleteBtn.style.pointerEvents = 'none';
                deleteBtn.style.transition = 'opacity 0.2s ease';
                
                // Calculate button position (middle of the path)
                const midX = (sourceAnchorX + targetAnchorX) / 2;
                const midY = (sourceAnchorY + targetAnchorY) / 2;
                
                // Create invisible larger hit area circle (for easier clicking)
                const hitArea = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                hitArea.setAttribute('cx', midX);
                hitArea.setAttribute('cy', midY);
                hitArea.setAttribute('r', '15'); // Larger hit area
                hitArea.setAttribute('fill', 'transparent');
                hitArea.style.cursor = 'pointer';
                hitArea.style.pointerEvents = 'all';
                
                // Create circle background (visible)
                const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                circle.setAttribute('cx', midX);
                circle.setAttribute('cy', midY);
                circle.setAttribute('r', '10');
                circle.setAttribute('fill', '#ef4444');
                circle.setAttribute('stroke', 'white');
                circle.setAttribute('stroke-width', '2');
                circle.style.cursor = 'pointer';
                
                // Create X icon
                const xLine1 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                xLine1.setAttribute('x1', midX - 4);
                xLine1.setAttribute('y1', midY - 4);
                xLine1.setAttribute('x2', midX + 4);
                xLine1.setAttribute('y2', midY + 4);
                xLine1.setAttribute('stroke', 'white');
                xLine1.setAttribute('stroke-width', '2');
                xLine1.setAttribute('stroke-linecap', 'round');
                
                const xLine2 = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                xLine2.setAttribute('x1', midX - 4);
                xLine2.setAttribute('y1', midY + 4);
                xLine2.setAttribute('x2', midX + 4);
                xLine2.setAttribute('y2', midY - 4);
                xLine2.setAttribute('stroke', 'white');
                xLine2.setAttribute('stroke-width', '2');
                xLine2.setAttribute('stroke-linecap', 'round');
                
                deleteBtn.appendChild(hitArea); // Add hit area first (behind)
                deleteBtn.appendChild(circle);
                deleteBtn.appendChild(xLine1);
                deleteBtn.appendChild(xLine2);
                
                // Helper function to show delete button
                const showDeleteButton = () => {
                    path.style.strokeWidth = '3';
                    path.style.opacity = '0.8';
                    deleteBtn.style.opacity = '1';
                    deleteBtn.style.pointerEvents = 'auto';
                };
                
                // Helper function to hide delete button
                let hideTimeout = null;
                const hideDeleteButton = () => {
                    // Clear any pending hide timeout
                    if (hideTimeout) {
                        clearTimeout(hideTimeout);
                        hideTimeout = null;
                    }
                    path.style.strokeWidth = '2';
                    path.style.opacity = '1';
                    deleteBtn.style.opacity = '0';
                    deleteBtn.style.pointerEvents = 'none';
                };
                
                // Show delete button when hovering over path
                path.addEventListener('mouseenter', () => {
                    if (hideTimeout) {
                        clearTimeout(hideTimeout);
                        hideTimeout = null;
                    }
                    showDeleteButton();
                });
                
                // Hide delete button when leaving path, with delay to allow transition to button
                path.addEventListener('mouseleave', () => {
                    hideTimeout = setTimeout(() => {
                        hideDeleteButton();
                    }, 200); // Delay to allow mouse to move to button
                });
                
                // Keep delete button visible when hovering over it
                deleteBtn.addEventListener('mouseenter', (e) => {
                    e.stopPropagation();
                    if (hideTimeout) {
                        clearTimeout(hideTimeout);
                        hideTimeout = null;
                    }
                    showDeleteButton();
                });
                
                // Hide delete button when leaving it
                deleteBtn.addEventListener('mouseleave', (e) => {
                    // Check if mouse is moving to the path
                    const relatedTarget = e.relatedTarget;
                    if (relatedTarget && path === relatedTarget) {
                        return; // Moving to path, keep visible
                    }
                    hideDeleteButton();
                });
                
                // Delete on click
                deleteBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    deleteConnection(conn.id);
                });
                
                path.style.cursor = 'pointer';
                
                svg.appendChild(path);
                svg.appendChild(deleteBtn);
            }
        });
    }

    /**
     * Enable dragging for nodes in Edit Mode
     */
    function enableDragging() {
        const container = document.getElementById('mindmap-display-container');
        if (!container) return;
        
        const nodes = container.querySelectorAll('[data-node-id]');
        nodes.forEach(node => {
            node.classList.add('mindmap-node--draggable');
            node.style.cursor = 'move';
            
            // Remove existing handlers to prevent duplicates
            node.removeEventListener('mousedown', handleNodeDragStart);
            node.addEventListener('mousedown', handleNodeDragStart);
        });
    }

    /**
     * Disable dragging for nodes
     */
    function disableDragging() {
        const container = document.getElementById('mindmap-display-container');
        if (!container) return;
        
        const nodes = container.querySelectorAll('[data-node-id]');
        nodes.forEach(node => {
            node.classList.remove('mindmap-node--draggable', 'mindmap-node--dragging');
            node.style.cursor = '';
            node.removeEventListener('mousedown', handleNodeDragStart);
        });
        
        // Clean up any ongoing drag
        if (draggedNode) {
            document.removeEventListener('mousemove', handleNodeDrag);
            document.removeEventListener('mouseup', handleNodeDragEnd);
            draggedNode = null;
        }
    }

    /**
     * Handle node drag start
     */
    function handleNodeDragStart(e) {
        // Edit Mode is always enabled
        if (isConnecting) return; // Don't drag while connecting
        
        const node = e.currentTarget;
        const nodeId = node.getAttribute('data-node-id');
        if (!nodeId) return;
        
        e.preventDefault();
        e.stopPropagation();
        
        draggedNode = node;
        node.classList.add('mindmap-node--dragging');
        
        const container = document.getElementById('mindmap-display-container');
        const containerRect = container.getBoundingClientRect();
        const mouseScreenX = e.clientX - containerRect.left;
        const mouseScreenY = e.clientY - containerRect.top;
        const mouseWorld = screenToWorld(mouseScreenX, mouseScreenY);
        
        const nodeX = parseFloat(node.style.left) || 0;
        const nodeY = parseFloat(node.style.top) || 0;
        
        // Calculate offset from mouse to node center in world coords
        dragOffset.x = mouseWorld.x - nodeX;
        dragOffset.y = mouseWorld.y - nodeY;
        
        document.addEventListener('mousemove', handleNodeDrag);
        document.addEventListener('mouseup', handleNodeDragEnd);
    }

    /**
     * Handle node drag
     */
    function handleNodeDrag(e) {
        if (!draggedNode) return;
        
        const container = document.getElementById('mindmap-display-container');
        if (!container) return;
        
        const containerRect = container.getBoundingClientRect();
        const nodeId = draggedNode.getAttribute('data-node-id');
        
        const mouseScreenX = e.clientX - containerRect.left;
        const mouseScreenY = e.clientY - containerRect.top;
        const mouseWorld = screenToWorld(mouseScreenX, mouseScreenY);
        
        // Calculate new position in world coords
        let newX = mouseWorld.x - dragOffset.x;
        let newY = mouseWorld.y - dragOffset.y;
        
        // Get node size for boundary checking (convert to world units)
        const nodeRect = draggedNode.getBoundingClientRect();
        const scale = layoutTransform.scale || 1;
        const nodeWidth = nodeRect.width / scale;
        const nodeHeight = nodeRect.height / scale;
        const paddingWorldX = layoutPadding / scale;
        const paddingWorldY = layoutPadding / scale;
        
        const topLeftWorld = screenToWorld(0, 0);
        const bottomRightWorld = screenToWorld(containerRect.width, containerRect.height);
        
        const minX = topLeftWorld.x + paddingWorldX + (nodeWidth / 2);
        const maxX = bottomRightWorld.x - paddingWorldX - (nodeWidth / 2);
        const minY = topLeftWorld.y + paddingWorldY + (nodeHeight / 2);
        const maxY = bottomRightWorld.y - paddingWorldY - (nodeHeight / 2);
        
        // Constrain to viewport bounds
        newX = Math.max(minX, Math.min(newX, maxX));
        newY = Math.max(minY, Math.min(newY, maxY));
        
        // Update position
        draggedNode.style.left = `${newX}px`;
        draggedNode.style.top = `${newY}px`;
        
        // Store in custom positions
        customPositions.set(nodeId, { x: newX, y: newY });
        
        // Update connections
        updateConnectionsForNode(nodeId);
    }

    /**
     * Handle node drag end
     */
    function handleNodeDragEnd(e) {
        if (!draggedNode) return;
        
        draggedNode.classList.remove('mindmap-node--dragging');
        draggedNode = null;
        
        document.removeEventListener('mousemove', handleNodeDrag);
        document.removeEventListener('mouseup', handleNodeDragEnd);
    }

    /**
     * Update connections when a node moves
     */
    function updateConnectionsForNode(nodeId) {
        const container = document.getElementById('mindmap-display-container');
        if (!container) return;
        
        const svg = container.querySelector('#mindmap-edges') || 
                   container.querySelector('.mindmap-visualization');
        if (!svg) return;
        
        // Remove and re-render all connections and their delete buttons
        const paths = svg.querySelectorAll('.mindmap-connection');
        paths.forEach(path => path.remove());
        const deleteButtons = svg.querySelectorAll('.mindmap-connection-delete');
        deleteButtons.forEach(btn => btn.remove());
        
        if (currentMindMap && currentMindMap.mind_map_data) {
            renderAllConnections(svg, currentMindMap.mind_map_data);
        }
    }

    /**
     * Update connection rendering (for mode changes)
     */
    function updateConnectionRendering() {
        const container = document.getElementById('mindmap-display-container');
        if (!container) return;
        
        const svg = container.querySelector('#mindmap-edges') || 
                   container.querySelector('.mindmap-visualization');
        if (!svg) return;

        // Remove all connections and their delete buttons, then re-render
        const paths = svg.querySelectorAll('.mindmap-connection');
        paths.forEach(path => path.remove());
        const deleteButtons = svg.querySelectorAll('.mindmap-connection-delete');
        deleteButtons.forEach(btn => btn.remove());

        // Re-render connections
        if (currentMindMap && currentMindMap.mind_map_data) {
            renderAllConnections(svg, currentMindMap.mind_map_data);
        }
    }

    // Export already happened earlier (right after function definitions)
    // This is just a verification log
    if (window.mindMapTool && typeof window.mindMapTool.open === 'function') {
        console.log('[Mind Map] Tool verified at end of IIFE');
    } else {
        console.error('[Mind Map] Tool export missing at end of IIFE! Re-exporting...');
        // Fallback: try to export again if it failed
        try {
            window.mindMapTool = {
                open: openMindMapPanel,
                close: closeMindMapPanel
            };
            console.log('[Mind Map] Tool re-exported successfully');
        } catch (e) {
            console.error('[Mind Map] Re-export also failed:', e);
        }
    }

    // Initialize on DOM ready
    try {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initMindMapTool);
        } else {
            // DOM already loaded, initialize immediately
            initMindMapTool();
        }
    } catch (e) {
        console.error('[Mind Map] Initialization error:', e);
    }

})();

// Final verification outside IIFE
console.log('[Mind Map] Script loaded. window.mindMapTool exists:', !!window.mindMapTool, typeof window.mindMapTool);
