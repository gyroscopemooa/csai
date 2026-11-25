// Inspired by DesignBookmark Scramble Text. The original title stays available to assistive tech.
(() => {
  const phrase = '나처럼 상담하는 AI';
  const glyphs = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789#%&*+=/<>';
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let active = null;
  function mount() {
    const title = document.querySelector('.hero h1');
    if (!title || title === active) return;
    active = title;
    if (reduced.matches) return;
    title.classList.add('scramble-title');
    title.setAttribute('aria-label', phrase);
    const cells = [...phrase].map(() => {
      const span = document.createElement('span');
      span.className = 'scramble-cell';
      span.setAttribute('aria-hidden', 'true');
      return span;
    });
    const caret = document.createElement('span');
    caret.className = 'scramble-caret';
    caret.setAttribute('aria-hidden', 'true');
    title.replaceChildren(...cells, caret);
    let frame = 0;
    function decode() {
      cancelAnimationFrame(frame);
      const start = performance.now();
      const settles = cells.map((_, i) => 180 + i * 35 + Math.random() * 280);
      const ticks = cells.map(() => 0);
      cells.forEach(cell => cell.classList.remove('ok'));
      function paint(now) {
        let pending = false;
        cells.forEach((cell, i) => {
          const target = phrase[i];
          if (now - start >= settles[i]) {
            cell.textContent = target;
            cell.classList.add('ok');
          } else {
            pending = true;
            if (target === ' ') { cell.textContent = ' '; cell.classList.add('ok'); }
            else if (now >= ticks[i]) {
              cell.textContent = glyphs[(Math.random() * glyphs.length) | 0];
              ticks[i] = now + 55;
            }
          }
        });
        caret.style.opacity = pending || Math.floor(now / 550) % 2 === 0 ? '1' : '0';
        if (pending) frame = requestAnimationFrame(paint);
      }
      frame = requestAnimationFrame(paint);
    }
    title.addEventListener('pointerenter', decode);
    decode();
  }
  new MutationObserver(mount).observe(document.getElementById('app'), { childList: true });
  mount();
})();
