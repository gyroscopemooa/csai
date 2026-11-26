'use strict';
// DesignBookmark Step Progress, adapted for the two CS AI consultation paths.
(() => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const spring = (x, k, c) => ({ x, t: x, v: 0, k, c });
  const step = (s, dt) => { const a = -s.k * (s.x - s.t) - s.c * s.v; s.v += a * dt; s.x += s.v * dt; };
  const mounted = new WeakSet();
  function mount(root) {
    if (mounted.has(root)) return;
    mounted.add(root);
    const buttons = [...root.querySelectorAll('.unify-step')];
    const detail = root.querySelector('.unify-step-detail');
    const bar = root.querySelector('.unify-step-bar');
    const line = spring(0, 160, 22);
    const states = buttons.map(() => ({ fill: spring(0, 260, 24), check: spring(0, 140, 20), pop: spring(1, 500, 14) }));
    let current = 0, visible = false, userUntil = 0, nextAt = performance.now() + 1500, last = performance.now();
    const observer = new IntersectionObserver(entries => { visible = entries[0].isIntersecting; if (visible) nextAt = performance.now() + 1500; }, { threshold: .2 });
    observer.observe(root);
    function select(index, user = false) {
      current = index;
      if (user) userUntil = performance.now() + 8000;
      line.t = index / (buttons.length - 1);
      buttons.forEach((button, i) => {
        const done = i < index || index === buttons.length - 1 && i === index;
        const active = i === index;
        button.classList.toggle('done', done);
        button.classList.toggle('active', active);
        button.setAttribute('aria-current', active ? 'step' : 'false');
        states[i].fill.t = done ? 1 : 0;
        states[i].check.t = done ? 1 : 0;
        if (active) { states[i].pop.x = .7; states[i].pop.v = 6; }
      });
      detail.textContent = buttons[index].title;
      nextAt = performance.now() + (index === buttons.length - 1 ? 2400 : 1800);
    }
    buttons.forEach((button, i) => button.addEventListener('click', () => select(i, true)));
    select(0);
    function frame(now) {
      if (!root.isConnected) { observer.disconnect(); return; }
      const dt = Math.min((now - last) / 1000, 1 / 30); last = now;
      if (visible && !reduced.matches && now > nextAt && now > userUntil) select((current + 1) % buttons.length);
      if (!reduced.matches) for (let j = 0; j < 4; j++) { step(line, dt / 4); states.forEach(s => { step(s.fill, dt / 4); step(s.check, dt / 4); step(s.pop, dt / 4); }); }
      bar.style.width = `${Math.max(0, Math.min(66.667, line.x * 66.667))}%`;
      buttons.forEach((button, i) => {
        const state = states[i], dot = button.querySelector('.unify-step-dot'), path = button.querySelector('path');
        dot.style.transform = `scale(${reduced.matches ? 1 : state.pop.x})`;
        dot.style.setProperty('--fill', Math.max(0, Math.min(1, state.fill.x)).toFixed(3));
        path.style.strokeDashoffset = String(22 * (1 - Math.max(0, Math.min(1, state.check.x))));
      });
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }
  const scan = () => document.querySelectorAll('[data-step-progress]').forEach(mount);
  new MutationObserver(scan).observe(document.getElementById('app'), { childList: true, subtree: true });
  scan();
})();
