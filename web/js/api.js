// Shared helpers for every page: talking to the API, formatting numbers, showing errors.
// The website never calculates results itself — it only asks the API and displays answers.

const OFFLINE_MESSAGE =
  "Engine offline — start it with <code>uvicorn api.main:app --reload</code> and refresh this page.";

const FAULT_NAMES = {
  INVERTER_TRIP: "Inverter trip",
  UNDERPERFORMANCE: "Underperformance",
  DEGRADATION: "Degradation / soiling",
  DATA_GAP: "Data gap",
  OVERHEATING: "Overheating",
  SENSOR_ISSUE: "Sensor / data issue",
};

const SEVERITIES = ["Critical", "High", "Medium", "Low"];

// Wording used everywhere for actual ÷ expected energy, and for the tariff.
const AVE_LABEL = "Actual vs expected";
const AVE_TIP = "Above 100% means the plant produced more than our model estimated.";
const TARIFF_LABEL = "assumed tariff — see About";

const STATIC_MISSING_MESSAGE = "This data is not in the static demo copy. Try another plant or date.";

/**
 * Static demo copy (GitHub Pages): the file holding the saved answer to one API request.
 * Must match api/export_static.py exactly, e.g. /api/overview {plant: 2, date: "2020-05-27"}
 * → static-api/overview/date-2020-05-27__plant-2.json
 */
function staticFile(path, params) {
  const endpoint = path.replace(/^\/?api\//, "");
  const keys = Object.keys(params).sort();
  const name = keys.length ? keys.map((key) => `${key}-${params[key]}`).join("__") : "index";
  return `static-api/${endpoint}/${name}.json`;
}

/** Ask the API (or, in the static copy, the saved file) for JSON. Throws an Error with a friendly message. */
async function fetchJSON(path, params = {}, options = {}) {
  const usable = Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== null && value !== undefined && value !== ""));
  if (STATIC_SITE && options.method === "POST") return saveStatusInBrowser(path, JSON.parse(options.body));
  // Relative address (no leading "/"), so the site also works inside a sub-folder like /solarsense/.
  const query = new URLSearchParams(usable).toString();
  const url = STATIC_SITE ? staticFile(path, usable) : (query ? `${path}?${query}` : path).replace(/^\//, "");
  let response;
  try {
    response = await fetch(url, options);
  } catch (networkError) {
    throw new Error(OFFLINE_MESSAGE);
  }
  if (!response.ok) {
    if (STATIC_SITE) throw new Error(STATIC_MISSING_MESSAGE);
    let detail = `Request failed (${response.status}).`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch (ignored) { /* the error body was not JSON — keep the generic message */ }
    throw new Error(escapeHTML(detail));   // escaped: it will be shown as HTML in the banner
  }
  const body = await response.json();
  return STATIC_SITE ? applyBrowserStatuses(body) : body;
}

/** Send JSON to the API (used for changing an alert's status). */
function postJSON(path, body) {
  return fetchJSON(path, {}, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// ---------- Static copy only: alert statuses are kept in this browser ----------
const STATUS_KEY = "solarsense-static-statuses";

function readBrowserStatuses() {
  try { return JSON.parse(window.localStorage.getItem(STATUS_KEY)) || {}; } catch (e) { return {}; }
}

/** Static copy: "Acknowledge / Resolve" is saved in this browser only (there is no server to save it). */
function saveStatusInBrowser(path, { status }) {
  const id = decodeURIComponent(path.split("/").slice(-2)[0]);
  const statuses = readBrowserStatuses();
  const local = new Date(Date.now() - new Date().getTimezoneOffset() * 60000);   // this computer's local time
  statuses[id] = { status, updated_at: local.toISOString().slice(0, 19) };
  try { window.localStorage.setItem(STATUS_KEY, JSON.stringify(statuses)); } catch (e) { /* not saved — fine */ }
  return Promise.resolve({ id, ...statuses[id] });
}

/** Static copy: show this browser's saved statuses on alerts (lists and single alerts). */
function applyBrowserStatuses(body) {
  const statuses = readBrowserStatuses();
  const apply = (alert) => (statuses[alert.id]
    ? { ...alert, status: statuses[alert.id].status, status_updated_at: statuses[alert.id].updated_at } : alert);
  if (Array.isArray(body.alerts)) body.alerts = body.alerts.map(apply);
  if (body.id && body.status) return apply(body);
  return body;
}

// ---------- Formatting (Indian number grouping, e.g. 1,23,456) ----------
const fmt = {
  number: (value, decimals = 0) =>
    value === null || value === undefined ? "–"
      : Number(value).toLocaleString("en-IN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals }),
  kwh: (value) => `${fmt.number(value)} kWh`,
  inr: (value) => (value === null || value === undefined ? "–" : `₹${fmt.number(value)}`),
  pct: (ratio, decimals = 0) => (ratio === null || ratio === undefined ? "–" : `${fmt.number(ratio * 100, decimals)}%`),
  date: (isoDate) =>
    new Date(`${isoDate.slice(0, 10)}T00:00:00`).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }),
  time: (isoDateTime) => isoDateTime.slice(11, 16),
  fault: (type) => FAULT_NAMES[type] || type,
};

/** Escape text before putting it into HTML (data should never become code). */
function escapeHTML(text) {
  return String(text).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);
}

/** A severity badge, e.g. <span class="badge Critical">Critical</span>. */
function severityBadge(severity) {
  return `<span class="badge ${escapeHTML(severity)}">${escapeHTML(severity)}</span>`;
}

/** An ⓘ icon that shows an explanation (used for every ASSUMPTION). */
function infoTip(text) {
  return `<span class="info" tabindex="0" data-tip="${escapeHTML(text)}" aria-label="${escapeHTML(text)}">i</span>`;
}

/** Show a red error banner at the top of the page (or replace the existing one). */
function showError(message) {
  let banner = document.getElementById("error-banner");
  if (!banner) {
    banner = document.createElement("div");
    banner.id = "error-banner";
    banner.className = "error-banner";
    banner.setAttribute("role", "alert");
    document.querySelector(".page").prepend(banner);
  }
  banner.innerHTML = message;   // messages are our own text (OFFLINE_MESSAGE) or escaped API details
}

/** Remove the error banner once things work again. */
function clearError() {
  const banner = document.getElementById("error-banner");
  if (banner) banner.remove();
}

// Display-only colour bands for actual vs expected (used by tiles and the heatmap; never for detection).
const PR_GOOD = 0.95;
const PR_WARN = 0.85;

/** "ok" / "warn" / "bad" / "none" for an actual-vs-expected ratio. */
function prStatus(ratio) {
  if (ratio === null || ratio === undefined) return "none";
  return ratio >= PR_GOOD ? "ok" : ratio >= PR_WARN ? "warn" : "bad";
}

/** True if an alert was happening at any time on the given day ("YYYY-MM-DD"). */
function alertOverlapsDay(alert, day) {
  const next = new Date(`${day}T00:00:00Z`);
  next.setUTCDate(next.getUTCDate() + 1);
  const dayStart = `${day}T00:00:00`;
  const dayEnd = `${next.toISOString().slice(0, 10)}T00:00:00`;
  return alert.start < dayEnd && alert.end > dayStart;
}
