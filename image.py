from openai import OpenAI
from config import *
import base64
from PIL import Image
import os
import replicate

# This will run on Render or similar

client = OpenAI()

def upscale_to_4k(input_path, output_path):
    """
    Upscale to 3840x2160 using a 'cover + center crop' approach.

    - Preserves aspect ratio
    - Fills the whole 4K frame (no black bars)
    - Crops a bit from the edges if needed
    """
    img = Image.open(input_path).convert("RGB")

    target_w, target_h = 3840, 2160
    src_w, src_h = img.size

    # Scale so the image fully covers the 4K frame (like CSS background-size: cover)
    scale = max(target_w / src_w, target_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)

    img = img.resize((new_w, new_h), resample=Image.LANCZOS)

    # Center crop to exactly 4K
    left   = (new_w - target_w) // 2
    top    = (new_h - target_h) // 2
    right  = left + target_w
    bottom = top + target_h

    img = img.crop((left, top, right, bottom))
    img.save(output_path, quality=95)
    return img.size


def generate_image_openai(output_path, prompt, model="gpt-image-1.5"):
    # 1. Generate the image
    # Supported sizes for gpt-image-1 are: '1024x1024', '1024x1536', '1536x1024', and 'auto'.
    # Other models are dall-e versions, but gpt-image-1 is supposedly the best.
    # Update- there is a 1.5 now.
    result = client.images.generate(
        model=model,
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

    upscale_to_4k(prescale_path, output_path)


def generate_image_replicate(output_path, prompt, model="black-forest-labs/flux-2-pro"):
    # Create client at call time so the env var is definitely available
    rc = replicate.Client(api_token=os.environ["REPLICATE_API_TOKEN"])
    output = rc.run(
        model,
        input={
            "prompt": prompt,
            "width": 1536,
            "height": 1024,
            "output_format": "png",
        }
    )

    # Replicate returns FileOutput objects with a .read() method
    # Some models return a single FileOutput, others return a list
    if isinstance(output, list):
        image_bytes = output[0].read()
    else:
        image_bytes = output.read()

    prescale_path = "prescale.png"
    with open(prescale_path, "wb") as f:
        f.write(image_bytes)

    upscale_to_4k(prescale_path, output_path)


def generate_image(output_path, prompt, model="openai:gpt-image-1.5"):
    """Dispatch to the correct provider based on model prefix (openai: or replicate:)."""
    if model.startswith("replicate:"):
        replicate_model = model[len("replicate:"):]
        generate_image_replicate(output_path, prompt, model=replicate_model)
    else:
        # Default to OpenAI; strip prefix if present
        openai_model = model[len("openai:"):] if model.startswith("openai:") else model
        generate_image_openai(output_path, prompt, model=openai_model)


if __name__ == "__main__":
    prompt = "A rustic stone cottage sits prominently in the foreground, constructed from varied earthy stones that reflect a golden hue in the soft, evening light. The setting is a tranquil vineyard. In the background, a dramatic sunset paints the sky in gradients of orange, pink, and purple, casting a warm glow over the landscape. In the background is a magnificent historical winery and tasting center, with ornate lettering of 'Chateau Schmucker'. Large wine barrels are stacked outside the winery. A few kangaroos watch from the background. Workers toil in the vineyard, some drinking blue cans of beer, digging with shovels, forming very  large piles of soil. Blue beer cans are strewn about. The composition captures the charm of rural life with a blend of natural and architectural beauty, evoking a sense of nostalgia and peace. The style is realistic with vibrant, rich colors and a focus on photorealistic detail."
    generate_image("test.png", prompt)
