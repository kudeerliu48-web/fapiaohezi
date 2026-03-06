"""Full preprocessing pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from config import settings
from preprocess.cropper import crop_image
from preprocess.orientation import apply_orientation
from preprocess.resizer import resolve_profile, resize_for_profile
from preprocess.unsharp import apply_unsharp
from utils.file_utils import write_json
from utils.image_utils import build_thumbnail, save_png, save_webp
from utils.sharpness import laplacian_variance


def _build_manifest(
    original_filename: str,
    original_size: tuple[int, int],
    processed_size: tuple[int, int],
    quality: int,
    processed_bytes: int,
    small_text: bool,
    upscale_applied: bool,
    unsharp_applied: bool,
    sharpness_in: float,
    sharpness_out: float,
) -> dict[str, Any]:
    """Build a manifest payload for one page."""

    manifest: dict[str, Any] = {
        "original": {"filename": original_filename, "size": [original_size[0], original_size[1]]},
        "processed": {
            "size": [processed_size[0], processed_size[1]],
            "format": "webp",
            "quality": quality,
            "bytes": processed_bytes,
        },
        "profile": "prod_default",
        "adaptive": {
            "small_text": small_text,
            "upscale_applied": upscale_applied,
            "unsharp_applied": unsharp_applied,
        },
        "sharpness": {"in": round(sharpness_in, 2), "out": round(sharpness_out, 2)},
    }
    if sharpness_out < sharpness_in * 0.85:
        manifest["warning"] = "sharpness dropped below 85% of input"
    return manifest


def process_image_to_page(image: Image.Image, page_dir: Path, original_filename: str) -> dict[str, Any]:
    """Execute the production preprocessing spec and write page artifacts."""

    page_dir.mkdir(parents=True, exist_ok=True)
    normalized = apply_orientation(image.convert("RGB"))
    input_path = page_dir / "input.png"
    save_png(normalized, input_path)

    sharpness_in = laplacian_variance(normalized)
    cropped, _ = crop_image(normalized)
    profile = resolve_profile(cropped)
    resized, resized_applied = resize_for_profile(cropped, profile)
    processed, unsharp_applied = apply_unsharp(resized, profile.small_text)
    sharpness_out = laplacian_variance(processed)

    processed_path = page_dir / "processed.webp"
    processed_bytes = save_webp(processed, processed_path, quality=profile.quality)

    thumb = build_thumbnail(processed, settings.thumb_long_edge)
    save_webp(thumb, page_dir / "thumb.webp", quality=60)

    manifest = _build_manifest(
        original_filename=original_filename,
        original_size=(normalized.width, normalized.height),
        processed_size=(processed.width, processed.height),
        quality=profile.quality,
        processed_bytes=processed_bytes,
        small_text=profile.small_text,
        upscale_applied=profile.small_text and resized_applied and max(cropped.width, cropped.height) < profile.target_long_edge,
        unsharp_applied=unsharp_applied,
        sharpness_in=sharpness_in,
        sharpness_out=sharpness_out,
    )
    write_json(page_dir / "manifest.json", manifest)
    return manifest


def reprocess_existing_input(page_dir: Path, original_filename: str) -> dict[str, Any]:
    """Re-run preprocessing using the stored input PNG as source."""

    input_path = page_dir / "input.png"
    with Image.open(input_path) as image:
        return process_image_to_page(image.copy(), page_dir=page_dir, original_filename=original_filename)
