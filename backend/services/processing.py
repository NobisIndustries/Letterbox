import asyncio
import logging
import tempfile
import time
from functools import partial
from pathlib import Path

import cv2
import numpy as np

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
    check_interval = 3*60  # check every 3 minutes
    try:
        while True:
            await asyncio.sleep(check_interval)
            if _processor is not None and time.monotonic() - _last_used > _IDLE_TIMEOUT:
                _unload_processor()
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("idle_unloader crashed")


# ---------------------------------------------------------------------------
# Classic (OpenCV) dewarping — 4-corner perspective transform
# ---------------------------------------------------------------------------

def _order_points(pts: np.ndarray) -> np.ndarray:
    """Order 4 points as: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    d = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(d)]
    rect[3] = pts[np.argmax(d)]
    return rect


def _detect_document_quad(mask: np.ndarray) -> np.ndarray | None:
    """Find the document quadrilateral from a binary mask."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    largest = max(contours, key=cv2.contourArea)
    hull = cv2.convexHull(largest)

    peri = cv2.arcLength(hull, True)
    for eps_mult in [0.02, 0.03, 0.04, 0.05, 0.07, 0.10]:
        approx = cv2.approxPolyDP(hull, eps_mult * peri, True)
        if len(approx) == 4:
            return _order_points(approx.reshape(4, 2))

    rect = cv2.minAreaRect(largest)
    box = cv2.boxPoints(rect)
    return _order_points(box)


def _detect_orientation(mask: np.ndarray) -> str:
    """Detect document orientation from MBD mask. Returns 'portrait' or 'landscape'."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return "portrait"
    largest = max(contours, key=cv2.contourArea)
    rect = cv2.minAreaRect(largest)
    (_, (rw, rh), _) = rect
    if rw < 1 or rh < 1:
        return "portrait"
    # minAreaRect returns width/height where width isn't necessarily the longer side
    ratio = max(rw, rh) / min(rw, rh)
    if ratio < 1.1:
        return "portrait"  # nearly square, treat as portrait
    # Determine which dimension is which by looking at the bounding box orientation
    # If the wider dimension is horizontal, it's landscape
    box = cv2.boxPoints(rect)
    box = _order_points(box)
    tl, tr, _, bl = box
    width = np.linalg.norm(tr - tl)
    height = np.linalg.norm(bl - tl)
    return "landscape" if width > height * 1.1 else "portrait"


def _classic_dewarp(img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Apply perspective correction using the MBD mask to find document corners."""
    quad = _detect_document_quad(mask)
    if quad is None:
        logger.warning("Classic dewarping: could not detect document quad, returning original")
        return img

    tl, tr, br, bl = quad
    width = int((np.linalg.norm(tr - tl) + np.linalg.norm(br - bl)) / 2)
    height = int((np.linalg.norm(bl - tl) + np.linalg.norm(br - tr)) / 2)

    if width < 100 or height < 100:
        logger.warning("Classic dewarping: detected quad too small, returning original")
        return img

    dst = np.array([
        [0, 0],
        [width - 1, 0],
        [width - 1, height - 1],
        [0, height - 1],
    ], dtype=np.float32)

    M = cv2.getPerspectiveTransform(quad, dst)
    return cv2.warpPerspective(
        img, M, (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


# ---------------------------------------------------------------------------
# Processing pipeline
# ---------------------------------------------------------------------------

def _process_sync(images: list[bytes], dewarping_method: str = "deep_learning") -> list[bytes]:
    proc = _get_processor()
    results = []

    if dewarping_method == "classic":
        # Classic path: use MBD for mask + orientation, then OpenCV perspective transform
        for img_bytes in images:
            arr = np.frombuffer(img_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not decode image bytes")

            h, w = img.shape[:2]
            logger.info("Classic dewarping: %dx%d", w, h)

            # Get MBD mask at full resolution for quad detection
            from backend.docres_inference._mbd import net1_net2_infer_single_im
            mask = net1_net2_infer_single_im(
                img, proc._seg_model, proc._device, output_size=(h, w)
            )

            # Detect orientation before dewarping
            orientation = _detect_orientation(mask)
            if orientation == "landscape":
                img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                mask = cv2.rotate(mask, cv2.ROTATE_90_CLOCKWISE)

            # Perspective correction
            img = _classic_dewarp(img, mask)

            # Downscale if needed
            if settings.max_image_width and img.shape[1] > settings.max_image_width:
                ratio = settings.max_image_width / img.shape[1]
                new_size = (settings.max_image_width, int(img.shape[0] * ratio))
                img = cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)

            # Enhancement
            img = proc.fast_enhance(img)

            _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, settings.jpeg_quality])
            results.append(buf.tobytes())
    else:
        # Deep learning path: use DocResProcessor.process() with orientation handling
        with tempfile.TemporaryDirectory() as tmpdir:
            output_paths = [str(Path(tmpdir) / f"out_{i}.jpg") for i in range(len(images))]
            proc.process(
                images, output_paths,
                max_output_width=settings.max_image_width,
                jpeg_quality=settings.jpeg_quality,
            )
            for p in output_paths:
                results.append(Path(p).read_bytes())

    return results


async def process_images(
    images: list[bytes],
    dewarping_method: str = "deep_learning",
) -> list[bytes]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, partial(_process_sync, images, dewarping_method)
    )
