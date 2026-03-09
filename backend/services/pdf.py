import io
from pathlib import Path

import img2pdf
from PIL import Image

from backend.config import settings


def _compress_image(image_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))

    # Resize if wider than max width
    if img.width > settings.max_image_width:
        ratio = settings.max_image_width / img.width
        new_size = (settings.max_image_width, int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    # Convert to RGB if needed (for JPEG)
    if img.mode != "RGB":
        img = img.convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=settings.jpeg_quality, optimize=True)
    return buf.getvalue()


def create_pdf(images: list[bytes], output_path: str) -> None:
    compressed = [_compress_image(img) for img in images]
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf_bytes = img2pdf.convert(compressed)
    path.write_bytes(pdf_bytes)
