(function () {
  var yr = document.getElementById('yr');
  if (yr) yr.textContent = new Date().getFullYear();

  var toggle = document.querySelector('.nav-toggle');
  var nav = document.getElementById('nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      toggle.textContent = open ? 'Close' : 'Menu';
    });
  }

  // Quote form: sends to FormSubmit, which emails the request to you.
  var form = document.getElementById('quote');
  if (!form) return;
  var note = document.getElementById('formNote');
  var btn = form.querySelector('button[type=submit]');

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var ok = true;
    ['name', 'phone'].forEach(function (n) {
      var el = form.elements[n];
      var bad = !el.value.trim();
      el.classList.toggle('invalid', bad);
      if (bad) ok = false;
    });
    if (!ok) {
      note.textContent = 'Please add your name and phone number.';
      return;
    }
    btn.disabled = true;
    btn.textContent = 'Sending...';
    fetch(form.action, {
      method: 'POST',
      body: new FormData(form),
      headers: { Accept: 'application/json' }
    }).then(function (res) {
      return res.json().then(function (j) { if (!res.ok || String(j.success) !== "true") throw new Error("send failed"); });
    }).then(function () {
      form.innerHTML =
        '<div class="form-done"><h3>Thanks, your request is in.</h3>' +
        '<p>We\'ll be in touch shortly to book your free quote. Need us sooner? Call or text ' +
        '<a href="tel:+14038662915">403-866-2915</a>.</p></div>';
    }).catch(function () {
      btn.disabled = false;
      btn.textContent = 'Send quote request';
      note.innerHTML = 'Something went wrong sending your request. Please call or text ' +
        '<a href="tel:+14038662915">403-866-2915</a> or email ' +
        '<a href="mailto:blackrocksurfaces@gmail.com">blackrocksurfaces@gmail.com</a>.';
    });
  });
})();

// Reviews carousel
(function () {
  var root = document.querySelector('.carousel');
  if (!root) return;
  var track = root.querySelector('.track');
  var slides = track.querySelectorAll('.slide');
  var dots = document.querySelectorAll('#reviews .dot');
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var current = 0, timer = null;

  function go(i) {
    current = (i + slides.length) % slides.length;
    track.scrollTo({ left: slides[current].offsetLeft - track.offsetLeft, behavior: reduce ? 'auto' : 'smooth' });
    mark();
  }
  function mark() {
    dots.forEach(function (d, j) { d.setAttribute('aria-current', j === current ? 'true' : 'false'); });
  }
  root.querySelector('.prev').addEventListener('click', function () { go(current - 1); restart(); });
  root.querySelector('.next').addEventListener('click', function () { go(current + 1); restart(); });
  dots.forEach(function (d, j) { d.addEventListener('click', function () { go(j); restart(); }); });
  track.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowRight') { e.preventDefault(); go(current + 1); restart(); }
    if (e.key === 'ArrowLeft') { e.preventDefault(); go(current - 1); restart(); }
  });
  var t;
  track.addEventListener('scroll', function () {
    clearTimeout(t);
    t = setTimeout(function () {
      var i = Math.round(track.scrollLeft / track.clientWidth);
      if (i !== current) { current = i; mark(); }
    }, 80);
  });
  function start() { if (!reduce && !timer) timer = setInterval(function () { go(current + 1); }, 7000); }
  function stop() { clearInterval(timer); timer = null; }
  function restart() { stop(); start(); }
  root.addEventListener('mouseenter', stop);
  root.addEventListener('mouseleave', start);
  root.addEventListener('focusin', stop);
  root.addEventListener('focusout', start);
  mark();
  start();
})();
