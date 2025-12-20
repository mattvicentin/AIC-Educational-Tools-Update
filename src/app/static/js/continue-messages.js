(function () {
  // prevent duplicate init
  if (window.__CONTINUE_INIT__) return;
  window.__CONTINUE_INIT__ = 'v1.2';

  function enhanceBubble(bubble) {
    if (!bubble || bubble.dataset.continueEnhanced === '1') return;

    const content = bubble.querySelector('.message-content');
    if (!content) return;

    // ALWAYS remove any old anchors first (cleanup before gating)
    content.querySelectorAll('a.continue-link, .continue-cta').forEach(el => el.remove());

    // Only add continue button if message was truncated
    const isTruncated = bubble.dataset.truncated === 'true';
    if (!isTruncated) return;

    const ts = content.querySelector('.message-timestamp');

    // figure out the last non-timestamp block to make it feel "end of the message"
    let lastTextEl = null;
    Array.from(content.children).forEach(el => {
      if (!el.classList.contains('message-timestamp')) lastTextEl = el;
    });

    // create CTA (inline-friendly)
    const a = document.createElement('button');
    a.type = 'button';
    a.className = 'continue-cta inline-flex items-center gap-1 text-xs text-primary hover:text-primary/80 ml-2 align-baseline';
    a.setAttribute('aria-label', 'Continue this response');
    a.innerHTML = `<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
      stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"></path><path d="m12 5 7 7-7 7"></path></svg> Continue`;

    // action: call the continue endpoint with message context
    a.addEventListener('click', async () => {
      // Get message ID from bubble
      const messageWrapper = bubble.closest('[data-message-id]');
      if (!messageWrapper) return;
      
      const messageId = messageWrapper.dataset.messageId;
      const chatId = window.location.pathname.match(/\/chat\/(\d+)/)?.[1];
      
      if (!chatId || !messageId) {
        console.error('Cannot continue: missing chat ID or message ID');
        return;
      }
      
      // Show loading state
      a.disabled = true;
      a.innerHTML = `<svg class="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg> Continuing...`;
      
      try {
        // Call the continue endpoint
        const response = await fetch(`/chat/${chatId}/continue/${messageId}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
          }
        });
        
        if (response.ok) {
          // Redirect or reload to show continued message
          window.location.reload();
        } else {
          console.error('Continue failed:', response.status);
          a.disabled = false;
          a.innerHTML = `<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"></path><path d="m12 5 7 7-7 7"></path></svg> Continue`;
        }
      } catch (error) {
        console.error('Continue error:', error);
        a.disabled = false;
        a.innerHTML = `<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
          stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"></path><path d="m12 5 7 7-7 7"></path></svg> Continue`;
      }
    });

    // preferred placement: at the very end of the AI text (inline in the last block if possible)
    if (lastTextEl && lastTextEl.nodeName === 'P') {
      lastTextEl.appendChild(document.createTextNode(' '));
      lastTextEl.appendChild(a);
    } else if (ts) {
      // fallback: just before timestamp (always before it, never after)
      content.insertBefore(a, ts);
    } else {
      content.appendChild(a);
    }

    bubble.dataset.continueEnhanced = '1';
  }

  function enhanceAll() {
    document.querySelectorAll('.message-bubble.assistant').forEach(enhanceBubble);
  }

  // initial pass
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', enhanceAll);
  } else {
    enhanceAll();
  }

  // observe future messages appended by polling
  const messages = document.getElementById('chat-messages');
  if (messages && !window.__CONTINUE_OBS__) {
    window.__CONTINUE_OBS__ = new MutationObserver(muts => {
      for (const m of muts) {
        m.addedNodes.forEach(node => {
          if (!(node instanceof HTMLElement)) return;
          if (node.matches?.('.message-bubble.assistant')) enhanceBubble(node);
          node.querySelectorAll?.('.message-bubble.assistant').forEach(enhanceBubble);
        });
      }
    });
    window.__CONTINUE_OBS__.observe(messages, { childList: true, subtree: true });
  }
})();

// Old functions removed - using new idempotent approach above
