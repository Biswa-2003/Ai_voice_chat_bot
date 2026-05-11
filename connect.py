"""
Run this to get a fresh browser URL.
Open the URL in your browser FIRST, then the agent joins you in the room.
"""
import asyncio
import os
import time
from dotenv import load_dotenv
from livekit import api

load_dotenv()

LIVEKIT_URL        = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY    = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
AGENT_NAME         = os.getenv("LIVEKIT_AGENT_NAME", "voicebot")


async def main():
    # Fresh room name every run — avoids stale dispatches from old sessions
    room_name = f"voicebot-{int(time.time())}"

    lkapi = api.LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)

    # 1. Create the room
    await lkapi.room.create_room(api.CreateRoomRequest(name=room_name))
    print(f"[OK] Room: {room_name}")

    # 2. Generate participant token
    token = (
        api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity("user-1")
        .with_name("Test User")
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
        .to_jwt()
    )

    playground_url = (
        f"https://agents-playground.livekit.io/"
        f"?liveKitUrl={LIVEKIT_URL}&token={token}"
    )

    print("\n" + "=" * 70)
    print("  STEP 1 — Open this URL in your browser and click Connect:")
    print("=" * 70)
    print(f"\n  {playground_url}\n")
    print("=" * 70)
    print("  STEP 2 — Once you see 'Connected', press Enter here to")
    print("           dispatch the agent to your room.")
    print("=" * 70 + "\n")

    input("  >> Press Enter after you are connected in the browser: ")

    # 3. Dispatch agent AFTER user is in the room
    try:
        dispatch = await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=AGENT_NAME,
                room=room_name,
            )
        )
        print(f"\n[OK] Agent dispatched! The bot will greet you in 2-3 seconds.\n")
    except Exception as e:
        print(f"[WARN] {e}")

    await lkapi.aclose()


if __name__ == "__main__":
    asyncio.run(main())
