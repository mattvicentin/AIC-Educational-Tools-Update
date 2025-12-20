// Restore Document Generation Tool
// Adds document generation dropdown to chat sidebar

document.addEventListener('DOMContentLoaded', function() {
    // Only on chat pages
    if (!/^\/chat\/\d+/.test(location.pathname)) return;
    
    const chatId = getChatIdFromUrl();
    if (!chatId) return;
    
    // Find sidebar and add document generation
    const sidebar = document.querySelector('.chat-sidebar') || 
                   document.querySelector('[class*="sidebar"]') ||
                   document.querySelector('.space-y-4');
    
    if (!sidebar) return;
    
    // Count messages for progressive unlock
    const messageCount = document.querySelectorAll('.message, [class*="message"]').length;
    
    // Create document generation HTML with tool-card structure
    const docGenHTML = `
    <section class="tool-card" id="doc-gen-card">
        <div class="tool-card__header">
            <div class="tool-card__title">
                <i data-lucide="file-text" class="w-4 h-4"></i>
                Generate Document
            </div>
            <button type="button" class="tool-card__chevron" aria-expanded="false" aria-controls="document-dropdown" onclick="toggleDocumentDropdown(this)">
                <i data-lucide="chevron-down" class="w-4 h-4"></i>
            </button>
        </div>
        <div class="tool-card__body" id="document-dropdown" hidden>
            <div class="space-y-3">
                <!-- Export Chat History -->
                <div>
                    <div class="text-xs font-medium text-foreground mb-1"><i data-lucide="download" class="w-4 h-4"></i> Export Chat History</div>
                    <div class="flex gap-1">
                        <button onclick="exportDocument(this, 'raw', 'txt', ${chatId})" 
                                class="flex-1 p-1 text-xs rounded border border-border hover:bg-accent transition-colors"
                                title="Export as .txt"><i data-lucide="file-text" class="w-3 h-3"></i> .txt</button>
                        <button onclick="exportDocument(this, 'raw', 'docx', ${chatId})" 
                                class="flex-1 p-1 text-xs rounded border border-border hover:bg-accent transition-colors"
                                title="Export as .docx"><i data-lucide="file-edit" class="w-3 h-3"></i> .docx</button>
                    </div>
                </div>
                
                <!-- Create Notes -->
                <div>
                    <div class="text-xs font-medium text-foreground mb-1"><i data-lucide="sticky-note" class="w-4 h-4"></i> Create Notes</div>
                    ${messageCount >= 5 ? `
                    <div class="flex gap-1">
                        <button onclick="exportDocument(this, 'notes', 'txt', ${chatId})" 
                                class="flex-1 p-1 text-xs rounded border border-border hover:bg-accent transition-colors"><i data-lucide="file-text" class="w-3 h-3"></i> .txt</button>
                        <button onclick="exportDocument(this, 'notes', 'docx', ${chatId})" 
                                class="flex-1 p-1 text-xs rounded border border-border hover:bg-accent transition-colors"><i data-lucide="file-edit" class="w-3 h-3"></i> .docx</button>
                    </div>` : 
                    `<div class="text-xs text-muted-foreground">${5 - messageCount} more messages needed</div>`}
                </div>
                
                <!-- Create Outline -->
                <div>
                    <div class="text-xs font-medium text-foreground mb-1"><i data-lucide="list-tree" class="w-4 h-4"></i> Create Outline</div>
                    ${messageCount >= 10 ? `
                    <div class="flex gap-1">
                        <button onclick="exportDocument(this, 'outline', 'txt', ${chatId})" 
                                class="flex-1 p-1 text-xs rounded border border-border hover:bg-accent transition-colors"><i data-lucide="file-text" class="w-3 h-3"></i> .txt</button>
                        <button onclick="exportDocument(this, 'outline', 'docx', ${chatId})" 
                                class="flex-1 p-1 text-xs rounded border border-border hover:bg-accent transition-colors"><i data-lucide="file-edit" class="w-3 h-3"></i> .docx</button>
                    </div>` :
                    `<div class="text-xs text-muted-foreground">${10 - messageCount} more messages needed</div>`}
                </div>
            </div>
        </div>
    </section>`;
    
    // Insert into Tools section (new collapsible structure) or fallback to old location
    const docDiv = document.createElement('div');
    docDiv.innerHTML = docGenHTML;
    
    // Priority 1: Try doc-gen-mount (tool-stack organization)
    const docMount = document.getElementById('doc-gen-mount');
    if (docMount) {
        // Append the section directly (not the wrapper div) so tool-stack spacing works
        docMount.appendChild(docDiv.firstElementChild);
        console.log('📦 Document dropdown injected into doc-gen-mount (tool-stack)');
    } else if (false) {  // Skip old toolsPanel method
        // Fallback disabled - use legacy method below
        console.log('⚠️ doc-gen-mount not found, using fallback');
    } else {
        // Priority 2: Fallback to old logic (before Room Members)
        const roomMembers = sidebar.querySelector('h3, .text-lg, [class*="member"]')?.parentElement;
        if (roomMembers) {
            // Insert section directly (not wrapper div) for consistent spacing
            roomMembers.parentNode.insertBefore(docDiv.firstElementChild, roomMembers);
            console.log('📦 Document dropdown injected before Room Members (legacy)');
        } else {
            // Priority 3: Last resort - insert at top of sidebar
            // Insert section directly (not wrapper div) for consistent spacing
            sidebar.insertBefore(docDiv.firstElementChild, sidebar.firstChild);
            console.log('📦 Document dropdown injected at sidebar top (fallback)');
        }
    }
    
    // Refresh Lucide icons
    if (window.lucide && typeof lucide.createIcons === 'function') {
        lucide.createIcons();
    }
});

function getChatIdFromUrl() {
    const match = window.location.pathname.match(/\/chat\/(\d+)/);
    return match ? match[1] : null;
}

function toggleDocumentDropdown(button) {
    const dropdown = document.getElementById('document-dropdown');
    
    if (dropdown && button) {
        // Toggle hidden attribute
        const isHidden = dropdown.hasAttribute('hidden');
        if (isHidden) {
            dropdown.removeAttribute('hidden');
            button.setAttribute('aria-expanded', 'true');
        } else {
            dropdown.setAttribute('hidden', '');
            button.setAttribute('aria-expanded', 'false');
        }
    }
}

function exportDocument(button, docType, format, chatId) {
    const original = button.innerHTML;
    button.innerHTML = '⏳';
    button.disabled = true;

    const form = document.createElement('form');
    form.method = 'POST';
    form.action = (docType === 'raw') 
        ? `/documents/chat/${chatId}/export-raw`
        : `/documents/chat/${chatId}/generate`;

    if (docType !== 'raw') {
        const dt = document.createElement('input');
        dt.type = 'hidden'; dt.name = 'doc_type'; dt.value = docType;
        form.appendChild(dt);
    }

    const fmt = document.createElement('input');
    fmt.type = 'hidden'; fmt.name = 'format'; fmt.value = format;
    form.appendChild(fmt);

    const token = document.cookie.split('; ').find(r => r.startsWith('csrf_token='))?.split('=')[1];
    if (token) {
        const csrf = document.createElement('input');
        csrf.type = 'hidden'; csrf.name = 'csrf_token'; csrf.value = token;
        form.appendChild(csrf);
    }

    document.body.appendChild(form);
    form.submit();

    setTimeout(() => { 
        button.innerHTML = original; 
        button.disabled = false; 
    }, 2000);
}

// Generic toggle function for tool cards
function toggleToolCard(button, bodyId) {
    const body = document.getElementById(bodyId);
    
    if (body && button) {
        // Toggle visibility
        const isHidden = body.hasAttribute('hidden');
        if (isHidden) {
            body.removeAttribute('hidden');
            button.setAttribute('aria-expanded', 'true');
        } else {
            body.setAttribute('hidden', '');
            button.setAttribute('aria-expanded', 'false');
        }
    }
}
