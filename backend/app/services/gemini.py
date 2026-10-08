import logging
import os
from typing import Optional
from app.config import GEMINI_API_KEY

logger = logging.getLogger("gemini")

# Priority model list for Gemini API compatibility
GEMINI_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.8-flash",
]

def get_deterministic_fallback(
    from_hospital: str,
    to_hospital: str,
    quantity: int,
    destination_shortage_hours: Optional[float] = None,
    source_safe_surplus: Optional[int] = None,
    dispatch_deadline_minutes: Optional[int] = 45,
) -> str:
    """
    Deterministic operational explanation required by prompt specification.
    Guarantees demo reliability under missing API key, timeout, or network issues.
    """
    return (
        f"Move {quantity} cylinders from {from_hospital} to {to_hospital} "
        f"because {to_hospital} reaches safety threshold first while "
        f"{from_hospital} retains safe surplus."
    )

def generate_recommendation_explanation(
    from_hospital: str,
    to_hospital: str,
    quantity: int,
    destination_shortage_hours: Optional[float] = None,
    source_safe_surplus: Optional[int] = None,
    dispatch_deadline_minutes: Optional[int] = 45,
    force_fallback: bool = False,
) -> str:
    """
    Calls Gemini API to generate ONE concise operational justification (<= 25 words).
    NON-NEGOTIABLE RULE: Gemini NEVER determines transfer parameters;
    it solely receives an already-computed deterministic recommendation and produces an explanation.
    Falls back gracefully on any failure, timeout, or missing key.
    """
    fallback = get_deterministic_fallback(
        from_hospital,
        to_hospital,
        quantity,
        destination_shortage_hours,
        source_safe_surplus,
        dispatch_deadline_minutes,
    )

    api_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "").strip()

    if force_fallback or not api_key:
        if not force_fallback:
            logger.info("GEMINI_API_KEY is not set. Using deterministic fallback explanation.")
        return fallback

    prompt = (
        f"You are an emergency operations coordinator for hospital oxygen rebalancing.\n"
        f"Explain in 15 to 25 words why transferring {quantity} oxygen cylinders from "
        f"{from_hospital} to {to_hospital} prevents an imminent shortage at {to_hospital} "
        f"while {from_hospital} safely retains its required surplus reserve."
    )

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        for model_name in GEMINI_MODELS:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        max_output_tokens=250,
                    )
                )

                if response and response.text:
                    cleaned = response.text.strip().replace("\n", " ").strip('"\'')
                    words = cleaned.split()
                    # Ensure explanation is meaningful (at least 6 words)
                    if len(words) >= 6:
                        if len(words) > 30:
                            cleaned = " ".join(words[:25]) + "..."
                        logger.info(f"Gemini explanation generated successfully via {model_name}: '{cleaned}'")
                        return cleaned
                    else:
                        logger.warning(f"Gemini returned unusually short text ('{cleaned}'). Trying next model...")
            except Exception as model_err:
                logger.warning(f"Gemini model {model_name} invocation failed: {model_err}. Trying fallback...")
                continue

        logger.warning("All Gemini model attempts failed. Returning deterministic fallback.")
        return fallback

    except Exception as exc:
        logger.warning(f"Gemini client invocation failed ({exc}). Using deterministic fallback.")
        return fallback
