#!/usr/bin/env python3
"""CLI batch generator for Samsung The Frame TV art images."""

import argparse
import random
import re
from pathlib import Path

from image import generate_image
from prompts import PromptSession, generate_creative_prompt

# ── Defaults ──────────────────────────────────────────────────────────

DEFAULT_THEME = (
    "South Australian landscapes, towns, and coastal regions — including vineyards, "
    "rolling agricultural hills, historic stone farmhouses, 19th-century Lutheran churches, "
    "bluestone cottages, rugged coastlines, windswept beaches, estuaries, river gums, "
    "vineyard cellars, wildlife such as kangaroos and blue fairy wrens, cottage gardens, "
    "native flowers, olive groves, sheep paddocks, dusty backroads, outback colours, "
    "quaint main streets, markets, cafes, and winery views — all evoking a sense of place, "
    "sunlight, texture, and everyday beauty unique to regional South Australia."
)

DEFAULT_STYLES = [
    "Photo-realistic",
    "Oil painting",
    "Watercolour",
    "Impressionist",
    "Cinematic film still",
    "Pencil sketch",
    "Japanese woodblock print",
    "Vintage travel poster",
    "Soft pastel drawing",
    "Golden-hour photography",
    "Dramatic chiaroscuro",
]

DEFAULT_COMPOSITIONS = [
    "Sweeping wide landscape",
    "Intimate close-up detail",
    "Bird's-eye aerial view",
    "Low angle looking up",
    "Shallow depth of field",
    "Framed through a doorway or window",
    "Symmetrical composition",
    "Rule of thirds with strong foreground interest",
    "Panoramic ultra-wide",
    "Over-the-shoulder perspective",
]

DEFAULT_MODELS = [
    "openai:gpt-image-1.5",
    "replicate:black-forest-labs/flux-2-pro",
    "replicate:black-forest-labs/flux-schnell",
]


def next_number(output_dir: Path) -> int:
    """Find the highest existing NNN.jpg in output_dir and return NNN+1."""
    highest = 0
    for f in output_dir.glob("*.jpg"):
        m = re.match(r"^(\d+)\.jpg$", f.name)
        if m:
            highest = max(highest, int(m.group(1)))
    return highest + 1


def main():
    parser = argparse.ArgumentParser(description="Generate Samsung The Frame art images")
    parser.add_argument("--count", type=int, default=10, help="Number of images to generate (default: 10)")
    parser.add_argument("--output", type=str, default="./gallery", help="Output directory (default: ./gallery)")
    parser.add_argument("--theme", type=str, default=DEFAULT_THEME, help="Creative theme for prompt generation")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    session = PromptSession()
    num = next_number(output_dir)

    for i in range(args.count):
        style = random.choice(DEFAULT_STYLES)
        composition = random.choice(DEFAULT_COMPOSITIONS)
        model = random.choice(DEFAULT_MODELS)
        quirkiness = random.choices([0, 1, 2, 3], weights=[0, 6, 3, 1])[0]

        print(f"\n[{i+1}/{args.count}] Generating image {num:03d}.jpg")
        print(f"  Model:       {model}")
        print(f"  Style:       {style}")
        print(f"  Composition: {composition}")
        print(f"  Quirkiness:  {quirkiness}")

        prompt = generate_creative_prompt(
            theme=args.theme,
            session=session,
            quirkiness=quirkiness,
            style=style,
            composition=composition,
        )
        print(f"  Prompt:      {prompt[:120]}{'...' if len(prompt) > 120 else ''}")

        output_path = str(output_dir / f"{num:03d}.jpg")
        generate_image(output_path, prompt, model=model)
        print(f"  Saved:       {output_path}")

        num += 1

    print(f"\nDone. {args.count} images saved to {output_dir}/")


if __name__ == "__main__":
    main()
