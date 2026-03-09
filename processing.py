import tempfile
from pathlib import Path

from docres_inference import DocResProcessor

MODELS_DIR = Path(__file__).parent / "models"

_processor: DocResProcessor | None = None


def get_processor() -> DocResProcessor:
    global _processor
    if _processor is None:
        _processor = DocResProcessor(
            docres_weights=str(MODELS_DIR / "docres.pkl"),
            mbd_weights=str(MODELS_DIR / "mbd.pkl"),
        )
    return _processor


def process_images(images: list[bytes]) -> list[bytes]:
    """Run DocRes on uploaded images and return processed image bytes."""
    proc = get_processor()
    results = []

    with tempfile.TemporaryDirectory() as tmpdir:
        output_paths = [str(Path(tmpdir) / f"out_{i}.jpg") for i in range(len(images))]
        proc.process(images, output_paths)
        for p in output_paths:
            results.append(Path(p).read_bytes())

    return results
