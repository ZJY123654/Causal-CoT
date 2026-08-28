import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


OUTPUT_DIR = Path(__file__).resolve().parent
INPUT_PATH = OUTPUT_DIR / "table_causal_effects.csv"
OUTPUT_STEM = OUTPUT_DIR / "fig_causal_effects"

LABELS = {
    "存在人的不安全动作": "Unsafe action (layer)",
    "隐患排查治理": "Hazard rectification governance",
    "监督检查": "Supervisory inspection",
    "隐患整改不闭环": "Rectification not closed-loop",
    "安全责任未落实": "Safety responsibility not implemented",
    "安全培训不足": "Insufficient safety training",
    "安全知识教育不足": "Insufficient safety-knowledge education",
    "作业人员不了解风险和控制措施": "Workers unaware of risks/control measures",
    "未按地质水文条件调整方案": "Plan not adapted to geo-hydrological conditions",
    "未识别危险源": "Hazard sources not identified",
    "职责不清": "Unclear responsibilities",
    "交叉作业协调不足": "Poor coordination of concurrent operations",
    "专项安全技术交底不足": "Insufficient task-specific safety briefing",
    "职工安全知识教育不足": "Insufficient worker safety education",
    "未系安全带": "Safety belt not used",
    "方案未落实": "Plan not implemented",
}


def read_rows() -> list[dict]:
    with INPUT_PATH.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    usable = []
    for row in rows:
        if row.get("run_success", "").lower() != "true":
            continue
        row["support"] = int(row["support"])
        for key in ("adjusted_ate", "ci95_low", "ci95_high", "p_value"):
            row[key] = float(row[key])
        usable.append(row)
    return sorted(usable, key=lambda row: row["adjusted_ate"])


def main() -> None:
    plt.rcParams.update(
        {
            "font.family": "Times New Roman",
            "font.size": 12,
            "font.weight": "bold",
            "axes.labelweight": "bold",
            "axes.linewidth": 1.2,
            "xtick.major.width": 1.2,
            "ytick.major.width": 1.2,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )

    rows = read_rows()
    y = np.arange(len(rows))
    effects = np.array([row["adjusted_ate"] * 100 for row in rows])
    lows = np.array([row["ci95_low"] * 100 for row in rows])
    highs = np.array([row["ci95_high"] * 100 for row in rows])
    significant = np.array(
        [row["ci95_low"] > 0 or row["ci95_high"] < 0 for row in rows], dtype=bool
    )
    colors = np.where(significant, "#D97948", "#4C89B8")

    fig, ax = plt.subplots(figsize=(11.4, 8.5), facecolor="white")
    ax.axvline(0, color="#4A4A4A", linewidth=1.35, linestyle="--", zorder=1)
    ax.hlines(y, lows, highs, color=colors, linewidth=2.0, zorder=2)
    ax.scatter(effects, y, s=67, c=colors, edgecolors="white", linewidths=0.8, zorder=3)
    cap_height = 0.16
    for idx, (low, high, color) in enumerate(zip(lows, highs, colors)):
        ax.vlines([low, high], idx - cap_height, idx + cap_height, color=color, linewidth=1.7)

    labels = [f"{LABELS[row['treatment']]}  (n={row['support']})" for row in rows]
    ax.set_yticks(y, labels=labels)
    ax.set_xlabel("Backdoor-adjusted ATE on severe-consequence probability (percentage points)")
    ax.set_xlim(min(lows) - 2.5, max(highs) + 3.0)
    ax.grid(axis="x", color="#D9D9D9", linewidth=0.8, alpha=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", labelsize=11.5)

    for tick in ax.get_xticklabels() + ax.get_yticklabels():
        tick.set_fontweight("bold")

    for idx, row in enumerate(rows):
        if not significant[idx]:
            continue
        ax.text(
            highs[idx] + 0.7,
            idx,
            f"{effects[idx]:.2f}",
            va="center",
            ha="left",
            fontsize=11.5,
            fontweight="bold",
            color="#A94723",
        )

    ax.text(
        0.01,
        1.012,
        "Orange: 95% bootstrap CI excludes zero     Blue: CI includes zero",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=11.5,
        fontweight="bold",
    )
    fig.subplots_adjust(left=0.42, right=0.96, top=0.93, bottom=0.105)

    for suffix in ("png", "pdf", "svg"):
        fig.savefig(
            OUTPUT_STEM.with_suffix(f".{suffix}"),
            dpi=600 if suffix == "png" else None,
            bbox_inches="tight",
            facecolor="white",
        )
    plt.close(fig)


if __name__ == "__main__":
    main()
