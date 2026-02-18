# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered art generator for Samsung The Frame TV. Generates images via OpenAI and Replicate APIs. Two-step workflow: batch generate candidates, curate, then AI-upscale the keepers to Samsung-compliant 4K JPEGs for USB playback.

## Running the Application

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=<your-key>
export REPLICATE_API_TOKEN=<your-token>

# Step 1: Generate candidates at native resolution
python generate.py --count 20

# Step 2: Browse gallery/, delete the ones you don't like

# Step 3: AI-upscale survivors to 4K
python upscale.py ./gallery
```

No server, no build step. CLI tools only.

There is no test suite, linter config, or CI pipeline.

## Architecture

**Two-step CLI workflow — no server, no database, no persistent state.**

### Source Files

- **generate.py** — CLI entry point. Generates creative prompts + images at native resolution (1536x1024 PNG). Saves numbered files.
- **upscale.py** — AI-upscales selected images to 4K via Real-ESRGAN on Replicate. Crops to 16:9, upscales 4x, downscales to exactly 3840x2160, saves as JPEG with sRGB ICC profile.
- **config.json** — All tunable settings: theme, styles, compositions, models, default count/output. CLI args override these values.
- **prompts.py** — Creative prompt generation via GPT-4.1. `PromptSession` tracks recent prompts/subjects to avoid repetition.
- **image.py** — Image generation dispatch to OpenAI (`gpt-image-1.5`) or Replicate (Flux models). Saves at native resolution.
- **inspiration.py** — Uses GPT-4o vision API to analyze reference images and produce generation prompts (available for future use).

### Samsung The Frame Compliance (after upscale.py)

- **Resolution**: 3840 x 2160 (4K)
- **Format**: JPEG
- **Color space**: sRGB (ICC profile embedded)
- **Aspect ratio**: 16:9

### Image Pipeline

1. `generate.py`: Creative prompt via GPT-4.1 (random style, composition, quirkiness)
2. `generate.py`: Image generated at 1536x1024 PNG via OpenAI or Replicate
3. Hand-curate: browse `gallery/`, delete rejects
4. `upscale.py`: Crop to 16:9, Real-ESRGAN 4x upscale, downscale to 3840x2160, save as JPEG with sRGB

### Output

- `generate.py` saves `001.png`, `002.png`, etc. Continues from highest existing number.
- `upscale.py` saves `001.jpg`, `002.jpg`, etc. in a `4k/` subdirectory by default.

## Dependencies

OpenAI API (`openai`), Replicate (`replicate`), Pillow (with HEIF support via `pillow-heif`), NumPy.
