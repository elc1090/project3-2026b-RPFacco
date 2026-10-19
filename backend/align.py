import math
import re

import numpy as np

OUTLIER_DEG = 10
POINT_SIGMA_DEG = 0.5
SENSOR_SIGMA_DEG = 3
NEIGHBOR_DEG = 60
NEIGHBOR_SIGMA_DEG = 2
MAX_STEP_DEG = 5
ITERATIONS = 50

def read_pto(path):
    images, points = [], []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("i "):
                fields = dict(re.findall(r"\s([A-Za-z]+)(=?[-\d.eE+]+)", line))
                hfov = fields["v"]
                hfov = images[int(hfov[1:])]["hfov"] if hfov.startswith("=") else float(hfov)
                images.append({
                    "w": int(fields["w"]), "h": int(fields["h"]), "hfov": hfov,
                    "ypr": (float(fields["y"]), float(fields["p"]), float(fields["r"])),
                })
            elif line.startswith("c "):
                m = re.match(r"c n(\d+) N(\d+) x(\S+) y(\S+) X(\S+) Y(\S+)", line)
                points.append((int(m[1]), int(m[2]), float(m[3]), float(m[4]), float(m[5]), float(m[6])))
    return images, points

def rotation(yaw, pitch, roll):
    y, p, rho = math.radians(yaw), math.radians(pitch), math.radians(-roll)
    forward = np.array([math.sin(y) * math.cos(p), math.cos(y) * math.cos(p), math.sin(p)])
    right0 = np.array([math.cos(y), -math.sin(y), 0.0])
    up0 = np.cross(right0, forward)
    right = math.cos(rho) * right0 + math.sin(rho) * up0
    up = -math.sin(rho) * right0 + math.cos(rho) * up0
    return np.column_stack([right, up, forward])

def angles(matrix):
    forward = matrix[:, 2]
    y = math.atan2(forward[0], forward[1])
    p = math.asin(max(-1.0, min(1.0, forward[2])))
    right0 = np.array([math.cos(y), -math.sin(y), 0.0])
    up0 = np.cross(right0, forward)
    rho = math.atan2(matrix[:, 0] @ up0, matrix[:, 0] @ right0)
    return math.degrees(y), math.degrees(p), -math.degrees(rho)

def camera_rays(images, index, xs, ys):
    w = np.array([images[i]["w"] for i in index], dtype=float)
    h = np.array([images[i]["h"] for i in index], dtype=float)
    focal = (w / 2) / np.tan(np.radians([images[i]["hfov"] for i in index]) / 2)
    rays = np.stack([(xs - w / 2) / focal, -(ys - h / 2) / focal, np.ones_like(xs)], axis=1)
    return rays / np.linalg.norm(rays, axis=1, keepdims=True)

def skew(v):
    zero = np.zeros(len(v))
    return np.stack([
        np.stack([zero, -v[:, 2], v[:, 1]], axis=1),
        np.stack([v[:, 2], zero, -v[:, 0]], axis=1),
        np.stack([-v[:, 1], v[:, 0], zero], axis=1),
    ], axis=1)

def exp_map(v):
    angle = np.linalg.norm(v, axis=1)[:, None, None]
    k = skew(v / np.maximum(angle[:, 0], 1e-12))
    return np.eye(3) + np.sin(angle) * k + (1 - np.cos(angle)) * (k @ k)

def log_map(m):
    cos = np.clip((np.trace(m, axis1=1, axis2=2) - 1) / 2, -1, 1)
    angle = np.arccos(cos)
    axis = np.stack([m[:, 2, 1] - m[:, 1, 2], m[:, 0, 2] - m[:, 2, 0], m[:, 1, 0] - m[:, 0, 1]], axis=1)
    scale = np.where(angle < 1e-9, 0.5, angle / (2 * np.maximum(np.sin(angle), 1e-12)))
    return axis * scale[:, None]

def robust_weight(residuals, sigma):
    return 1 / np.sqrt(1 + (np.linalg.norm(residuals, axis=1) / sigma) ** 2) / sigma**2

def refine_poses(pto_path):
    images, points = read_pto(pto_path)
    n = len(images)
    sensor = np.array([rotation(*image["ypr"]) for image in images])
    if not points:
        return [image["ypr"] for image in images]

    a = np.array([p[0] for p in points])
    b = np.array([p[1] for p in points])
    ray_a = camera_rays(images, a, np.array([p[2] for p in points]), np.array([p[3] for p in points]))
    ray_b = camera_rays(images, b, np.array([p[4] for p in points]), np.array([p[5] for p in points]))

    agreement = np.einsum("kij,kj,kil,kl->k", sensor[a], ray_a, sensor[b], ray_b)
    keep = agreement >= math.cos(math.radians(OUTLIER_DEG))
    a, b, ray_a, ray_b = a[keep], b[keep], ray_a[keep], ray_b[keep]

    axes = sensor[:, :, 2]
    close = np.triu(axes @ axes.T >= math.cos(math.radians(NEIGHBOR_DEG)), k=1)
    left, right = np.nonzero(close)

    poses = sensor.copy()
    for _ in range(ITERATIONS):
        H = np.zeros((n, n, 3, 3))
        g = np.zeros((n, 3))

        world_a = np.einsum("kij,kj->ki", poses[a], ray_a)
        world_b = np.einsum("kij,kj->ki", poses[b], ray_b)
        error = world_a - world_b
        weight = robust_weight(error, math.radians(POINT_SIGMA_DEG))[:, None, None]
        jac_a, jac_b = -skew(world_a), skew(world_b)
        np.add.at(H, (a, a), weight * jac_a.transpose(0, 2, 1) @ jac_a)
        np.add.at(H, (b, b), weight * jac_b.transpose(0, 2, 1) @ jac_b)
        np.add.at(H, (a, b), weight * jac_a.transpose(0, 2, 1) @ jac_b)
        np.add.at(H, (b, a), weight * jac_b.transpose(0, 2, 1) @ jac_a)
        np.add.at(g, a, (weight * jac_a.transpose(0, 2, 1) @ error[:, :, None])[:, :, 0])
        np.add.at(g, b, (weight * jac_b.transpose(0, 2, 1) @ error[:, :, None])[:, :, 0])

        drift = log_map(poses @ sensor.transpose(0, 2, 1))
        weight = robust_weight(drift, math.radians(SENSOR_SIGMA_DEG))
        H[np.arange(n), np.arange(n)] += weight[:, None, None] * np.eye(3)
        g += weight[:, None] * drift

        change = drift[left] - drift[right]
        weight = robust_weight(change, math.radians(NEIGHBOR_SIGMA_DEG))[:, None, None] * np.eye(3)
        np.add.at(H, (left, left), weight)
        np.add.at(H, (right, right), weight)
        np.add.at(H, (left, right), -weight)
        np.add.at(H, (right, left), -weight)
        np.add.at(g, left, (weight @ change[:, :, None])[:, :, 0])
        np.add.at(g, right, -(weight @ change[:, :, None])[:, :, 0])

        step = np.linalg.solve(H.transpose(0, 2, 1, 3).reshape(3 * n, 3 * n), -g.ravel()).reshape(n, 3)
        largest = np.degrees(np.linalg.norm(step, axis=1).max())
        if largest > MAX_STEP_DEG:
            step *= MAX_STEP_DEG / largest
        poses = exp_map(step) @ poses
        if largest < 1e-4:
            break

    return [angles(pose) for pose in poses]
