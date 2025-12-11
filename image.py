from openai import OpenAI
from config import *
import base64
from PIL import Image

# This will run on Render or similar

client = OpenAI()

def upscale_to_4k(input_path, output_path):
    img = Image.open(input_path).convert("RGB")

    target_w, target_h = 3840, 2160

    # Preserve aspect ratio, then letterbox or crop
    img = img.resize((target_w, target_h), resample=Image.LANCZOS)

    img.save(output_path, quality=95)
    return img.size

def generate_image(output_path, prompt):
    # 1. Generate the image
    # Supported sizes for gpt-image-1 are: '1024x1024', '1024x1536', '1536x1024', and 'auto'.
    # Other models are dall-e versions, but gpt-image-1 is supposedly the best.
    result = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1536x1024", # use the largest supported landscape size for the model
        n=1,
        quality="high"
    )

    # 2. Extract base64 data
    image_b64 = result.data[0].b64_json  # this is a base64-encoded PNG

    # 3. Decode and save to disk
    image_bytes = base64.b64decode(image_b64)

    prescale_path = "prescale.png"
    with open(prescale_path, "wb") as f:
        f.write(image_bytes)

    # To get closer to 4k resolution, must upscale. Ideally this would use torch or
    # similar, but I had trouble getting that to import, so just using bicubic for now.
    # This does not add information like torch would, but it's only about a 2:1 upscale
    # so alright for now.

    # temp
    do_scale = False
    if do_scale:
        upscale_to_4k(prescale_path, output_path)
    else:
        with open(output_path, "wb") as f:
            f.write(image_bytes)

