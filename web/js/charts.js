// Shared Chart.js setup so every chart looks the same: colours, fonts, tooltips, axis titles.

const Charts = {
  instances: {},

  /** Read a colour from the CSS variables (so charts follow the light/dark theme). */
  color(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  },

  /** Draw (or redraw) a chart in the canvas with this id. */
  draw(canvasId, config) {
    if (Charts.instances[canvasId]) Charts.instances[canvasId].destroy();
    const text = Charts.color("--text");
    const grid = Charts.color("--border");
    Chart.defaults.color = Charts.color("--muted");
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    Chart.defaults.borderColor = grid;
    config.options = config.options || {};
    config.options.responsive = true;
    config.options.maintainAspectRatio = false;
    config.options.plugins = Object.assign(
      { legend: { labels: { color: text, usePointStyle: true, boxHeight: 7 } } },
      config.options.plugins || {}
    );
    Charts.instances[canvasId] = new Chart(document.getElementById(canvasId), config);
    return Charts.instances[canvasId];
  },

  /** A titled axis, e.g. Charts.axis("Power (kW)"). */
  axis(title, extra = {}) {
    return Object.assign({ title: { display: true, text: title }, grid: { color: Charts.color("--border") } }, extra);
  },
};

/**
 * Chart.js plugin that shades time ranges behind the lines (e.g. alert periods).
 * ranges: [{ from: labelIndex, to: labelIndex, color: "rgba(...)" }]
 */
Charts.shade = (ranges) => ({
  id: "shade",
  beforeDatasetsDraw(chart) {
    const { ctx, chartArea, scales } = chart;
    ctx.save();
    for (const range of ranges) {
      const left = scales.x.getPixelForValue(range.from);
      const right = scales.x.getPixelForValue(range.to);
      ctx.fillStyle = range.color;
      ctx.fillRect(left, chartArea.top, Math.max(right - left, 3), chartArea.bottom - chartArea.top);
    }
    ctx.restore();
  },
});

/**
 * Chart.js plugin: a coloured sky band just above the plot, one block per 15-minute label (Phase W1).
 * skyLabels: one sky label (or null) per chart label. The chart needs options.layout.padding.top ≥ 16
 * and its legend at the bottom, so the band has room above the plot.
 */
Charts.skyStrip = (skyLabels) => ({
  id: "skyStrip",
  afterDraw(chart) {
    const { ctx, chartArea, scales } = chart;
    const step = skyLabels.length > 1 ? scales.x.getPixelForValue(1) - scales.x.getPixelForValue(0) : chartArea.width;
    ctx.save();
    skyLabels.forEach((label, i) => {
      if (!label || !SKY[label]) return;
      const left = Math.max(scales.x.getPixelForValue(i) - step / 2, chartArea.left);
      const right = Math.min(scales.x.getPixelForValue(i) + step / 2, chartArea.right);
      ctx.fillStyle = SKY[label].color;
      ctx.fillRect(left, chartArea.top - 14, right - left + 0.5, 10);
    });
    ctx.restore();
  },
});

/** Chart options that make room for the sky strip (legend moves below the chart). */
Charts.skyStripOptions = (options) => {
  options.layout = { padding: { top: 16 } };
  options.plugins = Object.assign({}, options.plugins, {
    legend: { position: "bottom", labels: { color: Charts.color("--text"), usePointStyle: true, boxHeight: 7 } },
  });
  return options;
};

/** Small HTML legend for the sky strip: ☀️ Clear ⛅ Partly cloudy … */
Charts.skyLegend = () => Object.entries(SKY)
  .map(([label, s]) => `<span><i class="sky-swatch" style="background:${s.color}"></i>${s.icon} ${label}</span>`).join("");

/** Turn a list of true/false flags (one per chart label) into shade ranges. */
Charts.rangesFromFlags = (flags, color) => {
  const ranges = [];
  flags.forEach((on, i) => {
    if (!on) return;
    const last = ranges[ranges.length - 1];
    if (last && last.to === i - 1) last.to = i;
    else ranges.push({ from: i, to: i, color });
  });
  return ranges;
};
