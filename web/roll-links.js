// DesignBookmark Roll Links movement, adapted to CS AI's plain JavaScript UI.
(() => {
  const examples = [
    ['고객 질문에 나 대신 답해줘', '교육한 내용을 바탕으로 고객 상담을 진행합니다.'],
    ['나 대신 일정 예약을 잡아줘', '예약 요청을 받고 확인할 수 있습니다.'],
    ['예약 완료되면 알림으로 알려줘', '예약 상태와 알림 설정을 한곳에서 관리합니다.'],
    ['환불 문의를 정리해줘', '고객의 요청을 상담 기록과 업무로 정리합니다.'],
  ];
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const spring = () => ({ x: 0, v: 0, t: 0, k: 380, c: 24 });
  const step = (s, dt) => { const a = -s.k * (s.x - s.t) - s.c * s.v; s.v += a * dt; s.x += s.v * dt; };
  let active = null;
  function mount() {
    const copy = document.querySelector('.hero-copy');
    if (!copy || copy === active) return;
    active = copy;
    const section = document.createElement('section');
    section.className = 'hero-examples';
    section.innerHTML = '<p class="hero-examples-title">CS AI에게 이렇게 부탁해 보세요</p><div class="hero-examples-list"></div><p class="hero-examples-detail" aria-live="polite"></p>';
    copy.after(section);
    const list = section.querySelector('.hero-examples-list');
    const detail = section.querySelector('.hero-examples-detail');
    const links = examples.map(([label, description], index) => {
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'hero-examples-link'; button.setAttribute('aria-label', label);
      const num = document.createElement('span'); num.className = 'num'; num.textContent = String(index + 1).padStart(2, '0'); num.setAttribute('aria-hidden', 'true');
      const letters = document.createElement('span'); letters.className = 'letters'; letters.setAttribute('aria-hidden', 'true');
      const cells = [...label].map(ch => {
        const shell = document.createElement('span'); shell.className = 'letter';
        const inner = document.createElement('span'); inner.className = 'letter-inner';
        for (let i = 0; i < 2; i++) { const glyph = document.createElement('i'); glyph.textContent = ch; inner.append(glyph); }
        shell.append(inner); letters.append(shell);
        return { inner, s: spring(), at: 0 };
      });
      button.append(num, letters); list.append(button);
      const link = { button, cells, description, on: false };
      button.addEventListener('pointerenter', () => { pointer = true; select(link); });
      button.addEventListener('focus', () => select(link));
      button.addEventListener('click', () => select(link));
      return link;
    });
    let pointer = false, auto = 0, autoAt = performance.now() + 800, last = performance.now();
    function select(link) {
      const now = performance.now();
      links.forEach(item => {
        item.on = item === link;
        item.button.classList.toggle('on', item.on);
        item.cells.forEach((cell, i) => { cell.at = now + i * 30; cell.s.t = item.on ? 1 : 0; });
      });
      list.classList.add('hot'); detail.textContent = link.description;
    }
    list.addEventListener('pointerleave', () => { pointer = false; autoAt = performance.now() + 900; });
    function frame(now) {
      if (!section.isConnected) return;
      const dt = Math.min((now - last) / 1000, 1 / 30); last = now;
      if (!pointer && now >= autoAt) { select(links[auto]); auto = (auto + 1) % links.length; autoAt = now + 1450; }
      if (!reduced.matches) for (let k = 0; k < 4; k++) links.forEach(link => link.cells.forEach(cell => { if (now >= cell.at) step(cell.s, dt / 4); }));
      links.forEach(link => link.cells.forEach(cell => { cell.inner.style.transform = `translateY(${-cell.s.x * 50}%)`; }));
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }
  let benefitsActive = null;
  function mountBenefits() {
    const grid = document.querySelector('.landing-benefit-grid');
    if (!grid || grid === benefitsActive) return;
    benefitsActive = grid;
    const entries = [...grid.querySelectorAll('.landing-benefit')].map(article => {
      const title = article.querySelector('.landing-roll-title');
      const label = title.textContent;
      title.textContent = '';
      title.setAttribute('aria-label', label);
      title.tabIndex = 0;
      const letters = document.createElement('span');
      letters.className = 'roll-letters';
      letters.setAttribute('aria-hidden', 'true');
      const cells = [];
      label.split(' ').forEach((word, wordIndex) => {
        if (wordIndex) letters.append(document.createTextNode(' '));
        const group = document.createElement('span'); group.className = 'roll-word';
        [...word].forEach(ch => {
          const shell = document.createElement('span'); shell.className = 'roll-letter';
          const inner = document.createElement('span'); inner.className = 'roll-letter-inner';
          for (let i = 0; i < 2; i++) { const glyph = document.createElement('i'); glyph.textContent = ch; inner.append(glyph); }
          shell.append(inner); group.append(shell);
          cells.push({ inner, s: spring(), at: 0 });
        });
        letters.append(group);
      });
      title.append(letters);
      return { article, title, cells, on: false };
    });
    let pointer = false, visible = false, auto = 0, autoOn = false, autoAt = performance.now() + 800, last = performance.now(), observer = null;
    if ('IntersectionObserver' in window) {
      observer = new IntersectionObserver(events => {
        visible = events[0].isIntersecting;
        if (visible) autoAt = performance.now() + 800;
        else {
          grid.classList.remove('hot');
          entries.forEach(item => {
            item.on = false; item.article.classList.remove('on');
            item.cells.forEach(cell => { cell.s.x = 0; cell.s.v = 0; cell.s.t = 0; });
          });
        }
      }, { threshold: 0.12 });
      observer.observe(grid);
    } else visible = true;
    function select(entry) {
      const now = performance.now();
      entries.forEach(item => {
        item.on = item === entry;
        item.article.classList.toggle('on', item.on);
        item.cells.forEach((cell, i) => { cell.at = now + i * 30; cell.s.t = item.on ? 1 : 0; });
      });
      grid.classList.toggle('hot', !!entry);
    }
    entries.forEach(entry => {
      entry.article.addEventListener('pointerenter', () => { pointer = true; select(entry); });
      entry.title.addEventListener('focus', () => { pointer = true; select(entry); });
      entry.title.addEventListener('blur', () => { pointer = false; autoAt = performance.now() + 900; });
      entry.title.addEventListener('click', () => { select(entry); autoAt = performance.now() + 1800; });
    });
    grid.addEventListener('pointerleave', () => { pointer = false; autoAt = performance.now() + 900; });
    function frame(now) {
      if (!grid.isConnected) { observer?.disconnect(); return; }
      const dt = Math.min((now - last) / 1000, 1 / 30); last = now;
      if (visible && !pointer && now >= autoAt) {
        if (autoOn) { select(null); autoOn = false; auto = (auto + 1) % entries.length; autoAt = now + 550; }
        else {
          const inView = item => { const r = item.article.getBoundingClientRect(); return r.bottom > 60 && r.top < innerHeight - 60; };
          if (!inView(entries[auto])) { const next = entries.findIndex(inView); if (next >= 0) auto = next; }
          const entry = entries[auto];
          if (inView(entry)) { select(entry); autoOn = true; autoAt = now + Math.max(2300, entry.cells.length * 40 + 900); }
          else autoAt = now + 500;
        }
      }
      if (visible && !reduced.matches) for (let k = 0; k < 4; k++) entries.forEach(item => item.cells.forEach(cell => { if (now >= cell.at) step(cell.s, dt / 4); }));
      entries.forEach(item => item.cells.forEach(cell => { cell.inner.style.transform = `translateY(${-cell.s.x * 50}%)`; }));
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }
  const mountAll = () => { mount(); mountBenefits(); };
  new MutationObserver(mountAll).observe(document.getElementById('app'), { childList: true, subtree: true });
  mountAll();
})();
