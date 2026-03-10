"""Self-contained DocRes document restoration inference module.

Usage:
    from docres_inference import DocResProcessor
    proc = DocResProcessor("path/to/docres.pkl", "path/to/mbd.pkl")
    proc.process(["input.png"], ["output.jpg"])
"""

from __future__ import annotations

import time
from collections import OrderedDict
from pathlib import Path

import cv2
import numpy as np
import torch

from ._model import Restormer
from ._prompts import dewarp_prompt, getBasecoord


def _convert_state_dict(state_dict):
    """Strip `module.` prefix from DataParallel checkpoint keys."""
    new_state_dict = OrderedDict()
    for k, v in state_dict.items():
        name = k[7:] if k.startswith("module.") else k
        new_state_dict[name] = v
    return new_state_dict


class DocResProcessor:
    """Document restoration processor.

    Applies dewarping (Restormer model) followed by fast OpenCV-based
    shadow removal and contrast enhancement.

    Args:
        docres_weights: Path to the docres.pkl checkpoint.
        mbd_weights: Path to the mbd.pkl checkpoint (required for dewarping).
        device: "auto", "cuda", or "cpu".
    """

    def __init__(
        self,
        docres_weights: str,
        mbd_weights: str,
        device: str = "auto",
    ):
        if device == "auto":
            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self._device = torch.device(device)

        print(f"[DocRes] Using device: {self._device}")
        print(f"[DocRes] PyTorch threads: {torch.get_num_threads()}, interop threads: {torch.get_num_interop_threads()}")

        # Enable flush-to-zero and denormals-are-zero mode.
        # Denormalized floats in model weights cause 100-1000x slowdowns
        # on CPUs that handle them in microcode (e.g. Intel N100).
        torch.set_flush_denormal(True)
        print(f"[DocRes] Flush denormals: {torch.get_flush_denormal()}")

        t0 = time.time()
        # Load Restormer model (used only for dewarping)
        self._model = Restormer(
            inp_channels=6,
            out_channels=3,
            dim=48,
            num_blocks=[2, 3, 3, 4],
            num_refinement_blocks=4,
            heads=[1, 2, 4, 8],
            ffn_expansion_factor=2.66,
            bias=False,
            LayerNorm_type="WithBias",
            dual_pixel_task=True,
        )
        state = _convert_state_dict(
            torch.load(docres_weights, map_location=self._device)["model_state"]
        )
        self._model.load_state_dict(state)
        self._model.eval()
        self._model.to(self._device)

        if self._device.type == "cuda":
            self._model.half()
        else:
            # Only quantize Linear layers. Conv2d dynamic quantization is not
            # well-supported in PyTorch and causes catastrophic slowdowns
            # on CPUs without AVX-512 (e.g. Intel N100).
            self._model = torch.quantization.quantize_dynamic(
                self._model, {torch.nn.Linear}, dtype=torch.qint8
            )

        print(f"[DocRes] Restormer loaded{' + quantized (int8)' if self._device.type != 'cuda' else ''} in {time.time() - t0:.1f}s")

        # Load MBD segmentation model
        from ._mbd import _load_seg_model

        t0 = time.time()
        self._seg_model = _load_seg_model(mbd_weights, self._device)
        print(f"[DocRes] MBD segmentation model loaded in {time.time() - t0:.1f}s")

    def process(
        self,
        images: list[str | bytes],
        output_paths: list[str | Path],
        jpeg_quality: int = 95,
        max_output_width: int = 0,
    ) -> None:
        """Process images through the restoration pipeline.

        Pipeline: dewarping (model) -> downscale -> enhance (OpenCV).

        Args:
            images: List of file paths or raw image bytes (BGR).
            output_paths: List of output file paths (one per input image).
            jpeg_quality: Output JPEG quality (1-100).
            max_output_width: Downscale after dewarping to this width before
                enhancement. 0 = no downscale.
        """
        if len(images) != len(output_paths):
            raise ValueError(
                f"images and output_paths must have the same length, "
                f"got {len(images)} and {len(output_paths)}"
            )
        n = len(images)
        for idx, (img_input, out_path) in enumerate(zip(images, output_paths), 1):
            label = img_input if isinstance(img_input, str) else f"image bytes ({len(img_input)} bytes)"
            print(f"[DocRes] [{idx}/{n}] Processing: {label}")
            t_total = time.time()

            img = self._load_image(img_input)
            h, w = img.shape[:2]
            print(f"[DocRes]   Loaded {w}x{h}")

            t0 = time.time()
            img = self._dewarping(img)
            print(f"[DocRes]   Dewarping done in {time.time() - t0:.1f}s")

            if max_output_width and img.shape[1] > max_output_width:
                t0 = time.time()
                ratio = max_output_width / img.shape[1]
                new_size = (max_output_width, int(img.shape[0] * ratio))
                img = cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)
                print(f"[DocRes]   Downscaled to {new_size[0]}x{new_size[1]} in {time.time() - t0:.3f}s")

            t0 = time.time()
            img = self.fast_enhance(img)
            print(f"[DocRes]   Enhancement done in {time.time() - t0:.1f}s")

            out_path = Path(out_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(
                str(out_path), img, [cv2.IMWRITE_JPEG_QUALITY, jpeg_quality]
            )
            print(f"[DocRes]   Saved to {out_path} (total: {time.time() - t_total:.1f}s)")

    def _load_image(self, img_input: str | bytes) -> np.ndarray:
        if isinstance(img_input, (str,)):
            img = cv2.imread(img_input)
            if img is None:
                raise FileNotFoundError(f"Could not read image: {img_input}")
            return img
        elif isinstance(img_input, (bytes, bytearray)):
            arr = np.frombuffer(img_input, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not decode image bytes")
            return img
        else:
            raise TypeError(f"Expected str or bytes, got {type(img_input)}")

    def _mbd_infer(self, img: np.ndarray, device: torch.device) -> np.ndarray:
        from ._mbd import net1_net2_infer_single_im

        return net1_net2_infer_single_im(img, self._seg_model, device)

    def _dewarping(self, im_org: np.ndarray) -> np.ndarray:
        INPUT_SIZE = 256
        h, w = im_org.shape[:2]

        t = time.time()
        im_masked, prompt_org = dewarp_prompt(im_org, self._mbd_infer, self._device)
        print(f"[DocRes]     dewarp_prompt (MBD seg + mask): {time.time() - t:.3f}s")

        t = time.time()
        # im_masked is already 256x256 from dewarp_prompt
        im_masked = im_masked / 255.0
        im_masked = torch.from_numpy(im_masked.transpose(2, 0, 1)).unsqueeze(0)
        im_masked = im_masked.float().to(self._device)

        prompt = torch.from_numpy(prompt_org.transpose(2, 0, 1)).unsqueeze(0)
        prompt = prompt.float().to(self._device)

        in_im = torch.cat((im_masked, prompt), dim=1)
        print(f"[DocRes]     preprocess (resize+to_tensor): {time.time() - t:.3f}s")

        base_coord = getBasecoord(INPUT_SIZE, INPUT_SIZE) / INPUT_SIZE

        t = time.time()
        with torch.inference_mode():
            pred = self._model(in_im)
        print(f"[DocRes]     Restormer forward pass: {time.time() - t:.3f}s")

        t = time.time()
        with torch.inference_mode():
            pred = pred[0][:2].permute(1, 2, 0).cpu().numpy()
            pred = pred + base_coord
        print(f"[DocRes]     pred to numpy + base_coord: {time.time() - t:.3f}s")

        t = time.time()
        for _ in range(15):
            pred = cv2.blur(pred, (3, 3), borderType=cv2.BORDER_REPLICATE)
        print(f"[DocRes]     15x blur smoothing (256x256): {time.time() - t:.3f}s")

        t = time.time()
        pred = cv2.resize(pred, (w, h)) * (w, h)
        pred = pred.astype(np.float32)
        print(f"[DocRes]     resize pred to {w}x{h}: {time.time() - t:.3f}s")

        t = time.time()
        out_im = cv2.remap(im_org, pred[:, :, 0], pred[:, :, 1], cv2.INTER_LINEAR)
        print(f"[DocRes]     cv2.remap {w}x{h}: {time.time() - t:.3f}s")

        return out_im

    @staticmethod
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

        Args:
            img: BGR uint8 image.
            shadow_strength: 0.0 = no shadow correction, 1.0 = full correction.
            shadow_dilate_size: Kernel size for dilation in bg estimation.
            shadow_median_size: Median blur kernel for bg estimation (must be odd).
            stretch_low_pct: Lower percentile for histogram stretch.
            stretch_high_pct: Upper percentile for histogram stretch.
            clahe_clip: CLAHE clip limit (0 = disable CLAHE).
            clahe_grid: CLAHE tile grid size.
            white_balance: Whether to apply gray-world white balance.
        """
        h, w = img.shape[:2]
        print(f"[DocRes]     enhance input: {w}x{h}")

        t = time.time()
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l_f = l.astype(np.float32)
        print(f"[DocRes]     BGR->LAB + split: {time.time() - t:.3f}s")

        # --- Shadow removal: additive illumination correction ---
        if shadow_strength > 0:
            t = time.time()
            kernel = np.ones((shadow_dilate_size, shadow_dilate_size), np.uint8)
            dilated = cv2.dilate(l, kernel)
            bg = cv2.medianBlur(dilated, shadow_median_size).astype(np.float32)
            target = np.max(bg)
            correction = (target - bg) * shadow_strength
            l_f = np.clip(l_f + correction, 0, 255)
            print(f"[DocRes]     shadow removal (dilate+medianBlur+correct): {time.time() - t:.3f}s")

        # --- Percentile histogram stretch ---
        t = time.time()
        lo = np.percentile(l_f, stretch_low_pct)
        hi = np.percentile(l_f, stretch_high_pct)
        if hi - lo > 10:
            l_f = np.clip((l_f - lo) / (hi - lo) * 255, 0, 255)
        l = l_f.astype(np.uint8)
        print(f"[DocRes]     histogram stretch: {time.time() - t:.3f}s")

        # --- CLAHE ---
        if clahe_clip > 0:
            clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(clahe_grid, clahe_grid))
            l = clahe.apply(l)

        t = time.time()
        enhanced = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
        print(f"[DocRes]     LAB->BGR merge: {time.time() - t:.3f}s")

        # --- Gray-world white balance ---
        if white_balance:
            t = time.time()
            avg_b, avg_g, avg_r = [enhanced[:, :, i].mean() for i in range(3)]
            avg_gray = (avg_b + avg_g + avg_r) / 3
            enhanced = enhanced.astype(np.float32)
            enhanced[:, :, 0] *= avg_gray / max(avg_b, 1)
            enhanced[:, :, 1] *= avg_gray / max(avg_g, 1)
            enhanced[:, :, 2] *= avg_gray / max(avg_r, 1)
            enhanced = np.clip(enhanced, 0, 255).astype(np.uint8)
            print(f"[DocRes]     white balance: {time.time() - t:.3f}s")

        return enhanced
