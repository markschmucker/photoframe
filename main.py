from datetime import datetime
from pathlib import Path
from typing import Optional, Literal

from PIL import Image
from fastapi import FastAPI, Form, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from openai import OpenAI  # NEW

from image import generate_image            # def generate_image(output_path: str, prompt: str) -> None
from ken_burns import generate_ken_burns_video  # def generate_ken_burns_video(image_path: str, video_path: str) -> None
from inspiration import generate_prompt_from_inspiration  # new helper


# ----- OpenAI client for creative prompts ----- #

oa_client = OpenAI()  # uses OPENAI_API_KEY from env

# Quirkiness is hard-coded for now- add UI later
def generate_creative_prompt(theme: str, quirkiness: int = 1) -> str:

    """
    Given a thematic description, ask the model to produce
    a rich, varied, photo-realistic scene prompt.
    """
    # Include the last N prompts to avoid repetition
    recent = "\n".join(f"- {p}" for p in state.recent_creative_prompts[-state.max_recent_prompts:])

    quirkiness_instructions = {
        0: "Keep the scene entirely realistic and grounded in real-world South Australia.",
        1: "Add a subtle creative twist or unexpectedly charming detail.",
        2: "Introduce a whimsical or imaginative element that still fits the scene.",
        3: "Allow surreal, dreamlike, or delightfully odd elements, while keeping the scene coherent."
    }

    quirk = quirkiness_instructions.get(quirkiness, quirkiness_instructions[0])

    meta = f"""
    You will generate exactly ONE imaginative, varied, photo-realistic scene description
    based on the following theme:

    "{theme}"

    Scene variety instruction:
    - {quirk}

    Rules:
    - Output only ONE prompt. No lists, no numbering.
    - Select only ONE or TWO elements from the theme, not all of them.
    - Keep it concise: 2–4 sentences max.
    - Describe a single coherent visual scene with a clear mood.
    - Do NOT repeat any recent prompts shown below.
    - Do NOT mention these instructions or the theme directly.
    - Return only the final prompt text.

    Recent prompts:
    {recent if recent else "(none yet)"}
    
    Image tweaks:
    - Do not make the image too yellow.
    """
    # ^^^ images were too yellow with gpt-image-1 but gpt-image-1.5 supposedly
    # improves on 1's warm color bias, so the tweak might not be necessary.

    resp = oa_client.chat.completions.create(
        model="gpt-4.1", # 4.1 mini seemed stupid
        messages=[
            {
                "role": "system",
                "content": "You are an imaginative prompt generator for image creation."
            },
            {
                "role": "user",
                "content": meta,
            },
        ],
        max_completion_tokens=2000,
    )

    prompt = resp.choices[0].message.content.strip()

    # Store this prompt so we don’t repeat it later
    state.recent_creative_prompts.append(prompt)

    # Trim list if too long
    if len(state.recent_creative_prompts) > state.max_recent_prompts:
        state.recent_creative_prompts = state.recent_creative_prompts[-state.max_recent_prompts:]

    return prompt


# ----- App state ----- #

class AppState:
    def __init__(self):
        # mode: "manual"       = use manual_prompt
        #       "inspiration"  = use inspiration_prompt (if set)
        #       "creative"     = auto-generate varied prompts from theme_prompt
        self.mode: Literal["manual", "inspiration", "creative"] = "creative"

        self.manual_prompt: str = "a cat chasing a dog"

        # Theme for creative mode
        self.theme_prompt = (
            "South Australian landscapes, towns, and coastal regions — including vineyards, "
            "rolling agricultural hills, historic stone farmhouses, 19th-century Lutheran churches, "
            "bluestone cottages, rugged coastlines, windswept beaches, estuaries, river gums, "
            "vineyard cellars, wildlife such as kangaroos and blue fairy wrens, cottage gardens, "
            "native flowers, olive groves, sheep paddocks, dusty backroads, outback colours, "
            "quaint main streets, markets, cafés, and winery views — all evoking a sense of place, "
            "sunlight, texture, and everyday beauty unique to regional South Australia."
        )

        self.creative_prompt: Optional[str] = None
        self.last_prompt_generated_at: Optional[datetime] = None
        self.recent_creative_prompts: list[str] = []
        self.max_recent_prompts: int = 20  # keep last 20, or whatever

        self.inspiration_image_path: Optional[str] = None
        self.inspiration_prompt: Optional[str] = None

        self.refresh_seconds: int = 300  # fast for dev; maybe 600 in prod

        self.last_image_generated_at: Optional[datetime] = None
        self.last_video_generated_at: Optional[datetime] = None


state = AppState()


def current_prompt() -> str:
    """Return the active prompt depending on mode."""
    if state.mode == "inspiration" and state.inspiration_prompt:
        return state.inspiration_prompt
    if state.mode == "creative" and state.creative_prompt:
        return state.creative_prompt
    # Fallback: manual
    return state.manual_prompt


# ----- Paths & constants ----- #

IMAGES_DIR = Path("images")
VIDEOS_DIR = Path("videos")
INSPIRATION_DIR = Path("inspiration")

IMAGES_DIR.mkdir(exist_ok=True)
VIDEOS_DIR.mkdir(exist_ok=True)
INSPIRATION_DIR.mkdir(exist_ok=True)

IMAGE_FILE = IMAGES_DIR / "current.png"
VIDEO_FILE = VIDEOS_DIR / "current.mp4"

IMAGE_URL = "/images/current.png"
VIDEO_URL = "/videos/current.mp4"


# ----- FastAPI setup ----- #

app = FastAPI()

# Serve static files
app.mount("/images", StaticFiles(directory=str(IMAGES_DIR)), name="images")
app.mount("/videos", StaticFiles(directory=str(VIDEOS_DIR)), name="videos")
app.mount("/inspiration", StaticFiles(directory=str(INSPIRATION_DIR)), name="inspiration")


# ----- HTML UI ----- #

@app.get("/", response_class=HTMLResponse)
async def index():
    mode_manual_checked = "checked" if state.mode == "manual" else ""
    mode_insp_checked = "checked" if state.mode == "inspiration" else ""
    mode_creative_checked = "checked" if state.mode == "creative" else ""

    # Inspiration section
    insp_info = ""
    has_any_inspiration = state.inspiration_prompt or state.inspiration_image_path

    if has_any_inspiration:
        preview_rel = getattr(state, "inspiration_preview_path", None)

        img_html = (
            f'<img src="{preview_rel}" style="max-width:100%; margin-top:0.5rem;">'
            if preview_rel
            else "<p><em>(No preview available for this format)</em></p>"
        )

        insp_info = f"""
        <h2>Inspiration</h2>
        <p><strong>Prompt from inspiration:</strong><br>
        <code>{state.inspiration_prompt or "(none yet)"}</code></p>
        {img_html}
        """

    return f"""
    <html>
      <head>
        <title>Photo Frame</title>
        <style>
          body {{ font-family: sans-serif; max-width: 900px; margin: 2rem auto; }}
          label {{ display:block; margin-top: 1rem; }}
          textarea {{ width: 100%; height: 6rem; }}
          fieldset {{ margin-top: 1.5rem; }}
          code {{ white-space: pre-wrap; }}
        </style>
      </head>
      <body>
        <h1>Photo Frame Control</h1>

        <form method="post" action="/set-prompt">
          <fieldset>
            <legend>Mode</legend>
            <label>
              <input type="radio" name="mode" value="manual" {mode_manual_checked}>
              Manual prompt
            </label>
            <label>
              <input type="radio" name="mode" value="inspiration" {mode_insp_checked}>
              Use prompt from inspiration image (if available)
            </label>
            <label>
              <input type="radio" name="mode" value="creative" {mode_creative_checked}>
              Creative theme (auto-generated varied prompts)
            </label>
          </fieldset>

          <label>Manual prompt:
            <textarea name="prompt">{state.manual_prompt}</textarea>
          </label>

          <label>Creative theme (used when mode = Creative):
            <textarea name="theme_prompt">{state.theme_prompt}</textarea>
          </label>

          <label>Refresh interval (seconds):
            <input type="number" name="refresh_seconds" value="{state.refresh_seconds}" min="60" step="60">
          </label>

          <button type="submit" style="margin-top:1rem;">Save</button>
        </form>

        <fieldset>
          <legend>Upload inspiration image</legend>
          <form method="post" action="/upload-inspiration" enctype="multipart/form-data">
            <label>Choose image:
              <input type="file" name="file" accept="image/*">
            </label>
            <button type="submit" style="margin-top:0.5rem;">Upload & generate prompt</button>
          </form>
        </fieldset>

        {insp_info}

        <p style="margin-top:2rem;">
          <strong>Active prompt (last used):</strong><br>
          <code>{current_prompt()}</code>
        </p>

        <p>
          API endpoints:<br/>
          <code>GET /api/prompt</code><br/>
          <code>POST /api/prompt</code><br/>
          <code>GET /api/next?mode=image|video</code><br/>
          <code>POST /upload-inspiration</code>
        </p>
      </body>
    </html>
    """


@app.post("/set-prompt", response_class=HTMLResponse)
async def set_prompt_form(
    prompt: str = Form(...),
    theme_prompt: str = Form(""),
    refresh_seconds: int = Form(600),
    mode: str = Form("manual"),
):
    # Update state
    if prompt.strip():
        state.manual_prompt = prompt.strip()

    if theme_prompt.strip():
        state.theme_prompt = theme_prompt.strip()

    state.refresh_seconds = max(int(refresh_seconds), 60)

    if mode == "inspiration":
        state.mode = "inspiration"
    elif mode == "creative":
        state.mode = "creative"
        # force new creative prompt next time
        state.creative_prompt = None
        state.last_prompt_generated_at = None
    else:
        state.mode = "manual"

    # force regeneration on next /api/next call
    state.last_image_generated_at = None
    state.last_video_generated_at = None

    return """
    <html>
      <head>
        <meta http-equiv="refresh" content="1;url=/" />
      </head>
      <body>
        <p>Updated settings. Redirecting...</p>
      </body>
    </html>
    """


@app.post("/upload-inspiration", response_class=HTMLResponse)
async def upload_inspiration(file: UploadFile = File(...)):
    # Save the uploaded file
    filename = f"inspiration_{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}_{file.filename}"
    dest = INSPIRATION_DIR / filename

    content = await file.read()
    dest.write_bytes(content)

    # Create JPEG preview if needed
    preview_rel = None
    suffix = dest.suffix.lower()
    if suffix in [".heic", ".heif"]:
        try:
            img = Image.open(dest).convert("RGB")
            preview_name = filename + ".jpg"
            preview_path = INSPIRATION_DIR / preview_name
            img.save(preview_path, "JPEG", quality=95)
            preview_rel = f"/inspiration/{preview_name}"
        except Exception:
            preview_rel = None  # fallback to no preview
    else:
        preview_rel = f"/inspiration/{filename}"

    # Generate prompt from the image (original HEIC/whatever)
    try:
        prompt = generate_prompt_from_inspiration(str(dest))
        state.inspiration_image_path = str(dest)
        state.inspiration_prompt = prompt
        state.mode = "inspiration"
        state.last_image_generated_at = None
        state.last_video_generated_at = None
        message = "Inspiration prompt generated successfully."
    except Exception as e:
        message = f"Error generating prompt from inspiration: {e}"

    # store preview path if available
    state.inspiration_preview_path = preview_rel

    return """
      <html>
        <head><meta http-equiv="refresh" content="1;url=/" /></head>
        <body><p>{}</p></body>
      </html>
    """.format(message)


# ----- JSON API ----- #

class PromptIn(BaseModel):
    prompt: str
    mode: Optional[Literal["manual", "inspiration", "creative"]] = None
    refresh_seconds: Optional[int] = None
    theme_prompt: Optional[str] = None


@app.get("/api/prompt")
async def get_prompt():
    return {
        "mode": state.mode,
        "manual_prompt": state.manual_prompt,
        "inspiration_prompt": state.inspiration_prompt,
        "theme_prompt": state.theme_prompt,
        "creative_prompt": state.creative_prompt,
        "refresh_seconds": state.refresh_seconds,
        "active_prompt": current_prompt(),
    }


@app.post("/api/prompt")
async def set_prompt(body: PromptIn):
    if body.prompt:
        state.manual_prompt = body.prompt.strip()

    if body.theme_prompt:
        state.theme_prompt = body.theme_prompt.strip()

    if body.refresh_seconds is not None:
        state.refresh_seconds = max(int(body.refresh_seconds), 60)

    if body.mode is not None:
        state.mode = body.mode
        if body.mode == "creative":
            state.creative_prompt = None
            state.last_prompt_generated_at = None

    state.last_image_generated_at = None
    state.last_video_generated_at = None

    return {
        "ok": True,
        "mode": state.mode,
        "manual_prompt": state.manual_prompt,
        "inspiration_prompt": state.inspiration_prompt,
        "theme_prompt": state.theme_prompt,
        "creative_prompt": state.creative_prompt,
        "refresh_seconds": state.refresh_seconds,
        "active_prompt": current_prompt(),
    }


@app.get("/api/next")
async def get_next_asset(mode: Literal["image", "video"] = "image"):
    """
    Called by the Pi every N seconds.
    - Only generates a new image/video if refresh_seconds has elapsed.
    - Otherwise returns the existing current.png/current.mp4 URLs.
    """
    now = datetime.utcnow()

    # Decide if we need a new image
    need_new_image = (
        state.last_image_generated_at is None
        or (now - state.last_image_generated_at).total_seconds() > state.refresh_seconds
    )

    if need_new_image:
        # If in creative mode, generate a fresh prompt from the theme
        if state.mode == "creative":
            state.creative_prompt = generate_creative_prompt(state.theme_prompt)
            state.last_prompt_generated_at = now

        # Generate a new image for the active prompt
        prompt = current_prompt()
        generate_image(str(IMAGE_FILE), prompt)
        state.last_image_generated_at = now

        # Invalidate video so it's recreated on next video request
        state.last_video_generated_at = None

    image_url = IMAGE_URL

    video_url: Optional[str] = None
    if mode == "video":
        # Generate video if none exists or if it predates the current image
        need_new_video = (
            state.last_video_generated_at is None
            or state.last_image_generated_at is None
            or state.last_video_generated_at < state.last_image_generated_at
        )
        if need_new_video:
            generate_ken_burns_video(str(IMAGE_FILE), str(VIDEO_FILE))
            state.last_video_generated_at = datetime.utcnow()

        video_url = VIDEO_URL

    return {
        "mode": state.mode,
        "prompt_used": current_prompt(),
        "generated_image_at": state.last_image_generated_at,
        "generated_video_at": state.last_video_generated_at if mode == "video" else None,
        "image_url": image_url,
        "video_url": video_url,
    }


@app.get("/display", response_class=HTMLResponse)
async def display_viewer():
    # Simple fullscreen viewer that polls /api/next?mode=video
    # and shows either a video (if available) or the image.
    return """
    <html>
      <head>
        <title>Photo Frame Display</title>
        <style>
          html, body {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            background: #000;
            overflow: hidden;
          }
          #container {
            position: fixed;
            inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #000;
          }
          img, video {
            max-width: 100vw;
            max-height: 100vh;
            width: 100vw;
            height: 100vh;
            object-fit: cover;
            background: #000;
          }
        </style>
      </head>
      <body>
        <div id="container">
          <img id="image" src="" style="display:none;" />
          <video id="video" src="" style="display:none;" autoplay muted loop playsinline></video>
        </div>

        <script>
          const apiUrl = "/api/next?mode=video";
          const origin = window.location.origin;

          const imgEl = document.getElementById("image");
          const vidEl = document.getElementById("video");

          let lastImageStamp = null;
          let lastVideoStamp = null;

          async function fetchNext() {
            try {
              const res = await fetch(apiUrl, { cache: "no-store" });
              if (!res.ok) {
                console.error("API error", res.status);
                return;
              }
              const data = await res.json();

              // Absolute URLs
              const imageUrl = data.image_url ? origin + data.image_url : null;
              const videoUrl = data.video_url ? origin + data.video_url : null;

              const imageStamp = data.generated_image_at || null;
              const videoStamp = data.generated_video_at || null;

              // Prefer video if available
              if (videoUrl) {
                // Only reload video if the timestamp changed
                if (videoStamp && videoStamp !== lastVideoStamp) {
                  lastVideoStamp = videoStamp;
                  vidEl.src = videoUrl + "?t=" + Date.now();  // bust cache
                  vidEl.load();
                }
                vidEl.style.display = "block";
                imgEl.style.display = "none";
              } else if (imageUrl) {
                // Only reload image if the timestamp changed
                if (imageStamp && imageStamp !== lastImageStamp) {
                  lastImageStamp = imageStamp;
                  imgEl.src = imageUrl + "?t=" + Date.now();  // bust cache
                }
                imgEl.style.display = "block";
                vidEl.style.display = "none";
              }
            } catch (e) {
              console.error("Error fetching next asset", e);
            }
          }

          // Initial fetch
          fetchNext();

          // Poll periodically (can be shorter than refresh_seconds)
          setInterval(fetchNext, 60 * 1000); // every 60 seconds
        </script>

      </body>
    </html>
    """


# ----- Run with: python main.py ----- #

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
