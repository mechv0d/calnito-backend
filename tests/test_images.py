from io import BytesIO
from types import SimpleNamespace

import pytest
from PIL import Image

import app.storage.images as images
from app.storage.images import ImageProcessingError, process_food_photo


def make_image_bytes(size=(2400, 1000), fmt="JPEG") -> bytes:
    image = Image.new("RGB", size, color=(200, 100, 50))
    out = BytesIO()
    image.save(out, format=fmt)
    return out.getvalue()


def test_process_food_photo_resizes_to_max_side_and_outputs_webp(monkeypatch):
    monkeypatch.setattr(
        images,
        "get_settings",
        lambda: SimpleNamespace(max_image_side_px=1200, webp_quality=75),
    )

    processed = process_food_photo(make_image_bytes())

    assert processed.content_type == "image/webp"
    assert max(processed.width, processed.height) == 1200

    reopened = Image.open(BytesIO(processed.bytes))
    assert reopened.format == "WEBP"
    assert reopened.size == (1200, 500)


def test_process_food_photo_rejects_invalid_bytes(monkeypatch):
    monkeypatch.setattr(
        images,
        "get_settings",
        lambda: SimpleNamespace(max_image_side_px=1200, webp_quality=75),
    )

    with pytest.raises(ImageProcessingError):
        process_food_photo(b"not an image")
