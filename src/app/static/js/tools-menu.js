/**
 * Tools Menu Handler
 * Manages the collapsible tools menu (Quiz, Flashcards, Mind Map, Narrative)
 */

(function() {
    'use strict';

    let menuOpen = false;
    let currentButton = null;
    let currentPopup = null;

    /**
     * Initialize tools menu functionality
     */
    function initToolsMenu() {
        console.log('Initializing tools menu...');
        
        // Use class selector to handle multiple instances
        const buttons = document.querySelectorAll('.tools-menu-button');
        console.log('Found buttons:', buttons.length);
        
        if (buttons.length === 0) {
            console.warn('No tools menu buttons found!');
            return;
        }
        
        buttons.forEach((button, index) => {
            console.log(`Setting up button ${index + 1}`);
            
            // Find the popup that follows this button
            let popup = button.nextElementSibling;
            
            // If next sibling is not the popup, search for it in parent
            if (!popup || !popup.classList.contains('tools-menu-popup')) {
                popup = button.parentElement.querySelector('.tools-menu-popup');
            }
            
            if (!popup || !popup.classList.contains('tools-menu-popup')) {
                console.warn('Tools menu: popup not found for button', button);
                return;
            }

            console.log('Button and popup found, setting up event listeners');

            // Toggle menu on button click
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                e.preventDefault();
                console.log('Button clicked!');
                toggleMenu(button, popup);
            });

            // Handle menu item clicks
            const menuItems = popup.querySelectorAll('.tools-menu-item');
            menuItems.forEach(item => {
                item.addEventListener('click', (e) => {
                    e.stopPropagation();
                    handleToolSelection(item.dataset.tool);
                    closeMenu();
                });
            });
        });
        
        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (menuOpen && currentPopup && !currentPopup.contains(e.target) && 
                currentButton && !currentButton.contains(e.target)) {
                closeMenu();
            }
        });

        // Close menu on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && menuOpen) {
                closeMenu();
            }
        });
        
        console.log('Tools menu initialization complete');
    }

    /**
     * Toggle menu open/closed
     */
    function toggleMenu(button, popup) {
        // Close any other open menus first
        if (menuOpen && (currentButton !== button || currentPopup !== popup)) {
            closeMenu();
        }

        if (menuOpen && currentButton === button) {
            closeMenu();
        } else {
            openMenu(button, popup);
        }
    }

    /**
     * Open the menu
     */
    function openMenu(button, popup) {
        menuOpen = true;
        currentButton = button;
        currentPopup = popup;
        const gap = 8;

        // Detach to body to avoid any ancestor clipping
        if (!popup._originParent) {
            popup._originParent = popup.parentElement;
        }
        if (popup.parentElement !== document.body) {
            document.body.appendChild(popup);
        }

        // Reset any previous positioning
        popup.style.left = '';
        popup.style.bottom = '';
        popup.style.right = '';
        popup.style.top = '';
        popup.style.transform = '';
        popup.style.maxHeight = '';
        popup.style.overflowY = '';

        // Ensure fixed positioning and visibility for measurement
        popup.style.position = 'fixed';
        popup.style.display = 'flex';
        popup.classList.remove('hidden');
        popup.style.visibility = 'hidden';
        popup.style.opacity = '0';

        // Measure after ensuring it's in the layout
        const buttonRect = button.getBoundingClientRect();
        const popupRect = popup.getBoundingClientRect();
        const popupWidth = popupRect.width || 220;
        const popupHeight = popupRect.height || 240;

        // Clamp horizontal position to viewport
        const maxLeft = Math.max(8, window.innerWidth - popupWidth - 8);
        const leftPosition = Math.min(Math.max(buttonRect.left, 8), maxLeft);

        // Prefer above; fallback below if not enough space
        const hasSpaceAbove = buttonRect.top >= popupHeight + gap + 8;
        let topPosition = hasSpaceAbove
            ? buttonRect.top - popupHeight - gap
            : buttonRect.bottom + gap;

        // If still overflowing at bottom, clamp and allow scroll inside
        const maxTop = window.innerHeight - popupHeight - 8;
        if (topPosition > maxTop) {
            topPosition = maxTop;
            popup.style.maxHeight = `calc(100vh - ${topPosition + 8}px)`;
            popup.style.overflowY = 'auto';
        }
        if (topPosition < 8) {
            topPosition = 8;
        }

        popup.style.left = `${leftPosition}px`;
        popup.style.top = `${topPosition}px`;
        popup.style.bottom = 'auto';
        popup.style.right = 'auto';
        popup.style.transform = 'none';

        // Now make it visible with animation
        popup.style.visibility = 'visible';
        popup.style.opacity = '1';

        console.debug('[tools-menu] open', {
            buttonRect,
            popupWidth,
            popupHeight,
            leftPosition,
            topPosition
        });

        button.setAttribute('aria-expanded', 'true');
        
        // Initialize Lucide icons if needed
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
        
        // Update position on scroll/resize to keep it aligned with button
        const updatePosition = () => {
            if (menuOpen && currentButton && currentPopup && !currentPopup.classList.contains('hidden')) {
                const rect = currentButton.getBoundingClientRect();
                const popupH = currentPopup.offsetHeight || 200;
                const popupW = currentPopup.offsetWidth || 220;
                const maxLeft = Math.max(8, window.innerWidth - popupW - 8);
                const leftPos = Math.min(Math.max(rect.left, 8), maxLeft);
                const hasSpaceAbove = rect.top >= popupH + gap + 8;
                let topPos = hasSpaceAbove
                    ? rect.top - popupH - gap
                    : rect.bottom + gap;
                const maxTopPos = window.innerHeight - popupH - 8;
                if (topPos > maxTopPos) topPos = maxTopPos;
                if (topPos < 8) topPos = 8;

                currentPopup.style.left = `${leftPos}px`;
                currentPopup.style.top = `${topPos}px`;
            }
        };
        
        // Store update function for cleanup
        popup._updatePosition = updatePosition;
        window.addEventListener('scroll', updatePosition, true);
        window.addEventListener('resize', updatePosition);
    }

    /**
     * Close the menu
     */
    function closeMenu() {
        if (currentPopup) {
            currentPopup.style.opacity = '0';
            currentPopup.style.visibility = 'hidden';
            // Small delay before hiding to allow fade-out
            setTimeout(() => {
            if (currentPopup) {
                currentPopup.classList.add('hidden');
                currentPopup.style.display = '';
                currentPopup.style.maxHeight = '';
                currentPopup.style.overflowY = '';
            }
        }, 150);
        
            // Clean up event listeners
            if (currentPopup._updatePosition) {
                window.removeEventListener('scroll', currentPopup._updatePosition, true);
                window.removeEventListener('resize', currentPopup._updatePosition);
                delete currentPopup._updatePosition;
            }
            // Reset positioning (but keep fixed for next open)
            currentPopup.style.left = '';
            currentPopup.style.top = '';
            currentPopup.style.bottom = '';
        }
        if (currentButton) {
            currentButton.setAttribute('aria-expanded', 'false');
        }
        
        menuOpen = false;
        currentButton = null;
        currentPopup = null;
    }

    /**
     * Handle tool selection
     */
    function handleToolSelection(tool) {
        console.log('Tool selected:', tool);
        
        // TODO: Implement tool-specific functionality
        // For now, just log the selection
        // This will be expanded based on requirements
        
        // Example: Could insert text into the message input
        const messageInput = document.getElementById('message-input');
        if (messageInput) {
            // You could insert a command or trigger a modal here
            // messageInput.value = `Create ${tool}...`;
            // messageInput.focus();
        }
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initToolsMenu);
    } else {
        initToolsMenu();
    }

    // Re-initialize after dynamic content loads (e.g., Lucide icons)
    if (typeof lucide !== 'undefined') {
        // Wait for Lucide to be ready
        setTimeout(() => {
            lucide.createIcons();
        }, 100);
    }

    // Export for external use
    window.toolsMenu = {
        open: openMenu,
        close: closeMenu,
        handleSelection: handleToolSelection
    };

})();
