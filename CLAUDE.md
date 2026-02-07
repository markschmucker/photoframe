# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered digital photo frame that generates images via OpenAI APIs and displays them with Ken Burns video effects. Designed to run on a Raspberry Pi connected to a display, with a web-based control panel.

## Running the Application

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=<your-key>
python main.py
```

Starts a FastAPI server on `0.0.0.0:8000` with auto-reload. No build step required.

There is no test suite, linter config, or CI pipeline.

## Architecture

**Single-process FastAPI app with in-memory state (no database).**

### Source Files

- **main.py** — FastAPI app, all routes, HTML UI, `AppState` singleton, creative prompt generation via GPT-4.1
- **image.py** — OpenAI `gpt-image-1.5` image generation (1536x1024), upscaling to 4K with Pillow LANCZOS
- **ken_burns.py** — Generates Ken Burns effect MP4 videos from a still image using OpenCV and imageio/ffmpeg
- **inspiration.py** — Uses GPT-4o vision API to analyze uploaded reference images and produce generation prompts
- **config.py** — Empty placeholder

### Three Operational Modes

1. **Manual** — User-provided static prompt
2. **Inspiration** — Vision API analyzes an uploaded reference image to generate a prompt
3. **Creative** — GPT-4.1 auto-generates varied prompts from a theme, tracking last 20 prompts to avoid repetition

### Key Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /` | HTML control panel |
| `GET /display` | Fullscreen viewer for the Pi (polls every 60s) |
| `GET /api/next?mode=image\|video` | Main polling endpoint — generates assets if refresh interval elapsed |
| `GET /api/prompt` / `POST /api/prompt` | JSON config API |
| `POST /upload-inspiration` | Upload reference image for inspiration mode |

### Asset Pipeline

1. Image generated at 1536x1024, upscaled to 4K (3840x2160) via center-crop
2. Saved as `images/current.png`
3. If video mode requested, Ken Burns effect applied (12-18s, 30fps) → `videos/current.mp4`
4. Video invalidated whenever a new image is generated

### State Management

`AppState` is a plain Python class instantiated as a module-level singleton. All state is in-memory and lost on restart. Refresh timing uses `datetime.utcnow()` comparisons.

## Dependencies

OpenAI API (`openai`), FastAPI + Uvicorn, Pillow (with HEIF support), OpenCV, NumPy, imageio with ffmpeg.
