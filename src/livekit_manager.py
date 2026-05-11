import asyncio
import logging
import os

from livekit.agents import AgentSession, AutoSubscribe, JobContext, llm
from livekit.agents.voice import Agent
from livekit.plugins import silero

from src.analytics import save_conversation_log
from src.conversation_manager import ConversationManager
from src.language_detector import LanguageDetector
from src.llm_processor import LLMProcessor
from src.stt_engine import get_stt_engine
from src.tts_engine import get_tts_engine

logger = logging.getLogger("livekit_manager")

_GREETINGS = {
    "en": (
        "Namaste and welcome! I'm your AI assistant. "
        "I'm here to help you today. You can speak in English or Hindi — "
        "whichever is comfortable for you."
    ),
    "hi": (
        "Namaste aur swaagat hai! Main aapka AI assistant hoon. "
        "Aap Hindi ya English mein baat kar sakte hain — "
        "jo bhi aapko comfortable lage."
    ),
}


async def run_voice_agent(ctx: JobContext, scenario: str) -> None:
    """Main voice agent entrypoint for a LiveKit room session."""
    logger.info("Connecting to room '%s' for scenario '%s'", ctx.room.name, scenario)
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info("Connected to LiveKit room")

    # -----------------------------------------------------------------
    # Initialise components
    # -----------------------------------------------------------------
    cm = ConversationManager(scenario=scenario)
    processor = LLMProcessor(scenario=scenario)
    detector = LanguageDetector()

    stt = get_stt_engine()
    tts = get_tts_engine(language="en")
    llm_engine = processor.get_engine()

    # Build initial chat context with the scenario system prompt
    initial_ctx = llm.ChatContext()
    initial_ctx.add_message(role="system", content=cm.get_system_prompt())

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=stt,
        llm=llm_engine,
        tts=tts,
        allow_interruptions=True,
    )

    agent = Agent(
        instructions=cm.get_system_prompt(),
        chat_ctx=initial_ctx,
    )

    # -----------------------------------------------------------------
    # Event: user speech transcribed
    # -----------------------------------------------------------------
    @session.on("user_input_transcribed")
    def on_user_input_transcribed(event) -> None:
        if not event.is_final:
            logger.debug("Partial transcript: %r", event.transcript)
            return

        text: str = (event.transcript or "").strip()
        if not text:
            return

        logger.info("User [%s]: %s", cm.current_language, text)

        # Detect language; check for explicit switch request
        detected_lang = detector.detect(text)
        switch_target = detector.is_switch_request(text)

        if switch_target and switch_target != cm.current_language:
            logger.info("Language switch requested: %s → %s", cm.current_language, switch_target)

        in_scope, topic = processor.check_scope_with_topic(text)
        cm.add_turn("user", text, language=detected_lang, topic=topic or "general")

        if not in_scope:
            logger.info("Scope violation detected: topic=%s", topic)
            cm.record_scope_violation(topic or "unknown")
            reply = processor.get_out_of_scope_message(detected_lang, topic)
            cm.add_turn("assistant", reply, language=detected_lang, topic="scope_redirect")
            session.say(reply, allow_interruptions=True, add_to_chat_ctx=True)
            return

        session.generate_reply(user_input=text, allow_interruptions=True)

    # -----------------------------------------------------------------
    # Event: assistant reply synthesised
    # -----------------------------------------------------------------
    @session.on("agent_speech_committed")
    def on_agent_speech_committed(event) -> None:
        text = getattr(event, "text", "") or ""
        if text:
            logger.info("Assistant [%s]: %s", cm.current_language, text)
            cm.add_turn("assistant", text, language=cm.current_language)

    # -----------------------------------------------------------------
    # Event: session error
    # -----------------------------------------------------------------
    @session.on("error")
    def on_error(event) -> None:
        logger.error("LiveKit session error: %s", event)

    # -----------------------------------------------------------------
    # Event: disconnection — save logs
    # -----------------------------------------------------------------
    @ctx.room.on("disconnected")
    def on_disconnected() -> None:
        log_dir = os.getenv("LOG_DIR", "logs")
        try:
            save_conversation_log(cm.to_context_dict(), log_dir=log_dir)
        except Exception as exc:
            logger.error("Failed to save conversation log: %s", exc)

    # -----------------------------------------------------------------
    # Start session and greet
    # -----------------------------------------------------------------
    await session.start(agent=agent, room=ctx.room)

    await asyncio.sleep(0.5)
    greeting_lang = os.getenv("DEFAULT_LANGUAGE", "en")
    greeting = _GREETINGS.get(greeting_lang, _GREETINGS["en"])
    cm.add_turn("assistant", greeting, language=greeting_lang)
    await session.say(greeting, allow_interruptions=True)
