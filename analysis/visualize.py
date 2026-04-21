"""
Generates eight publication-quality charts from results.json:
  1. Overall Decision Accuracy Comparison
  2. Hallucination Rate Comparison (Explanation vs Decision)
  3. Explanation Completeness & Faithfulness
  4. Pass/Fail Ratio (Eligibility Distribution)
  5. Per-Scheme Baseline Accuracy
  6. Per-Scheme Explanation Completeness
  7. Explanation Length Distribution
  8. Per-Scheme Hallucination Comparison

"""

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


plt.rcParams.update(
    {
        "figure.facecolor": "#ffffff",
        "axes.facecolor": "#ffffff",
        "axes.edgecolor": "#d1d5db",
        "axes.labelcolor": "#1f2937",
        "xtick.color": "#4b5563",
        "ytick.color": "#4b5563",
        "text.color": "#111827",
        "grid.color": "#e5e7eb",
        "grid.alpha": 0.85,
        "font.family": "DejaVu Sans",
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


PROPOSED_COLOR = "#2563eb"
BASELINE_COLOR = "#ea580c"
ACCENT_GOOD = "#16a34a"
ACCENT_BAD = "#dc2626"


results_path = os.path.join(os.path.dirname(__file__), "results.json")
with open(results_path, encoding="utf-8") as fh:
    data = json.load(fh)

figures_dir = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(figures_dir, exist_ok=True)


def bar_labels(ax, rects, fmt="{:.1f}%", color="black", offset=0.4):
    for rect in rects:
        h = rect.get_height()
        ax.text(
            rect.get_x() + rect.get_width() / 2.0,
            h + offset,
            fmt.format(h),
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold",
            color=color,
        )


fig, ax = plt.subplots(figsize=(7, 5))
fig.patch.set_facecolor("#eeeeee")

systems = ["Rule Engine\n+ LLM (Proposed)", "LLM Baseline"]
accuracies = [
    data["proposed_accuracy"] * 100,
    data["baseline_accuracy"] * 100,
]
colors = [PROPOSED_COLOR, BASELINE_COLOR]
x = np.arange(len(systems))

rects = ax.bar(x, accuracies, width=0.45, color=colors, edgecolor="none", zorder=3)

ax.set_ylim(0, 115)
ax.set_xticks(x)
ax.set_xticklabels(systems, fontsize=12)
ax.set_ylabel("Decision Accuracy (%)", fontsize=12)
ax.set_title(
    "Decision Accuracy Comparison",
    fontsize=14,
    fontweight="bold",
    color="white",
    pad=14,
)
ax.axhline(100, color="#ffffff22", lw=1, ls="--", zorder=2)
ax.yaxis.grid(True, zorder=0)
bar_labels(ax, rects)


delta = accuracies[0] - accuracies[1]
ax.annotate(
    f"+{delta:.1f}% vs Baseline",
    xy=(0, accuracies[0] + 2),
    fontsize=10,
    color=ACCENT_GOOD,
    fontweight="bold",
    ha="center",
)

fig.tight_layout()
out = os.path.join(figures_dir, "1_accuracy_comparison.png")
fig.savefig(out, dpi=180, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {out}")


fig, ax = plt.subplots(figsize=(7, 5))
fig.patch.set_facecolor("#eeeeee")

rates = [
    data["proposed_explanation_hallucination_rate"] * 100,
    data["baseline_decision_hallucination_rate"] * 100,
]
labels = [
    "Explanation\nHallucination\n(Proposed)",
    "Decision\nHallucination\n(Baseline)",
]
rects = ax.bar(
    x[:2],
    rates,
    width=0.45,
    color=[ACCENT_GOOD, ACCENT_BAD],
    edgecolor="none",
    zorder=3,
)

ax.set_ylim(0, max(rates) * 1.35 + 5)
ax.set_xticks(x[:2])
ax.set_xticklabels(labels, fontsize=11)
ax.set_ylabel("Hallucination Rate (%)", fontsize=12)
ax.set_title(
    "Hallucination Rate: Explanation vs Decision",
    fontsize=14,
    fontweight="bold",
    color="black",
    pad=14,
)
ax.yaxis.grid(True, zorder=0)
bar_labels(ax, rects)

fig.tight_layout()
out = os.path.join(figures_dir, "2_hallucination_rate.png")
fig.savefig(out, dpi=180, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {out}")


fig, ax = plt.subplots(figsize=(8, 5))
fig.patch.set_facecolor("#e1e1e1")

metrics = ["Completeness", "Faithfulness\n(Proposed)", "Faithfulness\n(Baseline)"]
values = [
    data["explanation_completeness"] * 100,
    data["proposed_faithfulness"] * 100,
    data["baseline_faithfulness"] * 100,
]
colors_exp = [PROPOSED_COLOR, PROPOSED_COLOR, BASELINE_COLOR]
x_exp = np.arange(len(metrics))

rects = ax.bar(x_exp, values, width=0.5, color=colors_exp, edgecolor="none", zorder=3)

ax.set_ylim(0, 115)
ax.set_xticks(x_exp)
ax.set_xticklabels(metrics, fontsize=11)
ax.set_ylabel("Quality Metric (%)", fontsize=12)
ax.set_title(
    "Explanation Quality: Completeness & Faithfulness",
    fontsize=14,
    fontweight="bold",
    color="black",
    pad=14,
)
ax.axhline(100, color="#aa0000", lw=1, ls="--", zorder=2)
ax.yaxis.grid(True, zorder=0)
bar_labels(ax, rects)

fig.tight_layout()
out = os.path.join(figures_dir, "3_explanation_quality.png")
fig.savefig(out, dpi=180, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {out}")


fig, ax = plt.subplots(figsize=(7, 5))
fig.patch.set_facecolor("#eeeeee")

sizes = [data["eligible_count"], data["not_eligible_count"]]
labels_pie = [
    f"Eligible\n{data['pass_ratio']*100:.1f}%\n({data['eligible_count']} cases)",
    f"Not Eligible\n{data['not_eligible_ratio']*100:.1f}%\n({data['not_eligible_count']} cases)",
]
colors_pie = [ACCENT_GOOD, BASELINE_COLOR]
wedges, texts, autotexts = ax.pie(
    sizes,
    labels=labels_pie,
    colors=colors_pie,
    autopct="",
    startangle=90,
    textprops={"fontsize": 11, "weight": "bold"},
    wedgeprops={"edgecolor": "white", "linewidth": 2},
)

ax.set_title(
    "Eligibility Distribution Across Test Cases",
    fontsize=14,
    fontweight="bold",
    color="white",
    pad=14,
)

fig.tight_layout()
out = os.path.join(figures_dir, "4_eligibility_distribution.png")
fig.savefig(out, dpi=180, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {out}")


scheme_data = data["per_scheme"]

short_names = {
    "Pradhan Mantri Awas Yojana": "PMAY",
    "Ayushman Bharat – PM-JAY": "PM-JAY",
    "National Social Assistance Programme – Old Age Pension": "NSAP",
    "Pradhan Mantri Ujjwala Yojana": "Ujjwala",
    "PM-KISAN Samman Nidhi": "PM-KISAN",
}
schemes = list(scheme_data.keys())
short = [short_names.get(s, s) for s in schemes]
b_accs = [scheme_data[s]["baseline_accuracy"] * 100 for s in schemes]


order = sorted(range(len(b_accs)), key=lambda i: b_accs[i], reverse=True)
short = [short[i] for i in order]
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
ax.set_title(
    "Per-Scheme Baseline Decision Accuracy",
    fontsize=14,
    fontweight="bold",
    color="white",
    pad=14,
)
ax.axvline(80, color="#ffffff33", lw=1, ls="--", zorder=2)
ax.xaxis.grid(True, zorder=0)

for bar_, v in zip(hbars, b_accs):
    ax.text(
        v + 1,
        bar_.get_y() + bar_.get_height() / 2,
        f"{v:.1f}%",
        va="center",
        fontsize=11,
        fontweight="bold",
        color="white",
    )

fig.tight_layout()
out = os.path.join(figures_dir, "5_per_scheme_baseline_accuracy.png")
fig.savefig(out, dpi=180, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {out}")


completeness = [
    scheme_data[schemes[i]]["explanation_completeness"] * 100 for i in order
]

fig, ax = plt.subplots(figsize=(8, 5))
fig.patch.set_facecolor("#eeeeee")

colors_c = [ACCENT_GOOD if v >= 90 else PROPOSED_COLOR for v in completeness]
hbars = ax.barh(y, completeness, height=0.5, color=colors_c, edgecolor="none", zorder=3)

ax.set_xlim(0, 115)
ax.set_yticks(y)
ax.set_yticklabels(short, fontsize=12)
ax.set_xlabel("Explanation Completeness (%)", fontsize=12)
ax.set_title(
    "Per-Scheme Explanation Completeness (Proposed)",
    fontsize=14,
    fontweight="bold",
    color="white",
    pad=14,
)
ax.axvline(90, color="#ffffff33", lw=1, ls="--", zorder=2)
ax.xaxis.grid(True, zorder=0)

for bar_, v in zip(hbars, completeness):
    ax.text(
        v + 1,
        bar_.get_y() + bar_.get_height() / 2,
        f"{v:.1f}%",
        va="center",
        fontsize=11,
        fontweight="bold",
        color="white",
    )

fig.tight_layout()
out = os.path.join(figures_dir, "6_per_scheme_completeness.png")
fig.savefig(out, dpi=180, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {out}")


fig, ax = plt.subplots(figsize=(8, 5))
fig.patch.set_facecolor("#eeeeee")

lengths = [
    data["min_explanation_length"],
    data["avg_explanation_length"],
    data["max_explanation_length"],
]
length_labels = [
    f"Min\n({int(data['min_explanation_length'])} words)",
    f"Avg\n({data['avg_explanation_length']:.1f} words)",
    f"Max\n({int(data['max_explanation_length'])} words)",
]
colors_len = [BASELINE_COLOR, PROPOSED_COLOR, ACCENT_GOOD]

rects = ax.bar(
    range(3), lengths, width=0.5, color=colors_len, edgecolor="none", zorder=3
)

max_len = max(lengths)
ax.set_ylim(0, max_len * 1.2)
ax.set_xticks(range(3))
ax.set_xticklabels(length_labels, fontsize=11)
ax.set_ylabel("Word Count", fontsize=12)
ax.set_title(
    "Explanation Length Distribution",
    fontsize=14,
    fontweight="bold",
    color="white",
    pad=14,
)
ax.yaxis.grid(True, zorder=0)

for rect in rects:
    h = rect.get_height()
    ax.text(
        rect.get_x() + rect.get_width() / 2.0,
        h + max_len * 0.02,
        f"{int(h)}",
        ha="center",
        va="bottom",
        fontsize=12,
        fontweight="bold",
        color="white",
    )

fig.tight_layout()
out = os.path.join(figures_dir, "7_explanation_length.png")
fig.savefig(out, dpi=180, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {out}")


prop_halluc = [
    scheme_data[schemes[i]]["proposed_explanation_hallucination_rate"] * 100
    for i in order
]
base_halluc = [
    scheme_data[schemes[i]]["baseline_decision_hallucination_rate"] * 100 for i in order
]

fig, ax = plt.subplots(figsize=(10, 5))
fig.patch.set_facecolor("#eeeeee")

x_pos = np.arange(len(short))
width = 0.35

bars1 = ax.bar(
    x_pos - width / 2,
    prop_halluc,
    width,
    label="Proposed (Explanation)",
    color=ACCENT_GOOD,
    edgecolor="none",
    zorder=3,
)
bars2 = ax.bar(
    x_pos + width / 2,
    base_halluc,
    width,
    label="Baseline (Decision)",
    color=ACCENT_BAD,
    edgecolor="none",
    zorder=3,
)

ax.set_ylabel("Hallucination Rate (%)", fontsize=12)
ax.set_title(
    "Per-Scheme Hallucination Comparison",
    fontsize=14,
    fontweight="bold",
    color="white",
    pad=14,
)
ax.set_xticks(x_pos)
ax.set_xticklabels(short, fontsize=11)
ax.legend(fontsize=10, loc="upper left")
ax.yaxis.grid(True, zorder=0)

for bars in [bars1, bars2]:
    for bar in bars:
        h = bar.get_height()
        if h > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                h + 1,
                f"{h:.1f}%",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
                color="white",
            )

fig.tight_layout()
out = os.path.join(figures_dir, "8_per_scheme_hallucination_comparison.png")
fig.savefig(out, dpi=180, bbox_inches="tight")
plt.close(fig)
print(f"Saved: {out}")

print("\n✓ All 8 charts successfully generated and saved to analysis/figures/")
