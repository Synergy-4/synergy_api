import asyncio
import logging
from app.services.tts_service import tts_service

logger = logging.getLogger(__name__)

async def inject_audio_urls(payload: dict) -> dict:
    """
    Takes a raw Claude SDUI payload, generates all audio in parallel,
    injects URLs back into the payload. Returns the enriched payload.
    """
    # Collect all (text, voice, target_key, parent_dict) tuples
    jobs = _extract_audio_jobs(payload)

    if not jobs:
        return payload

    # Generate all audio concurrently with fallback
    urls = await asyncio.gather(*[
        _safe_generate_audio_url(text, voice)
        for text, voice, _, _ in jobs
    ])

    # Inject URLs back into the payload dict
    for (text, voice, url_key, target_dict), url in zip(jobs, urls):
        target_dict[url_key] = url

    return payload

async def _safe_generate_audio_url(text: str, voice: str) -> str | None:
    try:
        return await tts_service.generate_audio_url(text, voice)
    except Exception as e:
        logger.error(f"TTS generation failed for text '{text[:20]}...': {e}")
        return None

def _extract_audio_jobs(payload: dict) -> list:
    """Walk the payload and return all TTS generation jobs needed."""
    jobs = []
    steps = payload.get("steps", [])

    for step in steps:

        # ── intro_1 and reward_1: voiceover_text → voiceover_audio_url ──
        if step.get("voiceover_text"):
            jobs.append((
                step["voiceover_text"],
                "child",               # child voice for all on-screen text
                "voiceover_audio_url",
                step
            ))

        gc = step.get("game_config")
        if not gc: continue

        # ── parent_instruction → parent_instruction_audio_url ──
        if gc.get("parent_instruction"):
            jobs.append((
                gc["parent_instruction"],
                "parent",             # parent voice — different from child voice
                "parent_instruction_audio_url",
                gc
            ))

        data = gc.get("data", {})

        # ── instruction_audio: replace text placeholder with URL ──
        if data.get("instruction_audio"):
            jobs.append((
                data["instruction_audio"],  # currently contains the text string
                "child",
                "instruction_audio",       # overwrite same key with URL
                data
            ))

        # ── question_audio: binary_choice, scenario_choice ──
        if data.get("question_audio"):
            jobs.append((
                data["question_audio"],
                "child",
                "question_audio",
                data
            ))

        # ── scenario_audio: scenario_choice only ──
        if data.get("scenario_audio"):
            jobs.append((
                data["scenario_audio"],
                "child",
                "scenario_audio",
                data
            ))

    return jobs
