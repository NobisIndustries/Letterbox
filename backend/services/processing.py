import asyncio
import logging
import tempfile
import time
from functools import partial
from pathlib import Path

from backend.config import settings

logger = logging.getLogger(__name__)

_processor = None
_last_used: float = time.monotonic()
_IDLE_TIMEOUT = 10 * 60  # 10 minutes


def _get_processor():
    global _processor, _last_used
    _last_used = time.monotonic()
    if _processor is None:
        from backend.docres_inference import DocResProcessor
        logger.info("Loading DocRes model weights...")
        _processor = DocResProcessor(
            docres_weights=str(settings.models_dir / "docres.pkl"),
            mbd_weights=str(settings.models_dir / "mbd.pkl"),
        )
        logger.info("DocRes model loaded.")
    return _processor


def _unload_processor():
    global _processor
    if _processor is not None:
        _processor = None
        logger.info("DocRes model weights unloaded due to inactivity.")


async def idle_unloader():
    """Periodically unloads model weights if idle for more than _IDLE_TIMEOUT seconds."""
    check_interval = 3 * 60  # check every 3 minutes
    while True:
        await asyncio.sleep(check_interval)
        if _processor is not None and time.monotonic() - _last_used > _IDLE_TIMEOUT:
            _unload_processor()


def _process_sync(images: list[bytes]) -> list[bytes]:
    proc = _get_processor()
    results = []
    with tempfile.TemporaryDirectory() as tmpdir:
        output_paths = [str(Path(tmpdir) / f"out_{i}.jpg") for i in range(len(images))]
        proc.process(images, output_paths, max_output_width=settings.max_image_width)
        for p in output_paths:
            results.append(Path(p).read_bytes())
    return results


async def process_images(images: list[bytes]) -> list[bytes]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_process_sync, images))
