#!/usr/bin/env python3
"""CLI batch generator for Samsung The Frame TV art images."""

import argparse
import json
import random
import re
from pathlib import Path

from image import generate_image
from prompts import PromptSession, generate_creative_prompt

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict:
    """Load config.json from the script directory."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    with open(CONFIG_PATH) as f:
        return json.load(f)


def next_number(output_dir: Path) -> int:
    """Find the highest existing NNN.jpg in output_dir and return NNN+1."""
    highest = 0
    for f in output_dir.glob("*.jpg"):
        m = re.match(r"^(\d+)\.jpg$", f.name)
        if m:
            highest = max(highest, int(m.group(1)))
    return highest + 1


def main():
    config = load_config()

    parser = argparse.ArgumentParser(description="Generate Samsung The Frame art images")
    parser.add_argument("--count", type=int, default=None, help=f"Number of images to generate (default: {config.get('count', 10)})")
    parser.add_argument("--output", type=str, default=None, help=f"Output directory (default: {config.get('output', './gallery')})")
    parser.add_argument("--theme", type=str, default=None, help="Creative theme for prompt generation")
    args = parser.parse_args()

    # CLI args override config
    count = args.count if args.count is not None else config.get("count", 10)
    output = args.output if args.output is not None else config.get("output", "./gallery")
    theme = args.theme if args.theme is not None else config["theme"]
    styles = config["styles"]
    compositions = config["compositions"]
    models = config["models"]

    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    session = PromptSession()
    num = next_number(output_dir)

    for i in range(count):
        style = random.choice(styles)
        composition = random.choice(compositions)
        model = random.choice(models)
        quirkiness = random.choices([0, 1, 2, 3], weights=[0, 6, 3, 1])[0]

        print(f"\n[{i+1}/{count}] Generating image {num:03d}.jpg")
        print(f"  Model:       {model}")
        print(f"  Style:       {style}")
        print(f"  Composition: {composition}")
        print(f"  Quirkiness:  {quirkiness}")

        prompt = generate_creative_prompt(
            theme=theme,
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

    print(f"\nDone. {count} images saved to {output_dir}/")


if __name__ == "__main__":
    main()
