import torch
import torch.nn as nn
import torch.nn.functional as F
from .aspp import build_aspp
from .decoder import build_decoder
from .backbone import build_backbone


class DeepLab(nn.Module):
    def __init__(self, backbone='resnet', output_stride=16, num_classes=21,
                 sync_bn=True, freeze_bn=False):
        super(DeepLab, self).__init__()
        if backbone == 'drn':
            output_stride = 8

        # Always use standard BatchNorm2d for inference
        BatchNorm = nn.BatchNorm2d

        self.backbone = build_backbone(backbone, output_stride, BatchNorm)
        self.aspp = build_aspp(backbone, output_stride, BatchNorm)
        self.decoder = build_decoder(num_classes, backbone, BatchNorm)

        self.freeze_bn = freeze_bn

    def forward(self, input):
        import time

        t = time.time()
        x, low_level_feat = self.backbone(input)
        print(f"[DocRes]         backbone (ResNet101): {time.time() - t:.3f}s  x={tuple(x.shape)} low={tuple(low_level_feat.shape)}")

        t = time.time()
        x = self.aspp(x)
        print(f"[DocRes]         ASPP: {time.time() - t:.3f}s  x={tuple(x.shape)}")

        t = time.time()
        x = self.decoder(x, low_level_feat)
        print(f"[DocRes]         decoder: {time.time() - t:.3f}s  x={tuple(x.shape)}")

        t = time.time()
        x = F.interpolate(x, size=input.size()[2:], mode='bilinear', align_corners=True)
        print(f"[DocRes]         interpolate: {time.time() - t:.3f}s")

        return x
