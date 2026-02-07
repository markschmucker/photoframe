import base64
from io import BytesIO
from pathlib import Path

from openai import OpenAI
from PIL import Image

client = OpenAI()  # expects OPENAI_API_KEY in env

# Optional: add HEIC/HEIF support if pillow-heif is installed
try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
    HEIC_SUPPORTED = True
except ImportError:
    HEIC_SUPPORTED = False


def _encode_image_to_base64(path: Path) -> tuple[str, str]:
    """
    Return (mime, base64_str) for the given image path.
    Converts HEIC/HEIF to JPEG in memory if pillow-heif is available.
    """
    suffix = path.suffix.lower()

    # Handle HEIC/HEIF by converting to JPEG in memory
    if suffix in [".heic", ".heif"]:
        if not HEIC_SUPPORTED:
            raise RuntimeError(
                "HEIC/HEIF file detected but pillow-heif is not installed. "
                "Run 'pip install pillow-heif' in your environment."
            )

        img = Image.open(path).convert("RGB")
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=95)
        data = buf.getvalue()
        mime = "image/jpeg"

    else:
        # For normal formats, just read raw bytes and guess mime
        if suffix in [".jpg", ".jpeg"]:
            mime = "image/jpeg"
        elif suffix in [".png"]:
            mime = "image/png"
        else:
            # default
            mime = "image/jpeg"

        with path.open("rb") as f:
            data = f.read()

    b64 = base64.b64encode(data).decode("utf-8")
    return mime, b64


def generate_prompt_from_inspiration(image_path: str) -> str:
    """
    Analyze an 'inspiration' image and return a rich, single-sentence prompt
    suitable for image generation.

    - image_path: local path to an image file (jpg/png/heic/etc.)
    - returns: text prompt

    Raises on API errors.
    """
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Inspiration image not found: {image_path}")

    mime, b64 = _encode_image_to_base64(path)
    data_url = f"data:{mime};base64,{b64}"

    resp = client.chat.completions.create(
        model="gpt-4o",  # or "gpt-4.1-mini" if you want cheaper
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a prompt writer for an AI image generator. "
                    "Given an image, write a rich, detailed prompt of 3–6 short sentences. "
                    "Describe the main subject, setting, composition (foreground / midground / background), "
                    "lighting, colors, mood, and overall style (e.g., realistic photo, oil painting, watercolor, etc.). "
                    "Use concrete, visual language and avoid generic words like 'beautiful' or 'nice'. "
                    "Do NOT mention 'photo', 'image', 'picture', 'in this image', or the act of describing. "
                    "Write it exactly as you would feed it to a text-to-image model."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Describe this image as a detailed prompt for a text-to-image model. "
                            "Be specific about subject, setting, lighting, colors, mood, and style."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url},
                    },
                ],
            },
        ],
        max_tokens=200,
    )

    prompt_text = resp.choices[0].message.content.strip()
    return prompt_text
