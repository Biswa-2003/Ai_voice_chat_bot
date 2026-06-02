"""
Main server — FastAPI app that serves the chat UI and runs the voice pipeline.

Endpoints:
  GET  /           → home page
  GET  /chat       → chat UI (chat.html)
  GET  /health     → {"status": "ok"}
  WS   /ws/{scenario}  → voice pipeline (browser ↔ Deepgram ↔ LLM ↔ TTS)
"""

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(),
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("token_server")

app = FastAPI(title="AI Voicebot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html><body style="font-family:sans-serif;padding:40px;background:#0f0f1a;color:#e0e0e0">
    <h2 style="color:#a78bfa">AI Voicebot — Server Running</h2>
    <p>Open <a href="/chat" style="color:#a78bfa">/chat</a> to talk to the bot.</p>
    <p>Status: <strong style="color:#34d399">Running</strong></p>
    </body></html>
    """


@app.get("/chat")
async def chat_ui():
    chat_path = os.path.join(os.path.dirname(__file__), "chat.html")
    return FileResponse(chat_path, media_type="text/html")


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})


@app.websocket("/ws/{scenario}")
async def voice_ws(
    websocket: WebSocket,
    scenario: str = "presale",
    voice: str = Query("female"),
):
    valid_scenarios = {"presale", "sales", "marketing"}
    if scenario not in valid_scenarios:
        scenario = "presale"
    voice_gender = "male" if voice == "male" else "female"
    await websocket.accept()
    logger.info("WebSocket connected — scenario=%s voice=%s", scenario, voice_gender)
    try:
        from src.voice_server import handle_voice_session
        await handle_voice_session(websocket, scenario, voice_gender=voice_gender)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error("WebSocket error: %s", exc)
    finally:
        logger.info("WebSocket disconnected — scenario=%s", scenario)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("TOKEN_SERVER_PORT", "8000"))
    uvicorn.run("token_server:app", host="0.0.0.0", port=port, reload=False)
