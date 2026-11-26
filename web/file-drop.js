'use strict';
// DesignBookmark File Drop motion, adapted to the real education upload flow.
(() => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const springs = new WeakMap();
  const spring = (x, k, c) => ({ x, t: x, v: 0, k, c });
  function animate(zone) {
    const state = { hover: spring(0, 300, 26), circle: spring(1, 420, 14), icon: spring(1, 420, 30), progress: spring(0, 420, 30), ring: spring(0, 300, 30), glow: spring(0, 260, 21), check: spring(0, 200, 26) };
    springs.set(zone, state);
    let last = performance.now();
    function frame(now) {
      if (!zone.isConnected) return;
      const active = zone.matches(':hover, :focus-visible, .dragging');
      state.hover.t = active ? 1 : 0;
      state.circle.t = zone.classList.contains('success') ? 1.16 : zone.classList.contains('selected') ? 1.1 : active ? 1.13 : 1;
      state.icon.t = zone.classList.contains('uploading') ? .8 : 1;
      state.progress.t = zone.classList.contains('uploading') ? 1 : 0;
      state.ring.t = zone.classList.contains('uploading') ? 1 : 0;
      state.glow.t = zone.classList.contains('success') ? 1 : 0;
      state.check.t = zone.classList.contains('success') ? 1 : 0;
      const dt = Math.min((now - last) / 1000, 1 / 30); last = now;
      if (!reduced.matches) for (let i = 0; i < 4; i++) Object.values(state).forEach(s => { const d = dt / 4, a = -s.k * (s.x - s.t) - s.c * s.v; s.v += a * d; s.x += s.v * d; });
      const icon = zone.querySelector('.file-drop-icon');
      icon.style.transform = reduced.matches ? '' : `translateY(${-2 * state.hover.x}px) scale(${state.circle.x * state.icon.x})`;
      icon.style.boxShadow = reduced.matches ? '' : `0 0 ${Math.max(0, 20 * state.glow.x)}px rgba(25,160,91,.25)`;
      zone.style.setProperty('--drop-ring', Math.max(0, Math.min(1, state.ring.x)).toFixed(3));
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }
  const scan = () => document.querySelectorAll('.education-file-drop').forEach(zone => { if (!springs.has(zone)) animate(zone); });
  new MutationObserver(scan).observe(document.getElementById('app'), { childList: true, subtree: true });
  scan();
})();
