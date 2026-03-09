from pathlib import Path

import img2pdf


def create_pdf(images: list[bytes], output_path: str) -> None:
    """Combine processed page images into a single PDF."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf_bytes = img2pdf.convert(images)
    path.write_bytes(pdf_bytes)
