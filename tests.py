# bodymap.py
# Explain it simply: this module draws a front-view body map using matplotlib.
# It shows organ and system status without using HTML or JavaScript.

from __future__ import annotations

from typing import Dict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse, Rectangle


def _organ_color(status: str):
    palette = {
        "GREEN": "#34C77B",
        "YELLOW": "#F2C94C",
        "ORANGE": "#F2994A",
        "RED": "#EB5757",
        "NEUTRAL": "#9CA3AF",
    }
    return palette.get(status, "#9CA3AF")


def draw_body_map(statuses: Dict[str, str]):
    fig, ax = plt.subplots(figsize=(6, 8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.set_aspect("equal")
    ax.axis("off")

    head = Circle((5, 10.6), 0.9, fill=False, edgecolor="#E5E7EB", linewidth=2)
    ax.add_patch(head)
    torso = Rectangle((3.7, 6.3), 2.6, 3.2, facecolor="none", edgecolor="#E5E7EB", linewidth=2)
    ax.add_patch(torso)
    left_arm = Rectangle((2.2, 7.0), 1.3, 2.0, facecolor="none", edgecolor="#E5E7EB", linewidth=2)
    right_arm = Rectangle((6.5, 7.0), 1.3, 2.0, facecolor="none", edgecolor="#E5E7EB", linewidth=2)
    ax.add_patch(left_arm)
    ax.add_patch(right_arm)
    left_leg = Rectangle((4.0, 2.1), 1.0, 3.8, facecolor="none", edgecolor="#E5E7EB", linewidth=2)
    right_leg = Rectangle((5.0, 2.1), 1.0, 3.8, facecolor="none", edgecolor="#E5E7EB", linewidth=2)
    ax.add_patch(left_leg)
    ax.add_patch(right_leg)

    brain = Circle((5, 10.3), 0.45, color=_organ_color(statuses.get("brain", "GREEN")))
    heart = Circle((5, 7.8), 0.55, color=_organ_color(statuses.get("heart", "GREEN")))
    lungs = Ellipse((4.2, 7.2), 1.2, 0.8, color=_organ_color(statuses.get("lungs", "GREEN")))
    lungs2 = Ellipse((5.8, 7.2), 1.2, 0.8, color=_organ_color(statuses.get("lungs", "GREEN")))
    stomach = Circle((5, 5.9), 0.7, color=_organ_color(statuses.get("stomach", "GREEN")))
    muscles = Ellipse((5, 4.4), 2.3, 1.4, color=_organ_color(statuses.get("muscles", "GREEN")))
    bones = Ellipse((5, 3.3), 2.6, 0.9, color=_organ_color(statuses.get("bones", "GREEN")))
    skin = Circle((5, 8.6), 2.7, facecolor="none", edgecolor="#E5E7EB", linewidth=1.5)

    ax.add_patch(skin)
    ax.add_patch(brain)
    ax.add_patch(heart)
    ax.add_patch(lungs)
    ax.add_patch(lungs2)
    ax.add_patch(stomach)
    ax.add_patch(muscles)
    ax.add_patch(bones)

    if statuses.get("radiation", "GREEN") == "RED":
        overlay = Ellipse((5, 6.8), 5.0, 6.5, facecolor="none", edgecolor="#EB5757", linewidth=2.5, linestyle=(0, (6, 5)))
        ax.add_patch(overlay)

    if statuses.get("heart", "GREEN") == "RED":
        pulse = Circle((5, 7.8), 0.8, fill=False, edgecolor="#EB5757", linewidth=2.5)
        ax.add_patch(pulse)

    if statuses.get("lungs", "GREEN") == "RED":
        pulse2 = Ellipse((5, 7.2), 1.6, 1.2, fill=False, edgecolor="#EB5757", linewidth=2.5)
        ax.add_patch(pulse2)

    plt.tight_layout()
    return fig


if __name__ == "__main__":
    fig = draw_body_map({
        "brain": "GREEN",
        "heart": "YELLOW",
        "lungs": "ORANGE",
        "stomach": "GREEN",
        "muscles": "GREEN",
        "bones": "GREEN",
        "radiation": "GREEN",
    })
    fig.savefig("body_map_demo.png")
    print("Body map created.")
