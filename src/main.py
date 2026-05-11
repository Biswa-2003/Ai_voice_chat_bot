import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

# ------------------------------------------------------------------
# Register all LiveKit plugins on the main thread at import time.
# LiveKit agents forks a subprocess per job; plugins must already be
# registered before the fork happens or they raise RuntimeError.
# ------------------------------------------------------------------
from livekit.plugins import openai, deepgram, elevenlabs, silero  # noqa: F401

# ------------------------------------------------------------------
# Logging — structured output with timestamp, level, and logger name
# ------------------------------------------------------------------
_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=_LOG_LEVEL,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("voicebot")

# ------------------------------------------------------------------
# Validate required environment variables before starting
# ------------------------------------------------------------------
_REQUIRED_VARS = [
    "LIVEKIT_URL",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "OPENAI_API_KEY",
    "DEEPGRAM_API_KEY",
    "ELEVEN_API_KEY",
]


def _check_env() -> None:
    missing = [v for v in _REQUIRED_VARS if not os.getenv(v)]
    if missing:
        logger.warning(
            "Missing environment variables: %s  — agent may fail at runtime",
            ", ".join(missing),
        )


_check_env()

# ------------------------------------------------------------------
# LiveKit entry point
# ------------------------------------------------------------------
from livekit.agents import WorkerOptions, cli, JobContext  # noqa: E402
from src.livekit_manager import run_voice_agent             # noqa: E402


async def entrypoint(ctx: JobContext) -> None:
    scenario = os.getenv("SCENARIO", "presale")
    logger.info("Starting voicebot | scenario=%s | room=%s", scenario, ctx.room.name)
    await run_voice_agent(ctx, scenario)


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name=os.getenv("LIVEKIT_AGENT_NAME", "voicebot"),
            port=int(os.getenv("LIVEKIT_AGENT_PORT", "0")),
        )
    )
