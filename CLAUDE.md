# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered art generator for Samsung The Frame TV. Generates images via OpenAI and Replicate APIs, outputting Samsung-compliant 4K JPEG files with sRGB profiles. Images are copied to a USB drive for Art Mode playback.

## Running the Application

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=<your-key>
export REPLICATE_API_TOKEN=<your-token>
python generate.py --count 10 --output ./gallery
```

No server, no build step. CLI batch generator only.

There is no test suite, linter config, or CI pipeline.

## Architecture

**CLI batch generator — no server, no database, no persistent state.**

### Source Files

- **generate.py** — CLI entry point. Parses args, loops N times generating creative prompts + images, saves numbered JPEGs.
- **prompts.py** — Creative prompt generation via GPT-4.1. `PromptSession` tracks recent prompts/subjects to avoid repetition. Decoupled from any app framework.
- **image.py** — Image generation via OpenAI (`gpt-image-1.5`) or Replicate (Flux models). Upscales to 4K (3840x2160) with center-crop, saves as JPEG with embedded sRGB ICC profile.
- **inspiration.py** — Uses GPT-4o vision API to analyze reference images and produce generation prompts (available for future use).

### Samsung The Frame Compliance

- **Resolution**: 3840 x 2160 (4K)
- **Format**: JPEG
- **Color space**: sRGB (ICC profile embedded)
- **Aspect ratio**: 16:9

### CLI Arguments

| Argument | Default | Description |
|---|---|---|
| `--count N` | 10 | Number of images to generate |
| `--output DIR` | `./gallery` | Output directory |
| `--theme TEXT` | South Australia theme | Creative theme for prompt generation |

### Image Pipeline

1. Creative prompt generated via GPT-4.1 (random style, composition, quirkiness)
2. Image generated at 1536x1024 via OpenAI or Replicate
3. Upscaled to 3840x2160 via Pillow LANCZOS center-crop
4. Saved as `NNN.jpg` with sRGB ICC profile

### Output Numbering

Files are saved as `001.jpg`, `002.jpg`, etc. The script detects the highest existing number in the output directory and continues from there.

## Dependencies

OpenAI API (`openai`), Replicate (`replicate`), Pillow (with HEIF support via `pillow-heif`), NumPy.
