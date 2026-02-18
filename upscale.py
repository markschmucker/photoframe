#!/usr/bin/env python3
"""
AI-upscale selected images to Samsung The Frame 4K JPEGs.

Workflow:
  1. python generate.py --count 20        # generate candidates
  2. Browse gallery/, delete the ones you don't like
  3. python upscale.py                      # upscale survivors to 4K
"""

import os
import sys
from io import BytesIO
from pathlib import Path

import replicate
from PIL import Image, ImageCms

# sRGB ICC profile for Samsung The Frame compliance
_srgb_profile = ImageCms.createProfile("sRGB")
_srgb_icc_bytes = ImageCms.ImageCmsProfile(_srgb_profile).tobytes()

TARGET_W, TARGET_H = 3840, 2160


def ai_upscale_to_4k(input_path: str, output_path: str) -> tuple[int, int]:
    """
    AI-upscale via Real-ESRGAN 4x, crop to 16:9 before upscaling to minimize
    waste, then downscale to exactly 3840x2160.

    Steps:
      1. Open source image, center-crop to 16:9 aspect ratio
      2. Real-ESRGAN 4x upscale
      3. LANCZOS downscale to exactly 3840x2160 (from >4K source, so high quality)
      4. Save as JPEG with sRGB ICC profile
    """
    # 1. Crop source to 16:9 before sending to upscaler
    img = Image.open(input_path).convert("RGB")
    src_w, src_h = img.size
    target_ratio = TARGET_W / TARGET_H  # 16:9 = 1.778

    # Crop to 16:9: keep full width, trim height (or vice versa)
    desired_h = int(src_w / target_ratio)
    desired_w = int(src_h * target_ratio)

    if desired_h <= src_h:
        # Source is taller than 16:9 — crop height
        crop_top = (src_h - desired_h) // 2
        img = img.crop((0, crop_top, src_w, crop_top + desired_h))
    else:
        # Source is wider than 16:9 — crop width
        crop_left = (src_w - desired_w) // 2
        img = img.crop((crop_left, 0, crop_left + desired_w, src_h))

    cropped_w, cropped_h = img.size
    print(f"  Cropped:     {src_w}x{src_h} -> {cropped_w}x{cropped_h} (16:9)")

    # Save cropped version to a temp file for upload
    tmp_path = str(Path(input_path).parent / "_upscale_tmp.png")
    img.save(tmp_path, "PNG")

    # 2. AI upscale 4x
    rc = replicate.Client(api_token=os.environ["REPLICATE_API_TOKEN"])
    with open(tmp_path, "rb") as f:
        output = rc.run(
            "nightmareai/real-esrgan",
            input={
                "image": f,
                "scale": 4,
                "face_enhance": False,
            },
        )

    if isinstance(output, list):
        upscaled_bytes = output[0].read()
    else:
        upscaled_bytes = output.read()

    upscaled = Image.open(BytesIO(upscaled_bytes)).convert("RGB")
    up_w, up_h = upscaled.size
    print(f"  Upscaled:    {up_w}x{up_h} (AI 4x)")

    # 3. Downscale to exactly 3840x2160 (from >4K, so quality is excellent)
    final = upscaled.resize((TARGET_W, TARGET_H), resample=Image.LANCZOS)

    # 4. Save as JPEG with sRGB
    final.save(output_path, "JPEG", quality=95, icc_profile=_srgb_icc_bytes)

    # Clean up temp file
    os.remove(tmp_path)

    return final.size


INPUT_DIR = Path(__file__).parent / "gallery"
OUTPUT_DIR = Path(__file__).parent / "gallery" / "4k"


def main():
    files = sorted(INPUT_DIR.glob("*.png"))
    if not files:
        print(f"No PNG files found in {INPUT_DIR}")
        sys.exit(1)

    output_dir = OUTPUT_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Upscaling {len(files)} image(s) to {output_dir}/\n")

    for i, f in enumerate(files):
        out_name = f.stem + ".jpg"
        out_path = str(output_dir / out_name)
        print(f"[{i+1}/{len(files)}] {f.name} -> {out_name}")
        ai_upscale_to_4k(str(f), out_path)
        print(f"  Saved:       {out_path}\n")

    print(f"Done. {len(files)} images upscaled to {output_dir}/")


if __name__ == "__main__":
    main()
