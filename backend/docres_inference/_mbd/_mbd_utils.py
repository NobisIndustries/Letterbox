import cv2
import numpy as np
import torch
import itertools
import torch.nn as nn
from torch.autograd import Variable


def reorder(myPoints):
    myPoints = myPoints.reshape((4, 2))
    myPointsNew = np.zeros((4, 1, 2), dtype=np.int32)
    add = myPoints.sum(1)
    myPointsNew[0] = myPoints[np.argmin(add)]
    myPointsNew[3] = myPoints[np.argmax(add)]
    diff = np.diff(myPoints, axis=1)
    myPointsNew[1] = myPoints[np.argmin(diff)]
    myPointsNew[2] = myPoints[np.argmax(diff)]
    return myPointsNew


def findMiddle(corners, mask, points=[0.25, 0.5, 0.75]):
    num_middle_points = len(points)
    top = [np.array([])] * num_middle_points
    bottom = [np.array([])] * num_middle_points
    left = [np.array([])] * num_middle_points
    right = [np.array([])] * num_middle_points

    center_top = []
    center_bottom = []
    center_left = []
    center_right = []

    center = (int((corners[0][0][1] + corners[3][0][1]) / 2), int((corners[0][0][0] + corners[3][0][0]) / 2))
    for ratio in points:
        center_top.append((center[0], int(corners[0][0][0] * (1 - ratio) + corners[1][0][0] * ratio)))
        center_bottom.append((center[0], int(corners[2][0][0] * (1 - ratio) + corners[3][0][0] * ratio)))
        center_left.append((int(corners[0][0][1] * (1 - ratio) + corners[2][0][1] * ratio), center[1]))
        center_right.append((int(corners[1][0][1] * (1 - ratio) + corners[3][0][1] * ratio), center[1]))

    for i in range(0, center[0], 1):
        for j in range(num_middle_points):
            if top[j].size == 0:
                if mask[i, center_top[j][1]] == 255:
                    top[j] = np.asarray([center_top[j][1], i])
                    top[j] = top[j].reshape(1, 2)

    for i in range(mask.shape[0] - 1, center[0], -1):
        for j in range(num_middle_points):
            if bottom[j].size == 0:
                if mask[i, center_bottom[j][1]] == 255:
                    bottom[j] = np.asarray([center_bottom[j][1], i])
                    bottom[j] = bottom[j].reshape(1, 2)

    for i in range(mask.shape[1] - 1, center[1], -1):
        for j in range(num_middle_points):
            if right[j].size == 0:
                if mask[center_right[j][0], i] == 255:
                    right[j] = np.asarray([i, center_right[j][0]])
                    right[j] = right[j].reshape(1, 2)

    for i in range(0, center[1]):
        for j in range(num_middle_points):
            if left[j].size == 0:
                if mask[center_left[j][0], i] == 255:
                    left[j] = np.asarray([i, center_left[j][0]])
                    left[j] = left[j].reshape(1, 2)

    return np.asarray(top + bottom + left + right)


def DP_algorithm(contours):
    biggest = np.array([])
    max_area = 0
    step = 0.001
    count = 0

    ### largest contours
    for i in contours:
        area = cv2.contourArea(i)
        if area > max_area:
            max_area = area
            biggest_contours = i
    peri = cv2.arcLength(biggest_contours, True)

    ### find four corners
    while True:
        approx = cv2.approxPolyDP(biggest_contours, (0.01 + step * count) * peri, True)
        if len(approx) == 4:
            biggest = approx
            break
        count += 1
        if count > 200:
            break
    return biggest, max_area, biggest_contours


def cvimg2torch(img):
    if len(img.shape) == 2:
        img = np.expand_dims(img, axis=-1)
    img = img.astype(float) / 255.0
    img = img.transpose(2, 0, 1)  # NHWC -> NCHW
    img = np.expand_dims(img, 0)
    img = torch.from_numpy(img).float()
    return img


def torch2cvimg(tensor):
    im_list = []
    for i in range(tensor.shape[0]):
        im = tensor.detach().cpu().data.numpy()[i]
        im = im.transpose(1, 2, 0)
        im = np.clip(im, 0, 1)
        im = (im * 255).astype(np.uint8)
        im_list.append(im)
    return im_list


class TPSGridGen(nn.Module):
    def __init__(self, target_height, target_width, target_control_points):
        super(TPSGridGen, self).__init__()
        assert target_control_points.ndimension() == 2
        assert target_control_points.size(1) == 2
        N = target_control_points.size(0)
        self.num_points = N
        target_control_points = target_control_points.float()

        # create padded kernel matrix
        forward_kernel = torch.zeros(N + 3, N + 3)
        target_control_partial_repr = self.compute_partial_repr(target_control_points, target_control_points)
        forward_kernel[:N, :N].copy_(target_control_partial_repr)
        forward_kernel[:N, -3].fill_(1)
        forward_kernel[-3, :N].fill_(1)
        forward_kernel[:N, -2:].copy_(target_control_points)
        forward_kernel[-2:, :N].copy_(target_control_points.transpose(0, 1))
        # compute inverse matrix
        inverse_kernel = torch.inverse(forward_kernel)

        # create target coordinate matrix
        HW = target_height * target_width
        target_coordinate = list(itertools.product(range(target_height), range(target_width)))
        target_coordinate = torch.Tensor(target_coordinate)  # HW x 2
        Y, X = target_coordinate.split(1, dim=1)
        Y = Y * 2 / (target_height - 1) - 1
        X = X * 2 / (target_width - 1) - 1
        target_coordinate = torch.cat([X, Y], dim=1)  # convert from (y, x) to (x, y)
        target_coordinate_partial_repr = self.compute_partial_repr(target_coordinate.to(target_control_points.device), target_control_points)
        target_coordinate_repr = torch.cat([
            target_coordinate_partial_repr, torch.ones(HW, 1), target_coordinate
        ], dim=1)

        # register precomputed matrices
        self.register_buffer('inverse_kernel', inverse_kernel)
        self.register_buffer('padding_matrix', torch.zeros(3, 2))
        self.register_buffer('target_coordinate_repr', target_coordinate_repr)

    def forward(self, source_control_points):
        assert source_control_points.ndimension() == 3
        assert source_control_points.size(1) == self.num_points
        assert source_control_points.size(2) == 2
        batch_size = source_control_points.size(0)

        Y = torch.cat([source_control_points, Variable(self.padding_matrix.expand(batch_size, 3, 2))], 1)
        mapping_matrix = torch.matmul(Variable(self.inverse_kernel), Y)
        source_coordinate = torch.matmul(Variable(self.target_coordinate_repr), mapping_matrix)
        return source_coordinate

    def compute_partial_repr(self, input_points, control_points):
        N = input_points.size(0)
        M = control_points.size(0)
        pairwise_diff = input_points.view(N, 1, 2) - control_points.view(1, M, 2)
        pairwise_diff_square = pairwise_diff * pairwise_diff
        pairwise_dist = pairwise_diff_square[:, :, 0] + pairwise_diff_square[:, :, 1]
        repr_matrix = 0.5 * pairwise_dist * torch.log(pairwise_dist)
        # fix numerical error for 0 * log(0), substitute all nan with 0
        mask = repr_matrix != repr_matrix
        repr_matrix.masked_fill_(mask, 0)
        return repr_matrix


def mask_base_dewarper(image, mask, device):
    """TPS-based dewarping using mask contours.

    Args:
        image: ndarray HxWx3 uint8
        mask: ndarray HxW uint8
        device: torch.device

    Returns:
        dewarped: ndarray HxWx3 uint8
        grid: ndarray HxWx2 float
    """
    import torch.nn.functional as F

    ## get contours
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, method=cv2.CHAIN_APPROX_SIMPLE)

    ## get biggest contours and four corners based on Douglas-Peucker algorithm
    four_corners, maxArea, contour = DP_algorithm(contours)
    four_corners = reorder(four_corners)

    ## reserve biggest contours and remove other noisy contours
    new_mask = np.zeros_like(mask)
    new_mask = cv2.drawContours(new_mask, [contour], -1, 255, cv2.FILLED)

    ## obtain middle points
    ratios = [0.25, 0.5, 0.75]
    middle = findMiddle(corners=four_corners, mask=new_mask, points=ratios)

    ## all points
    source_points = np.concatenate((four_corners, middle), axis=0)

    ## target points
    h, w = image.shape[:2]
    padding = 0
    target_points = [[padding, padding], [w - padding, padding], [padding, h - padding], [w - padding, h - padding]]
    for ratio in ratios:
        target_points.append([int((w - 2 * padding) * ratio) + padding, padding])
    for ratio in ratios:
        target_points.append([int((w - 2 * padding) * ratio) + padding, h - padding])
    for ratio in ratios:
        target_points.append([padding, int((h - 2 * padding) * ratio) + padding])
    for ratio in ratios:
        target_points.append([w - padding, int((h - 2 * padding) * ratio) + padding])

    ## dewarp based on generated grid
    source_points = source_points.reshape(-1, 2) / np.array([image.shape[:2][::-1]]).reshape(1, 2)
    source_points = torch.from_numpy(source_points).float().to(device)
    source_points = source_points.unsqueeze(0)
    source_points = (source_points - 0.5) * 2
    target_points = np.asarray(target_points).reshape(-1, 2) / np.array([image.shape[:2][::-1]]).reshape(1, 2)
    target_points = torch.from_numpy(target_points).float()
    target_points = (target_points - 0.5) * 2

    model = TPSGridGen(target_height=256, target_width=256, target_control_points=target_points)
    model = model.to(device)
    grid = model(source_points).view(-1, 256, 256, 2).permute(0, 3, 1, 2)
    grid = F.interpolate(grid, (h, w), mode='bilinear').permute(0, 2, 3, 1)
    dewarped = torch2cvimg(F.grid_sample(cvimg2torch(image).to(device), grid))[0]
    return dewarped, grid[0].cpu().numpy()
