import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_STEM = OUTPUT_DIR / "fig_case_hec_kg"
CASE_ID = "HCA-b9630e82d7"

COLORS = {
    "case": "#D99532",
    "direct": "#C95D54",
    "management": "#3E8E8C",
    "culture": "#5B8F58",
    "process": "#8666A7",
    "measure": "#3E78A8",
    "ink": "#263238",
    "muted": "#66727C",
    "line": "#7A858E",
    "panel": "#F6F8FA",
    "border": "#C8CFD5",
}

DISPLAY = {
    "临时建筑坍塌致使人员伤亡事故": "Temporary-\nstructure collapse\naccident",
    "挡墙整体稳定性差": "Poor retaining-\nwall stability",
    "安全培训流于形式": "Safety training reduced\nto a formality",
    "未充分考虑地质条件": "Geological conditions\nnot fully considered",
    "施工现场监督检查不力": "Weak on-site\nsupervision",
    "隐患排查整改不落实": "Hazard rectification\nnot implemented",
    "安全管理不到位": "Inadequate safety\nmanagement",
    "重进度轻安全": "Schedule prioritized\nover safety",
    "安全投入不足": "Insufficient safety\ninvestment",
    "安全责任意识淡薄": "Weak safety\naccountability",
    "挡墙坍塌导致人员坠落": "Retaining-wall\ncollapse and\nworker fall",
    "落实安全生产责任制度": "Enforce safety\nresponsibility\nsystem",
}

REQUIRED_EDGES = [
    ("临时建筑坍塌致使人员伤亡事故", "hasDirectCause", "挡墙整体稳定性差"),
    ("挡墙整体稳定性差", "hasManagementCause", "安全培训流于形式"),
    ("挡墙整体稳定性差", "hasManagementCause", "未充分考虑地质条件"),
    ("挡墙整体稳定性差", "hasManagementCause", "施工现场监督检查不力"),
    ("挡墙整体稳定性差", "hasManagementCause", "隐患排查整改不落实"),
    ("挡墙整体稳定性差", "hasManagementCause", "安全管理不到位"),
    ("安全管理不到位", "hasCultureCause", "重进度轻安全"),
    ("安全管理不到位", "hasCultureCause", "安全投入不足"),
    ("安全管理不到位", "hasCultureCause", "安全责任意识淡薄"),
    ("挡墙整体稳定性差", "leadTo", "挡墙坍塌导致人员坠落"),
    ("挡墙整体稳定性差", "controlledBy", "落实安全生产责任制度"),
]

GROUPS = [
    (0.25, 3.40, "Case evidence", COLORS["case"]),
    (3.80, 2.80, "Direct cause", COLORS["direct"]),
    (6.75, 4.50, "Management causes", COLORS["management"]),
    (11.40, 3.80, "Culture causes", COLORS["culture"]),
    (15.35, 3.60, "Evolution /\ncontrol", COLORS["process"]),
]

POSITIONS = {
    "临时建筑坍塌致使人员伤亡事故": (1.95, 0.00),
    "挡墙整体稳定性差": (5.20, 0.00),
    "安全培训流于形式": (9.00, 2.20),
    "未充分考虑地质条件": (9.00, 1.10),
    "施工现场监督检查不力": (9.00, 0.00),
    "隐患排查整改不落实": (9.00, -1.10),
    "安全管理不到位": (9.00, -2.20),
    "重进度轻安全": (13.30, 1.10),
    "安全投入不足": (13.30, 0.00),
    "安全责任意识淡薄": (13.30, -1.10),
    "挡墙坍塌导致人员坠落": (17.15, 1.85),
    "落实安全生产责任制度": (17.15, -1.85),
}

NODE_STYLE = {
    "临时建筑坍塌致使人员伤亡事故": (3.00, 1.55, "case"),
    "挡墙整体稳定性差": (2.50, 1.35, "direct"),
    "安全培训流于形式": (3.75, 0.96, "management"),
    "未充分考虑地质条件": (3.75, 0.96, "management"),
    "施工现场监督检查不力": (3.75, 0.96, "management"),
    "隐患排查整改不落实": (3.75, 0.96, "management"),
    "安全管理不到位": (3.75, 0.96, "management"),
    "重进度轻安全": (3.05, 1.00, "culture"),
    "安全投入不足": (3.05, 1.00, "culture"),
    "安全责任意识淡薄": (3.05, 1.00, "culture"),
    "挡墙坍塌导致人员坠落": (3.10, 1.30, "process"),
    "落实安全生产责任制度": (3.10, 1.30, "measure"),
}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


def validate_source_graph() -> None:
    entities = {
        row["id"]: row
        for row in read_jsonl(PROJECT_ROOT / "data/kg/entities.jsonl")
        if row.get("case_id") == CASE_ID or CASE_ID in row.get("source_cases", [])
    }
    observed = set()
    for relation in read_jsonl(PROJECT_ROOT / "data/kg/triples.jsonl"):
        if relation.get("case_id") != CASE_ID and CASE_ID not in relation.get("source_cases", []):
            continue
        source = entities.get(relation.get("source_id"), {})
        target = entities.get(relation.get("target_id"), {})
        if source and target:
            observed.add((source.get("name"), relation.get("type"), target.get("name")))
    missing = [edge for edge in REQUIRED_EDGES if edge not in observed]
    if missing:
        raise ValueError(f"Case graph changed; missing required edges: {missing}")


def draw_panel(ax, x: float, width: float, title: str, color: str) -> None:
    panel = FancyBboxPatch(
        (x, -4.00), width, 8.00,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        facecolor=COLORS["panel"], edgecolor="#E1E5E8", linewidth=0.9, zorder=0,
    )
    ax.add_patch(panel)
    ax.add_patch(Rectangle((x, 3.78), width, 0.22, facecolor=color, edgecolor="none", zorder=1))
    ax.text(x + 0.20, 3.30, title, ha="left", va="center", fontsize=32,
            fontweight="bold", color=color, linespacing=0.90, zorder=4)


def draw_node(ax, name: str) -> None:
    x, y = POSITIONS[name]
    width, height, semantic = NODE_STYLE[name]
    color = COLORS[semantic]
    shadow = FancyBboxPatch(
        (x - width / 2 + 0.045, y - height / 2 - 0.05), width, height,
        boxstyle="round,pad=0.035,rounding_size=0.07",
        facecolor="#D9DEE2", edgecolor="none", alpha=0.55, zorder=2,
    )
    ax.add_patch(shadow)
    card = FancyBboxPatch(
        (x - width / 2, y - height / 2), width, height,
        boxstyle="round,pad=0.035,rounding_size=0.07",
        facecolor="white", edgecolor=COLORS["border"], linewidth=1.2, zorder=3,
    )
    ax.add_patch(card)
    ax.add_patch(Rectangle((x - width / 2, y - height / 2), 0.12, height,
                           facecolor=color, edgecolor="none", zorder=4))
    fontsize = 27
    ax.text(x + 0.06, y, DISPLAY[name], ha="center", va="center", fontsize=fontsize,
            fontweight="bold", color=COLORS["ink"], linespacing=0.98, zorder=5)


def node_boundary(name: str, side: str) -> tuple[float, float]:
    x, y = POSITIONS[name]
    width, height, _ = NODE_STYLE[name]
    offsets = {"left": (-width / 2, 0), "right": (width / 2, 0),
               "top": (0, height / 2), "bottom": (0, -height / 2)}
    dx, dy = offsets[side]
    return x + dx, y + dy


def arrow(ax, start, end, color=None, linewidth=1.55, zorder=1) -> None:
    ax.add_patch(FancyArrowPatch(
        start, end, arrowstyle="-|>", mutation_scale=12, linewidth=linewidth,
        color=color or COLORS["line"], connectionstyle="arc3,rad=0",
        shrinkA=0, shrinkB=0, zorder=zorder,
    ))


def line(ax, xs, ys, color=None, linewidth=1.35, zorder=1) -> None:
    ax.plot(xs, ys, color=color or COLORS["line"], linewidth=linewidth, zorder=zorder)


def relation_tag(ax, x: float, y: float, text: str, color: str) -> None:
    ax.text(x, y, text, ha="center", va="center", fontsize=22, fontweight="bold",
            style="italic", color=color,
            bbox={"boxstyle": "round,pad=0.23", "fc": "white", "ec": "#D9DEE2", "lw": 0.8},
            zorder=6)


def draw_edges(ax) -> None:
    arrow(ax, node_boundary("临时建筑坍塌致使人员伤亡事故", "right"),
          node_boundary("挡墙整体稳定性差", "left"),
          color=COLORS["direct"], linewidth=2.2)
    relation_tag(ax, 3.60, 1.08, "hasDirectCause", COLORS["direct"])

    source = node_boundary("挡墙整体稳定性差", "right")
    rail_x = 6.88
    line(ax, [source[0], rail_x], [source[1], source[1]], linewidth=1.6)
    management_names = ["安全培训流于形式", "未充分考虑地质条件", "施工现场监督检查不力",
                        "隐患排查整改不落实", "安全管理不到位"]
    ys = [POSITIONS[name][1] for name in management_names]
    line(ax, [rail_x, rail_x], [min(ys), max(ys)], linewidth=1.6)
    for name in management_names:
        target = node_boundary(name, "left")
        arrow(ax, (rail_x, target[1]), target, linewidth=1.45)
    relation_tag(ax, 6.95, 2.84, "hasManagementCause", COLORS["management"])

    source = node_boundary("安全管理不到位", "right")
    rail_x = 11.52
    line(ax, [source[0], rail_x], [source[1], source[1]], color=COLORS["culture"], linewidth=1.8)
    culture_names = ["重进度轻安全", "安全投入不足", "安全责任意识淡薄"]
    ys = [POSITIONS[name][1] for name in culture_names]
    line(ax, [rail_x, rail_x], [min(ys), max(ys)], color=COLORS["culture"], linewidth=1.8)
    for name in culture_names:
        target = node_boundary(name, "left")
        arrow(ax, (rail_x, target[1]), target, color=COLORS["culture"], linewidth=1.7)
    relation_tag(ax, 11.62, -3.43, "hasCultureCause", COLORS["culture"])

    direct_top = node_boundary("挡墙整体稳定性差", "top")
    process_left = node_boundary("挡墙坍塌导致人员坠落", "left")
    top_lane = 4.55
    line(ax, [direct_top[0], direct_top[0]], [direct_top[1], top_lane],
         color=COLORS["process"], linewidth=1.9)
    line(ax, [direct_top[0], process_left[0] - 0.24], [top_lane, top_lane],
         color=COLORS["process"], linewidth=1.9)
    arrow(ax, (process_left[0] - 0.24, top_lane), process_left,
          color=COLORS["process"], linewidth=1.9)
    relation_tag(ax, 13.55, 4.55, "leadTo", COLORS["process"])

    direct_bottom = node_boundary("挡墙整体稳定性差", "bottom")
    measure_left = node_boundary("落实安全生产责任制度", "left")
    bottom_lane = -4.55
    line(ax, [direct_bottom[0], direct_bottom[0]], [direct_bottom[1], bottom_lane],
         color=COLORS["measure"], linewidth=1.9)
    line(ax, [direct_bottom[0], measure_left[0] - 0.24], [bottom_lane, bottom_lane],
         color=COLORS["measure"], linewidth=1.9)
    arrow(ax, (measure_left[0] - 0.24, bottom_lane), measure_left,
          color=COLORS["measure"], linewidth=1.9)
    relation_tag(ax, 13.55, -4.55, "controlledBy", COLORS["measure"])


def main() -> None:
    validate_source_graph()
    plt.rcParams.update({
        "font.family": "Times New Roman", "font.size": 12, "font.weight": "bold",
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    })
    fig, ax = plt.subplots(figsize=(22.0, 12.0), facecolor="white")
    ax.set_xlim(0.05, 19.20)
    ax.set_ylim(-5.20, 5.15)
    ax.axis("off")
    for x, width, title, color in GROUPS:
        draw_panel(ax, x, width, title, color)
    draw_edges(ax)
    for name in POSITIONS:
        draw_node(ax, name)
    fig.subplots_adjust(left=0.015, right=0.985, top=0.985, bottom=0.02)
    for suffix in ("png", "pdf", "svg"):
        fig.savefig(OUTPUT_STEM.with_suffix(f".{suffix}"),
                    dpi=600 if suffix == "png" else None,
                    bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
