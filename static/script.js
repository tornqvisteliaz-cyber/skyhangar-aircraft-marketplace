// SkyHangar minimal client-side helpers

document.addEventListener('DOMContentLoaded', () => {
  // Auto-hide success messages after a few seconds if present
  const alerts = document.querySelectorAll('.alert-success');
  alerts.forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity 0.4s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 400);
    }, 4000);
  });
});
