"""
analysis/visualize.py

Generates four publication-quality charts from results.json:
  1. Overall Decision Accuracy Comparison (bar)
  2. Hallucination Rate Comparison (bar)
  3. Per-Scheme Baseline Accuracy (horizontal bar)
  4. Per-Scheme Hallucination Count (horizontal bar)

Run AFTER evaluate.py:
    python analysis/evaluate.py
    python analysis/visualize.py
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ── Style ────────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor": "#ffffff",    # pure white
    "axes.facecolor": "#ffffff",      # pure white
    "axes.edgecolor": "#d1d5db",      # light gray border
    "axes.labelcolor": "#1f2937",     # dark gray labels
    "xtick.color": "#4b5563",         # medium gray ticks
    "ytick.color": "#4b5563",         # medium gray ticks
    "text.color": "#111827",          # near-black text
    "grid.color": "#e5e7eb",          # very light gray grid
    "grid.alpha": 0.85,                # slightly more visible for light mode
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

# Refined colors for better contrast on white backgrounds
PROPOSED_COLOR = "#2563eb"   # deeper, professional blue
BASELINE_COLOR = "#ea580c"   # rich burnt orange
ACCENT_GOOD    = "#16a34a"   # forest green (readable on white)
ACCENT_BAD     = "#dc2626"   # strong red (readable on white)

# ── Load results ─────────────────────────────────────────────────────────────
results_path = os.path.join(os.path.dirname(__file__), "results.json")
with open(results_path, encoding="utf-8") as fh:
    data = json.load(fh)

figures_dir = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(figures_dir, exist_ok=True)

# ── Helpers ──────────────────────────────────────────────────────────────────

def bar_labels(ax, rects, fmt="{:.1f}%", color="white", offset=0.4):
    for rect in rects:
        h = rect.get_height()
        ax.text(
            rect.get_x() + rect.get_width() / 2.0,
            h + offset,
            fmt.format(h),
            ha="center", va="bottom",
            fontsize=11, fontweight="bold", color=color,
        )


# ── Chart 1: Overall Decision Accuracy ───────────────────────────────────────
fig, ax = plt.subplots(figsize=(7, 5))
fig.patch.set_facecolor("#eeeeee")

systems  = ["Rule Engine\n+ LLM (Proposed)", "LLM Baseline"]
accuracies = [
    data["proposed_accuracy"] * 100,
    data["baseline_accuracy"] * 100,
]
colors = [PROPOSED_COLOR, BASELINE_COLOR]
x = np.arange(len(systems))

rects = ax.bar(x, accuracies, width=0.45, color=colors,
               edgecolor="none", zorder=3)

ax.set_ylim(0, 115)
ax.set_xticks(x)
ax.set_xticklabels(systems, fontsize=12)
ax.set_ylabel("Decision Accuracy (%)", fontsize=12)
ax.set_title("Decision Accuracy Comparison", fontsize=14, fontweight="bold",
             color="white", pad=14)
ax.axhline(100, color="#ffffff22", lw=1, ls="--", zorder=2)
ax.yaxis.grid(True, zorder=0)
bar_labels(ax, rects)

# Annotate delta
delta = accuracies[0] - accuracies[1]
ax.annotate(
    f"+{delta:.1f}% vs Baseline",
    xy=(0, accuracies[0] + 2),
    fontsize=10, color=ACCENT_GOOD, fontweight="bold", ha="center",
)

fig.tight_layout()
out = os.path.join(figures_dir, "1_accuracy_comparison.png")
fig.savefig(out, dpi=180, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {out}")


# ── Chart 2: Hallucination Rate ───────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7, 5))
fig.patch.set_facecolor("#eeeeee")

rates = [
    data["proposed_hallucination_rate"] * 100,
    data["baseline_hallucination_rate"] * 100,
]
rects = ax.bar(x, rates, width=0.45,
               color=[ACCENT_GOOD, ACCENT_BAD],
               edgecolor="none", zorder=3)

ax.set_ylim(0, max(rates) * 1.35 + 5)
ax.set_xticks(x)
ax.set_xticklabels(systems, fontsize=12)
ax.set_ylabel("Hallucination Rate (%)", fontsize=12)
ax.set_title("Hallucination Rate: Proposed vs Baseline", fontsize=14,
             fontweight="bold", color="white", pad=14)
ax.yaxis.grid(True, zorder=0)
bar_labels(ax, rects)

fig.tight_layout()
out = os.path.join(figures_dir, "2_hallucination_rate.png")
fig.savefig(out, dpi=180, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {out}")


# ── Chart 3: Per-Scheme Baseline Accuracy ────────────────────────────────────
scheme_data = data["per_scheme"]
# Short names for readability
short_names = {
    "Pradhan Mantri Awas Yojana": "PMAY",
    "Ayushman Bharat – PM-JAY": "PM-JAY",
    "National Social Assistance Programme – Old Age Pension": "NSAP",
    "Pradhan Mantri Ujjwala Yojana": "Ujjwala",
    "PM-KISAN Samman Nidhi": "PM-KISAN",
}
schemes = list(scheme_data.keys())
short  = [short_names.get(s, s) for s in schemes]
b_accs = [scheme_data[s]["baseline_accuracy"] * 100 for s in schemes]

# Sort by accuracy descending
order = sorted(range(len(b_accs)), key=lambda i: b_accs[i], reverse=True)
short  = [short[i]  for i in order]
b_accs = [b_accs[i] for i in order]

fig, ax = plt.subplots(figsize=(8, 5))
fig.patch.set_facecolor("#eeeeee")

colors_bar = [ACCENT_GOOD if v >= 80 else BASELINE_COLOR for v in b_accs]
y = np.arange(len(short))
hbars = ax.barh(y, b_accs, height=0.5, color=colors_bar, edgecolor="none", zorder=3)

ax.set_xlim(0, 115)
ax.set_yticks(y)
ax.set_yticklabels(short, fontsize=12)
ax.set_xlabel("Baseline LLM Accuracy (%)", fontsize=12)
ax.set_title("Per-Scheme Baseline Accuracy", fontsize=14,
             fontweight="bold", color="white", pad=14)
ax.axvline(80, color="#ffffff33", lw=1, ls="--", zorder=2)
ax.xaxis.grid(True, zorder=0)

for bar_, v in zip(hbars, b_accs):
    ax.text(v + 1, bar_.get_y() + bar_.get_height() / 2,
            f"{v:.1f}%", va="center", fontsize=11, fontweight="bold",
            color="white")

fig.tight_layout()
out = os.path.join(figures_dir, "3_per_scheme_accuracy.png")
fig.savefig(out, dpi=180, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {out}")


# ── Chart 4: Per-Scheme Hallucination Count ───────────────────────────────────
h_counts = [scheme_data[schemes[i]]["hallucinations"] for i in order]

fig, ax = plt.subplots(figsize=(8, 5))
fig.patch.set_facecolor("#eeeeee")

colors_h = [ACCENT_BAD if v > 0 else ACCENT_GOOD for v in h_counts]
hbars = ax.barh(y, h_counts, height=0.5, color=colors_h, edgecolor="none", zorder=3)

ax.set_xlim(0, max(h_counts) * 1.35 + 1)
ax.set_yticks(y)
ax.set_yticklabels(short, fontsize=12)
ax.set_xlabel("Number of Hallucinated Decisions", fontsize=12)
ax.set_title("Per-Scheme Hallucination Count (Baseline LLM)", fontsize=14,
             fontweight="bold", color="white", pad=14)
ax.xaxis.grid(True, zorder=0)

for bar_, v in zip(hbars, h_counts):
    ax.text(v + 0.1, bar_.get_y() + bar_.get_height() / 2,
            str(v), va="center", fontsize=12, fontweight="bold", color="white")

fig.tight_layout()
out = os.path.join(figures_dir, "4_per_scheme_hallucinations.png")
fig.savefig(out, dpi=180, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {out}")

print("\nAll charts saved to analysis/figures/")
