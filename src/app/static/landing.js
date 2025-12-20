// Subtle grayscale on scroll for the background gradient
document.addEventListener('scroll', () => {
  const bg = document.querySelector('.landing-bg');
  if (!bg) return;
  const max = 0.6; // max grayscale at bottom
  const progress = Math.min(1, window.scrollY / (document.body.scrollHeight - window.innerHeight || 1));
  const value = Math.min(max, progress * max);
  bg.style.filter = `grayscale(${(value * 100).toFixed(0)}%)`;
});


