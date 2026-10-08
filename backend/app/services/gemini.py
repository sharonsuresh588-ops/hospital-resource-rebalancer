import logging
import os
from typing import Optional, Dict, Any
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
                    if len(words) >= 6:
                        if len(words) > 30:
                            cleaned = " ".join(words[:25]) + "..."
                        logger.info(f"Gemini explanation generated successfully via {model_name}: '{cleaned}'")
                        return cleaned
                    else:
                        logger.warning(f"Gemini returned short text ('{cleaned}'). Trying next model...")
            except Exception as model_err:
                logger.warning(f"Gemini model {model_name} invocation failed: {model_err}. Trying fallback...")
                continue

        logger.warning("All Gemini model attempts failed. Returning deterministic fallback.")
        return fallback

    except Exception as exc:
        logger.warning(f"Gemini client invocation failed ({exc}). Using deterministic fallback.")
        return fallback


def generate_copilot_brief(
    action_type: str,
    facts: Dict[str, Any],
    force_fallback: bool = False,
) -> str:
    """
    Feature 9 — Gemini Operations Copilot.
    Generates tailored operational communication briefs using strictly Python-computed facts.
    Supported action types:
      - 'brief_coordinator': 2-sentence executive dispatch brief for emergency operations chief.
      - 'explain_donor_selection': Clear explanation why chosen donor won over other hospitals.
      - 'generate_escalation': Formal regional mutual-aid emergency escalation memo.
      - 'summarize_outcome': Post-intervention outcome analysis.
    """
    # Deterministic fallback generators
    if action_type == "brief_coordinator":
        fallback = (
            f"EXECUTIVE BRIEF: {facts.get('recipient_name', 'Hospital A')} is facing oxygen depletion within "
            f"{facts.get('time_to_shortage', '1.3')} hours. Deterministic optimizer recommends dispatching "
            f"{facts.get('quantity', 40)} cylinders from {facts.get('donor_name', 'Hospital B')}, which maintains "
            f"a safe surplus of {facts.get('safe_surplus', 82)} units and can deliver within {facts.get('transit_time', 25)} minutes."
        )
        prompt_instruction = "Generate a concise 2-sentence executive dispatch briefing for the Operations Chief."

    elif action_type == "explain_donor_selection":
        fallback = (
            f"DONOR SELECTION RATIONALE: {facts.get('donor_name', 'Hospital B')} was selected over other network facilities "
            f"because it achieved the highest feasibility score ({facts.get('donor_score', 1248)}). It preserves {facts.get('safe_surplus', 82)} units "
            f"of safe surplus, guarantees 4-hour forward demand protection, and transit requires only {facts.get('transit_time', 25)} minutes."
        )
        prompt_instruction = "Explain why this specific donor hospital won over other facilities based on the facts provided."

    elif action_type == "generate_escalation":
        fallback = (
            f"REGIONAL MUTUAL-AID ESCALATION: Regional inventory constraints require external stockpile intervention. "
            f"Facility {facts.get('recipient_name', 'Hospital A')} requires immediate emergency depot cylinder delivery "
            f"before the {facts.get('deadline_minutes', 45)}-minute critical shortage horizon."
        )
        prompt_instruction = "Draft a formal mutual-aid emergency escalation dispatch memo."

    elif action_type == "summarize_outcome":
        fallback = (
            f"INTERVENTION OUTCOME: Approved transfer of {facts.get('quantity', 40)} cylinders averted {facts.get('prevented_hours', 5.0)} "
            f"shortage-hours. Recipient stock was stabilized above critical threshold, while donor reserves were preserved with zero secondary shortages."
        )
        prompt_instruction = "Summarize the intervention outcome and averted shortage metrics."

    else:
        fallback = "Operational status confirmed based on network deterministic metrics."
        prompt_instruction = "Summarize the current operational status."

    api_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "").strip()
    if force_fallback or not api_key:
        return fallback

    prompt = (
        f"You are an emergency operations coordinator copilot for a hospital network.\n"
        f"Task: {prompt_instruction}\n"
        f"Strictly use ONLY these deterministic operational facts:\n"
        f"{facts}\n"
        f"Style: Professional, concise, high-urgency, and matter-of-fact. Maximum 45 words."
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
                        max_output_tokens=300,
                    )
                )

                if response and response.text:
                    cleaned = response.text.strip().replace("\n", " ").strip('"\'')
                    if len(cleaned.split()) >= 8:
                        return cleaned
            except Exception:
                continue

        return fallback
    except Exception:
        return fallback
