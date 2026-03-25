import asyncio
import logging
from app.services.tts_service import tts_service

logger = logging.getLogger(__name__)

# ── Carrier phrase builder ────────────────────────────────────────────────────

# Maps each phoneme string to the exact TTS input that produces the
# cleanest audio. Stops (b/p/t/d/k/g) get "buh"-style carrier phrases
# because TTS cannot produce a pure stop consonant in isolation.
# Continuants (m/n/s/f/sh) are held and sound fine.

_PHONEME_CARRIER: dict[str, str] = {
    # Vowels
    "a":   "The letter A makes the sound... a, a, a",
    "e":   "The letter E makes the sound... e, e, e",
    "i":   "The letter I makes the sound... i, i, i",
    "o":   "The letter O makes the sound... o, o, o",
    "u":   "The letter U makes the sound... u, u, u",

    # Consonants — stops (unavoidable schwa, say "buh" not "bee")
    "b":   "The sound is... buh... buh... buh",
    "p":   "The sound is... puh... puh... puh",
    "t":   "The sound is... tuh... tuh... tuh",
    "d":   "The sound is... duh... duh... duh",
    "k":   "The sound is... kuh... kuh... kuh",
    "g":   "The sound is... guh... guh... guh",
    "c":   "The sound is... kuh... kuh... kuh",  # C as in cat

    # Consonants — continuants (can be held cleanly)
    "m":   "The sound is... mmmm... mmmm",
    "n":   "The sound is... nnnn... nnnn",
    "f":   "The sound is... ffff... ffff",
    "v":   "The sound is... vvvv... vvvv",
    "s":   "The sound is... ssss... ssss",
    "z":   "The sound is... zzzz... zzzz",
    "l":   "The sound is... llll... llll",
    "r":   "The sound is... rrrr... rrrr",
    "h":   "The sound is... hhhh... hhhh",
    "w":   "The sound is... wwww... wwww",
    "y":   "The sound is... yyyy... yyyy",
    "j":   "The sound is... juh... juh... juh",
    "qu":  "The sound is... kwuh... kwuh... kwuh",
    "x":   "The sound is... ks... ks... ks",

    # Digraphs
    "sh":  "The letters S-H make the sound... shhhh... shhhh",
    "ch":  "The letters C-H make the sound... chuh... chuh... chuh",
    "th":  "The letters T-H make the sound... thuh... thuh... thuh",
    "wh":  "The letters W-H make the sound... wuh... wuh... wuh",
    "ph":  "The letters P-H make the sound... ffff... ffff",
    "ck":  "The letters C-K make the sound... kuh... kuh... kuh",

    # Blends — include anchor word so TTS handles the blend in context
    "bl":  "The blend B-L sounds like... bl, bl, bl — as in blue",
    "br":  "The blend B-R sounds like... br, br, br — as in bread",
    "cl":  "The blend C-L sounds like... cl, cl, cl — as in clap",
    "cr":  "The blend C-R sounds like... cr, cr, cr — as in crab",
    "dr":  "The blend D-R sounds like... dr, dr, dr — as in drum",
    "fl":  "The blend F-L sounds like... fl, fl, fl — as in flag",
    "fr":  "The blend F-R sounds like... fr, fr, fr — as in frog",
    "gl":  "The blend G-L sounds like... gl, gl, gl — as in glue",
    "gr":  "The blend G-R sounds like... gr, gr, gr — as in grass",
    "pl":  "The blend P-L sounds like... pl, pl, pl — as in plane",
    "pr":  "The blend P-R sounds like... pr, pr, pr — as in press",
    "st":  "The blend S-T sounds like... st, st, st — as in star",
    "tr":  "The blend T-R sounds like... tr, tr, tr — as in tree",
}


def _phoneme_to_tts_text(phoneme: str, stage: int, anchor_word: str | None = None) -> str:
    """
    Returns the TTS input string for a given phoneme.

    For Stage 4 CVC words and Stage 5 sight words, the phoneme IS the word —
    use a simple carrier: "The word is... {word}".

    For Stages 1–3, look up the carrier phrase map. If not found, fall back
    to a generic carrier using the anchor_word if available.
    """
    p = phoneme.lower().strip()

    # Stage 4 CVC and Stage 5 sight words — phoneme is the full word
    if stage in (4, 5):
        return f"The word is... {p}"

    # Stages 1–3 — look up carrier phrase
    if p in _PHONEME_CARRIER:
        return _PHONEME_CARRIER[p]

    # Fallback — use anchor word if available
    if anchor_word:
        return f"The sound is... {p}... {p}... {p} — as in {anchor_word}"

    return f"The sound is... {p}... {p}... {p}"


# ── Main injection entry point ────────────────────────────────────────────────

async def inject_audio_urls(payload: dict) -> dict:
    """
    Takes a raw Claude SDUI payload, generates all audio in parallel,
    injects URLs back into the payload. Returns the enriched payload.

    Jobs are collected from ALL steps and ALL game types, then dispatched
    concurrently via asyncio.gather().
    """
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

# ── Job extraction ────────────────────────────────────────────────────────────

def _extract_audio_jobs(payload: dict) -> list[tuple[str, str, str, dict]]:
    """
    Walk the payload and return all TTS generation jobs needed.

    Each job is a tuple of:
        (tts_input_text, voice_id, url_key_to_set, target_dict)
    """
    jobs: list[tuple[str, str, str, dict]] = []
    steps: list[dict] = payload.get("steps", [])

    for step in steps:

        # ── voiceover_text → voiceover_audio_url (intro + reward steps) ──────
        if step.get("voiceover_text"):
            jobs.append((
                step["voiceover_text"],
                "child",
                "voiceover_audio_url",
                step,
            ))

        gc: dict | None = step.get("game_config")
        if not gc:
            continue

        # ── parent_instruction → parent_instruction_audio_url ─────────────────
        if gc.get("parent_instruction"):
            jobs.append((
                gc["parent_instruction"],
                "parent",
                "parent_instruction_audio_url",
                gc,
            ))

        game_type: str = gc.get("game_type", "")
        data: dict = gc.get("data", {})

        # ── Route to per-game-type handler ────────────────────────────────────
        if game_type == "phonics_phonetics":
            jobs.extend(_phonics_jobs(data))

        elif game_type == "colour_matching":
            pass  # No data-level audio for colour matching

        else:
            jobs.extend(_standard_game_jobs(data))

    return jobs


# ── Standard game types (tap_to_select, drag_to_target, etc.) ────────────────

def _standard_game_jobs(data: dict) -> list[tuple[str, str, str, dict]]:
    """
    Handles all non-phonics game types.
    """
    jobs = []

    # instruction_audio
    if data.get("instruction_audio"):
        jobs.append((
            data["instruction_audio"],
            "child",
            "instruction_audio",
            data,
        ))

    # question_audio
    if data.get("question_audio"):
        jobs.append((
            data["question_audio"],
            "child",
            "question_audio",
            data,
        ))

    # scenario_audio
    if data.get("scenario_audio"):
        jobs.append((
            data["scenario_audio"],
            "child",
            "scenario_audio",
            data,
        ))

    return jobs


# ── Phonics game type ─────────────────────────────────────────────────────────

def _phonics_jobs(data: dict) -> list[tuple[str, str, str, dict]]:
    """
    Handles phonics_phonetics game type.
    """
    jobs = []
    stage: int = data.get("phonics_stage", 1)
    trials: list[dict] = data.get("trials", [])

    for trial in trials:
        phoneme: str = trial.get("phoneme", "")
        anchor_word: str | None = trial.get("anchor_word")

        if not phoneme:
            continue

        # ── Main phoneme audio ─────────────────────────────────────────────
        tts_text = _phoneme_to_tts_text(phoneme, stage, anchor_word)
        jobs.append((
            tts_text,
            "child",
            "phoneme_audio_url",
            trial,
        ))

        # ── CVC breakdown — individual letter phonemes (Stage 4 only) ─────
        cvc: dict | None = trial.get("cvc_breakdown")
        if cvc and isinstance(cvc, dict):
            letters: list[str] = cvc.get("letters", [])
            if letters:
                jobs.extend(_cvc_letter_jobs(cvc, letters, stage))

    return jobs


def _cvc_letter_jobs(
    cvc: dict,
    letters: list[str],
    stage: int,
) -> list[tuple[str, str, str, dict]]:
    """
    For a CVC breakdown like ["C", "A", "T"], generate one TTS job per letter.
    """
    jobs = []

    # Pre-size the list so indices are stable during async writes
    cvc["phoneme_audio_urls"] = [None] * len(letters)

    for idx, letter in enumerate(letters):
        phoneme = letter.lower()
        # Use Stage 1/2 carrier logic for individual letters within CVC
        tts_text = _phoneme_to_tts_text(phoneme, stage=1, anchor_word=None)

        # Wrap the list slot as a dict so the injection loop can set it
        slot_dict = _ListSlot(cvc["phoneme_audio_urls"], idx)

        jobs.append((tts_text, "child", "value", slot_dict))

    return jobs


class _ListSlot:
    """
    Thin adapter that lets the injection loop treat a list slot like a dict.
    inject_audio_urls does:  target_dict[url_key] = url
    We need:                 some_list[idx]       = url
    """
    def __init__(self, lst: list, idx: int):
        self._lst = lst
        self._idx = idx

    def __setitem__(self, key: str, value):
        self._lst[self._idx] = value

    def __getitem__(self, key: str):
        return self._lst[self._idx]

    def get(self, key: str, default=None):
        return self._lst[self._idx] if self._lst[self._idx] is not None else default
