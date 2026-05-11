# Deployment Guide

## Overview

The project deploys two services:

| Service | What it does | File |
|---------|-------------|------|
| **Agent** | Connects to LiveKit 24/7, listens for voice calls | `Dockerfile` |
| **Token Server** | FastAPI API that gives users a connection URL | `Dockerfile.api` |

```
User Browser
     │
     ▼
Token Server (Railway) ──── creates room + token + dispatches agent
     │
     ▼
LiveKit Cloud ◄──────────── Agent (Railway) — running 24/7
     │
     ▼
User gets playground_url → connects → bot speaks
```

---

## Part 1 — Push Code to GitHub

### Step 1 — Install Git
- Download from: https://git-scm.com/download/win
- Install with all default settings
- Restart VS Code after installing

### Step 2 — Create GitHub Repository
1. Go to https://github.com → Sign in
2. Click **New repository**
3. Name: `Ai_voice_chat_bot`
4. Set to Public
5. Do NOT add README
6. Click **Create repository**

### Step 3 — Push Code
Open terminal in VS Code and run:

```bash
cd voicebot-screening-project

git init
git config user.email "your-email@gmail.com"
git config user.name "your-github-username"

git add .
git commit -m "AI Voicebot - LiveKit Multilingual Platform - Complete Project"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/Ai_voice_chat_bot.git
git push -u origin main
```

✅ All 48 files pushed to GitHub

---

## Part 2 — Deploy on Railway

Railway URL: https://railway.app

### Step 1 — Create Account
1. Go to https://railway.app
2. Sign up with GitHub (free — 30 days / $5 trial)

### Step 2 — Deploy the Agent Service

1. Click **New Project**
2. Select **GitHub Repository**
3. Select `Ai_voice_chat_bot`
4. Railway auto-detects `Dockerfile` and starts building
5. Wait for **"Deployment successful"** ✅

### Step 3 — Add Environment Variables to Agent

Click the service → **Variables** tab → add all these:

```
LIVEKIT_URL=wss://ai-chat-bot-ikj1ac62.livekit.cloud
LIVEKIT_API_KEY=APIxHbp88wJdVJP
LIVEKIT_API_SECRET=upz4geNdArFYe0fSSVZjm8vZXH0uE457ddFey1IGGtZB
LIVEKIT_AGENT_NAME=voicebot
LIVEKIT_AGENT_PORT=0
OPENAI_API_KEY=sk-or-v1-78a57b3a...
OPENAI_MODEL=openai/gpt-4o-mini
DEEPGRAM_API_KEY=871711596a917d01...
ELEVEN_API_KEY=sk_a58fc138...
SARVAM_API_KEY=sk_r8vyjmx3_iGnjG...
TTS_PROVIDER=sarvam
TTS_EN_IN_VOICE_ID=9BWtsMINqrJLrRacOk9x
TTS_HI_VOICE_ID=9BWtsMINqrJLrRacOk9x
SCENARIO=presale
DEFAULT_LANGUAGE=en
LOG_DIR=logs
LOG_LEVEL=INFO
TOKEN_SERVER_PORT=8000
```

Click **Save** → Railway redeploys automatically.

### Step 4 — Verify Agent is Running

Click service → **Deploy Logs** → you should see:
```
registered worker — agent_name: voicebot — region: ...
```
✅ Agent is live 24/7 on Railway

---

### Step 5 — Add Token Server Service

1. Go back to project canvas
2. Click **`+ Add`** (top right)
3. Select **`GitHub Repository`**
4. Select `Ai_voice_chat_bot`
5. Set **Dockerfile path** to:
```
/Dockerfile.api
```
6. Add the same environment variables as Step 3
7. Click **Deploy**

### Step 6 — Generate Public Domain for Token Server

1. Click on the token server service
2. Go to **`Settings`** tab
3. Scroll to **Networking**
4. Click **`Generate Domain`**
5. Copy your URL:
```
https://ai-voice-chat-bot-api.railway.app
```

---

## Part 3 — How to Connect (After Deployment)

### Option A — Full URL (Automatic)
Visit in browser:
```
https://YOUR-TOKEN-SERVER.railway.app/connect
```

Returns JSON:
```json
{
  "room": "voicebot-1234567",
  "scenario": "presale",
  "livekit_url": "wss://ai-chat-bot-ikj1ac62.livekit.cloud",
  "token": "eyJhbGci...",
  "playground_url": "https://agents-playground.livekit.io/?liveKitUrl=...&token=...",
  "message": "Open playground_url in your browser to start talking to the bot."
}
```

Copy `playground_url` → open in browser → click Connect → **bot speaks!**

### Option B — Manual (Playground)
1. Go to https://agents-playground.livekit.io
2. Click **Manual** tab
3. Paste:
   - **WSS URL:** `wss://ai-chat-bot-ikj1ac62.livekit.cloud`
   - **Token:** (get fresh token from `/connect` endpoint)
4. Click **Connect**

### Option C — Different Scenarios
```
https://YOUR-TOKEN-SERVER.railway.app/connect?scenario=presale
https://YOUR-TOKEN-SERVER.railway.app/connect?scenario=sales
https://YOUR-TOKEN-SERVER.railway.app/connect?scenario=marketing
```

---

## What is Permanent vs Temporary

| Item | Permanent? | Notes |
|------|-----------|-------|
| LiveKit URL (`wss://...`) | ✅ Yes | Never changes |
| Railway Agent URL | ✅ Yes | Runs 24/7 |
| Token Server URL | ✅ Yes | Always available |
| Connection Token | ❌ No | Expires in 6 hours — get fresh from `/connect` |

---

## Local Development (Without Railway)

```bash
# Terminal 1 — Start agent
cd voicebot-screening-project
python -m src.main start

# Terminal 2 — Start token server
python token_server.py

# Get connection URL
curl http://localhost:8000/connect

# Or open in browser
http://localhost:8000/connect
```

---

## Files Created for Deployment

| File | Purpose |
|------|---------|
| `Dockerfile` | Builds and runs the voice agent |
| `Dockerfile.api` | Builds and runs the token server |
| `docker-compose.yml` | Runs both services together locally |
| `token_server.py` | FastAPI server — generates tokens + dispatches agent |
| `.gitignore` | Excludes `.env`, logs, cache from GitHub |

---

## Troubleshooting

**Agent shows Offline on Railway:**
- Check Deploy Logs for errors
- Verify all environment variables are set correctly
- Redeploy by clicking **Redeploy** button

**Token expired error:**
- Tokens expire after 6 hours
- Visit `/connect` again to get a fresh token

**Bot not speaking after connecting:**
- Check Railway Deploy Logs — look for `received job request`
- Make sure `SARVAM_API_KEY` is set correctly
- Make sure `TTS_PROVIDER=sarvam`

**Bot connects but no audio:**
- Check microphone permissions in browser
- Allow microphone access when browser asks
