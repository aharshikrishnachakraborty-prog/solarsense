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
