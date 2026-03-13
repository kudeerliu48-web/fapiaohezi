"""Orientation normalization."""

from __future__ import annotations

from PIL import Image

from utils.image_utils import correct_orientation


def apply_orientation(image: Image.Image) -> Image.Image:
    """Normalize image orientation using EXIF metadata."""

    return correct_orientation(image)
