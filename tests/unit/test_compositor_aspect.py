import pytest

from rendering.compositor import canvas_fit_scale


def test_aspect_fit_is_unity_when_output_matches_canvas() -> None:
    assert canvas_fit_scale(1920, 1080, 1920, 1080) == pytest.approx((1.0, 1.0))


def test_portrait_preview_letterboxes_landscape_canvas_vertically() -> None:
    scale = canvas_fit_scale(768, 1024, 1920, 1080)

    assert scale[0] == pytest.approx(1.0)
    assert scale[1] == pytest.approx((768 / 1024) / (1920 / 1080))


def test_ultrawide_preview_letterboxes_landscape_canvas_horizontally() -> None:
    scale = canvas_fit_scale(3440, 1440, 1920, 1080)

    assert scale[0] == pytest.approx((1920 / 1080) / (3440 / 1440))
    assert scale[1] == pytest.approx(1.0)
