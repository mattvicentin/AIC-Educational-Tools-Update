// Animate the rainbow background to grayscale as user scrolls
(function() {
  const bg = document.querySelector('.landing-bg');
  if (!bg) return;

  // Get the main steps container
  const steps = document.querySelector('.landing-steps');
  if (!steps) return;

  // Helper: throttle
  function throttle(fn, wait) {
    let last = 0;
    return function(...args) {
      const now = Date.now();
      if (now - last >= wait) {
        last = now;
        fn.apply(this, args);
      }
    };
  }

  function updateBgGrayscale() {
    // Get scroll progress relative to the landing steps
    const rect = steps.getBoundingClientRect();
    const windowHeight = window.innerHeight;
    // When top of steps is at top of viewport: progress = 0
    // When bottom of steps is at bottom of viewport: progress = 1
    const total = rect.height + windowHeight;
    let progress = 1 - (rect.bottom / total);
    progress = Math.max(0, Math.min(1, progress));
    // Grayscale from 0% (top) to 100% (bottom)
    const grayscale = Math.round(progress * 100);
    bg.style.filter = `grayscale(${grayscale}%)`;
  }

  // Initial update
  updateBgGrayscale();
  // Listen to scroll and resize
  window.addEventListener('scroll', throttle(updateBgGrayscale, 16));
  window.addEventListener('resize', throttle(updateBgGrayscale, 32));
})(); 