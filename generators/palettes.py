"""Curated looks extracted from the supplied JP Palette.aco swatches.

The source ACO contains 251 unnamed swatches. These named looks are curated
four-colour subsets; primary/secondary are the first two colours.
"""
from __future__ import annotations

from copy import deepcopy

JP_PALETTE_LOOKS = {
    "Sakura · 桜": ["#F8C3CD", "#F4A7B9", "#FEDFE1", "#DC9FB4"],
    "Beni · 紅": ["#CB1B45", "#8E354A", "#B5495B", "#FFFFFB"],
    "Matcha · 抹茶": ["#7BA23F", "#91AD70", "#42602D", "#FCFAF2"],
    "Ai · 藍": ["#006284", "#2B5F75", "#577C8A", "#FFFFFB"],
    "Fuji · 藤": ["#8A6BBE", "#8F77B5", "#B28FCE", "#3C2F41"],
    "Kitsune · 狐": ["#C46243", "#DB8E71", "#6A4028", "#FCFAF2"],
    "Yamabuki · 山吹": ["#FFC408", "#E9CD4C", "#A28C37", "#554236"],
    "Sumi · 墨": ["#0B1013", "#787878", "#BDC0BA", "#FFFFFB"],
    "Shinbashi · 新橋": ["#00AA90", "#66BAB7", "#4F726C", "#0B1013"],
    "Riso · リソ": ["#D0104C", "#FFC408", "#8A6BBE", "#FCFAF2"],
}


def palette_look(name: str) -> dict[str, str | list[str]]:
    colours = JP_PALETTE_LOOKS[name]
    return {
        "name": name,
        "primary_color": colours[0],
        "secondary_color": colours[1],
        "background_color": colours[3],
        "colors": list(colours),
    }


def random_palette_look(rng) -> dict[str, str | list[str]]:
    import random
    chooser = rng if rng is not None else random
    return palette_look(chooser.choice(tuple(JP_PALETTE_LOOKS)))


def palette_names() -> list[str]:
    return list(JP_PALETTE_LOOKS)
