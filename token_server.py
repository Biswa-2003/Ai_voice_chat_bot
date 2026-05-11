"""
Token Server — FastAPI service that:
  1. Creates a LiveKit room
  2. Dispatches the voicebot agent to that room
  3. Returns a token + ready-to-use playground URL

Endpoints:
  GET  /          → health check
  GET  /connect   → returns room, token, and playground URL
  GET  /connect?scenario=sales  → use a specific scenario
"""

import os
import time
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, HTMLResponse
from livekit import api

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("token_server")

app = FastAPI(title="Voicebot Token Server")

LIVEKIT_URL        = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY    = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
AGENT_NAME         = os.getenv("LIVEKIT_AGENT_NAME", "voicebot")


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html><body style="font-family:sans-serif;padding:40px">
    <h2>AI Voicebot — Token Server</h2>
    <p>Use <a href="/connect">/connect</a> to get a room URL.</p>
    <p>Use <code>/connect?scenario=sales</code> for a specific scenario.</p>
    <p>Status: <strong style="color:green">Running</strong></p>
    </body></html>
    """


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/connect")
async def connect(
    scenario: str = Query(default=None, description="presale | sales | marketing"),
    user_name: str = Query(default="User", description="Display name for participant"),
):
    active_scenario = scenario or os.getenv("SCENARIO", "presale")
    room_name = f"voicebot-{int(time.time())}"

    try:
        lkapi = api.LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)

        # Create room
        await lkapi.room.create_room(api.CreateRoomRequest(name=room_name))
        logger.info("Room created: %s", room_name)

        # Dispatch agent
        await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=AGENT_NAME,
                room=room_name,
                metadata=active_scenario,
            )
        )
        logger.info("Agent dispatched to room: %s (scenario: %s)", room_name, active_scenario)

        # Generate participant token
        token = (
            api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
            .with_identity(f"user-{int(time.time())}")
            .with_name(user_name)
            .with_grants(api.VideoGrants(room_join=True, room=room_name))
            .to_jwt()
        )

        await lkapi.aclose()

        playground_url = (
            f"https://agents-playground.livekit.io/"
            f"?liveKitUrl={LIVEKIT_URL}&token={token}"
        )

        return JSONResponse({
            "room": room_name,
            "scenario": active_scenario,
            "livekit_url": LIVEKIT_URL,
            "token": token,
            "playground_url": playground_url,
            "message": "Open playground_url in your browser to start talking to the bot."
        })

    except Exception as e:
        logger.error("Failed to create session: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("TOKEN_SERVER_PORT", "8000"))
    uvicorn.run("token_server:app", host="0.0.0.0", port=port, reload=False)
