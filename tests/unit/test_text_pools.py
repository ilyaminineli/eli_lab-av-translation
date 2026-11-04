from generators.text_pools import TEXT_POOLS, random_text_sample


def test_bilingual_random_text_sample_is_seeded_and_contains_both_scripts() -> None:
    first = random_text_sample("bilingual", "memory", 12, seed=42)
    second = random_text_sample("bilingual", "memory", 12, seed=42)

    assert first == second
    assert any("A" <= char <= "Z" for char in first)
    assert any("\u3040" <= char <= "\u30ff" or "\u4e00" <= char <= "\u9fff" for char in first)


def test_random_text_pool_has_all_themes_and_languages() -> None:
    assert {"memory", "body", "signal", "ritual", "identity", "random"} <= set(TEXT_POOLS)
    for theme in TEXT_POOLS:
        assert TEXT_POOLS[theme]["en"]
        assert TEXT_POOLS[theme]["ja"]


def test_random_text_sample_clamps_count_and_unknown_values() -> None:
    sample = random_text_sample("unknown", "missing-theme", 0, seed=1)

    assert sample
    assert len(sample.splitlines()) == 1


def test_dictionary_candidates_are_optional_and_seeded(tmp_path) -> None:
    dictionary = tmp_path / "dictionary"
    dictionary.mkdir()
    (dictionary / "a.txt").write_text("apple\napricot\narchive\n", encoding="utf-8")
    first = random_text_sample(
        "english", "random", 3, seed=5, dictionary_path=tmp_path, use_dictionary=True
    )
    second = random_text_sample(
        "english", "random", 3, seed=5, dictionary_path=tmp_path, use_dictionary=True
    )
    assert first == second
