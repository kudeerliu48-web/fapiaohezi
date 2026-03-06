"""Resizing rules."""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

from config import settings
from utils.image_utils import resize_long_edge


@dataclass(frozen=True)
class ResizeProfile:
    """Resolved adaptive resizing configuration."""

    small_text: bool
    target_long_edge: int
    quality: int
    allow_upscale: bool


def resolve_profile(image: Image.Image) -> ResizeProfile:
    """Choose the adaptive profile based on current image size."""

    small_text = max(image.width, image.height) < settings.small_text_threshold
    if small_text:
        return ResizeProfile(
            small_text=True,
            target_long_edge=settings.small_text_long_edge,
            quality=settings.small_text_webp_quality,
            allow_upscale=True,
        )
    return ResizeProfile(
        small_text=False,
        target_long_edge=settings.default_long_edge,
        quality=settings.default_webp_quality,
        allow_upscale=False,
    )


def resize_for_profile(image: Image.Image, profile: ResizeProfile) -> tuple[Image.Image, bool]:
    """Resize the image according to the adaptive profile."""

    return resize_long_edge(
        image=image,
        long_edge=profile.target_long_edge,
        allow_upscale=profile.allow_upscale,
    )
