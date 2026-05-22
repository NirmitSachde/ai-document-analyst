"use strict";

/* =================================================================
   AI Document Analyst — frontend application
   Industry-grade dark UI: live status, toasts, button spinners,
   skeleton loaders, friendly errors, and client-side rate limiting
   matched to the Gemini free-tier (10 req/min, well under 15 RPM).
   ================================================================= */

const $ = (id) => document.getElementById(id);
const STORAGE_KEY = "aida.backendUrl";
const USER_KEY_STORAGE = "aida.userApiKey";

function getUserApiKey() {
  return localStorage.getItem(USER_KEY_STORAGE) || "";
}

let activeDoc = null;
let allDocs = [];
let availableSamples = [];
let activeProvider = "gemini"; // overwritten by refreshStatus once /provider responds

/* ------------------------------------------------------------------
   Backend URL resolution
   ------------------------------------------------------------------ */

function getBackendUrl() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored !== null && stored !== "") return stored.replace(/\/+$/, "");
  if (typeof window.AIDA_BACKEND === "string" && window.AIDA_BACKEND) {
    return window.AIDA_BACKEND.replace(/\/+$/, "");
  }
  return "";
}

/* ------------------------------------------------------------------
   HTML escape
   ------------------------------------------------------------------ */

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

/* ------------------------------------------------------------------
   Client-side rate limiter — sliding window
   Mirrors the backend's 10/minute. The backend is the source of truth,
   but blocking on the client side gives a faster UX (no round-trip) and
   protects against rapid clicks.
   ------------------------------------------------------------------ */

const RATE_LIMIT_PER_MIN = 12;
const rateCalls = []; // timestamps (ms)

function rateLimitCheck() {
  const now = Date.now();
  // Drop entries older than 60s
  while (rateCalls.length && now - rateCalls[0] > 60_000) rateCalls.shift();
  if (rateCalls.length >= RATE_LIMIT_PER_MIN) {
    const waitMs = 60_000 - (now - rateCalls[0]);
    const wait = Math.max(1, Math.ceil(waitMs / 1000));
    const err = new Error(`Rate limit: ${RATE_LIMIT_PER_MIN} requests per minute. Please wait ${wait}s.`);
    err.code = "rate_limited_client";
    err.retryAfter = wait;
    throw err;
  }
  rateCalls.push(now);
}

/* ------------------------------------------------------------------
   Toast notifications
   ------------------------------------------------------------------ */

function toast(message, kind = "info", durationMs = 5000) {
  const el = document.createElement("div");
  el.className = "toast " + kind;
  el.innerHTML = `<span class="dot"></span><span>${escapeHtml(message)}</span>`;
  $("toasts").appendChild(el);
  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transition = "opacity 0.2s ease";
    setTimeout(() => el.remove(), 220);
  }, durationMs);
}

/* ------------------------------------------------------------------
   Friendly error mapping. Hides upstream details from the user.
   ------------------------------------------------------------------ */

function friendlyError(error, status) {
  if (error && error.code === "rate_limited_client") {
    return `You're going a bit fast — please wait ${error.retryAfter}s and try again.`;
  }
  if (status === 429) {
    // Differentiate "per-minute throttle" (slowapi) from "daily quota used"
    // by sniffing the detail string the backend sent.
    const d = (error?.message || "").toLowerCase();
    if (d.includes("quota") || d.includes("today")) {
      return "The free-tier quota for today has been used up. The site will work again in a few hours.";
    }
    return "Too many requests. Please wait about a minute and try again.";
  }
  if (status === 503) {
    return error?.message || "The model service isn't configured on this deployment. Please check back later.";
  }
  if (status === 404) {
    return "That document or sample isn't on the server (it may have been wiped after a restart).";
  }
  if (status === 400 && error && /question/i.test(error.message || "")) {
    return "Please type a question first.";
  }
  if (status === 413) {
    return "That file is too large. Please use a file under 20 MB.";
  }
  if (status >= 500) {
    return "The service is having trouble right now. Please try again in a moment.";
  }
  if (error && /fetch|network/i.test(error.message || "")) {
    return "Can't reach the service — likely waking up from sleep, or a network hiccup. Wait ~30 seconds and try again.";
  }
  return error?.message || "Something went wrong. Please try again.";
}

/* ------------------------------------------------------------------
   API wrapper. Applies rate limit, returns parsed JSON, throws on
   non-2xx with the upstream `detail` attached.
   ------------------------------------------------------------------ */

async function api(method, path, body, opts = {}) {
  if (opts.rateLimited !== false) rateLimitCheck();
  const init = { method, headers: {} };
  if (body !== undefined) {
    if (body instanceof FormData) {
      init.body = body;
    } else {
      init.headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(body);
    }
  }
  // BYO key: if the user pasted their own API key into Settings, send it as
  // a header so the backend uses their key instead of the server's env var.
  const userKey = getUserApiKey();
  if (userKey && opts.sendKey !== false) {
    const headerName = activeProvider === "claude" ? "X-Anthropic-Key" : "X-Gemini-Key";
    init.headers[headerName] = userKey;
  }
  const url = getBackendUrl() + path;
  let resp;
  try {
    resp = await fetch(url, init);
  } catch (e) {
    const err = new Error("network: " + e.message);
    err.networkFailure = true;
    throw err;
  }
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || resp.statusText);
    const err = new Error(detail);
    err.status = resp.status;
    err.data = data;
    throw err;
  }
  return data;
}

/* ------------------------------------------------------------------
   Loading helpers: button spinner + section skeleton
   ------------------------------------------------------------------ */

function setBtnLoading(btn, loading) {
  if (!btn) return;
  const label = btn.querySelector(".btn-label");
  const spin  = btn.querySelector(".spinner");
  btn.disabled = !!loading;
  if (spin)  spin.hidden = !loading;
  if (label) label.style.opacity = loading ? "0.7" : "1";
}

function skeleton(lines = 3) {
  const items = [];
  for (let i = 0; i < lines; i++) {
    const cls = ["long", "mid", "short"][i % 3] || "long";
    items.push(`<div class="skeleton skel-line ${cls}">x</div>`);
  }
  return `<div class="skeleton-block">${items.join("")}</div>`;
}

/* ------------------------------------------------------------------
   Rendering: docs, results, history
   ------------------------------------------------------------------ */

function renderMetaShort(doc) {
  return `<strong>${escapeHtml(doc.filename)}</strong> · ${doc.char_count.toLocaleString()} chars · ${(doc.size_bytes / 1024).toFixed(1)} KB`;
}

function selectDoc(doc, preview) {
  activeDoc = doc;
  $("doc-section").hidden = false;
  $("actions-section").hidden = false;
  $("doc-meta").innerHTML = `Document #${doc.id} · ${renderMetaShort(doc)} · uploaded ${new Date(doc.uploaded_at).toLocaleString()}`;
  $("doc-preview").textContent = preview !== undefined ? preview : "(preview only shown on first load)";
  $("results").innerHTML = "";
  $("results-section").hidden = true;
}

function deselectDoc() {
  activeDoc = null;
  $("doc-section").hidden = true;
  $("actions-section").hidden = true;
  $("results-section").hidden = true;
  $("results").innerHTML = "";
}

function appendResult(title, html) {
  $("results-section").hidden = false;
  const block = document.createElement("div");
  block.className = "result-block";
  block.innerHTML = `<h3>${escapeHtml(title)}</h3>` + html;
  $("results").prepend(block);
}

function showSkeletonResult(title) {
  const id = "skel-" + Date.now();
  $("results-section").hidden = false;
  const block = document.createElement("div");
  block.className = "result-block";
  block.id = id;
  block.innerHTML = `<h3>${escapeHtml(title)}</h3>${skeleton(4)}`;
  $("results").prepend(block);
  return id;
}

function replaceSkeleton(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = el.querySelector("h3").outerHTML + html;
}

function removeSkeleton(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function renderSummary(s) {
  const entities = (s.entities || []).map((e) =>
    `<span class="entity" title="${escapeHtml(e.context)}">${escapeHtml(e.name)} (${escapeHtml(e.type)})</span>`
  ).join(" ");
  const points = (s.key_points || []).map((p) => `<li>${escapeHtml(p)}</li>`).join("");
  const actions = (s.action_items || []).map((a) => `<li>${escapeHtml(a)}</li>`).join("");
  const dates = (s.dates || []).map((d) => `<li>${escapeHtml(d)}</li>`).join("");
  return `
    <p><strong>Overview:</strong> ${escapeHtml(s.overview || "")}</p>
    <p><strong>Key points</strong></p><ul>${points || "<li class='muted'>None.</li>"}</ul>
    <p><strong>Entities</strong></p><div>${entities || "<span class='muted small'>None.</span>"}</div>
    <p><strong>Action items</strong></p><ul>${actions || "<li class='muted'>None.</li>"}</ul>
    <p><strong>Dates</strong></p><ul>${dates || "<li class='muted'>None.</li>"}</ul>
  `;
}

function renderRequirements(r) {
  if (!r.requirements?.length) {
    return `<p class="muted">No requirements found.</p>` +
           (r.notes ? `<p><strong>Notes:</strong> ${escapeHtml(r.notes)}</p>` : "");
  }
  const rows = r.requirements.map((req) => `
    <div class="req-row">
      <span class="req-id">${escapeHtml(req.id)}</span>
      <span><span class="tag ${escapeHtml(req.priority)}">${escapeHtml(req.priority)}</span></span>
      <span>
        <div>${escapeHtml(req.description)}</div>
        <small class="muted small">
          category: ${escapeHtml(req.category)}
          ${req.dependencies?.length ? "· depends on: " + req.dependencies.map(escapeHtml).join(", ") : ""}
        </small>
      </span>
    </div>
  `).join("");
  return rows + (r.notes ? `<p class="muted small" style="margin-top:0.75rem">Notes: ${escapeHtml(r.notes)}</p>` : "");
}

function renderAnswer(question, a) {
  const citations = (a.citations || []).map((c) =>
    `<div class="citation">"${escapeHtml(c.quote)}" — ${escapeHtml(c.location_hint)}</div>`
  ).join("");
  return `
    <p><strong>Q:</strong> ${escapeHtml(question)}</p>
    <p><strong>A:</strong> ${escapeHtml(a.answer)}
      <span class="tag confidence-${escapeHtml(a.confidence)}">confidence: ${escapeHtml(a.confidence)}</span>
    </p>
    ${citations || "<p class='muted small'>No citations.</p>"}
  `;
}

function renderCompare(impact) {
  const changes = (impact.changes || []).map((c) => {
    const before = c.before ? `<div class="diff-before">− ${escapeHtml(c.before)}</div>` : "";
    const after = c.after ? `<div class="diff-after">+ ${escapeHtml(c.after)}</div>` : "";
    return `
      <div class="change-row">
        <div class="change-head">
          <span class="tag change-${escapeHtml(c.kind)}">${escapeHtml(c.kind)}</span>
          <span class="req-id">${escapeHtml(c.requirement_id)}</span>
        </div>
        ${before}${after}
        <small class="muted small">${escapeHtml(c.rationale)}</small>
      </div>
    `;
  }).join("");
  return `
    <p><strong>Summary:</strong> ${escapeHtml(impact.summary)}
      <span class="tag ${escapeHtml(impact.risk_level)}">risk: ${escapeHtml(impact.risk_level)}</span>
    </p>
    ${changes || "<p class='muted'>No changes detected.</p>"}
    ${impact.stakeholder_notes ? `<p><strong>Stakeholder notes:</strong> ${escapeHtml(impact.stakeholder_notes)}</p>` : ""}
  `;
}

/* ------------------------------------------------------------------
   Doc list + compare selects
   ------------------------------------------------------------------ */

function populateCompareSelects(docs) {
  const before = $("before-select");
  const after = $("after-select");
  const options = docs.map((d) =>
    `<option value="${d.id}">#${d.id} ${escapeHtml(d.filename)}</option>`
  ).join("");
  before.innerHTML = options;
  after.innerHTML = options;
  $("compare-section").hidden = docs.length < 2;
  if (docs.length >= 2) {
    after.value  = String(docs[0].id);
    before.value = String(docs[1].id);
  }
}

async function refreshDocList() {
  try {
    allDocs = await api("GET", "/documents", undefined, { rateLimited: false });
    const list = $("doc-list");
    if (!allDocs.length) {
      list.innerHTML = `<p class="muted small">No documents yet. Try a sample above to get started.</p>`;
      $("compare-section").hidden = true;
      return;
    }
    list.innerHTML = allDocs.map((d) => `
      <div class="doc-list-item">
        <span class="meta">#${d.id} · ${renderMetaShort(d)}</span>
        <span class="actions">
          <button class="btn" data-id="${d.id}" data-action="use">Use</button>
        </span>
      </div>
    `).join("");
    list.querySelectorAll("button[data-action='use']").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.dataset.id, 10);
        const doc = allDocs.find((d) => d.id === id);
        if (doc) selectDoc(doc);
      });
    });
    populateCompareSelects(allDocs);
  } catch (e) {
    $("doc-list").innerHTML = `<p class="muted small">${escapeHtml(friendlyError(e, e.status))}</p>`;
  }
}

/* ------------------------------------------------------------------
   Status pill — poll /health every 30s
   ------------------------------------------------------------------ */

async function refreshStatus({ silent = false } = {}) {
  const pill = $("status-pill");
  const text = $("status-text");
  // Only show "Checking…" on the very first load — on routine background polls
  // keep the existing pill state until we know the new answer, so the UI
  // doesn't flicker every 30 seconds.
  if (!silent) {
    pill.className = "status-pill warm";
    text.textContent = "Checking…";
  }
  // Hard timeout so a stalled backend doesn't leave the pill stuck.
  const ac = new AbortController();
  const t = setTimeout(() => ac.abort(), 8000);
  try {
    const resp = await fetch(getBackendUrl() + "/provider", { signal: ac.signal });
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    const info = await resp.json();
    activeProvider = info.name || "gemini";
    const usingOwnKey = !!getUserApiKey();
    if (usingOwnKey) {
      pill.className = "status-pill byo";
      text.textContent = "Live (your key)";
    } else {
      pill.className = "status-pill live";
      text.textContent = info.configured ? "Live" : "Live (no server key)";
    }
    $("provider-name").textContent = info.name || "—";
    $("provider-model").textContent = info.model || "—";
  } catch (e) {
    pill.className = "status-pill down";
    text.textContent = "Offline";
  } finally {
    clearTimeout(t);
  }
}

/* ------------------------------------------------------------------
   Samples
   ------------------------------------------------------------------ */

async function refreshSamples() {
  try {
    availableSamples = await api("GET", "/examples", undefined, { rateLimited: false });
    const sel = $("sample-select");
    if (!availableSamples.length) {
      sel.innerHTML = `<option value="">(no samples available)</option>`;
      $("btn-load-sample").disabled = true;
      $("sample-help").textContent = "Backend reports no samples bundled with this deployment.";
      return;
    }
    sel.innerHTML = availableSamples.map((s) =>
      `<option value="${escapeHtml(s.id)}" title="${escapeHtml(s.description)}">${escapeHtml(s.label)}</option>`
    ).join("");
    // Show the description of the selected sample
    const updateHelp = () => {
      const cur = availableSamples.find((s) => s.id === sel.value);
      $("sample-help").textContent = cur?.description || "";
    };
    sel.addEventListener("change", updateHelp);
    updateHelp();
  } catch (e) {
    $("sample-select").innerHTML = `<option value="">(samples unavailable)</option>`;
    $("btn-load-sample").disabled = true;
    $("sample-help").textContent = "Couldn't reach the backend to list samples.";
  }
}

/* ------------------------------------------------------------------
   Event wiring
   ------------------------------------------------------------------ */

// --- Hero: load sample ---
$("btn-load-sample").addEventListener("click", async () => {
  const sel = $("sample-select");
  const sampleId = sel.value;
  if (!sampleId) return;
  const btn = $("btn-load-sample");
  setBtnLoading(btn, true);
  try {
    const result = await api("POST", `/examples/${encodeURIComponent(sampleId)}/load`, {}, { rateLimited: false });
    selectDoc(result.document, result.preview);
    await refreshDocList();
    toast(`Loaded sample: ${result.document.filename}`, "success");
  } catch (e) {
    toast(friendlyError(e, e.status), "error");
  } finally {
    setBtnLoading(btn, false);
  }
});

// --- Hero: upload your own ---
$("upload-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const file = $("file-input").files[0];
  if (!file) return;
  const btn = ev.target.querySelector("button[type=submit]");
  setBtnLoading(btn, true);
  const fd = new FormData();
  fd.append("file", file);
  try {
    const result = await api("POST", "/upload", fd, { rateLimited: false });
    selectDoc(result.document, result.preview);
    await refreshDocList();
    toast(`Uploaded #${result.document.id}: ${result.document.filename}`, "success");
  } catch (e) {
    toast(friendlyError(e, e.status), "error");
  } finally {
    setBtnLoading(btn, false);
    $("file-input").value = "";
  }
});

// --- Doc section: clear ---
$("btn-deselect").addEventListener("click", deselectDoc);

// --- Actions: summary + requirements ---
async function runDocAction(label, path, btn) {
  if (!activeDoc) return;
  setBtnLoading(btn, true);
  const refresh = $("refresh-toggle").checked ? "?refresh=true" : "";
  const skelId = showSkeletonResult(label);
  try {
    const data = await api("GET", `/${path}/${activeDoc.id}${refresh}`);
    if (path === "summary")            replaceSkeleton(skelId, renderSummary(data));
    else if (path === "requirements")  replaceSkeleton(skelId, renderRequirements(data));
    await refreshHistory();
  } catch (e) {
    removeSkeleton(skelId);
    toast(friendlyError(e, e.status), "error");
  } finally {
    setBtnLoading(btn, false);
  }
}

$("btn-summary").addEventListener("click", (ev) => runDocAction("Summary", "summary", ev.currentTarget));
$("btn-requirements").addEventListener("click", (ev) => runDocAction("Requirements", "requirements", ev.currentTarget));

// --- Actions: Q&A ---
$("ask-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  if (!activeDoc) return;
  const question = $("question-input").value.trim();
  if (!question) return;
  const btn = ev.target.querySelector("button[type=submit]");
  setBtnLoading(btn, true);
  const skelId = showSkeletonResult("Q&A");
  try {
    const answer = await api("POST", "/qa", { doc_id: activeDoc.id, question });
    replaceSkeleton(skelId, renderAnswer(question, answer));
    $("question-input").value = "";
    await refreshHistory();
  } catch (e) {
    removeSkeleton(skelId);
    toast(friendlyError(e, e.status), "error");
  } finally {
    setBtnLoading(btn, false);
  }
});

// --- Compare ---
$("compare-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const before = parseInt($("before-select").value, 10);
  const after  = parseInt($("after-select").value, 10);
  if (before === after) {
    toast("Pick two different documents to compare.", "error");
    return;
  }
  const btn = ev.target.querySelector("button[type=submit]");
  setBtnLoading(btn, true);
  const skelId = showSkeletonResult(`Change impact (#${before} → #${after})`);
  try {
    const impact = await api("POST", "/compare", { doc_id_before: before, doc_id_after: after });
    replaceSkeleton(skelId, renderCompare(impact));
    await refreshHistory();
  } catch (e) {
    removeSkeleton(skelId);
    toast(friendlyError(e, e.status), "error");
  } finally {
    setBtnLoading(btn, false);
  }
});

// --- Clear results ---
$("btn-clear-results").addEventListener("click", () => {
  $("results").innerHTML = "";
  $("results-section").hidden = true;
});

// --- History ---
async function refreshHistory() {
  try {
    const rows = await api("GET", "/history?limit=20", undefined, { rateLimited: false });
    const el = $("history-list");
    if (!rows.length) {
      el.innerHTML = `<p class="muted small">Nothing yet. Run a summary, extraction, Q&A, or compare to see entries here.</p>`;
      return;
    }
    el.innerHTML = rows.map((r) => {
      const when = new Date(r.created_at).toLocaleTimeString();
      const docs = r.kind === "compare"
        ? `#${r.document_id} → #${r.secondary_document_id}`
        : `#${r.document_id}`;
      const detail = r.question ? `<span class="q">"${escapeHtml(r.question)}"</span>` : "";
      return `<div class="history-row">
        <span class="tag history-${escapeHtml(r.kind)}">${escapeHtml(r.kind)}</span>
        <span>${docs}</span>
        ${detail}
        <span class="when">${escapeHtml(when)}</span>
      </div>`;
    }).join("");
  } catch (e) {
    $("history-list").innerHTML = `<p class="muted small">${escapeHtml(friendlyError(e, e.status))}</p>`;
  }
}

$("btn-refresh-history").addEventListener("click", refreshHistory);

/* ------------------------------------------------------------------
   Settings dialog
   ------------------------------------------------------------------ */

const settingsDialog = $("settings-dialog");

$("open-settings").addEventListener("click", () => {
  $("backend-url").value = localStorage.getItem(STORAGE_KEY) || "";
  $("user-api-key").value = getUserApiKey();
  if (typeof settingsDialog.showModal === "function") {
    settingsDialog.showModal();
  } else {
    settingsDialog.setAttribute("open", "");
  }
});

$("close-settings").addEventListener("click", () => settingsDialog.close());

$("settings-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();

  // Backend URL
  const urlVal = $("backend-url").value.trim().replace(/\/+$/, "");
  if (urlVal === "") {
    localStorage.removeItem(STORAGE_KEY);
  } else {
    try { new URL(urlVal); }
    catch { toast("That doesn't look like a valid backend URL.", "error"); return; }
    localStorage.setItem(STORAGE_KEY, urlVal);
  }

  // User API key
  const keyVal = $("user-api-key").value.trim();
  const hadKey = !!getUserApiKey();
  if (keyVal === "") {
    localStorage.removeItem(USER_KEY_STORAGE);
    if (hadKey) toast("Cleared your API key. Using the server's key.", "info");
  } else {
    localStorage.setItem(USER_KEY_STORAGE, keyVal);
    toast("Saved. Future requests will use your API key.", "success");
  }

  settingsDialog.close();
  await Promise.all([refreshStatus(), refreshSamples(), refreshDocList(), refreshHistory()]);
});

$("reset-settings").addEventListener("click", async () => {
  localStorage.removeItem(STORAGE_KEY);
  localStorage.removeItem(USER_KEY_STORAGE);
  $("backend-url").value = "";
  $("user-api-key").value = "";
  toast("Cleared all settings.", "info");
  settingsDialog.close();
  await Promise.all([refreshStatus(), refreshSamples(), refreshDocList(), refreshHistory()]);
});

/* ------------------------------------------------------------------
   Boot
   ------------------------------------------------------------------ */

(async function boot() {
  await refreshStatus();
  await Promise.all([refreshSamples(), refreshDocList(), refreshHistory()]);
  // Re-check status periodically so the dot reflects backend health.
  // Silent = don't flip to "Checking…" on each poll — only the first load shows that.
  setInterval(() => refreshStatus({ silent: true }), 30_000);
})();
