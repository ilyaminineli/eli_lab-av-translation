from __future__ import annotations

from media.asset_index import VisualAssetIndex


def test_visual_asset_index_classifies_and_filters_by_purpose(tmp_path) -> None:
    paper = tmp_path / "Paper"
    masks = tmp_path / "Masks"
    paper.mkdir()
    masks.mkdir()
    (paper / "old_paper_texture.jpg").write_bytes(b"image")
    (masks / "alpha_mask.png").write_bytes(b"image")
    (paper / "readme.txt").write_text("not an image")

    index = VisualAssetIndex([tmp_path])
    assets = index.scan()

    assert len(assets) == 2
    assert index.search(purpose="surface")[0].name == "old paper texture"
    assert index.search(purpose="mask")[0].name == "alpha mask"
    assert index.search(query="paper", kind="image")[0].category == "paper"


def test_visual_asset_index_ignores_missing_roots(tmp_path) -> None:
    index = VisualAssetIndex([tmp_path / "missing"])
    assert index.scan() == []
