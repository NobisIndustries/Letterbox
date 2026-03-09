import asyncio
import tempfile
from functools import partial
from pathlib import Path

from backend.config import settings

_processor = None


def _get_processor():
    global _processor
    if _processor is None:
        from backend.docres_inference import DocResProcessor
        _processor = DocResProcessor(
            docres_weights=str(settings.models_dir / "docres.pkl"),
            mbd_weights=str(settings.models_dir / "mbd.pkl"),
        )
    return _processor


def _process_sync(images: list[bytes]) -> list[bytes]:
    proc = _get_processor()
    results = []
    with tempfile.TemporaryDirectory() as tmpdir:
        output_paths = [str(Path(tmpdir) / f"out_{i}.jpg") for i in range(len(images))]
        proc.process(images, output_paths)
        for p in output_paths:
            results.append(Path(p).read_bytes())
    return results


async def process_images(images: list[bytes]) -> list[bytes]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_process_sync, images))
