import json
import math
import textwrap
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_STEM = OUTPUT_DIR / "fig_global_hec_kg"
FONT_SCALE = 3.0

TYPE_COLORS = {
    "AccidentCase": "#F2B36D",
    "AccidentType": "#6FA8DC",
    "ConstructionActivity": "#87B5E1",
    "EngineeringObject": "#4F83C2",
    "EnvironmentCondition": "#71C1C8",
    "EquipmentFacility": "#9DAEDB",
    "SafetyCultureDefect": "#72BF77",
    "SafetyManagementDefect": "#A4D59D",
    "SafetyCapabilityDefect": "#B7A2D6",
    "UnsafeAction": "#F29F67",
    "UnsafeObjectState": "#E8857B",
    "AccidentProcess": "#C6A0D5",
    "Consequence": "#E49BC2",
    "PreventiveMeasure": "#74B8B8",
}

TYPE_LABELS = {
    "AccidentCase": "Accident case",
    "AccidentType": "Accident type",
    "ConstructionActivity": "Construction activity",
    "EngineeringObject": "Engineering object",
    "EnvironmentCondition": "Environment condition",
    "EquipmentFacility": "Equipment facility",
    "SafetyCultureDefect": "Safety culture defect",
    "SafetyManagementDefect": "Safety management defect",
    "SafetyCapabilityDefect": "Safety capability defect",
    "UnsafeAction": "Unsafe action",
    "UnsafeObjectState": "Unsafe object state",
    "AccidentProcess": "Accident process",
    "Consequence": "Consequence",
    "PreventiveMeasure": "Preventive measure",
}

BOX_LABELS = {
    "AccidentCase": "Accident\ncase",
    "AccidentType": "Accident\ntype",
    "ConstructionActivity": "Construction\nactivity",
    "EngineeringObject": "Engineering\nobject",
    "EnvironmentCondition": "Environment\ncondition",
    "EquipmentFacility": "Equipment\nfacility",
    "SafetyCultureDefect": "Safety\nculture\ndefect",
    "SafetyManagementDefect": "Safety\nmanagement\ndefect",
    "SafetyCapabilityDefect": "Safety\ncapability\ndefect",
    "UnsafeAction": "Unsafe\naction",
    "UnsafeObjectState": "Unsafe\nobject state",
    "AccidentProcess": "Accident\nprocess",
    "Consequence": "Consequence",
    "PreventiveMeasure": "Preventive\nmeasure",
}

BACKBONE_POS = {
    "AccidentCase": (0.9, 0.0),
    "AccidentType": (0.6, 4.0),
    "ConstructionActivity": (3.65, 4.0),
    "EngineeringObject": (6.7, 4.0),
    "EnvironmentCondition": (9.75, 4.0),
    "EquipmentFacility": (12.8, 4.0),
    "UnsafeAction": (4.2, 0.9),
    "UnsafeObjectState": (4.2, -1.8),
    "SafetyCapabilityDefect": (7.3, 1.25),
    "SafetyManagementDefect": (10.1, 0.0),
    "SafetyCultureDefect": (13.0, 0.0),
    "AccidentProcess": (7.25, -2.55),
    "Consequence": (10.15, -4.7),
    "PreventiveMeasure": (4.2, -5.35),
}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


def normalize_layout(pos: dict[str, np.ndarray]) -> dict[str, tuple[float, float]]:
    values = np.array(list(pos.values()), dtype=float)
    mins = values.min(axis=0)
    spans = np.maximum(values.max(axis=0) - mins, 1e-9)
    scaled = (values - mins) / spans
    scaled[:, 0] = scaled[:, 0] * 1.9 - 0.95
    scaled[:, 1] = scaled[:, 1] * 1.9 - 0.95
    return {node: tuple(value) for node, value in zip(pos, scaled)}


def draw_global_graph(ax, graph: nx.Graph, entities: dict[str, dict]) -> tuple[int, int]:
    components = sorted(nx.connected_components(graph), key=len, reverse=True)
    core_nodes = components[0]
    core = graph.subgraph(core_nodes).copy()
    pos = nx.forceatlas2_layout(
        core,
        max_iter=45,
        scaling_ratio=4.0,
        gravity=1.2,
        seed=17,
    )
    pos = normalize_layout(pos)

    edge_segments = np.array(
        [[pos[source], pos[target]] for source, target in core.edges()], dtype=float
    )
    if len(edge_segments):
        from matplotlib.collections import LineCollection

        collection = LineCollection(
            edge_segments,
            colors="#8C9298",
            linewidths=0.22,
            alpha=0.15,
            zorder=1,
            rasterized=True,
        )
        ax.add_collection(collection)

    nodes_by_type: dict[str, list[str]] = defaultdict(list)
    for node in core:
        nodes_by_type[entities[node]["label"]].append(node)
    for label, nodes in nodes_by_type.items():
        xy = np.array([pos[node] for node in nodes])
        size = 8.5 if label == "AccidentCase" else 4.8
        ax.scatter(
            xy[:, 0],
            xy[:, 1],
            s=size,
            c=TYPE_COLORS[label],
            edgecolors="none",
            alpha=0.82,
            zorder=2,
            rasterized=True,
        )

    ax.set_xlim(-1.02, 1.02)
    ax.set_ylim(-1.02, 1.02)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.text(
        0.01,
        1.01,
        "(a) Connected canonical HEC-KG",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=18 * FONT_SCALE,
        fontweight="bold",
        color="#196A99",
    )
    ax.text(
        0.01,
        0.895,
        f"{core.number_of_nodes():,} nodes  |  {core.number_of_edges():,} relations",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=13 * FONT_SCALE,
        fontweight="bold",
        color="#4D4D4D",
    )
    return core.number_of_nodes(), core.number_of_edges()


def edge_boundary(center, toward, width=2.8, height=2.0):
    dx = toward[0] - center[0]
    dy = toward[1] - center[1]
    tx = width / 2 / abs(dx) if dx else float("inf")
    ty = height / 2 / abs(dy) if dy else float("inf")
    scale = min(tx, ty)
    return center[0] + scale * dx, center[1] + scale * dy


def draw_backbone_node(ax, label: str, count: int) -> None:
    x, y = BACKBONE_POS[label]
    width = 2.8
    height = 2.0
    patch = FancyBboxPatch(
        (x - width / 2, y - height / 2),
        width,
        height,
        boxstyle="round,pad=0.04,rounding_size=0.07",
        facecolor=TYPE_COLORS[label],
        edgecolor="#333333",
        linewidth=1.25,
        zorder=3,
    )
    ax.add_patch(patch)
    ax.text(
        x,
        y + 0.28,
        BOX_LABELS[label],
        ha="center",
        va="center",
        fontsize=10.5 * FONT_SCALE,
        fontweight="bold",
        linespacing=0.94,
        zorder=4,
    )
    ax.text(
        x,
        y - 0.68,
        f"n = {count:,}",
        ha="center",
        va="center",
        fontsize=9.7 * FONT_SCALE,
        fontweight="bold",
        color="#333333",
        zorder=4,
    )


def draw_backbone_edge(ax, source: str, target: str, relation: str, count: int, rad: float) -> None:
    start = BACKBONE_POS[source]
    end = BACKBONE_POS[target]
    edge_start = edge_boundary(start, end)
    edge_end = edge_boundary(end, start)
    linewidth = 0.8 + 1.7 * math.log1p(count) / math.log1p(1800)
    arrow = FancyArrowPatch(
        edge_start,
        edge_end,
        arrowstyle="-|>",
        mutation_scale=22,
        linewidth=linewidth,
        color="#59636D",
        alpha=0.88,
        connectionstyle=f"arc3,rad={rad}",
        zorder=1,
    )
    ax.add_patch(arrow)

def draw_type_projection(ax, entity_counts: Counter, triples: list[dict], entities: dict[str, dict]) -> None:
    type_edges: Counter[tuple[str, str, str]] = Counter()
    for triple in triples:
        source = entities.get(triple.get("source_id"), {})
        target = entities.get(triple.get("target_id"), {})
        if source and target:
            type_edges[(source["label"], triple["type"], target["label"])] += 1

    edge_rads = {
        ("AccidentCase", "hasAccidentType", "AccidentType"): -0.06,
        ("AccidentCase", "occursInActivity", "ConstructionActivity"): -0.05,
        ("AccidentCase", "involvesObject", "EngineeringObject"): -0.04,
        ("AccidentCase", "hasEnvironmentCondition", "EnvironmentCondition"): -0.08,
        ("AccidentCase", "involvesEquipment", "EquipmentFacility"): -0.10,
        ("AccidentCase", "hasConsequence", "Consequence"): 0.13,
        ("AccidentCase", "hasDirectCause", "UnsafeAction"): -0.04,
        ("AccidentCase", "hasDirectCause", "UnsafeObjectState"): 0.04,
        ("UnsafeAction", "hasCapabilityCause", "SafetyCapabilityDefect"): -0.06,
        ("UnsafeAction", "hasManagementCause", "SafetyManagementDefect"): -0.15,
        ("UnsafeObjectState", "hasManagementCause", "SafetyManagementDefect"): 0.06,
        ("SafetyManagementDefect", "hasCultureCause", "SafetyCultureDefect"): 0.0,
        ("UnsafeAction", "leadTo", "AccidentProcess"): 0.08,
        ("UnsafeObjectState", "leadTo", "AccidentProcess"): -0.05,
        ("UnsafeAction", "controlledBy", "PreventiveMeasure"): 0.10,
        ("UnsafeObjectState", "controlledBy", "PreventiveMeasure"): -0.06,
    }

    for (source, relation, target), count in type_edges.items():
        if source in BACKBONE_POS and target in BACKBONE_POS:
            draw_backbone_edge(
                ax,
                source,
                target,
                relation,
                count,
                edge_rads.get((source, relation, target), 0.0),
            )
    for label in BACKBONE_POS:
        draw_backbone_node(ax, label, entity_counts[label])

    ax.set_xlim(-0.95, 14.55)
    ax.set_ylim(-6.7, 6.15)
    ax.axis("off")
    ax.text(
        0.0,
        1.055,
        "(b) Type-level projection\n(edge width encodes relation frequency)",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=17 * FONT_SCALE,
        fontweight="bold",
        color="#B65B22",
    )


def main() -> None:
    plt.rcParams.update(
        {
            "font.family": "Times New Roman",
            "font.size": 11 * FONT_SCALE,
            "font.weight": "bold",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )

    entity_rows = read_jsonl(PROJECT_ROOT / "data/fusion/canonical_entities.jsonl")
    triple_rows = read_jsonl(PROJECT_ROOT / "data/fusion/canonical_triples.jsonl")
    entities = {row["id"]: row for row in entity_rows}
    graph = nx.Graph()
    graph.add_nodes_from(entities)
    for triple in triple_rows:
        if triple.get("source_id") in entities and triple.get("target_id") in entities:
            graph.add_edge(triple["source_id"], triple["target_id"])

    entity_counts = Counter(row["label"] for row in entity_rows)
    fig = plt.figure(figsize=(30.0, 18.0), facecolor="white")
    ax_global = fig.add_axes([0.02, 0.13, 0.46, 0.57])
    ax_types = fig.add_axes([0.50, 0.12, 0.49, 0.58])

    core_nodes, core_edges = draw_global_graph(ax_global, graph, entities)
    draw_type_projection(ax_types, entity_counts, triple_rows, entities)

    handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="",
            markerfacecolor=color,
            markeredgecolor="none",
            markersize=20,
            label=TYPE_LABELS[label],
        )
        for label, color in TYPE_COLORS.items()
    ]
    legend = fig.legend(
        handles=handles,
        loc="lower left",
        bbox_to_anchor=(0.025, 0.73, 0.95, 0.26),
        ncol=4,
        mode="expand",
        frameon=False,
        handletextpad=0.42,
        columnspacing=0.9,
        labelspacing=0.72,
        fontsize=12.8 * FONT_SCALE,
    )
    for text in legend.get_texts():
        text.set_fontweight("bold")

    isolated_count = nx.number_of_isolates(graph)
    footer = (
        f"Canonical HEC-KG: {graph.number_of_nodes():,} entities and "
        f"{graph.number_of_edges():,} relations. The connected evidence core contains "
        f"{core_nodes:,} entities; {isolated_count:,} accepted entities currently have no validated relation."
    )
    fig.text(
        0.02,
        0.022,
        textwrap.fill(footer, width=112),
        ha="left",
        va="bottom",
        fontsize=12.8 * FONT_SCALE,
        fontweight="bold",
        color="#333333",
    )

    for suffix in ("png", "pdf", "svg"):
        fig.savefig(
            OUTPUT_STEM.with_suffix(f".{suffix}"),
            dpi=300 if suffix == "png" else None,
            bbox_inches="tight",
            facecolor="white",
        )
    plt.close(fig)


if __name__ == "__main__":
    main()
