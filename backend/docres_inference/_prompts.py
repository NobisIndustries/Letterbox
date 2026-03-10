import time
from functools import lru_cache

import cv2
import numpy as np


@lru_cache(maxsize=4)
def getBasecoord(h, w):
    base_coord0 = np.tile(np.arange(h).reshape(h, 1), (1, w)).astype(np.float32)
    base_coord1 = np.tile(np.arange(w).reshape(1, w), (h, 1)).astype(np.float32)
    base_coord = np.concatenate((np.expand_dims(base_coord1, -1), np.expand_dims(base_coord0, -1)), -1)
    return base_coord


def dewarp_prompt(img, mbd_infer_fn, device):
    """Generate dewarping prompt. Returns (masked_img_256, prompt_array).

    Resizes image to 256x256 *before* applying mask to avoid operating on
    the full-resolution image.
    """
    h, w = img.shape[:2]

    t = time.time()
    mask = mbd_infer_fn(img, device)
    print(f"[DocRes]       mbd_infer_fn total: {time.time() - t:.3f}s")

    t = time.time()
    base_coord = getBasecoord(256, 256) / 256
    # MBD already outputs at 256x256, just resize the image to match
    img_small = cv2.resize(img, (256, 256))
    # mask is already 256x256 from MBD output_size
    img_small[mask == 0] = 0
    mask_norm = mask / 255.0
    result = img_small, np.concatenate((base_coord, np.expand_dims(mask_norm, -1)), -1)
    print(f"[DocRes]       mask apply + coord gen (256x256, was {w}x{h}): {time.time() - t:.3f}s")
    return result
