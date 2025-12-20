/**
 * pin-toggle.js
 * Handles pin/unpin functionality for messages and comments
 * 
 * Features:
 * - Toggle pin state with CSRF protection
 * - Idempotent operations
 * - Optimistic UI updates
 * - Error handling with revert
 */

(function() {
    'use strict';
    
    /**
     * Get CSRF token from cookie
     */
    function getCsrfToken() {
        const name = 'csrf_token=';
        const decodedCookie = decodeURIComponent(document.cookie);
        const cookieArray = decodedCookie.split(';');
        
        for (let cookie of cookieArray) {
            cookie = cookie.trim();
            if (cookie.indexOf(name) === 0) {
                return cookie.substring(name.length);
            }
        }
        return null;
    }
    
    /**
     * Toggle pin state for a message or comment
     */
    async function togglePin(button) {
        // Prevent double-clicks
        if (button.disabled) {
            return;
        }
        
        button.disabled = true;
        
        try {
            const chatContainer = document.querySelector('[data-chat-id]');
            if (!chatContainer) {
                throw new Error('Chat container not found');
            }
            
            const chatId = chatContainer.dataset.chatId;
            const messageId = button.dataset.pinMessage;
            const commentId = button.dataset.pinComment;
            const isPinned = button.dataset.pinned === 'true';
            
            if (!messageId && !commentId) {
                throw new Error('No message or comment ID found');
            }
            
            // Determine endpoint
            const endpoint = isPinned 
                ? `/chat/${chatId}/unpin` 
                : `/chat/${chatId}/pin`;
            
            // Prepare request body
            const body = messageId 
                ? { message_id: parseInt(messageId) }
                : { comment_id: parseInt(commentId) };
            
            // Get CSRF token
            const csrfToken = getCsrfToken();
            
            // Optimistic UI update
            const originalText = button.innerHTML;
            button.innerHTML = isPinned ? 'Unpinning...' : 'Pinning...';
            button.classList.add('opacity-50');
            
            // Make request
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken || ''
                },
                body: JSON.stringify(body)
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `Request failed with status ${response.status}`);
            }
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Operation failed');
            }
            
            // Update button state
            const newPinnedState = data.pinned;
            button.dataset.pinned = newPinnedState ? 'true' : 'false';
            
            if (newPinnedState) {
                button.innerHTML = '📌 Unpin';
            } else {
                button.innerHTML = 'Pin';
            }
            
            button.classList.remove('opacity-50');
            
            // Refresh the sidebar pins in-place (no page reload)
            if (typeof window.refreshPins === 'function') {
                window.refreshPins();
            }
            
            // Show brief success feedback
            button.classList.add('text-green-600');
            setTimeout(() => {
                button.classList.remove('text-green-600');
            }, 1000);
            
        } catch (error) {
            console.error('Pin toggle error:', error);
            
            // Revert UI on error
            button.innerHTML = button.dataset.pinned === 'true' ? '📌 Unpin' : 'Pin';
            button.classList.remove('opacity-50');
            
            // Show error message
            const errorMsg = document.createElement('span');
            errorMsg.className = 'text-xs text-red-600 ml-2';
            errorMsg.textContent = 'Error: ' + (error.message || 'Failed to toggle pin');
            button.parentElement.appendChild(errorMsg);
            
            setTimeout(() => {
                errorMsg.remove();
            }, 3000);
        } finally {
            button.disabled = false;
        }
    }
    
    /**
     * Initialize pin toggle handlers
     */
    function init() {
        // Use event delegation for all pin toggle buttons
        document.addEventListener('click', function(e) {
            const pinToggle = e.target.closest('.pin-toggle');
            if (pinToggle) {
                e.preventDefault();
                togglePin(pinToggle);
            }
        });
        
        console.log('📌 Pin toggle functionality initialized');
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

