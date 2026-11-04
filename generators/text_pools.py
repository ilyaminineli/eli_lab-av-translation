from __future__ import annotations

import random

# Short phrases chosen for visual composition: compact, bilingual and non-sentential.
TEXT_POOLS: dict[str, dict[str, tuple[str, ...]]] = {
    "memory": {
        "en": (
            "MEMORY", "AFTERIMAGE", "ARCHIVE", "REMNANT", "RECALL",
            "ERASURE", "ECHO", "TRACE", "REMEMBER", "NO RETURN",
            "THE SHAPE OF LOSS", "NOTHING STAYS",
        ),
        "ja": (
            "記憶", "残像", "記録", "痕跡", "忘却", "反復",
            "不在", "回想", "余白", "消去", "残響", "帰れない",
        ),
    },
    "body": {
        "en": (
            "BODY", "SKIN", "BLOOD", "TOUCH", "HUNGER", "DESIRE",
            "GENDER", "BREATH", "VEIL", "SENSATION", "THE OTHER",
        ),
        "ja": (
            "身体", "皮膚", "血", "接触", "空腹", "欲望",
            "性", "呼吸", "仮面", "感覚", "他者", "輪郭",
        ),
    },
    "signal": {
        "en": (
            "SIGNAL", "NOISE", "STATIC", "TRANSMISSION", "FEEDBACK",
            "CARRIER", "FREQUENCY", "INTERRUPT", "REBOOT", "ERROR",
            "LOST CONNECTION", "DECODE",
        ),
        "ja": (
            "信号", "雑音", "静電気", "伝送", "反響", "搬送波",
            "周波数", "中断", "再起動", "誤差", "接続不能", "解読",
        ),
    },
    "ritual": {
        "en": (
            "RITUAL", "OFFERING", "WITNESS", "THRESHOLD", "CURSE",
            "TOLERANCE", "GAZE", "VESSEL", "RETURN", "PROOF",
            "COLLECTION", "SACRED ERROR",
        ),
        "ja": (
            "儀式", "供物", "証人", "境界", "呪い", "寛容",
            "視線", "器", "帰還", "証明", "収集", "聖なる誤差",
        ),
    },
    "identity": {
        "en": (
            "IDENTITY", "INTEGRATION", "OUTSIDER", "BLIND SPOT",
            "MIRROR", "DOUBLE", "ALIAS", "NO CATEGORY", "BECOMING",
            "UNDEFINED", "ANOTHER NAME",
        ),
        "ja": (
            "自己", "統合", "異邦人", "盲点", "鏡", "分身",
            "別名", "分類不能", "変容", "未定義", "もう一つの名",
        ),
    },
    "random": {
        "en": (
            "LOVE", "RESET", "GHOST", "ANGEL", "BLIND", "EMPTY",
            "CURSE", "GAZE", "LONELINESS", "INTEGRATION", "DESIRE",
            "PROOF", "STATIC", "MERCY", "VANISH",
        ),
        "ja": (
            "愛", "再起動", "幽霊", "天使", "盲目", "空虚",
            "呪い", "視線", "孤独", "統合", "欲望", "証明",
            "雑音", "慈悲", "消失",
        ),
    },
}


def random_text_sample(
    language: str = "bilingual",
    theme: str = "random",
    count: int = 16,
    seed: int | None = None,
) -> str:
    """Return a reproducible-ready set of short English and/or Japanese text fragments."""
    if language not in {"english", "japanese", "bilingual"}:
        language = "bilingual"
    if theme not in TEXT_POOLS:
        theme = "random"
    rng = random.Random(seed)
    pool = TEXT_POOLS[theme]
    if language == "english":
        source = pool["en"]
    elif language == "japanese":
        source = pool["ja"]
    else:
        source = tuple(
            item for pair in zip(pool["en"], pool["ja"]) for item in pair
        )
    sample_count = max(1, min(60, int(count)))
    if sample_count <= len(source):
        selected = rng.sample(source, sample_count)
    else:
        selected = [rng.choice(source) for _ in range(sample_count)]
    return "\n".join(selected)
