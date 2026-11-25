// Word Roll adaptation for the CS AI landing page. Motion values match the source.
(() => {
  const words = ['내 서비스에', '홈페이지에', '네이버 톡톡에', '카카오톡 채널에'];
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const spring = (x, k, c) => ({ x, v: 0, t: x, k, c });
  const step = (s, dt) => { const a = -s.k * (s.x - s.t) - s.c * s.v; s.v += a * dt; s.x += s.v * dt; };
  let active = null;
  function mount() {
    const copy = document.querySelector('.hero-inner > p.muted');
    if (!copy || copy === active) return;
    active = copy;
    copy.className = 'hero-copy';
    copy.innerHTML = '직접 교육한 AI 상담사를<br><button type="button" class="word-roll" aria-label="내 서비스에 AI 상담사를 붙여보세요"><span class="word-roll-slot"></span></button> 붙여보세요.<br>고객 상담을 24시간 도와드립니다.';
    const button = copy.querySelector('.word-roll');
    const slot = copy.querySelector('.word-roll-slot');
    if (reduced.matches) { slot.textContent = words[0]; return; }
    const width = spring(0, 320, 30);
    let live = [], index = 0, last = performance.now(), nextAt = last + 2400;
    function show(word, first = false) {
      const now = performance.now();
      live.forEach(item => {
        if (item.out) return;
        item.out = true;
        item.letters.forEach((letter, i) => letter.at = now + i * 22);
        item.removeAt = now + 1000;
      });
      const el = document.createElement('span');
      el.className = 'word-roll-word';
      const letters = [...word].map(ch => {
        const node = document.createElement('span');
        node.className = 'word-roll-char'; node.textContent = ch; el.append(node);
        return { node, s: spring(first ? 0 : 1, 420, 26), at: now + 60 + el.childElementCount * 28 };
      });
      slot.append(el);
      live.push({ el, letters, out: false });
      width.t = el.offsetWidth;
      if (first) width.x = width.t;
      button.setAttribute('aria-label', word + ' AI 상담사를 붙여보세요');
    }
    function advance() { index = (index + 1) % words.length; show(words[index]); nextAt = performance.now() + 2400; }
    button.addEventListener('click', advance);
    show(words[0], true);
    function frame(now) {
      if (!button.isConnected) return;
      const dt = Math.min((now - last) / 1000, 1 / 30); last = now;
      if (now >= nextAt) advance();
      for (let i = 0; i < 4; i++) {
        step(width, dt / 4);
        live.forEach(item => item.letters.forEach(letter => {
          if (now >= letter.at) letter.s.t = item.out ? -1 : 0;
          step(letter.s, dt / 4);
        }));
      }
      slot.style.width = width.x + 'px';
      live.forEach(item => {
        item.letters.forEach(letter => {
          const y = letter.s.x;
          letter.node.style.transform = `translateY(${y * 105}%)`;
          letter.node.style.opacity = Math.max(0, Math.min(1, 1 - Math.abs(y) * .9));
        });
        if (item.removeAt && now >= item.removeAt) item.el.remove();
      });
      live = live.filter(item => item.el.isConnected);
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }
  new MutationObserver(mount).observe(document.getElementById('app'), { childList: true });
  mount();
})();
