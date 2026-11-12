// Countdowns: <div data-countdown="ISO date"> with [data-d|h|m|s] children.
document.querySelectorAll('[data-countdown]').forEach((el) => {
  const target = new Date(el.dataset.countdown);
  const set = (k, v) => (el.querySelector(`[data-${k}]`).textContent = String(v).padStart(2, '0'));
  let live = false; // only auto-reload if we watched it reach zero (avoids loops on wrong clocks)
  const tick = () => {
    const s = Math.floor((target - Date.now()) / 1000);
    if (s <= 0) {
      el.classList.add('done');
      clearInterval(timer);
      if (live && 'reload' in el.dataset) location.reload();
      return;
    }
    live = true;
    set('d', Math.floor(s / 86400));
    set('h', Math.floor(s / 3600) % 24);
    set('m', Math.floor(s / 60) % 60);
    set('s', s % 60);
  };
  const timer = setInterval(tick, 1000);
  tick();
});

const music = document.getElementById('music');
if (music) {
  const btn = document.querySelector('.music-btn');
  const sync = () => btn.setAttribute('aria-pressed', String(!music.paused));
  music.addEventListener('play', sync);
  music.addEventListener('pause', sync);
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    music.paused ? music.play() : music.pause();
  });
}

// Cover: tap -> voice plays over the photo -> 1s pause -> curtain lifts -> song starts
const cover = document.querySelector('.cover');
if (document.body.classList.contains('sealed')) {
  const voice = document.getElementById('voice');
  const btn = cover.querySelector('.cover-btn');
  const lift = () => {
    if (cover.classList.contains('opening')) return;
    voice?.pause();
    cover.classList.add('opening');
    document.body.classList.remove('sealed');
    try { sessionStorage.opened = 1; } catch (e) {}
    if (music) {
      music.muted = false;
      music.play().catch(() => {});
    }
    setTimeout(() => cover.remove(), 1100);
  };
  btn.focus();
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    cover.classList.add('playing');
    // iPhone only lets audio start inside a tap: start the song muted and pause it at once.
    // It stays unlocked and buffered at second 0, so it starts instantly when the curtain lifts.
    if (music) {
      music.muted = true;
      music.play().then(() => cover.classList.contains('opening') || music.pause()).catch(() => {});
    }
    if (!voice) return lift();
    // countdown = what is left of the voice + the 1s pause, so guests know to wait
    const count = cover.querySelector('.cover-wait b');
    const tick = () => {
      if (voice.duration) count.textContent = Math.max(1, Math.ceil(voice.duration - voice.currentTime + 1));
    };
    setInterval(tick, 250);
    voice.addEventListener('ended', () => setTimeout(lift, 1000));
    voice.addEventListener('error', lift);
    voice.play().catch(lift);
    cover.addEventListener('click', lift); // a second tap skips the voice
  });
} else {
  cover.remove();
  // no cover this time (already opened in this tab): the song starts on the first tap
  if (music) document.addEventListener('click', () => music.paused && music.play().catch(() => {}), { once: true });
}

const calm = matchMedia('(prefers-reduced-motion: reduce)').matches;

document.querySelectorAll('.carousel').forEach((c) => {
  const track = c.querySelector('.carousel-track');
  const step = () => track.firstElementChild.offsetWidth + 20;
  c.querySelectorAll('.carousel-btn').forEach((b) =>
    b.addEventListener('click', () => track.scrollBy({ left: b.dataset.dir * step(), behavior: 'smooth' }))
  );
  if (calm) return;
  // autoplay until the guest touches it
  const auto = setInterval(() => {
    const end = track.scrollLeft + track.clientWidth >= track.scrollWidth - 5;
    track.scrollTo({ left: end ? 0 : track.scrollLeft + step(), behavior: 'smooth' });
  }, 3500);
  c.addEventListener('pointerdown', () => clearInterval(auto), { once: true });
});

// Panels pop in like comic frames when scrolled into view
const seen = new IntersectionObserver(
  (entries) => entries.forEach((e) => e.isIntersecting && (e.target.classList.add('in'), seen.unobserve(e.target))),
  { rootMargin: '0px 0px -12% 0px' } // no threshold: a very tall panel (big album) must still appear
);
document.querySelectorAll('.panel').forEach((p) => seen.observe(p));

// Confetti right after confirming
if (!calm && location.hash === '#asistencia' && document.querySelector('.status-yes')) {
  const colors = ['#e3122b', '#1b4fd6', '#ffd21f', '#ff6fae', '#fff'];
  for (let i = 0; i < 60; i++) {
    const c = document.createElement('i');
    c.className = 'confetti';
    c.style.cssText = `left:${Math.random() * 94}%;background:${colors[i % 5]};animation-duration:${2 + Math.random() * 2.5}s;animation-delay:${Math.random()}s`;
    c.addEventListener('animationend', () => c.remove());
    document.body.append(c);
  }
}
