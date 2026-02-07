from pathlib import Path
from typing import Tuple

import cv2
import numpy as np
from PIL import Image
import imageio
import random


FOURK = (3840, 2160)  # (width, height)

def random_ken_burns_params():
    # Gentle ranges; feel free to widen once you like it
    duration_sec = random.choice([15, 20, 25])
    fps = 30

    zoom_end = random.uniform(1.06, 1.18)  # subtle → moderate zoom
    zoom_start = 1.0

    # Pan fractions (0..1). Keep small so you don't "run off" the subject.
    # We'll pick a start and end; generator interprets them as fractions of max crop offset.
    pan_start = (random.uniform(0.0, 0.25), random.uniform(0.0, 0.25))
    pan_end   = (random.uniform(0.75, 1.0), random.uniform(0.75, 1.0))

    # Randomize direction sometimes
    if random.random() < 0.5:
        pan_start, pan_end = pan_end, pan_start

    return dict(
        duration_sec=duration_sec,
        fps=fps,
        zoom_start=zoom_start,
        zoom_end=zoom_end,
        pan_start=pan_start,
        pan_end=pan_end,
    )

def load_and_fill_4k(image_path: str) -> np.ndarray:
    """
    Load an image, resize it to *cover* a 4K frame (like CSS background-size: cover),
    then center crop to exactly 3840x2160.
    Returns: np.ndarray in RGB, shape (H, W, 3).
    """
    target_w, target_h = FOURK

    im = Image.open(image_path).convert("RGB")
    src_w, src_h = im.size
    src_ratio = src_w / src_h
    target_ratio = target_w / target_h

    if src_ratio > target_ratio:
        # Source is wider than target → fit height, crop width
        new_h = target_h
        new_w = int(new_h * src_ratio)
    else:
        # Source is taller/narrower → fit width, crop height
        new_w = target_w
        new_h = int(new_w / src_ratio)

    im = im.resize((new_w, new_h), Image.LANCZOS)

    # Center crop to 4K
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    right = left + target_w
    bottom = top + target_h

    im = im.crop((left, top, right, bottom))
    return np.array(im)  # RGB uint8


def generate_ken_burns_video(
    image_path: str,
    output_path: str,
    duration_sec: int = 15,
    fps: int = 30,
    zoom_start: float = 1.0,
    zoom_end: float = 1.10,
    pan_start: Tuple[float, float] = (0.0, 0.0),
    pan_end: Tuple[float, float] = (0.05, 0.05),
) -> str:
    """
    Create a Ken Burns–style video from a single image.

    - image_path: input image
    - output_path: mp4 file to write
    - duration_sec: length of video
    - fps: frames per second
    - zoom_start/zoom_end: 1.0 = full frame, 1.1 = 10% zoom in
    - pan_*: fractional offsets (0..1) of how far we shift the crop over time

    Returns: output_path
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    base = load_and_fill_4k(image_path)  # RGB
    height, width, _ = base.shape

    frame_count = duration_sec * fps

    # Use imageio's ffmpeg writer with H.264, browser-friendly pixel format
    # imageio will stream frames to ffmpeg, no huge memory footprint.
    writer = imageio.get_writer(
        output_path,
        fps=fps,
        codec="libx264",
        pixelformat="yuv420p",
        macro_block_size=8,
    )

    try:
        for i in range(frame_count):
            t = i / max(frame_count - 1, 1)

            # Interpolate zoom and pan
            scale = zoom_start + (zoom_end - zoom_start) * t
            pan_x = pan_start[0] + (pan_end[0] - pan_start[0]) * t
            pan_y = pan_start[1] + (pan_end[1] - pan_start[1]) * t

            # Compute crop size for this scale
            crop_w = int(width / scale)
            crop_h = int(height / scale)

            # Max pan offsets (in pixels)
            max_offset_x = width - crop_w
            max_offset_y = height - crop_h

            # Pan offsets based on fractions
            offset_x = int(max_offset_x * pan_x)
            offset_y = int(max_offset_y * pan_y)

            x0 = offset_x
            y0 = offset_y
            x1 = x0 + crop_w
            y1 = y0 + crop_h

            cropped = base[y0:y1, x0:x1]

            # Resize back to 4K frame size
            frame_rgb = cv2.resize(
                cropped, (width, height), interpolation=cv2.INTER_LANCZOS4
            )

            # imageio expects RGB; we already have RGB
            writer.append_data(frame_rgb)

    finally:
        writer.close()

    return output_path
