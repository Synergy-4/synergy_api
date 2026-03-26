import asyncio
import io
import hashlib
from functools import lru_cache
from pocket_tts import TTSModel
import scipy.io.wavfile
import numpy as np
from pydub import AudioSegment
from app.core.config import settings
from app.core.storage import audio_storage
from app.core.redis import redis_client
import logging

logger = logging.getLogger(__name__)

# ── Synergy's two voices ───────────────────────────────────────────────
# Child voice: warm, friendly, conversational female
# Parent voice: calm, slightly slower, encouraging
CHILD_VOICE  = "kid.WAV"
PARENT_VOICE = "kid.WAV"

class TTSService:
    """Singleton. Loaded once at app startup, held in memory."""

    def __init__(self):
        self._model = None
        self._voices = {}
        self._lock = asyncio.Lock()

    async def startup(self):
        """Called once in FastAPI lifespan. Slow — runs in thread pool."""
        logger.info("Loading Pocket TTS model...")
        loop = asyncio.get_event_loop()

        # Load model in thread pool — blocks ~5s on first run
        self._model = await loop.run_in_executor(
            None, TTSModel.load_model
        )

        # Pre-load both voice states — slow once, free every time after
        self._voices["child"]  = await loop.run_in_executor(
            None, self._model.get_state_for_audio_prompt, CHILD_VOICE
        )
        self._voices["parent"] = await loop.run_in_executor(
            None, self._model.get_state_for_audio_prompt, PARENT_VOICE
        )
        logger.info("Pocket TTS ready. Both voice states loaded.")

    async def generate_audio_url(self, text: str, voice: str = "child") -> str:
        """
        Main entry point. Returns a CDN URL for the audio of `text`.
        Checks Redis cache first — only calls TTS on cache miss.
        """
        # 1. Compute deterministic cache key
        cache_key = f"tts:{hashlib.sha256(f'{text}:{voice}'.encode()).hexdigest()}"

        # 2. Redis cache hit → return immediately
        cached_url = await redis_client.get(cache_key)
        if cached_url:
            return cached_url.decode() if isinstance(cached_url, bytes) else cached_url

        # 3. Storage backend hit check
        file_hash = cache_key[4:]   # strip "tts:" prefix
        file_path = f"{file_hash[:2]}/{file_hash}.mp3" # no "audio/" prefix
        
        if await audio_storage.exists(file_path):
            base = settings.AUDIO_LOCAL_BASE_URL if settings.AUDIO_STORAGE_BACKEND == "local" else settings.R2_PUBLIC_URL
            url = f"{base.rstrip('/')}/audio/{file_path}"
            await redis_client.setex(cache_key, 2592000, url)
            return url

        # 4. Generate audio (run sync model in thread pool)
        async with self._lock:   # prevent concurrent TTS on same CPU
            loop = asyncio.get_event_loop()
            audio_tensor = await loop.run_in_executor(
                None,
                self._model.generate_audio,
                self._voices[voice],
                text
            )

        # 5. Convert torch tensor → WAV bytes → MP3 bytes
        mp3_bytes = await loop.run_in_executor(
            None, self._tensor_to_mp3, audio_tensor
        )

        # 6. Upload to backend
        url = await audio_storage.upload(mp3_bytes, file_path, content_type="audio/mpeg")

        # 7. Cache the URL in Redis for 30 days
        await redis_client.setex(cache_key, 2592000, url)

        return url

    def _tensor_to_mp3(self, audio_tensor) -> bytes:
        """Convert 1D torch tensor to MP3 bytes via WAV intermediate."""
        # Write WAV to in-memory buffer
        wav_buffer = io.BytesIO()
        scipy.io.wavfile.write(
            wav_buffer,
            self._model.sample_rate,
            audio_tensor.numpy()
        )
        wav_buffer.seek(0)

        # Convert WAV → MP3 at 128kbps (speech quality, small file)
        segment = AudioSegment.from_wav(wav_buffer)
        mp3_buffer = io.BytesIO()
        segment.export(mp3_buffer, format="mp3", bitrate="128k")
        return mp3_buffer.getvalue()


# Module-level singleton — imported everywhere
tts_service = TTSService()
