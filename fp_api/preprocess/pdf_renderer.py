"""PDF rendering utilities."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import fitz
from PIL import Image


def count_pdf_pages(pdf_path: Path) -> int:
    """Return the number of pages in a PDF file."""

    with fitz.open(pdf_path) as document:
        return document.page_count


def iter_pdf_images(pdf_path: Path, dpi: int) -> Iterator[Image.Image]:
    """Yield PDF pages as PIL images at the requested DPI."""

    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    with fitz.open(pdf_path) as document:
        for page in document:
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            yield Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)


def render_pdf_to_images(pdf_path: Path, dpi: int) -> list[Image.Image]:
    """Render each PDF page to a PIL image at the requested DPI."""

    return list(iter_pdf_images(pdf_path=pdf_path, dpi=dpi))
