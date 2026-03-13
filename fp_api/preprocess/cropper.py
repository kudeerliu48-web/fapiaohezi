"""Cropping logic."""

from __future__ import annotations

from PIL import Image

from config import settings
from utils.image_utils import conservative_crop_white_border


def crop_image(image: Image.Image) -> tuple[Image.Image, bool]:
    """Apply conservative white-border cropping when enabled."""

    if not settings.enable_crop:
        return image, False
    return conservative_crop_white_border(image)
