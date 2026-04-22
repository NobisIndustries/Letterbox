import asyncio
import ctypes
import gc
import logging
import time
from functools import partial

import cv2
import numpy as np
import torch

from backend.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Image enhancement (shared by both processing paths)
# ---------------------------------------------------------------------------

def fast_enhance(
    img: np.ndarray,
    shadow_strength: float = 0.8,
    shadow_dilate_size: int = 9,
    shadow_median_size: int = 9,
    stretch_low_pct: float = 1.5,
    stretch_high_pct: float = 98.0,
    clahe_clip: float = 0.0,
    clahe_grid: int = 8,
    white_balance: bool = True,
) -> np.ndarray:
    """Combined deshadow + appearance enhancement (pure OpenCV).

    All operations work in LAB space (single conversion).
    """
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l_f = l.astype(np.float32)

    # --- Shadow removal: additive illumination correction ---
    if shadow_strength > 0:
        kernel = np.ones((shadow_dilate_size, shadow_dilate_size), np.uint8)
        dilated = cv2.dilate(l, kernel)
        bg = cv2.medianBlur(dilated, shadow_median_size).astype(np.float32)
        target = np.max(bg)
        correction = (target - bg) * shadow_strength
        l_f = np.clip(l_f + correction, 0, 255)

    # --- Histogram-aware black/white point stretch ---
    # Use Otsu's method to find the ink/paper boundary, then derive
    # black and white points from actual histogram peaks rather than
    # raw percentiles (which fail on low-content pages).
    l_u8 = np.clip(l_f, 0, 255).astype(np.uint8)
    otsu_thresh, _ = cv2.threshold(l_u8, 0, 255, cv2.THRESH_OTSU)

    # Check if the histogram is actually bimodal (document-like) by
    # measuring inter-class variance. On photos/flyers the distribution
    # is continuous and Otsu's split is arbitrary — fall back to gentle
    # percentile stretch in that case.
    ink_mask = l_f < otsu_thresh
    ink_ratio = np.count_nonzero(ink_mask) / l_f.size
    is_bimodal = False
    if 0.005 < ink_ratio < 0.95:
        ink_mean = l_f[ink_mask].mean()
        paper_mean = l_f[~ink_mask].mean()
        is_bimodal = (paper_mean - ink_mean) > 60

    if is_bimodal:
        # Document-like: anchor to actual ink/paper peaks
        lo = np.percentile(l_f[ink_mask], 5.0)
        hi = np.percentile(l_f[~ink_mask], 95.0)
    elif ink_ratio <= 0.005:
        # Almost no dark content — barely stretch
        lo = 0.0
        hi = np.percentile(l_f, stretch_high_pct)
    else:
        # Continuous distribution (photo/flyer) — gentle percentile stretch
        lo = np.percentile(l_f, stretch_low_pct)
        hi = np.percentile(l_f, stretch_high_pct)

    if hi - lo > 10:
        l_f = np.clip((l_f - lo) / (hi - lo) * 255, 0, 255)
    l = l_f.astype(np.uint8)

    # --- CLAHE ---
    if clahe_clip > 0:
        clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(clahe_grid, clahe_grid))
        l = clahe.apply(l)

    enhanced = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

    # --- Gray-world white balance ---
    if white_balance:
        avg_b, avg_g, avg_r = [enhanced[:, :, i].mean() for i in range(3)]
        avg_gray = (avg_b + avg_g + avg_r) / 3
        enhanced = enhanced.astype(np.float32)
        enhanced[:, :, 0] *= avg_gray / max(avg_b, 1)
        enhanced[:, :, 1] *= avg_gray / max(avg_g, 1)
        enhanced[:, :, 2] *= avg_gray / max(avg_r, 1)
        enhanced = np.clip(enhanced, 0, 255).astype(np.uint8)

    return enhanced

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
        gc.collect()
        torch.clear_autocast_cache()
        # Ask glibc to return freed memory to the OS
        try:
            ctypes.CDLL("libc.so.6").malloc_trim(0)
        except OSError:
            pass
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
            img = fast_enhance(img)

            _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, settings.jpeg_quality])
            results.append(buf.tobytes())
    else:
        # Deep learning path: dewarping via DocRes, then our own enhancement
        for img_bytes in images:
            img = proc._load_image(img_bytes)
            img = proc._dewarping(img)

            if settings.max_image_width and img.shape[1] > settings.max_image_width:
                ratio = settings.max_image_width / img.shape[1]
                new_size = (settings.max_image_width, int(img.shape[0] * ratio))
                img = cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)

            img = fast_enhance(img)

            _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, settings.jpeg_quality])
            results.append(buf.tobytes())

    return results


async def process_images(
    images: list[bytes],
    dewarping_method: str = "deep_learning",
) -> list[bytes]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, partial(_process_sync, images, dewarping_method)
    )
