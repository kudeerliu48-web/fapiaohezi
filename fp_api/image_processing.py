import io
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageFilter, ImageOps


@dataclass(frozen=True)
class ProcessProfile:
    small_text_threshold: int = 1200
    default_long_edge: int = 2000
    small_text_long_edge: int = 2400
    default_webp_quality: int = 82
    small_text_webp_quality: int = 86


def _is_image_ext(ext: str) -> bool:
    ext = (ext or "").lower()
    return ext in {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}


def _is_pdf_ext(ext: str) -> bool:
    return (ext or "").lower() == ".pdf"


def _resize_long_edge(image: Image.Image, long_edge: int, allow_upscale: bool) -> Tuple[Image.Image, bool]:
    w, h = image.size
    cur = max(w, h)
    if cur == 0:
        return image, False
    if cur <= long_edge and not allow_upscale:
        return image, False
    if cur == long_edge:
        return image, False

    scale = long_edge / float(cur)
    if scale > 1.0 and not allow_upscale:
        return image, False

    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    return image.resize((new_w, new_h), Image.LANCZOS), True


def _conservative_crop_white_border(image: Image.Image, threshold: int = 245, margin: int = 4) -> Tuple[Image.Image, bool]:
    """Conservative white-border crop. Works best for scanned invoices."""
    if image.mode != "RGB":
        image = image.convert("RGB")

    gray = image.convert("L")
    # Turn "near white" into 0 and content into 255, then bbox on content.
    bw = gray.point(lambda p: 0 if p >= threshold else 255, mode="L")
    bbox = bw.getbbox()
    if not bbox:
        return image, False

    left, top, right, bottom = bbox
    left = max(0, left - margin)
    top = max(0, top - margin)
    right = min(image.width, right + margin)
    bottom = min(image.height, bottom + margin)

    # Avoid cropping too aggressively (e.g. already tight)
    if right - left < image.width * 0.6 or bottom - top < image.height * 0.6:
        return image, False

    return image.crop((left, top, right, bottom)), True


def _apply_unsharp(image: Image.Image, enabled: bool) -> Tuple[Image.Image, bool]:
    if not enabled:
        return image, False
    sharpened = image.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    return sharpened, True


def _save_webp(image: Image.Image, output_path: Path, quality: int) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Ensure RGB for webp
    img = image.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=quality, method=6)
    data = buf.getvalue()
    output_path.write_bytes(data)
    return len(data)


def process_images_to_webp_pages(
    *,
    images: List[Image.Image],
    processed_dir: Path,
    base_id: str,
    original_filename: str,
    profile: ProcessProfile | None = None,
) -> List[dict]:
    """Process a list of PIL images into webp pages under processed_dir.

    Returns a list of per-page dicts: {page_index, processed_filename, bytes, width, height}.
    """
    profile = profile or ProcessProfile()
    results: List[dict] = []

    for idx, img in enumerate(images, start=1):
        normalized = ImageOps.exif_transpose(img.convert("RGB"))
        cropped, _ = _conservative_crop_white_border(normalized)

        small_text = max(cropped.width, cropped.height) < profile.small_text_threshold
        target_long_edge = profile.small_text_long_edge if small_text else profile.default_long_edge
        quality = profile.small_text_webp_quality if small_text else profile.default_webp_quality

        resized, _ = _resize_long_edge(cropped, long_edge=target_long_edge, allow_upscale=small_text)
        processed, _ = _apply_unsharp(resized, enabled=small_text)

        processed_filename = f"{base_id}_p{idx}.webp"
        out_path = processed_dir / processed_filename
        out_bytes = _save_webp(processed, out_path, quality=quality)

        results.append(
            {
                "page_index": idx,
                "processed_filename": processed_filename,
                "processed_bytes": out_bytes,
                "processed_width": processed.width,
                "processed_height": processed.height,
                "original_filename": original_filename,
            }
        )

    return results


def process_upload_to_pages(
    *,
    upload_path: Path,
    original_filename: str,
    processed_dir: Path,
    base_id: str,
    pdf_dpi: int = 200,
) -> List[dict]:
    """Given an uploaded file path (pdf/image), return processed webp page artifacts."""
    ext = upload_path.suffix.lower()

    if _is_pdf_ext(ext):
        try:
            from preprocess.pdf_renderer import render_pdf_to_images
        except ModuleNotFoundError as e:
            # preprocess/pdf_renderer.py depends on PyMuPDF (fitz)
            if "fitz" in str(e):
                raise ModuleNotFoundError(
                    "Missing dependency 'fitz' (PyMuPDF). Please install pymupdf and restart the backend."
                )
            raise

        images = render_pdf_to_images(upload_path, dpi=pdf_dpi)
        return process_images_to_webp_pages(
            images=images,
            processed_dir=processed_dir,
            base_id=base_id,
            original_filename=original_filename,
        )

    if _is_image_ext(ext):
        with Image.open(upload_path) as im:
            images = [im.copy()]
        return process_images_to_webp_pages(
            images=images,
            processed_dir=processed_dir,
            base_id=base_id,
            original_filename=original_filename,
        )

    raise ValueError(f"Unsupported file extension: {ext}")
