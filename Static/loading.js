/**
 * Loading state management utility
 * Prevents double-clicking and shows loading states for buttons
 */

class LoadingManager {
    constructor() {
        this.loadingButtons = new Set();
    }

    /**
     * Set a button to loading state
     * @param {HTMLElement} button - The button element
     * @param {string} loadingText - Text to show while loading (optional)
     */
    setLoading(button, loadingText = 'Processing...') {
        if (this.loadingButtons.has(button)) {
            return; // Already loading
        }

        this.loadingButtons.add(button);
        
        // Store original text and state
        button.dataset.originalText = button.textContent;
        button.dataset.originalDisabled = button.disabled;
        
        // Show loading state but don't disable immediately for form submission
        button.textContent = loadingText;
        
        // Add loading class for styling
        button.classList.add('loading');
        
        // Add spinner if not already present
        if (!button.querySelector('.spinner')) {
            const spinner = document.createElement('span');
            spinner.className = 'spinner';
            spinner.innerHTML = '⏳';
            button.insertBefore(spinner, button.firstChild);
        }
        
        // Disable button after a short delay to allow form submission
        setTimeout(() => {
            if (this.loadingButtons.has(button)) {
                button.disabled = true;
            }
        }, 100);
    }

    /**
     * Reset a button from loading state
     * @param {HTMLElement} button - The button element
     */
    resetLoading(button) {
        if (!this.loadingButtons.has(button)) {
            return; // Not loading
        }

        this.loadingButtons.delete(button);
        
        // Restore original text and state
        if (button.dataset.originalText) {
            button.textContent = button.dataset.originalText;
        }
        if (button.dataset.originalDisabled !== undefined) {
            button.disabled = button.dataset.originalDisabled === 'true';
        }
        
        // Remove loading class
        button.classList.remove('loading');
        
        // Remove spinner
        const spinner = button.querySelector('.spinner');
        if (spinner) {
            spinner.remove();
        }
    }

    /**
     * Check if a button is currently loading
     * @param {HTMLElement} button - The button element
     * @returns {boolean}
     */
    isLoading(button) {
        return this.loadingButtons.has(button);
    }

    /**
     * Set loading state for all buttons in a form
     * @param {HTMLFormElement} form - The form element
     * @param {string} loadingText - Text to show while loading (optional)
     */
    setFormLoading(form, loadingText = 'Processing...') {
        const buttons = form.querySelectorAll('button[type="submit"]');
        buttons.forEach(button => this.setLoading(button, loadingText));
    }

    /**
     * Reset loading state for all buttons in a form
     * @param {HTMLFormElement} form - The form element
     */
    resetFormLoading(form) {
        const buttons = form.querySelectorAll('button[type="submit"]');
        buttons.forEach(button => this.resetLoading(button));
    }
}

// Global instance
const loadingManager = new LoadingManager();

// Auto-disable forms on submit
document.addEventListener('DOMContentLoaded', function() {
    // Handle all forms with loading states
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            // Set loading state but allow form to submit
            loadingManager.setFormLoading(form);
        });
    });

    // Handle individual buttons that might not be in forms
    document.querySelectorAll('button[type="submit"], .btn-primary, .btn-secondary').forEach(button => {
        button.addEventListener('click', function(e) {
            // If this is a submit button, set loading state
            if (this.type === 'submit' || this.classList.contains('btn-primary')) {
                loadingManager.setLoading(this);
            }
        });
    });
});

// Export for use in other scripts
window.loadingManager = loadingManager; 