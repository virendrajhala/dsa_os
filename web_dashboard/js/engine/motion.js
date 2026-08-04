export function reducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function viewSwitch(fn) {
  if (reducedMotion() || !document.startViewTransition) {
    fn();
    return;
  }
  document.startViewTransition(fn);
}

export function animateCount(el, value, { format = (v) => String(v) } = {}) {
  if (el.dataset.counted === String(value)) return; // once per value per load
  el.dataset.counted = String(value);
  if (reducedMotion() || !(value > 0)) {
    el.textContent = format(value);
    return;
  }
  const start = performance.now();
  const dur = 500;
  const tick = (now) => {
    const t = Math.min(1, (now - start) / dur);
    el.textContent = format(Math.round(value * (1 - Math.pow(1 - t, 3))));
    if (t < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}
