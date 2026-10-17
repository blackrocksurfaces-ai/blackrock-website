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
