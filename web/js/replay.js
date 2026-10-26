// Live replay on the Overview page: plays the chosen day in 15-minute ticks so the demo feels like
// real-time monitoring. Every number comes precomputed from /api/replay — nothing is added up here.

const TOAST_SECONDS = 6;
const MAX_TOASTS = 3;

const Replay = {
  data: null, tick: 0, timer: null, active: false,

  async start() {
    const { plant, date } = Layout.state;
    try {
      Replay.data = await fetchJSON("/api/replay", { plant, date });
    } catch (error) {
      showError(error.message);
      return;
    }
    Replay.active = true;
    Replay.tick = 0;
    Replay.setButtons(true);
    // Draw the full-day chart frame once, then reveal it tick by tick.
    renderDayChart({ performance_ratio: null }, { points: Replay.data.ticks });
    Replay.play();
  },

  play() {
    clearInterval(Replay.timer);
    const speed = Number(document.getElementById("replay-speed").value);
    Replay.timer = setInterval(Replay.step, 1000 / speed);
    document.getElementById("replay-pause").textContent = "Pause";
  },

  togglePause() {
    if (Replay.timer) {
      clearInterval(Replay.timer);
      Replay.timer = null;
      document.getElementById("replay-pause").textContent = "Resume";
    } else {
      Replay.play();
    }
  },

  /** Stop the replay. restore = true puts the normal full-day view back. */
  stop(restore = true) {
    clearInterval(Replay.timer);
    Replay.timer = null;
    if (!Replay.active) return;
    Replay.active = false;
    Replay.setButtons(false);
    document.getElementById("toasts").innerHTML = "";
    if (restore && lastData) renderAll(lastData);
  },

  step() {
    const ticks = Replay.data.ticks;
    if (Replay.tick >= ticks.length) {
      clearInterval(Replay.timer);
      Replay.timer = null;
      document.getElementById("replay-pause").hidden = true;
      document.getElementById("takeaway").textContent += " — replay finished.";
      return;
    }
    Replay.show(Replay.tick);
    Replay.data.events.filter((e) => e.tick === Replay.tick).forEach(Replay.toast);
    Replay.tick += 1;
  },

  show(i) {
    const { ticks, tariff_inr_per_kwh, tariff_note } = Replay.data;
    const t = ticks[i];
    renderKpis({ ...t, tariff_inr_per_kwh, tariff_note });
    const sky = t.sky_label && SKY[t.sky_label] ? `${SKY[t.sky_label].icon} ${t.sky_label.toLowerCase()}` : "";
    const panel = t.module_temp_c === null || t.module_temp_c === undefined ? "" : `panels ${fmt.number(t.module_temp_c)} °C`;
    const weatherNow = [sky, panel].filter(Boolean).join(", ");
    document.getElementById("takeaway").innerHTML =
      `<span class="live-dot"></span>Live replay · ${fmt.time(t.timestamp)}${weatherNow ? ` · ${weatherNow}` : ""} — plant ` +
      `has made ${fmt.pct(t.performance_ratio)} of expected so far; ${fmt.kwh(t.fault_loss_kwh)} lost to faults so far.`;
    Replay.showWeather(t);
    const chart = Charts.instances["day-chart"];
    const upTo = (key) => ticks.map((p, j) => (j <= i ? p[key] : null));
    chart.data.datasets[0].data = upTo("actual_kw");
    chart.data.datasets[1].data = upTo("expected_kw");
    chart.data.datasets[2].data = upTo("irradiation");
    chart.update("none");
    document.getElementById("day-chart-title").textContent = `Live: ${fmt.time(t.timestamp)} — ${fmt.number(t.actual_kw)} kW now (expected ${fmt.number(t.expected_kw)} kW)`;
  },

  /** Weather mini-card during replay: the sky icon and panel temperature change every tick. */
  showWeather(t) {
    const icon = document.getElementById("wm-icon");
    if (!icon) return;   // no weather data for this plant/day
    icon.textContent = t.sky_label && SKY[t.sky_label] ? SKY[t.sky_label].icon : "🌙";
    document.getElementById("wm-sky-label").textContent = "Sky now";
    document.getElementById("wm-sky").textContent = t.sky_label || "too dark to judge";
    document.getElementById("wm-temp-label").textContent = "Panel temperature now";
    document.getElementById("wm-temp").textContent = t.module_temp_c === null ? "–" : `${fmt.number(t.module_temp_c)} °C`;
  },

  toast(event) {
    const box = document.getElementById("toasts");
    while (box.children.length >= MAX_TOASTS) box.firstChild.remove();
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.innerHTML = `<a href="alerts.html?id=${encodeURIComponent(event.id)}">
      <div class="list-title">${severityBadge(event.severity)} New alert: ${fmt.fault(event.fault_type)}</div>
      <div class="list-meta">${event.inverter === "ALL" ? "Whole plant" : `Inverter ${escapeHTML(event.inverter)}`} · ${escapeHTML(event.id)}</div></a>`;
    box.appendChild(toast);
    setTimeout(() => toast.remove(), TOAST_SECONDS * 1000);
  },

  setButtons(playing) {
    document.getElementById("replay-start").hidden = playing;
    ["replay-pause", "replay-speed", "replay-stop"].forEach((id) => { document.getElementById(id).hidden = !playing; });
  },
};

document.getElementById("replay-start").addEventListener("click", Replay.start);
document.getElementById("replay-pause").addEventListener("click", Replay.togglePause);
document.getElementById("replay-stop").addEventListener("click", () => Replay.stop(true));
document.getElementById("replay-speed").addEventListener("change", () => { if (Replay.timer) Replay.play(); });
