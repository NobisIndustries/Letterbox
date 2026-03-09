import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from ._deeplab import DeepLab
from ._mbd_utils import cvimg2torch, mask_base_dewarper


def _load_seg_model(model_path, device):
    """Load the MBD segmentation model."""
    seg_model = DeepLab(
        num_classes=1,
        backbone='resnet',
        output_stride=16,
        sync_bn=None,
        freeze_bn=False,
    )
    # Wrap in DataParallel to match checkpoint key format, then load
    seg_model = nn.DataParallel(seg_model)
    checkpoint = torch.load(model_path, map_location=device)
    seg_model.load_state_dict(checkpoint['model_state'])
    seg_model = seg_model.module  # unwrap DataParallel
    seg_model.to(device)
    seg_model.eval()
    if device.type == "cpu":
        seg_model = torch.quantization.quantize_dynamic(
            seg_model, {torch.nn.Linear, torch.nn.Conv2d}, dtype=torch.qint8
        )
    return seg_model


def net1_net2_infer_single_im(img, seg_model, device):
    """Run MBD segmentation to produce a document mask.

    Args:
        img: ndarray HxWx3 uint8 (BGR)
        seg_model: loaded DeepLab model
        device: torch.device

    Returns:
        mask_pred: ndarray HxW uint8
    """
    h_org, w_org = img.shape[:2]
    img_resized = cv2.resize(img, (448, 448))
    img_resized = cv2.GaussianBlur(img_resized, (15, 15), 0, 0)
    img_resized = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
    img_tensor = cvimg2torch(img_resized).to(device)

    with torch.no_grad():
        pred = seg_model(img_tensor)
        mask_pred = pred[:, 0, :, :].unsqueeze(1)
        mask_pred = F.interpolate(mask_pred, (h_org, w_org))
        mask_pred = mask_pred.squeeze(0).squeeze(0).cpu().numpy()
        mask_pred = (mask_pred * 255).astype(np.uint8)
        kernel = np.ones((3, 3))
        mask_pred = cv2.dilate(mask_pred, kernel, iterations=3)
        mask_pred = cv2.erode(mask_pred, kernel, iterations=3)
        mask_pred[mask_pred > 100] = 255
        mask_pred[mask_pred < 100] = 0

    return mask_pred
