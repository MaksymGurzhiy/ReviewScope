"""Shared matplotlib styling for all diploma diagrams.

Style choices (per Odessa Polytechnic methodology):
  - black text on white background, no chartjunk;
  - sans-serif heading-size text >= 10 pt;
  - Ukrainian labels;
  - exported as 200 dpi PNG, A4 friendly.
"""
from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Ellipse, FancyArrowPatch, Rectangle
from matplotlib.lines import Line2D

# ---- global config ---------------------------------------------------------
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.linewidth": 0.8,
})

DIAG_DIR = Path(__file__).resolve().parents[2] / "docs" / "diagrams"
DIAG_DIR.mkdir(parents=True, exist_ok=True)


# ---- primitives -----------------------------------------------------------
def new_canvas(w: float = 8.0, h: float = 5.0):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


def ucase(ax, x, y, text, w=2.6, h=0.8, fs=10):
    """Draw a Use-Case ellipse and return its bbox center."""
    e = Ellipse((x, y), width=w, height=h, fill=True,
                facecolor="white", edgecolor="black", lw=1.0)
    ax.add_patch(e)
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, wrap=True)
    return (x, y)


def actor(ax, x, y, name="Користувач", fs=10):
    """Stick-figure actor."""
    head = Ellipse((x, y + 0.55), 0.28, 0.32, fill=False, lw=1.0)
    ax.add_patch(head)
    ax.add_line(Line2D([x, x], [y + 0.39, y - 0.20], lw=1.0, color="black"))
    ax.add_line(Line2D([x - 0.30, x + 0.30], [y + 0.20, y + 0.20], lw=1.0, color="black"))
    ax.add_line(Line2D([x, x - 0.25], [y - 0.20, y - 0.55], lw=1.0, color="black"))
    ax.add_line(Line2D([x, x + 0.25], [y - 0.20, y - 0.55], lw=1.0, color="black"))
    ax.text(x, y - 0.78, name, ha="center", va="top", fontsize=fs)
    return (x, y)


def box(ax, x, y, w, h, text, *, fs=10, fc="white", ec="black",
        rounding=0.05, bold=False, align="center"):
    """Rounded rectangle with centered text."""
    p = FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                       boxstyle=f"round,pad=0.02,rounding_size={rounding}",
                       linewidth=1.0, edgecolor=ec, facecolor=fc)
    ax.add_patch(p)
    weight = "bold" if bold else "normal"
    ha = "center" if align == "center" else "left"
    tx = x if align == "center" else x - w / 2 + 0.15
    ax.text(tx, y, text, ha=ha, va="center", fontsize=fs,
            fontweight=weight, wrap=True)
    return (x, y)


def rect(ax, x, y, w, h, text, *, fs=10, fc="white", ec="black", bold=False):
    p = Rectangle((x - w / 2, y - h / 2), w, h, linewidth=1.0,
                  edgecolor=ec, facecolor=fc)
    ax.add_patch(p)
    weight = "bold" if bold else "normal"
    ax.text(x, y, text, ha="center", va="center", fontsize=fs,
            fontweight=weight, wrap=True)
    return (x, y)


def arrow(ax, p1, p2, *, label=None, style="-|>", lw=1.0, ls="-",
          fs=9, color="black", offset=(0, 0.18)):
    """Solid arrow between two points (centers)."""
    a = FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=14,
                        linewidth=lw, color=color, linestyle=ls,
                        shrinkA=8, shrinkB=8)
    ax.add_patch(a)
    if label:
        mx = (p1[0] + p2[0]) / 2 + offset[0]
        my = (p1[1] + p2[1]) / 2 + offset[1]
        ax.text(mx, my, label, ha="center", va="center", fontsize=fs)


def line(ax, p1, p2, *, lw=1.0, ls="-", color="black"):
    ax.add_line(Line2D([p1[0], p2[0]], [p1[1], p2[1]], lw=lw, ls=ls, color=color))


def assoc(ax, actor_xy, ucase_xy, *, ucase_w=2.6, ucase_h=0.8, lw=1.0):
    """Association line that stops at ellipse / actor borders, never crosses
    the body of the use-case."""
    import math
    ax_x, ax_y = actor_xy
    ux, uy = ucase_xy
    dx, dy = ux - ax_x, uy - ax_y
    dist = math.hypot(dx, dy) or 1.0
    # actor border: 0.30 from torso center
    ax_off = 0.30
    sx = ax_x + dx / dist * ax_off
    sy = ax_y + dy / dist * ax_off
    # ellipse border (parametric)
    # solve for t s.t. ((tx)/(w/2))^2 + ((ty)/(h/2))^2 = 1
    rw, rh = ucase_w / 2, ucase_h / 2
    rdx = -dx; rdy = -dy
    t = 1.0 / math.sqrt((rdx / rw) ** 2 + (rdy / rh) ** 2)
    ex = ux + rdx * t
    ey = uy + rdy * t
    ax.add_line(Line2D([sx, ex], [sy, ey], lw=lw, color="black"))


def diamond(ax, x, y, w=1.0, h=0.6, text="", fs=9):
    pts = [(x, y + h / 2), (x + w / 2, y), (x, y - h / 2), (x - w / 2, y)]
    poly = plt.Polygon(pts, fill=True, facecolor="white", edgecolor="black", lw=1.0)
    ax.add_patch(poly)
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, wrap=True)
    return (x, y)


def save(fig, name: str):
    out = DIAG_DIR / f"{name}.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out.name}")
    return out
