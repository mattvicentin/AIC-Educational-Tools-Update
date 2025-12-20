/**
 * pin-chat.js
 * Purpose: Handle pin-seeded chat creation flow
 * Status: [ACTIVE]
 * Created: 2025-12-04
 * 
 * Phase 4A: CTA button setup
 * Phase 4B: Option picker modal and API integration
 */

(function() {
    'use strict';

    // ==========================================================================
    // CONFIGURATION
    // ==========================================================================
    
    const PIN_CHAT_OPTIONS = [
        { key: 'explore', label: 'Explore & Brainstorm', icon: '💡', desc: 'Discover connections and generate new ideas' },
        { key: 'study', label: 'Study & Master', icon: '📚', desc: 'Deeply understand and test your knowledge' },
        { key: 'research_essay', label: 'Draft Research Essay', icon: '📝', desc: 'Synthesize into a well-structured essay' },
        { key: 'presentation', label: 'Build Presentation', icon: '📊', desc: 'Create a compelling presentation' },
        { key: 'learning_exercise', label: 'Create Learning Exercise', icon: '🎮', desc: 'Design interactive learning activities' },
        { key: 'startup', label: 'Plan Startup', icon: '🚀', desc: 'Develop business ideas and strategies' },
        { key: 'artistic', label: 'Create Something Artistic', icon: '🎨', desc: 'Express ideas through creative work' },
        { key: 'social_impact', label: 'Create Social Impact', icon: '🌍', desc: 'Plan for positive change' },
        { key: 'analyze', label: 'Analyze & Summarize', icon: '🔍', desc: 'Find patterns and key insights' }
    ];

    // ==========================================================================
    // MODAL HTML
    // ==========================================================================
    
    function createModalHTML() {
        const optionsHTML = PIN_CHAT_OPTIONS.map(opt => `
            <button type="button" 
                    class="pin-chat-option w-full p-3 text-left border border-border rounded-lg hover:border-primary hover:bg-primary/5 transition-all group"
                    data-option="${opt.key}">
                <div class="flex items-start gap-3">
                    <span class="text-2xl">${opt.icon}</span>
                    <div class="flex-1">
                        <div class="font-medium text-foreground group-hover:text-primary transition-colors">${opt.label}</div>
                        <div class="text-xs text-muted-foreground mt-0.5">${opt.desc}</div>
                    </div>
                </div>
            </button>
        `).join('');

        return `
            <div id="pin-chat-modal" class="pin-chat-modal fixed inset-0 z-50 hidden" role="dialog" aria-modal="true" aria-labelledby="pin-chat-modal-title">
                <div class="pin-chat-modal-backdrop absolute inset-0 bg-black/50 backdrop-blur-sm"></div>
                <div class="pin-chat-modal-container absolute inset-0 flex items-center justify-center p-4">
                    <div class="pin-chat-modal-content bg-background border border-border rounded-xl shadow-2xl max-w-md w-full max-h-[80vh] overflow-hidden">
                        <!-- Header -->
                        <div class="p-4 border-b border-border">
                            <div class="flex items-center justify-between">
                                <div class="flex items-center gap-2">
                                    <i data-lucide="sparkles" class="w-5 h-5 text-primary"></i>
                                    <h2 id="pin-chat-modal-title" class="text-lg font-semibold">Create Chat from Pins</h2>
                                </div>
                                <button type="button" class="pin-chat-modal-close p-1 rounded-md hover:bg-muted transition-colors" aria-label="Close">
                                    <i data-lucide="x" class="w-5 h-5"></i>
                                </button>
                            </div>
                            <p class="text-sm text-muted-foreground mt-1">
                                Using <span class="pin-count-display font-medium text-primary">0</span> shared pins
                            </p>
                        </div>
                        
                        <!-- Options -->
                        <div class="p-4 overflow-y-auto max-h-[50vh]">
                            <p class="text-sm font-medium mb-3">What would you like to do with these pins?</p>
                            <div class="space-y-2">
                                ${optionsHTML}
                            </div>
                        </div>
                        
                        <!-- Footer -->
                        <div class="p-4 border-t border-border bg-muted/30">
                            <div class="flex items-center justify-between text-xs text-muted-foreground">
                                <span>All shared pins will be included</span>
                                <span class="pin-chat-loading hidden">
                                    <i data-lucide="loader-2" class="w-4 h-4 animate-spin inline"></i>
                                    Creating...
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    // ==========================================================================
    // MODAL FUNCTIONS
    // ==========================================================================
    
    let currentRoomId = null;
    let currentPinCount = 0;

    function showModal(roomId, pinCount) {
        currentRoomId = roomId;
        currentPinCount = pinCount;
        
        let modal = document.getElementById('pin-chat-modal');
        
        // Create modal if it doesn't exist
        if (!modal) {
            const wrapper = document.createElement('div');
            wrapper.innerHTML = createModalHTML();
            document.body.appendChild(wrapper.firstElementChild);
            modal = document.getElementById('pin-chat-modal');
            
            // Re-initialize Lucide icons
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
            
            // Setup modal event listeners
            setupModalListeners(modal);
        }
        
        // Update pin count display
        const countDisplay = modal.querySelector('.pin-count-display');
        if (countDisplay) {
            countDisplay.textContent = pinCount;
        }
        
        // Show modal
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        
        // Focus first option for accessibility
        setTimeout(() => {
            const firstOption = modal.querySelector('.pin-chat-option');
            if (firstOption) firstOption.focus();
        }, 100);
    }

    function hideModal() {
        const modal = document.getElementById('pin-chat-modal');
        if (modal) {
            modal.classList.add('hidden');
            document.body.style.overflow = '';
        }
        currentRoomId = null;
        currentPinCount = 0;
    }

    function setupModalListeners(modal) {
        // Close button
        const closeBtn = modal.querySelector('.pin-chat-modal-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', hideModal);
        }
        
        // Backdrop click
        const backdrop = modal.querySelector('.pin-chat-modal-backdrop');
        if (backdrop) {
            backdrop.addEventListener('click', hideModal);
        }
        
        // Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
                hideModal();
            }
        });
        
        // Option buttons
        modal.querySelectorAll('.pin-chat-option').forEach(btn => {
            btn.addEventListener('click', () => {
                const option = btn.dataset.option;
                createPinChat(option);
            });
        });
    }

    // ==========================================================================
    // API INTEGRATION
    // ==========================================================================
    
    async function createPinChat(option) {
        if (!currentRoomId) {
            console.error('No room ID set');
            return;
        }
        
        const modal = document.getElementById('pin-chat-modal');
        const loadingEl = modal?.querySelector('.pin-chat-loading');
        const optionBtns = modal?.querySelectorAll('.pin-chat-option');
        
        // Show loading state
        if (loadingEl) loadingEl.classList.remove('hidden');
        optionBtns?.forEach(btn => btn.disabled = true);
        
        try {
            // Get all shared pin IDs from the page
            const pinIds = getSharedPinIds();
            
            if (pinIds.length < 3) {
                throw new Error('At least 3 shared pins are required');
            }
            
            // Get CSRF token
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content 
                || document.cookie.match(/csrf_token=([^;]+)/)?.[1]
                || '';
            
            const response = await fetch(`/room/${currentRoomId}/chats/from-pins`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    pin_ids: pinIds,
                    option: option
                })
            });
            
            const data = await response.json();
            
            if (data.success && data.chat_id) {
                // Redirect to new chat
                window.location.href = `/chat/${data.chat_id}`;
            } else {
                throw new Error(data.error || 'Failed to create chat');
            }
            
        } catch (error) {
            console.error('Error creating pin chat:', error);
            alert(error.message || 'Failed to create chat. Please try again.');
            
            // Reset loading state
            if (loadingEl) loadingEl.classList.add('hidden');
            optionBtns?.forEach(btn => btn.disabled = false);
        }
    }

    function getSharedPinIds() {
        // Try to get pin IDs from the data attributes on pin cards
        const pinCards = document.querySelectorAll('[data-panel="shared"] .pin-card[data-pin-id]');
        if (pinCards.length > 0) {
            return Array.from(pinCards).map(card => parseInt(card.dataset.pinId, 10)).filter(id => !isNaN(id));
        }
        
        // Fallback: try to get from share toggle buttons
        const shareButtons = document.querySelectorAll('[data-panel="shared"] .share-pin-toggle[data-pin-id]');
        if (shareButtons.length > 0) {
            return Array.from(shareButtons).map(btn => parseInt(btn.dataset.pinId, 10)).filter(id => !isNaN(id));
        }
        
        // Fallback: try remove buttons
        const removeButtons = document.querySelectorAll('[data-panel="shared"] .remove-pin-btn[data-pin-id]');
        if (removeButtons.length > 0) {
            return Array.from(removeButtons).map(btn => parseInt(btn.dataset.pinId, 10)).filter(id => !isNaN(id));
        }
        
        console.warn('Could not find shared pin IDs in the DOM');
        return [];
    }

    // ==========================================================================
    // INITIALIZATION
    // ==========================================================================
    
    function init() {
        // Add click listeners to all "Start Chat from Pins" buttons
        document.querySelectorAll('.pin-chat-start-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const roomId = btn.dataset.roomId;
                const pinCount = parseInt(btn.dataset.pinCount, 10) || 0;
                
                if (roomId && pinCount >= 3) {
                    showModal(roomId, pinCount);
                } else {
                    alert('At least 3 shared pins are required to create a chat.');
                }
            });
        });
        
        console.log('[pin-chat] Initialized');
    }

    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose for debugging
    window.PinChat = {
        showModal,
        hideModal,
        getSharedPinIds
    };

})();

