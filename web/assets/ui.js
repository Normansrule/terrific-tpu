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
    ["index.html", "Home", "Start here: the story of a chip that only multiplies", "main"],
    ["tour.html", "3-D tour", "Fly through the whole chip while it runs a neural network", "main"],
    ["zoom.html", "Pod → transistor", "One continuous zoom from 4,096 chips down to four transistors", "main"],
    ["xray.html", "Chip X-ray", "Zoom from the die down to single standard cells", "more"],
    ["race.html", "The race", "CPU vs vector unit vs systolic array: speed and energy", "more"],
    ["compile.html", "Compiler", "Design a network, compile it to TinyTPU, run it", "main"],
    ["challenges.html", "Challenges", "Program the chip, beat the par, earn stars", "main"],
    ["research.html", "Research", "Papers behind every idea, mapped to the code", "main"],
    ["quiz.html", "Quiz", "24 questions with explanations, and a printable worksheet", "more"],
    ["lab.html", "Live lab", "Run three experiments in the browser on both chip models", "more"],
    ["present.html", "Lecture slides", "15 slides with speaker notes; arrow keys, F for fullscreen, print to PDF", "more"],
    ["chip.html", "Chip simulator", "Write assembly and step it clock by clock", "more"],
    ["wave.html", "Waveform viewer", "Every signal, every cycle, like GTKWave in the browser", "more"],
    ["playground.html", "Systolic array", "Edit weights and inputs, watch every multiply", "more"],
    ["array3d.html", "Array in 3-D", "Spin a 24 × 24 array with live partial sums", "more"],
    ["apps.html", "Applications", "Image filters, quantum search, graph triangles", "more"],
    ["explorers.html", "Numbers & roofline", "Quantization and the roofline model", "more"]
  ];
  const DOCS = [["01-what-is-a-tpu", "Lesson 1 · What is a TPU?"], ["04-systolic-arrays", "Lesson 4 · Systolic arrays"], ["07-architecture", "Lesson 7 · Architecture"],
    ["08-rtl-walkthrough", "Lesson 8 · RTL walkthrough"], ["10-pipelining-v2", "Lesson 10 · Pipelining v2"], ["12-rtl-to-silicon", "Lesson 12 · RTL to silicon"],
    ["15-application-gallery", "Lesson 15 · Application gallery"], ["16-experiments", "Lesson 16 · Experiments"], ["17-labs", "Lesson 17 · Labs"], ["19-research-frontiers", "Lesson 19 · Research frontiers"], ["20-reading-the-tpu-paper", "Lesson 20 · Reading the TPU paper"], ["21-fpga", "Lesson 21 · Running on a real FPGA"], ["glossary", "Glossary"]];
  const LOGO = `<svg viewBox="0 0 32 32" aria-hidden="true"><defs><linearGradient id="lg" x1="0" x2="1" y1="0" y2="1">
    <stop offset="0" stop-color="#60A5FA"/><stop offset=".5" stop-color="#A78BFA"/><stop offset="1" stop-color="#E879F9"/></linearGradient></defs>
    <rect x="3" y="3" width="26" height="26" rx="7" fill="none" stroke="url(#lg)" stroke-width="2.4"/>
    ${[0,1,2].map(r => [0,1,2].map(c => `<rect x="${8.5 + c * 5.5}" y="${8.5 + r * 5.5}" width="4" height="4" rx="1.2" fill="${r + c === 2 ? "#E879F9" : "#A78BFA"}" opacity="${r + c === 2 ? 1 : .55}"/>`).join("")).join("")}</svg>`;
  const here = (location.pathname.split("/").pop() || "index.html");
  const moreHere = PAGES.some(p => p[3] === "more" && p[0] === here);
  document.querySelectorAll("nav.site").forEach(nav => {
    nav.innerHTML = `<a class="brand" href="index.html">${LOGO}<span>terrific-tpu</span></a>` +
      PAGES.filter(p => p[3] === "main").map(([h, t]) => `<a href="${h}"${h === here ? ' aria-current="page"' : ""}>${t}</a>`).join("") +
      `<div class="more"><button class="morebtn" aria-expanded="false" aria-haspopup="true"${moreHere ? ' aria-current="page"' : ""}>Explore ▾</button><div class="menu" role="menu">` +
      PAGES.filter(p => p[3] === "more").map(([h, t, d]) => `<a role="menuitem" href="${h}"${h === here ? ' aria-current="page"' : ""}><b>${t}</b><span>${d}</span></a>`).join("") + `</div></div>` +
      `<span class="spacer"></span><button class="kbar" id="kbar" aria-label="Search pages and lessons">⌕ Search <kbd>Ctrl K</kbd></button>` +
      `<button class="tt" id="tt" aria-label="Toggle light and dark theme">${theme === "dark" ? "☀" : "☾"}</button>` +
      `<a class="gh" href="${REPO}" aria-label="Source on GitHub">★ GitHub</a>`;
    const mb = nav.querySelector(".morebtn"), menu = nav.querySelector(".menu");
    mb.onclick = e => { e.stopPropagation(); const open = mb.getAttribute("aria-expanded") !== "true"; mb.setAttribute("aria-expanded", open); menu.classList.toggle("open", open);
      if (open) { const r = mb.getBoundingClientRect(); menu.style.left = Math.min(r.left, innerWidth - 330) + "px"; menu.style.top = (r.bottom + 6) + "px"; } };
    document.addEventListener("click", () => { mb.setAttribute("aria-expanded", "false"); menu.classList.remove("open"); });
  });

  // ---------------- command palette (Ctrl/Cmd + K, or "/")
  const pal = document.createElement("div"); pal.className = "palette"; pal.hidden = true;
  pal.innerHTML = `<div class="pbox" role="dialog" aria-label="Search"><input placeholder="Jump to a page or lesson…" aria-label="Search"><ul></ul><div class="phint">↑ ↓ to move · Enter to open · Esc to close</div></div>`;
  document.body.appendChild(pal);
  const items = PAGES.map(([h, t, d]) => ({ href: h, t, d, k: "page" })).concat(DOCS.map(([f, t]) => ({ href: `${REPO}/blob/main/docs/${f}.md`, t, d: "on GitHub", k: "lesson" })),
    [{ href: REPO, t: "Source code on GitHub", d: "Verilog, tools, lessons", k: "link" }]);
  const pin = pal.querySelector("input"), pul = pal.querySelector("ul"); let sel = 0, shown = items;
  const renderPal = () => { const q = pin.value.toLowerCase().trim();
    shown = items.filter(i => !q || (i.t + " " + i.d).toLowerCase().split(/\s+/).some(w => w.startsWith(q)) || (i.t + i.d).toLowerCase().includes(q)).slice(0, 12);
    sel = Math.min(sel, Math.max(0, shown.length - 1));
    pul.innerHTML = shown.map((i, n) => `<li${n === sel ? ' class="sel"' : ""}><a href="${i.href}"><span class="k">${i.k}</span><b>${i.t}</b><span>${i.d}</span></a></li>`).join("") || `<li class="none">No match</li>`; };
  const openPal = () => { pal.hidden = false; pin.value = ""; sel = 0; renderPal(); pin.focus(); };
  const closePal = () => { pal.hidden = true; };
  pin.addEventListener("input", () => { sel = 0; renderPal(); });
  pin.addEventListener("keydown", e => { if (e.key === "ArrowDown") { sel = Math.min(shown.length - 1, sel + 1); renderPal(); e.preventDefault(); }
    if (e.key === "ArrowUp") { sel = Math.max(0, sel - 1); renderPal(); e.preventDefault(); }
    if (e.key === "Enter" && shown[sel]) location.href = shown[sel].href; if (e.key === "Escape") closePal(); });
  pal.addEventListener("click", e => { if (e.target === pal) closePal(); });
  addEventListener("keydown", e => { const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName);
    if ((e.key === "k" && (e.ctrlKey || e.metaKey)) || (e.key === "/" && !typing)) { e.preventDefault(); pal.hidden ? openPal() : closePal(); } });
  const kb = document.getElementById("kbar"); if (kb) kb.onclick = openPal;

  // ---------------- scroll progress bar
  const prog = document.createElement("div"); prog.className = "progress"; document.body.appendChild(prog);
  addEventListener("scroll", () => { const h = document.documentElement.scrollHeight - innerHeight; prog.style.transform = `scaleX(${h > 0 ? scrollY / h : 0})`; }, { passive: true });

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
