// Chat Accessibility Enhancements
// Mobile menu a11y, focus management, and ARIA attributes

document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenuClose = document.getElementById('mobile-menu-close');
    const mobileMenuOverlay = document.getElementById('mobile-menu-overlay');
    const mobileMenuPanel = document.getElementById('mobile-menu-panel');

    // Enhanced mobile menu functions with a11y (simplified, robust implementation)
    function openMobileMenu() {
        if (!mobileMenuOverlay || !mobileMenuPanel) return;
        
        mobileMenuOverlay.classList.remove('hidden');
        setTimeout(() => mobileMenuPanel.classList.remove('translate-x-full'), 10);
        mobileMenuButton?.setAttribute('aria-expanded', 'true');
        document.body.style.overflow = 'hidden';
        
        // Focus first focusable element
        const firstFocusable = mobileMenuPanel.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
        firstFocusable?.focus();
    }

    function closeMobileMenu() {
        if (!mobileMenuOverlay || !mobileMenuPanel) return;
        
        mobileMenuPanel.classList.add('translate-x-full');
        setTimeout(() => {
            mobileMenuOverlay.classList.add('hidden');
            document.body.style.overflow = '';
            mobileMenuButton?.setAttribute('aria-expanded', 'false');
            mobileMenuButton?.focus();
        }, 300);
    }

    // Focus trap implementation
    let focusTrapElements = [];
    
    function setupFocusTrap(container) {
        focusTrapElements = container.querySelectorAll('a, button, [tabindex]:not([tabindex="-1"])');
        
        if (focusTrapElements.length > 0) {
            const firstElement = focusTrapElements[0];
            const lastElement = focusTrapElements[focusTrapElements.length - 1];
            
            function trapFocus(e) {
                if (e.key === 'Tab') {
                    if (e.shiftKey) {
                        // Shift + Tab
                        if (document.activeElement === firstElement) {
                            e.preventDefault();
                            lastElement.focus();
                        }
                    } else {
                        // Tab
                        if (document.activeElement === lastElement) {
                            e.preventDefault();
                            firstElement.focus();
                        }
                    }
                }
            }
            
            document.addEventListener('keydown', trapFocus);
            container._focusTrapHandler = trapFocus;
        }
    }
    
    function removeFocusTrap() {
        const container = mobileMenuPanel;
        if (container && container._focusTrapHandler) {
            document.removeEventListener('keydown', container._focusTrapHandler);
            delete container._focusTrapHandler;
        }
    }

    // Enhanced mobile menu event listeners
    if (mobileMenuButton) {
        // Initialize ARIA state
        mobileMenuButton.setAttribute('aria-expanded', 'false');
        
        mobileMenuButton.addEventListener('click', function(e) {
            e.preventDefault();
            openMobileMenu();
        });
    }

    if (mobileMenuClose) {
        mobileMenuClose.addEventListener('click', function(e) {
            e.preventDefault();
            closeMobileMenu();
        });
    }

    // Close on overlay click
    if (mobileMenuOverlay) {
        mobileMenuOverlay.addEventListener('click', function(e) {
            if (e.target === mobileMenuOverlay) {
                closeMobileMenu();
            }
        });
    }

    // Close on Escape (already handled in base template, but ensure it calls our function)
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && mobileMenuOverlay && !mobileMenuOverlay.classList.contains('hidden')) {
            closeMobileMenu();
        }
    });

    // Close when resized to desktop
    window.addEventListener('resize', function() {
        if (window.innerWidth >= 768 && mobileMenuOverlay && !mobileMenuOverlay.classList.contains('hidden')) {
            closeMobileMenu();
        }
    });
});

// Focus mode accessibility
document.addEventListener('DOMContentLoaded', function() {
    const focusButton = document.querySelector('[onclick*="toggleFocusMode"]');
    
    if (focusButton) {
        // Initialize ARIA state
        focusButton.setAttribute('aria-pressed', 'false');
        
        // Override the focus mode toggle to include a11y
        window.toggleFocusMode = function() {
            document.body.classList.toggle('focus-mode');
            const isPressed = document.body.classList.contains('focus-mode');
            
            // Update ARIA state
            focusButton.setAttribute('aria-pressed', isPressed.toString());
            
            // Announce state change
            const announcement = isPressed ? 'Focus mode enabled' : 'Focus mode disabled';
            announceToScreenReader(announcement);
        };
    }
});

// Screen reader announcements
function announceToScreenReader(message) {
    const announcement = document.createElement('div');
    announcement.setAttribute('aria-live', 'polite');
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = message;
    
    document.body.appendChild(announcement);
    
    // Remove after announcement
    setTimeout(() => {
        document.body.removeChild(announcement);
    }, 1000);
}

// Add aria-labels to emoji buttons
document.addEventListener('DOMContentLoaded', function() {
    // Scroll to bottom button
    const scrollButton = document.querySelector('[onclick*="scrollToBottom"]');
    if (scrollButton && !scrollButton.getAttribute('aria-label')) {
        scrollButton.setAttribute('aria-label', 'Scroll to bottom of conversation');
    }
    
    // Export buttons (if they don't already have aria-label)
    document.querySelectorAll('button[onclick*="exportDocument"]').forEach(button => {
        if (!button.getAttribute('aria-label')) {
            const text = button.textContent.trim();
            if (text.includes('📄')) {
                button.setAttribute('aria-label', 'Export as text file');
            } else if (text.includes('📝')) {
                button.setAttribute('aria-label', 'Export as Word document');
            }
        }
    });
    
    // Other emoji buttons
    document.querySelectorAll('button').forEach(button => {
        const text = button.textContent.trim();
        if (!button.getAttribute('aria-label') && /^[\u{1F300}-\u{1F5FF}]/u.test(text)) {
            // Button starts with emoji but has no aria-label
            button.setAttribute('aria-label', `Action: ${text}`);
        }
    });
});

// Time formatting for message timestamps
function formatTimes() {
    document.querySelectorAll('time.msg-time[data-ts]').forEach(t => {
        const ts = Number(t.dataset.ts) * 1000;
        if (!Number.isNaN(ts)) {
            t.textContent = new Date(ts).toLocaleString();
        }
    });
}

// Lucide icon refresh after dynamic content changes
function refreshLucideIcons(container = document) {
    if (window.lucide && typeof lucide.createIcons === 'function') {
        lucide.createIcons({ nameAttr: 'data-lucide' });
    }
}

// Initialize time formatting
document.addEventListener('DOMContentLoaded', formatTimes);

// Export utilities for other scripts
window.chatUtils = {
    formatTimes,
    refreshLucideIcons,
    announceToScreenReader
};
