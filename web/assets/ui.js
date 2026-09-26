/* =====================================================================
   ui.js - shared behaviour for every terrific-tpu page
   - one navigation bar for all pages (current page highlighted)
   - dark/light theme (remembered)
   - reveal-on-scroll, number tickers, spotlight cards, copy buttons
   ===================================================================== */
(function () {
  const root = document.documentElement;
  let theme = "dark";
  try { theme = localStorage.getItem("tt-theme") || "dark"; } catch (e) {}
  root.dataset.theme = theme;

  const REPO = "https://github.com/Normansrule/terrific-tpu";
  const PAGES = [
    ["index.html", "Home"], ["tour.html", "3-D chip tour"], ["chip.html", "Chip simulator"],
    ["playground.html", "Systolic array"], ["array3d.html", "Array in 3-D"], ["apps.html", "Applications"],
    ["challenges.html", "Challenges"], ["explorers.html", "Numbers & roofline"]
  ];
  const LOGO = `<svg viewBox="0 0 32 32" aria-hidden="true"><defs><linearGradient id="lg" x1="0" x2="1" y1="0" y2="1">
    <stop offset="0" stop-color="#60A5FA"/><stop offset=".5" stop-color="#A78BFA"/><stop offset="1" stop-color="#E879F9"/></linearGradient></defs>
    <rect x="3" y="3" width="26" height="26" rx="7" fill="none" stroke="url(#lg)" stroke-width="2.4"/>
    ${[0,1,2].map(r => [0,1,2].map(c => `<rect x="${8.5 + c * 5.5}" y="${8.5 + r * 5.5}" width="4" height="4" rx="1.2" fill="${r + c === 2 ? "#E879F9" : "#A78BFA"}" opacity="${r + c === 2 ? 1 : .55}"/>`).join("")).join("")}</svg>`;
  const here = (location.pathname.split("/").pop() || "index.html");
  document.querySelectorAll("nav.site").forEach(nav => {
    nav.innerHTML = `<a class="brand" href="index.html">${LOGO}<span>terrific-tpu</span></a>` +
      PAGES.map(([h, t]) => `<a href="${h}"${h === here ? ' aria-current="page"' : ""}>${t}</a>`).join("") +
      `<span class="spacer"></span><button class="tt" id="tt" aria-label="Toggle light and dark theme">${theme === "dark" ? "☀" : "☾"}</button>` +
      `<a class="gh" href="${REPO}" aria-label="Source on GitHub">★ GitHub</a>`;
  });
  const tt = document.getElementById("tt");
  if (tt) tt.onclick = () => {
    theme = root.dataset.theme === "dark" ? "light" : "dark"; root.dataset.theme = theme;
    try { localStorage.setItem("tt-theme", theme); } catch (e) {}
    tt.textContent = theme === "dark" ? "☀" : "☾";
    window.dispatchEvent(new Event("themechange"));
  };

  if (!document.querySelector("footer.site") && !("nofooter" in document.body.dataset)) {
    const f = document.createElement("footer"); f.className = "site";
    f.innerHTML = `<span>terrific-tpu · a Tensor Processing Unit (TPU) you can read, run, and break · MIT license</span>
      <span><a href="${REPO}">Source</a> · <a href="${REPO}/tree/main/docs">Lessons</a> · <a href="${REPO}#run-it-ubuntu-or-windows-subsystem-for-linux">Run it locally</a></span>`;
    document.body.appendChild(f);
  }

  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  // reveal on scroll
  const io = "IntersectionObserver" in window ? new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
  }), { threshold: 0.12 }) : null;
  document.querySelectorAll("[data-reveal]").forEach((el, i) => {
    el.style.transitionDelay = (el.dataset.reveal || 0) + "ms";
    io && !reduce ? io.observe(el) : el.classList.add("in");
  });
  // number tickers
  const tick = el => {
    const end = parseFloat(el.dataset.count), dec = (el.dataset.count.split(".")[1] || "").length, t0 = performance.now(), dur = 1400;
    const fmt = v => v.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
    if (reduce) { el.textContent = fmt(end); return; }
    const step = now => { const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 3);
      el.textContent = fmt(end * e); if (p < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  };
  const io2 = "IntersectionObserver" in window ? new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting) { tick(e.target); io2.unobserve(e.target); } })) : null;
  document.querySelectorAll("[data-count]").forEach(el => io2 ? io2.observe(el) : tick(el));
  // spotlight cards
  document.querySelectorAll(".spot").forEach(el => el.addEventListener("pointermove", e => {
    const r = el.getBoundingClientRect();
    el.style.setProperty("--mx", (e.clientX - r.left) + "px"); el.style.setProperty("--my", (e.clientY - r.top) + "px");
  }));
  // copy buttons
  document.querySelectorAll("pre.cmd").forEach(pre => {
    const b = document.createElement("button"); b.className = "copy"; b.textContent = "Copy";
    b.onclick = () => {
      const txt = [...pre.querySelectorAll("code")].map(c => c.innerText).join("\n") || pre.innerText;
      const clean = txt.split("\n").filter(l => !l.trim().startsWith("#")).join("\n").trim();
      (navigator.clipboard ? navigator.clipboard.writeText(clean) : Promise.reject()).then(
        () => { b.textContent = "Copied ✓"; setTimeout(() => b.textContent = "Copy", 1500); },
        () => { b.textContent = "Select + Ctrl-C"; });
    };
    pre.appendChild(b);
  });
})();
