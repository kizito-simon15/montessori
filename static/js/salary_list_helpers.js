// salary_list_helpers.js – 24 Jun 2025
// -----------------------------------------------------------------------------
// Lightweight, dependency‑free helpers for the salary_list.html template.
// • Collapsible month buckets (remember state)
// • Instant client‑side search by staff name / ID
// • Pure‑JS month filter (hide/show buckets without reload)
// • Quick links to existing PDF endpoints (print / save)
// -----------------------------------------------------------------------------

/* eslint-env browser */

// ──────────────────────────────────────────────────────────────────────────────
// Utility helpers
// ──────────────────────────────────────────────────────────────────────────────
const $   = (sel, ctx = document) => ctx.querySelector(sel);
const $$  = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));
const on  = (el, type, fn) => el && el.addEventListener(type, fn);
const qs  = () => new URLSearchParams(window.location.search);
const saveState = (key, val) => localStorage.setItem(key, JSON.stringify(val));
const loadState = (key, def = null) => {
  try { return JSON.parse(localStorage.getItem(key)) ?? def; }
  catch { return def; }
};

// Debounce – limit rapid‑fire events (e.g. keypress) to improve perf
function debounce (fn, ms = 300) {
  let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

// ──────────────────────────────────────────────────────────────────────────────
// Accordion handling – one section per month bucket
// ──────────────────────────────────────────────────────────────────────────────
function initAccordions () {
  $$(".bucket").forEach((sec, idx) => {
    const header = $("header", sec);
    const body   = $(".body",   sec);
    const btn    = $(".tgl",    header);

    // restore saved state (collapsed / expanded)
    const closed = loadState(`bucket-${idx}`, false);
    if (closed) {
      body.style.display = "none";
      header.classList.add("closed");
    }

    on(btn, "click", () => {
      const isClosed = body.style.display === "none";
      body.style.display = isClosed ? "" : "none";
      header.classList.toggle("closed", !isClosed);
      saveState(`bucket-${idx}`, !isClosed);
    });
  });
}

// ──────────────────────────────────────────────────────────────────────────────
// Client‑side instant search – hides buckets that have no matching rows
// ──────────────────────────────────────────────────────────────────────────────
function initLiveSearch () {
  const input = $('input[name="q"]');
  if (!input) return;

  const doFilter = () => {
    const term = input.value.trim().toLowerCase();
    $$(".bucket").forEach(sec => {
      const rows = $$('tbody tr', sec);
      let match = false;
      rows.forEach(tr => {
        const txt = tr.textContent.toLowerCase();
        const rowMatch = term === "" || txt.includes(term);
        tr.style.display = rowMatch ? "" : "none";
        if (rowMatch) match = true;
      });
      sec.style.display = match ? "" : "none";
    });
  };

  on(input, "input", debounce(doFilter, 150));
}

// ──────────────────────────────────────────────────────────────────────────────
// Pure JS FROM/TO month dropdowns – instantly hide/show buckets without reload
// ──────────────────────────────────────────────────────────────────────────────
function initMonthFilter () {
  const selFrom = $('select[name="from"]');
  const selTo   = $('select[name="to"]');
  if (!selFrom || !selTo) return;

  const apply = () => {
    const from = selFrom.value;
    const to   = selTo.value;
    $$(".bucket").forEach(sec => {
      const m = sec.dataset.month; // "YYYY-MM"
      const inRange = (!from || m >= from) && (!to || m <= to);
      sec.style.display = inRange ? "" : "none";
    });
  };

  on(selFrom, "change", apply);
  on(selTo,   "change", apply);

  // run once on load (important when user navigates back)
  apply();
}

// ──────────────────────────────────────────────────────────────────────────────
// PDF helpers – open back‑end routes in a new tab preserving current filters
// -----------------------------------------------------------------------------
function initPdfButtons () {
  const btnPrint = $("#printBtn");
  const btnSave  = $("#saveBtn");
  const buildUrl = (endpoint) => {
    const p = new URLSearchParams(window.location.search);
    return `/finance/salaries/${endpoint}/?` + p.toString();
  };
  on(btnPrint, "click", () => window.open(buildUrl("print"), "_blank"));
  on(btnSave,  "click", () => window.open(buildUrl("save"),  "_blank"));
}

// ──────────────────────────────────────────────────────────────────────────────
// Kick‑off once DOM ready
// -----------------------------------------------------------------------------
window.addEventListener("DOMContentLoaded", () => {
  initAccordions();
  initLiveSearch();
  initMonthFilter();
  initPdfButtons();

  // subtle fade‑in for nicer UX
  document.body.classList.add("vs-loaded");
});

