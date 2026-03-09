import cv2
import numpy as np


def getBasecoord(h, w):
    base_coord0 = np.tile(np.arange(h).reshape(h, 1), (1, w)).astype(np.float32)
    base_coord1 = np.tile(np.arange(w).reshape(1, w), (h, 1)).astype(np.float32)
    base_coord = np.concatenate((np.expand_dims(base_coord1, -1), np.expand_dims(base_coord0, -1)), -1)
    return base_coord


def dewarp_prompt(img, mbd_infer_fn, device):
    """Generate dewarping prompt. Returns (masked_img, prompt_array)."""
    mask = mbd_infer_fn(img, device)
    base_coord = getBasecoord(256, 256) / 256
    img[mask == 0] = 0
    mask = cv2.resize(mask, (256, 256)) / 255
    return img, np.concatenate((base_coord, np.expand_dims(mask, -1)), -1)
