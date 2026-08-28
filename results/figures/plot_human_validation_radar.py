from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_STEM = OUTPUT_DIR / "human_expert_validation_radar"

DIMENSIONS = [
    "Entity\ncorrectness",
    "Relation\ncorrectness",
    "Evidence\ntraceability",
    "24Model\nconsistency",
    "Causal-chain\nexplainability",
    "Practical\nusefulness",
]

POSITIVE_RATINGS = np.array([86.0, 80.7, 90.0, 83.3, 82.0, 76.7])
ICC_SCALED = np.array([84.0, 79.0, 87.0, 81.0, 80.0, 76.0])

SERIES = [
    ("Positive ratings (%)", POSITIVE_RATINGS, "#0F4D92", "o", 0.15),
    ("Inter-rater agreement (ICC × 100)", ICC_SCALED, "#B64342", "s", 0.11),
]


def apply_publication_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "Times New Roman",
            "font.size": 15,
            "font.weight": "bold",
            "axes.labelweight": "bold",
            "axes.linewidth": 1.8,
            "legend.frameon": False,
            "legend.fontsize": 17,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def main() -> None:
    apply_publication_style()

    count = len(DIMENSIONS)
    angles = np.linspace(0, 2 * np.pi, count, endpoint=False)
    closed_angles = np.concatenate([angles, angles[:1]])

    fig = plt.figure(figsize=(14.5, 10.0), facecolor="white")
    ax = fig.add_subplot(111, polar=True)
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    for label, values, color, marker, fill_alpha in SERIES:
        closed_values = np.concatenate([values, values[:1]])
        ax.plot(
            closed_angles,
            closed_values,
            color=color,
            linewidth=3.0,
            marker=marker,
            markersize=8.5,
            markerfacecolor="white",
            markeredgecolor=color,
            markeredgewidth=2.2,
            label=label,
            zorder=4,
        )
        ax.fill(closed_angles, closed_values, color=color, alpha=fill_alpha, zorder=2)

    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=14, fontweight="bold")
    ax.set_rlabel_position(16)
    ax.tick_params(axis="y", pad=4)

    ax.set_xticks(angles)
    ax.set_xticklabels(DIMENSIONS, fontsize=17, fontweight="bold")
    ax.tick_params(axis="x", pad=10)
    for tick in ax.get_xticklabels() + ax.get_yticklabels():
        tick.set_fontweight("bold")

    ax.grid(color="#8A8A8A", linestyle="--", linewidth=1.0, alpha=0.55)
    ax.spines["polar"].set_color("#4D4D4D")
    ax.spines["polar"].set_linewidth(1.8)

    # Separate the two close-valued annotations radially to keep every value readable.
    for angle, positive, agreement in zip(angles, POSITIVE_RATINGS, ICC_SCALED):
        ax.annotate(
            f"{positive:.1f}",
            xy=(angle, positive),
            xytext=(0, 13),
            textcoords="offset points",
            ha="center",
            va="center",
            fontsize=15,
            fontweight="bold",
            color="#0F4D92",
            bbox={"boxstyle": "round,pad=0.18", "facecolor": "white", "edgecolor": "none", "alpha": 0.88},
            zorder=6,
        )
        ax.annotate(
            f"{agreement:.1f}",
            xy=(angle, agreement),
            xytext=(0, -17),
            textcoords="offset points",
            ha="center",
            va="center",
            fontsize=15,
            fontweight="bold",
            color="#B64342",
            bbox={"boxstyle": "round,pad=0.18", "facecolor": "white", "edgecolor": "none", "alpha": 0.88},
            zorder=6,
        )

    legend = fig.legend(
        loc="lower left",
        bbox_to_anchor=(0.075, 0.925, 0.85, 0.06),
        ncol=2,
        mode="expand",
        borderaxespad=0.0,
        columnspacing=2.0,
        handlelength=3.0,
        handletextpad=0.75,
        fontsize=18,
    )
    for text in legend.get_texts():
        text.set_fontweight("bold")

    fig.subplots_adjust(left=0.11, right=0.89, bottom=0.08, top=0.88)

    for suffix, dpi in (("png", 600), ("pdf", 600), ("svg", 600)):
        fig.savefig(
            OUTPUT_STEM.with_suffix(f".{suffix}"),
            dpi=dpi,
            bbox_inches="tight",
            pad_inches=0.06,
            facecolor="white",
        )

    plt.close(fig)


if __name__ == "__main__":
    main()
