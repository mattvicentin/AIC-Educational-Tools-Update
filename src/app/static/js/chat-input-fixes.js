// Chat Input Overlap Fix
// Prevents fixed input bar from overlapping content/footer
function padForComposer() {
    const cm = document.querySelector('.chat-input-container');
    const msgs = document.getElementById('chat-messages');
    if (cm && msgs) {
        msgs.style.paddingBottom = `${cm.offsetHeight + 16}px`;
    }
}

// Initialize on load and resize
window.addEventListener('resize', padForComposer);
document.addEventListener('DOMContentLoaded', padForComposer);

// Re-pad after dynamic content changes (message additions)
function repadAfterMessage() {
    setTimeout(padForComposer, 100); // Small delay for DOM updates
}

// Export this for use by other scripts
window.chatInputFixes = {
    padForComposer,
    repadAfterMessage
};
