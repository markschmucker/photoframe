import random

from openai import OpenAI

oa_client = OpenAI()  # uses OPENAI_API_KEY from env


class PromptSession:
    """Tracks recent prompts and subjects within a generation session to avoid repetition."""

    def __init__(self, max_recent: int = 20):
        self.max_recent = max_recent
        self.recent_prompts: list[str] = []
        self.recent_subjects: list[str] = []

    def record(self, prompt: str, subjects: list[str]) -> None:
        self.recent_prompts.append(prompt)
        if len(self.recent_prompts) > self.max_recent:
            self.recent_prompts = self.recent_prompts[-self.max_recent:]

        self.recent_subjects.extend(subjects)
        if len(self.recent_subjects) > self.max_recent * 3:
            self.recent_subjects = self.recent_subjects[-(self.max_recent * 3):]


def generate_creative_prompt(
    theme: str,
    session: PromptSession,
    quirkiness: int = 1,
    style: str = "",
    composition: str = "",
) -> str:
    """
    Given a thematic description, ask GPT-4.1 to produce a rich, varied scene prompt.
    Tracks recent prompts/subjects via the session to avoid repetition.
    """
    recent = "\n".join(f"- {p}" for p in session.recent_prompts[-session.max_recent:])

    quirkiness_instructions = {
        0: "Keep the scene entirely realistic and grounded in real-world South Australia.",
        1: "Add a subtle creative twist or unexpectedly charming detail.",
        2: "Introduce a whimsical or imaginative element that still fits the scene.",
        3: "Allow surreal, dreamlike, or delightfully odd elements, while keeping the scene coherent.",
    }

    quirk = quirkiness_instructions.get(quirkiness, quirkiness_instructions[0])

    style_instruction = (
        f'- The image MUST be rendered in this artistic style: "{style}". '
        f"Incorporate the visual qualities of this style into the scene description."
        if style
        else "- Use a photo-realistic style."
    )

    composition_instruction = (
        f'- Use this composition/camera angle: "{composition}".' if composition else ""
    )

    recent_subjects = ", ".join(session.recent_subjects[-session.max_recent:])

    meta = f"""
    You will generate exactly ONE imaginative, varied scene description
    based on the following theme:

    "{theme}"

    Scene variety instruction:
    - {quirk}

    Rules:
    - Output only ONE prompt. No lists, no numbering.
    - Select only ONE or TWO elements from the theme, not all of them.
    - Keep it concise: 2-4 sentences max.
    - Describe a single coherent visual scene with a clear mood.
    {style_instruction}
    {composition_instruction}
    - Do NOT repeat any recent prompts shown below.
    - Do NOT feature any of these recently used subjects: {recent_subjects if recent_subjects else "(none yet)"}. Pick something DIFFERENT from the theme.
    - Do NOT mention these instructions or the theme directly.
    - On the LAST line, write "Subjects:" followed by a comma-separated list of the 1-3 main subjects/elements you chose (e.g. "Subjects: vineyard, stone farmhouse"). This line will be stripped and used for tracking.

    Recent prompts:
    {recent if recent else "(none yet)"}
    """

    resp = oa_client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "system",
                "content": "You are an imaginative prompt generator for image creation.",
            },
            {"role": "user", "content": meta},
        ],
        max_completion_tokens=2000,
    )

    raw = resp.choices[0].message.content.strip()

    # Extract and track subjects from the last line
    lines = raw.split("\n")
    prompt = raw
    subjects = []
    if lines[-1].lower().startswith("subjects:"):
        subjects_line = lines[-1].split(":", 1)[1].strip()
        subjects = [s.strip().lower() for s in subjects_line.split(",") if s.strip()]
        prompt = "\n".join(lines[:-1]).strip()

    session.record(prompt, subjects)
    return prompt
