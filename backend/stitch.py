import glob
import json
import os
import re
import subprocess
import sys
import zipfile

from PIL import Image, ImageOps

from align import refine_poses

HUGIN_IMAGE = "hugin-poc"
PHOTO_NAME = re.compile(r"^360_photos/level_\d\d_shot_\d\d\.jpg$")
PHOTO_EDGE = 1920
PANO_WIDTH = 4096

def hugin(folder, *args):
    return subprocess.run(
        ["docker", "run", "--rm", "-v", f"{os.path.abspath(folder)}:/work", "-w", "/work", HUGIN_IMAGE, *args],
        check=True, capture_output=True, text=True, timeout=600,
    )

def extract_photos(folder):
    photos_dir = os.path.join(folder, "photos")

    names = []
    with zipfile.ZipFile(os.path.join(folder, "input.zip")) as archive:
        metadata = json.loads(archive.read("metadata.json"))
        os.makedirs(photos_dir, exist_ok=True)
        for photo in metadata["photos"]:
            if not PHOTO_NAME.match(photo["file"]):
                raise ValueError(f"Nome de foto inesperado: {photo['file']}")
            if not photo.get("rotation") or not photo.get("fov"):
                raise ValueError(f"Foto sem rotação ou FOV: {photo['file']}")

            name = os.path.basename(photo["file"])
            with archive.open(photo["file"]) as source:
                image = ImageOps.exif_transpose(Image.open(source))
                image.thumbnail((PHOTO_EDGE, PHOTO_EDGE))
                image.save(os.path.join(photos_dir, name), quality=95)
            names.append(f"photos/{name}")

    return metadata["photos"], names

def sensor_poses(photos):
    reference = next((p["rotation"]["yaw"] for p in photos if p["tilt"] == 0), 0)

    poses = []
    for photo in photos:
        rotation = photo["rotation"]
        yaw = (rotation["yaw"] - reference + 180) % 360 - 180
        poses.append((yaw, rotation["pitch"], -rotation["roll"]))
    return poses

def pose_args(poses):
    values = []
    for i, (yaw, pitch, roll) in enumerate(poses):
        values.append(f"y{i}={yaw:.4f}")
        values.append(f"p{i}={pitch:.4f}")
        values.append(f"r{i}={roll:.4f}")
    return "--set=" + ",".join(values)

def stitch(folder):
    photos, names = extract_photos(folder)
    fov = photos[0]["fov"]["horizontal"]
    project = os.path.join(folder, "project.pto")

    hugin(folder, "pto_gen", "-p", "0", "-f", f"{fov:.4f}", "-o", "project.pto", *names)
    hugin(folder, "pto_var", pose_args(sensor_poses(photos)), "-o", "project.pto", "project.pto")
    hugin(
        folder, "pano_modify", "--projection=2", "--fov=360x180",
        f"--canvas={PANO_WIDTH}x{PANO_WIDTH // 2}", "-o", "project.pto", "project.pto",
    )
    hugin(folder, "cpfind", "--prealigned", "-o", "project.pto", "project.pto")
    hugin(folder, "pto_var", pose_args(refine_poses(project)), "-o", "project.pto", "project.pto")
    hugin(folder, "nona", "-m", "TIFF_m", "-o", "part_", "project.pto")

    parts = sorted(glob.glob(os.path.join(folder, "part_*.tif")))
    hugin(folder, "enblend", "-w", "-o", "pano.tif", *[os.path.basename(p) for p in parts])

    tif_path = os.path.join(folder, "pano.tif")
    jpg_path = os.path.join(folder, "pano.jpg")
    Image.open(tif_path).convert("RGB").save(jpg_path, quality=90)

    for path in parts + [tif_path]:
        os.remove(path)

    return jpg_path

if __name__ == "__main__":
    try:
        print(stitch(sys.argv[1]))
    except subprocess.CalledProcessError as error:
        sys.exit(error.stderr)
