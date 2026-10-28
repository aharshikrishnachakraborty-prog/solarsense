"""Draw the app icons (the amber sun logo) for the installable app (PWA).

Run once from the solarsense folder:   python -m engine.make_icons
Writes web/icons/icon-192.png, icon-512.png, icon-maskable-512.png and apple-touch-icon.png.
"""

import math

import matplotlib
matplotlib.use("Agg")   # draw to files only, no window
import matplotlib.pyplot as plt

from engine import config

AMBER, DARK = "#f59e0b", "#0f141b"


def draw_icon(path, size, sun_scale):
    """Dark rounded background with the sun; sun_scale < 1 leaves the safe margin Android's 'maskable' icons need."""
    fig = plt.figure(figsize=(1, 1), dpi=size)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.axis("off")
    fig.patch.set_facecolor(DARK)
    ax.add_patch(plt.Circle((0, 0), 0.36 * sun_scale, color=AMBER))
    for i in range(8):   # 8 rays around the sun, like the logo in web/js/layout.js
        angle = i * math.pi / 4
        inner, outer = 0.52 * sun_scale, 0.80 * sun_scale
        ax.plot([inner * math.cos(angle), outer * math.cos(angle)], [inner * math.sin(angle), outer * math.sin(angle)],
                color=AMBER, linewidth=5 * sun_scale, solid_capstyle="round")   # in points: the icon is 72 wide
    fig.savefig(path, dpi=size, facecolor=DARK)
    plt.close(fig)


if __name__ == "__main__":
    folder = config.WEB_DIR / "icons"
    folder.mkdir(exist_ok=True)
    draw_icon(folder / "icon-192.png", 192, 1.0)
    draw_icon(folder / "icon-512.png", 512, 1.0)
    draw_icon(folder / "icon-maskable-512.png", 512, 0.75)
    draw_icon(folder / "apple-touch-icon.png", 180, 0.9)
    print(f"Icons written to {folder}")
