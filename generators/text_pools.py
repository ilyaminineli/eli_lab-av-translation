from __future__ import annotations

import random
import re
from pathlib import Path

# Curated phrases are retained as a reliable fallback and for short-form collage text.
TEXT_POOLS: dict[str, dict[str, tuple[str, ...]]] = {
    "memory": {
        "en": (
            "MEMORY", "AFTERIMAGE", "ARCHIVE", "REMNANT", "RECALL", "ERASURE",
            "ECHO", "TRACE", "REMEMBER", "NO RETURN", "THE SHAPE OF LOSS",
            "NOTHING STAYS",
        ),
        "ja": (
            "記憶", "残像", "記録", "痕跡", "忘却", "反復", "不在", "回想",
            "余白", "消去", "残響", "帰れない",
        ),
    },
    "body": {
        "en": (
            "BODY", "SKIN", "BLOOD", "TOUCH", "HUNGER", "DESIRE", "GENDER",
            "BREATH", "VEIL", "SENSATION", "THE OTHER",
        ),
        "ja": (
            "身体", "皮膚", "血", "接触", "空腹", "欲望", "性", "呼吸",
            "仮面", "感覚", "他者", "輪郭",
        ),
    },
    "signal": {
        "en": (
            "SIGNAL", "NOISE", "STATIC", "TRANSMISSION", "FEEDBACK", "CARRIER",
            "FREQUENCY", "INTERRUPT", "REBOOT", "ERROR", "LOST CONNECTION",
            "DECODE",
        ),
        "ja": (
            "信号", "雑音", "静電気", "伝送", "反響", "搬送波", "周波数",
            "中断", "再起動", "誤差", "接続不能", "解読",
        ),
    },
    "ritual": {
        "en": (
            "RITUAL", "OFFERING", "WITNESS", "THRESHOLD", "CURSE", "TOLERANCE",
            "GAZE", "VESSEL", "RETURN", "PROOF", "COLLECTION", "SACRED ERROR",
        ),
        "ja": (
            "儀式", "供物", "証人", "境界", "呪い", "寛容", "視線", "器",
            "帰還", "証明", "収集", "聖なる誤差",
        ),
    },
    "identity": {
        "en": (
            "IDENTITY", "INTEGRATION", "OUTSIDER", "BLIND SPOT", "MIRROR",
            "DOUBLE", "ALIAS", "NO CATEGORY", "BECOMING", "UNDEFINED",
            "ANOTHER NAME",
        ),
        "ja": (
            "自己", "統合", "異邦人", "盲点", "鏡", "分身", "別名", "分類不能",
            "変容", "未定義", "もう一つの名",
        ),
    },
    "random": {
        "en": (
            "LOVE", "RESET", "GHOST", "ANGEL", "BLIND", "EMPTY", "CURSE",
            "GAZE", "LONELINESS", "INTEGRATION", "DESIRE", "PROOF", "STATIC",
            "MERCY", "VANISH",
        ),
        "ja": (
            "愛", "再起動", "幽霊", "天使", "盲目", "空虚", "呪い", "視線",
            "孤独", "統合", "欲望", "証明", "雑音", "慈悲", "消失",
        ),
    },
}

_THEME_HINTS = {
    "memory": ("memory", "remember", "recall", "archive", "trace", "記憶", "記録", "忘却", "残像"),
    "body": ("body", "skin", "blood", "body", "touch", "身体", "皮膚", "血", "接触"),
    "signal": (
        "signal", "noise", "radio", "frequency", "transmission",
        "信号", "雑音", "周波数", "伝送",
    ),
    "ritual": ("ritual", "sacred", "offering", "altar", "curse", "儀式", "供物", "呪い", "神"),
    "identity": ("identity", "self", "person", "name", "mirror", "自己", "名前", "鏡", "他者"),
}


def _dictionary_candidates(root: Path, language: str, theme: str) -> list[str]:
    """Read the repository's local dictionaries lazily; never require them to exist."""
    candidates: list[str] = []
    dictionary_dir = root / "dictionary"
    if not dictionary_dir.is_dir():
        return candidates
    files = sorted(dictionary_dir.glob("*.txt"))
    if language == "english":
        files = [p for p in files if p.stem.lower() in set("abcdefghijklmnopqrstuvwxyz")]
    elif language == "japanese":
        files = [p for p in files if p.name == "special_readings.txt"]
    else:
        files = [p for p in files if p.name in {"special_readings.txt", "supplementary_kanji.txt"}]
    hints = tuple(item.casefold() for item in _THEME_HINTS.get(theme, ()))
    for path in files:
        try:
            with path.open("r", encoding="utf-8-sig", errors="ignore") as handle:
                for raw in handle:
                    line = raw.strip()
                    if not line or len(line) > 72 or line.startswith("#"):
                        continue
                    # English dictionary files are alphabetized; use one clean lexical headword.
                    # Japanese reading lists may be tab-separated; choose the CJK column.
                    parts = [part.strip("・、。[](){}") for part in re.split(r"[\t,;| ]+", line)]
                    parts = [part for part in parts if part]
                    if language == "english":
                        term = next((
                            part for part in parts
                            if re.fullmatch(r"[A-Za-z][A-Za-z'’-]*", part)
                        ), "")
                    else:
                        term = next((
                            part for part in parts
                            if any(
                                "\u3040" <= ch <= "\u30ff"
                                or "\u4e00" <= ch <= "\u9fff"
                                for ch in part
                            )
                        ), "")
                    if not term or len(term) > 24:
                        continue
                    if hints and not any(hint in line.casefold() for hint in hints):
                        continue
                    candidates.append(term.upper() if language == "english" else term)
        except OSError:
            continue
    # Bound memory and keep sampling responsive on multi-megabyte wordlists.
    return list(dict.fromkeys(candidates))[:12000]


def random_text_sample(
        language: str = "bilingual",
        theme: str = "random",
        count: int = 16,
        seed: int | None = None,
        dictionary_path: str | Path | None = None,
        use_dictionary: bool = True,
) -> str:
    """Return a seeded English/Japanese phrase set, optionally enriched from local dictionaries."""
    if language not in {"english", "japanese", "bilingual"}:
        language = "bilingual"
    if theme not in TEXT_POOLS:
        theme = "random"
    rng = random.Random(seed)
    pool = TEXT_POOLS[theme]
    english = list(pool["en"])
    japanese = list(pool["ja"])
    if use_dictionary:
        root = Path(dictionary_path) if dictionary_path else Path(__file__).resolve().parents[1]
        if language in {"english", "bilingual"}:
            english.extend(_dictionary_candidates(root, "english", theme))
        if language in {"japanese", "bilingual"}:
            japanese.extend(_dictionary_candidates(root, "japanese", theme))
    english = list(dict.fromkeys(english))
    japanese = list(dict.fromkeys(japanese))
    if language == "english":
        source = english
    elif language == "japanese":
        source = japanese
    else:
        source = [item for pair in zip(english, japanese) for item in pair]
    sample_count = max(1, min(60, int(count)))
    if not source:
        source = list(pool["en"] if language == "english" else pool["ja"])
    if sample_count <= len(source):
        selected = rng.sample(source, sample_count)
    else:
        selected = [rng.choice(source) for _ in range(sample_count)]
    return "\n".join(selected)
