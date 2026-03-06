"""Unsharp mask helpers."""

from __future__ import annotations

from PIL import Image, ImageFilter


def apply_unsharp(image: Image.Image, enabled: bool) -> tuple[Image.Image, bool]:
    """Apply a light unsharp mask for small-text pages."""

    if not enabled:
        return image, False
    sharpened = image.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    return sharpened, True
