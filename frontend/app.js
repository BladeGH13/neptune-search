// ── Config ────────────────────────────────────────────────────────────────
const API_BASE = "https://neptune-search-api.onrender.com"; // Change to your Render URL
// const API_BASE = "http://localhost:8000";  // Uncomment for local dev

// ── Starfield ─────────────────────────────────────────────────────────────
(function initStars() {
  const canvas = document.getElementById("stars");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  let stars = [];

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    generateStars();
  }

  function generateStars() {
    stars = Array.from({ length: 180 }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: Math.random() * 1.5 + 0.2,
      alpha: Math.random() * 0.8 + 0.2,
      speed: Math.random() * 0.3 + 0.05,
      twinkleSpeed: Math.random() * 0.02 + 0.005,
      twinklePhase: Math.random() * Math.PI * 2,
    }));
  }

  function draw(t) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const s of stars) {
      s.twinklePhase += s.twinkleSpeed;
      const brightness = s.alpha * (0.7 + 0.3 * Math.sin(s.twinklePhase));
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(200, 230, 255, ${brightness})`;
      ctx.fill();
    }
    requestAnimationFrame(draw);
  }

  window.addEventListener("resize", resize);
  resize();
  requestAnimationFrame(draw);
})();

// ── Autocomplete ──────────────────────────────────────────────────────────
let suggestTimeout = null;
let currentSuggestions = [];
let activeSuggestion = -1;

function getInput() {
  return document.getElementById("homeQuery") || document.getElementById("resultsQuery");
}

function getSuggestionsEl() {
  return document.getElementById("suggestions");
}

async function fetchSuggestions(q) {
  if (q.length < 2) { hideSuggestions(); return; }
  try {
    const res = await fetch(`${API_BASE}/suggest?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    showSuggestions(data.suggestions || []);
  } catch {
    hideSuggestions();
  }
}

function showSuggestions(items) {
  const el = getSuggestionsEl();
  if (!el || !items.length) { hideSuggestions(); return; }
  currentSuggestions = items;
  activeSuggestion = -1;
  el.innerHTML = items
    .map((s, i) => `<div class="suggestion-item" data-i="${i}" onclick="pickSuggestion(${i})">${escHtml(s)}</div>`)
    .join("");
  el.classList.add("open");
}

function hideSuggestions() {
  const el = getSuggestionsEl();
  if (el) el.classList.remove("open");
  currentSuggestions = [];
  activeSuggestion = -1;
}

function pickSuggestion(i) {
  const s = currentSuggestions[i];
  if (!s) return;
  const input = getInput();
  if (input) input.value = s;
  hideSuggestions();
  navigateToResults(s);
}

// Set up input listeners
document.addEventListener("DOMContentLoaded", () => {
  const input = getInput();
  if (!input) return;

  // On results page: prefill query from URL
  if (window.location.pathname.includes("results")) {
    const q = new URLSearchParams(window.location.search).get("q") || "";
    input.value = q;
    if (q) runSearch(q);
  }

  input.addEventListener("input", (e) => {
    clearTimeout(suggestTimeout);
    const val = e.target.value.trim();
    if (!val) { hideSuggestions(); return; }
    suggestTimeout = setTimeout(() => fetchSuggestions(val), 250);
  });

  input.addEventListener("keydown", (e) => {
    const items = getSuggestionsEl()?.querySelectorAll(".suggestion-item") || [];
    if (e.key === "ArrowDown") {
      activeSuggestion = Math.min(activeSuggestion + 1, items.length - 1);
      updateActiveItem(items);
      e.preventDefault();
    } else if (e.key === "ArrowUp") {
      activeSuggestion = Math.max(activeSuggestion - 1, -1);
      updateActiveItem(items);
      e.preventDefault();
    } else if (e.key === "Escape") {
      hideSuggestions();
    } else if (e.key === "Enter" && activeSuggestion >= 0) {
      pickSuggestion(activeSuggestion);
      e.preventDefault();
    }
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".search-form")) hideSuggestions();
  });
});

function updateActiveItem(items) {
  items.forEach((el, i) => el.classList.toggle("active", i === activeSuggestion));
  if (activeSuggestion >= 0 && items[activeSuggestion]) {
    getInput().value = currentSuggestions[activeSuggestion];
  }
}

// ── Search navigation ─────────────────────────────────────────────────────
function doSearch(event) {
  event.preventDefault();
  const input = getInput();
  const q = input?.value.trim();
  if (!q) return;
  navigateToResults(q);
}

function navigateToResults(q) {
  const isResultsPage = window.location.pathname.includes("results");
  if (isResultsPage) {
    history.pushState({}, "", `?q=${encodeURIComponent(q)}`);
    runSearch(q);
  } else {
    window.location.href = `results.html?q=${encodeURIComponent(q)}`;
  }
}

// ── Core search ───────────────────────────────────────────────────────────
let currentPage = 1;
let currentQuery = "";

async function runSearch(q, page = 1) {
  currentQuery = q;
  currentPage = page;
  hideSuggestions();

  // Show loading
  setVisible("loading", true);
  setVisible("resultsList", false);
  setVisible("instantAnswer", false);
  setVisible("aiSummary", false);
  setVisible("statsBar", false);
  setVisible("pagination", false);
  setVisible("emptyState", false);

  try {
    const url = `${API_BASE}/search?q=${encodeURIComponent(q)}&page=${page}&per_page=10`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`API error ${res.status}`);
    const data = await res.json();
    renderResults(data);
  } catch (err) {
    showError(err.message);
  } finally {
    setVisible("loading", false);
  }
}

function renderResults(data) {
  // Instant AI answer
  if (data.instant_answer) {
    const ia = data.instant_answer;
    const el = document.getElementById("instantAnswer");
    el.innerHTML = `
      <div class="instant-answer-badge">⚡ Neptune AI · ${ia.type}</div>
      <div class="instant-answer-title">${escHtml(ia.title)}</div>
      <div class="instant-answer-body">${escHtml(ia.body)}</div>
      ${ia.source ? `<div style="font-size:11px;color:var(--np-muted);margin-top:8px">${escHtml(ia.source)}</div>` : ""}
    `;
    setVisible("instantAnswer", true);
  }

  // AI summary
  if (data.ai_summary) {
    document.getElementById("aiSummary").textContent = "◎ " + data.ai_summary;
    setVisible("aiSummary", true);
  }

  // Stats
  const statsEl = document.getElementById("statsBar");
  if (data.total > 0) {
    statsEl.textContent = `About ${data.total.toLocaleString()} results`;
    setVisible("statsBar", true);
  }

  // Results
  const list = document.getElementById("resultsList");
  if (!data.results || data.results.length === 0) {
    setVisible("emptyState", true);
    return;
  }

  list.innerHTML = data.results.map(r => `
    <article class="result-card" onclick="openResult('${escAttr(r.url)}')">
      <div class="result-domain">
        <img class="result-favicon" src="https://www.google.com/s2/favicons?domain=${escAttr(r.domain)}&sz=16" alt="" />
        <span>${escHtml(r.domain)}</span>
        <span style="opacity:0.5">›</span>
        <span style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escHtml(r.url)}</span>
      </div>
      <div class="result-title">${escHtml(r.title)}</div>
      <div class="result-snippet">${r.snippet || escHtml(r.url)}</div>
    </article>
  `).join("");

  setVisible("resultsList", true);

  // Pagination
  const totalPages = Math.ceil(data.total / data.per_page);
  if (totalPages > 1) {
    renderPagination(data.page, totalPages);
  }
}

function renderPagination(current, total) {
  const el = document.getElementById("pagination");
  const pages = [];

  // Always show first, last, current ±2
  const toShow = new Set([1, total]);
  for (let i = Math.max(1, current - 2); i <= Math.min(total, current + 2); i++) toShow.add(i);
  const sorted = [...toShow].sort((a, b) => a - b);

  let html = current > 1
    ? `<button class="page-btn" onclick="runSearch('${escAttr(currentQuery)}', ${current - 1})">← Prev</button>`
    : "";

  let prev = 0;
  for (const p of sorted) {
    if (prev && p - prev > 1) html += `<span style="color:var(--np-muted);padding:0 4px">…</span>`;
    html += `<button class="page-btn ${p === current ? "active" : ""}" onclick="runSearch('${escAttr(currentQuery)}', ${p})">${p}</button>`;
    prev = p;
  }

  if (current < total) {
    html += `<button class="page-btn" onclick="runSearch('${escAttr(currentQuery)}', ${current + 1})">Next →</button>`;
  }

  el.innerHTML = html;
  setVisible("pagination", true);
}

function openResult(url) {
  window.open(url, "_blank", "noopener");
}

function showError(msg) {
  const list = document.getElementById("resultsList");
  list.innerHTML = `<div style="padding:40px 0;color:var(--np-muted);text-align:center">
    <div style="font-size:32px;margin-bottom:12px">⚠</div>
    <p>Could not reach Neptune Search API.</p>
    <p style="font-size:12px;margin-top:8px;font-family:var(--font-mono)">${escHtml(msg)}</p>
  </div>`;
  setVisible("resultsList", true);
}

// ── Helpers ───────────────────────────────────────────────────────────────
function setVisible(id, show) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.toggle("hidden", !show);
}

function escHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escAttr(str) {
  return String(str ?? "").replace(/'/g, "\\'");
}