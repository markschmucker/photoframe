from openai import OpenAI
import base64
import os
import replicate

client = OpenAI()


def generate_image_openai(output_path, prompt, model="gpt-image-1.5"):
    result = client.images.generate(
        model=model,
        prompt=prompt,
        size="1536x1024",
        n=1,
        quality="high",
    )

    image_b64 = result.data[0].b64_json
    image_bytes = base64.b64decode(image_b64)

    with open(output_path, "wb") as f:
        f.write(image_bytes)


def generate_image_replicate(output_path, prompt, model="black-forest-labs/flux-2-pro"):
    rc = replicate.Client(api_token=os.environ["REPLICATE_API_TOKEN"])

    output = rc.run(
        model,
        input={
            "prompt": prompt,
            "aspect_ratio": "3:2",
            "output_format": "png",
        },
    )

    if isinstance(output, list):
        image_bytes = output[0].read()
    else:
        image_bytes = output.read()

    with open(output_path, "wb") as f:
        f.write(image_bytes)


def generate_image(output_path, prompt, model="openai:gpt-image-1.5"):
    """Dispatch to the correct provider based on model prefix (openai: or replicate:)."""
    if model.startswith("replicate:"):
        replicate_model = model[len("replicate:"):]
        generate_image_replicate(output_path, prompt, model=replicate_model)
    else:
        openai_model = model[len("openai:"):] if model.startswith("openai:") else model
        generate_image_openai(output_path, prompt, model=openai_model)
