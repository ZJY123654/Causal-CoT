from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_STEM = OUTPUT_DIR / "baseline_comparison_with_error_bars"

METHODS = [
    "Zero-shot",
    "Few-shot",
    "Auto-CoT",
    "Plan-and-Solve",
    "GraphRAG-Extract",
    "Causal-CoT",
]

METRICS = [
    "Entity Precision",
    "Entity Recall",
    "Entity F1-score",
    "Relation Precision",
    "Relation Recall",
    "Relation F1-score",
]

# Rows correspond to METHODS and columns correspond to METRICS.
MEANS = np.array(
    [
        [76.8, 67.4, 71.8, 68.7, 56.9, 62.2],
        [80.4, 73.8, 76.9, 73.6, 62.8, 67.7],
        [82.1, 76.6, 79.2, 76.2, 67.1, 71.3],
        [83.5, 77.9, 80.6, 78.0, 68.5, 72.9],
        [85.1, 80.6, 82.8, 81.2, 73.9, 77.3],
        [88.3, 85.7, 87.0, 85.8, 81.6, 83.6],
    ],
    dtype=float,
)

SDS = np.array(
    [
        [2.6, 3.0, 2.4, 3.2, 3.5, 2.9],
        [2.3, 2.7, 2.2, 2.9, 3.2, 2.6],
        [2.1, 2.4, 2.0, 2.7, 3.0, 2.5],
        [2.0, 2.3, 1.9, 2.5, 2.8, 2.3],
        [1.8, 2.1, 1.7, 2.2, 2.6, 2.1],
        [1.5, 1.8, 1.4, 1.9, 2.1, 1.7],
    ],
    dtype=float,
)

# Color-blind-friendly palette with the proposed method emphasized in deep blue.
COLORS = ["#7A7A7A", "#E69F00", "#CC79A7", "#009E73", "#56B4E9", "#0072B2"]
HATCHES = ["//", "\\\\", "..", "--", "xx", ""]


def apply_publication_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "Times New Roman",
            "font.size": 15,
            "font.weight": "bold",
            "axes.labelweight": "bold",
            "axes.linewidth": 1.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
            "legend.fontsize": 16,
            "xtick.labelsize": 15,
            "ytick.labelsize": 15,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )


def main() -> None:
    apply_publication_style()

    fig, ax = plt.subplots(figsize=(20, 8.8))
    x = np.arange(len(METRICS), dtype=float)
    bar_width = 0.13
    offsets = (np.arange(len(METHODS)) - (len(METHODS) - 1) / 2) * bar_width

    for method_idx, (method, color, hatch) in enumerate(zip(METHODS, COLORS, HATCHES)):
        positions = x + offsets[method_idx]
        bars = ax.bar(
            positions,
            MEANS[method_idx],
            width=bar_width,
            yerr=SDS[method_idx],
            label=method,
            color=color,
            edgecolor="black",
            linewidth=1.15,
            hatch=hatch,
            error_kw={
                "ecolor": "black",
                "elinewidth": 1.45,
                "capsize": 3.5,
                "capthick": 1.45,
            },
            zorder=3,
        )

        for bar, mean, sd in zip(bars, MEANS[method_idx], SDS[method_idx]):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                mean + sd + 1.05,
                f"{mean:.1f}",
                ha="center",
                va="bottom",
                fontsize=15,
                fontweight="bold",
                color="black",
                clip_on=False,
                zorder=5,
            )

    ax.set_ylabel("Score (%)", fontsize=18, fontweight="bold", labelpad=10)
    ax.set_xticks(x)
    ax.set_xticklabels(METRICS, fontsize=16, fontweight="bold")
    ax.tick_params(axis="x", pad=5, width=1.6, length=5)
    ax.tick_params(axis="y", width=1.6, length=5)
    for tick in ax.get_yticklabels():
        tick.set_fontweight("bold")

    ax.set_ylim(0, 100)
    ax.set_yticks(np.arange(0, 101, 20))
    ax.set_xlim(-0.56, len(METRICS) - 0.44)
    ax.yaxis.grid(True, linestyle="--", linewidth=0.8, alpha=0.35, zorder=0)
    ax.xaxis.grid(False)

    legend = fig.legend(
        loc="lower left",
        bbox_to_anchor=(0.055, 0.915, 0.94, 0.07),
        ncol=6,
        mode="expand",
        borderaxespad=0.0,
        columnspacing=1.0,
        handlelength=2.3,
        handleheight=1.15,
        handletextpad=0.55,
        fontsize=16,
    )
    for text in legend.get_texts():
        text.set_fontweight("bold")

    fig.subplots_adjust(left=0.065, right=0.995, bottom=0.12, top=0.89)

    for suffix, dpi in (("png", 600), ("pdf", 600), ("svg", 600)):
        fig.savefig(
            OUTPUT_STEM.with_suffix(f".{suffix}"),
            dpi=dpi,
            bbox_inches="tight",
            pad_inches=0.04,
            facecolor="white",
        )

    plt.close(fig)


if __name__ == "__main__":
    main()
