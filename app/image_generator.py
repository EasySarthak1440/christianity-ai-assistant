import os
import re

from dotenv import load_dotenv

load_dotenv()

STYLE_SUFFIX = "in the style of classical Christian art, reverent, painterly"

_DISRESPECT_JESUS = re.compile(
    r"\b(jesus|christ|messiah|savior|son of god|jesus christ)"
    r"\s+(is\s+)?(a\s+)?(fake|myth|cartoon|joke|clown|fraud|horrible|violent|"
    r"terrible|stupid|dumb|evil|hateful|criminal|sinner|failed|weak|imaginary)\b",
    re.IGNORECASE,
)

_DISRESPECT_GOD = re.compile(
    r"\b(god|yahweh|jehovah|lord|creator|almighty|holy spirit)"
    r"\s+(is\s+)?(a\s+)?(fake|myth|evil|violent|tyrant|cruel|hateful|"
    r"imaginary|stupid|dumb|dead|not real|makes no sense)\b",
    re.IGNORECASE,
)

_VIOLENT_MIX = re.compile(
    r"\b((jesus|christ|god|cross|bible|church|christian)"
    r".{0,30}(blood|gore|violence|war|weapon|gun|explosi|attack|murder|"
    r"torture|execution|beheading|killing|massacre)"
    r"|"
    r"(blood|gore|violence|war|weapon|gun|explosi|attack|murder|"
    r"torture|execution|beheading|killing|massacre)"
    r".{0,30}(jesus|christ|god|cross|bible|church|christian))\b",
    re.IGNORECASE,
)

_SEXUAL_MIX = re.compile(
    r"\b((jesus|christ|god|mary|virgin|saint|cross|bible|church)"
    r".{0,30}(naked|nudity|sexual|porn|erotic|seductive|provocative|"
    r"lust|adultery|perversion|obscene)"
    r"|"
    r"(naked|nudity|sexual|porn|erotic|seductive|provocative|"
    r"lust|adultery|perversion|obscene)"
    r".{0,30}(jesus|christ|god|mary|virgin|saint|cross|bible|church))\b",
    re.IGNORECASE,
)

_POLITICAL_MIX = re.compile(
    r"\b(jesus|christ|god|bible|christian|cross)"
    r".{0,40}((political)\s+(party|agenda|candidate|movement|ideology)|"
    r"endors|vote|democra|republica|slogan|propaganda|nazi|"
    r"communis|fascis|marxis)",
    re.IGNORECASE,
)

_BLOCKED_TOPIC_PATTERNS = [
    (_DISRESPECT_JESUS, "Disrespectful depiction of Jesus/Christ"),
    (_DISRESPECT_GOD, "Disrespectful depiction of God"),
    (_VIOLENT_MIX, "Mixing Christian imagery with violence"),
    (_SEXUAL_MIX, "Mixing Christian imagery with sexual content"),
    (_POLITICAL_MIX, "Mixing Christian imagery with political content"),
]

def validate_prompt(prompt: str) -> dict:
    for pattern, reason in _BLOCKED_TOPIC_PATTERNS:
        if pattern.search(prompt):
            return {
                "allowed": False,
                "enhanced_prompt": "",
                "reason": reason,
                "safe_response": (
                    "I'm not able to generate this image. The prompt appears to "
                    "mix Christian themes with content that could be disrespectful. "
                    "Please rephrase with a reverent Christian theme."
                ),
            }
    enhanced = f"{prompt.strip()}, {STYLE_SUFFIX}"
    return {
        "allowed": True,
        "enhanced_prompt": enhanced,
        "reason": "",
        "safe_response": "",
    }

def generate_image(prompt: str) -> dict:
    hf_token = os.getenv("HF_API_TOKEN")
    if not hf_token:
        return {
            "image_url": None,
            "available": False,
            "message": "Image generation is not available — no HF_API_TOKEN configured.",
        }
    try:
        import base64
        from io import BytesIO

        from huggingface_hub import InferenceClient

        client = InferenceClient(token=hf_token, timeout=120)
        image = client.text_to_image(
            prompt,
            model="black-forest-labs/FLUX.1-schnell",
        )
        buf = BytesIO()
        image.save(buf, format="PNG")
        data_url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
        return {"image_url": data_url, "available": True, "message": ""}
    except Exception as e:
        return {
            "image_url": None,
            "available": False,
            "message": f"Image generation failed: {str(e)}",
        }
