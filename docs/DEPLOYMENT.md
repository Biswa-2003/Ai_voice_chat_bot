# Deployment Guide

## Option 1: Local Development

See [SETUP.md](SETUP.md) for local environment setup and running the agent directly.

---

## Option 2: Docker (Local or Server)

### Build the Image

```bash
docker build -t voicebot:latest .
```

### Run the Container

```bash
docker run --env-file .env voicebot:latest
```

### Run with Explicit Variables

```bash
docker run \
  -e LIVEKIT_URL=wss://your-project.livekit.cloud \
  -e LIVEKIT_API_KEY=APIxxxxxxxxxx \
  -e LIVEKIT_API_SECRET=your-secret \
  -e OPENAI_API_KEY=sk-... \
  -e DEEPGRAM_API_KEY=your-deepgram-key \
  -e ELEVEN_API_KEY=your-elevenlabs-key \
  -e SCENARIO=presale \
  -v $(pwd)/logs:/app/logs \
  voicebot:latest
```

Mount `-v $(pwd)/logs:/app/logs` to persist conversation logs on the host.

---

## Option 3: AWS EC2

### 1. Launch an Instance

- AMI: Ubuntu Server 22.04 LTS
- Instance type: t3.small (minimum), t3.medium (recommended)
- Security group: allow outbound TCP 443 (LiveKit, APIs)

### 2. Install Dependencies

```bash
sudo apt update && sudo apt install -y python3.11 python3-pip python3-venv docker.io
sudo usermod -aG docker ubuntu
```

### 3. Deploy with Docker

```bash
git clone <your-repo-url> /home/ubuntu/voicebot
cd /home/ubuntu/voicebot
cp .env.example .env
# Edit .env with your credentials
nano .env

docker build -t voicebot .
docker run -d --restart=always --env-file .env -v /home/ubuntu/logs:/app/logs voicebot
```

### 4. Monitor

```bash
docker logs -f $(docker ps -q --filter ancestor=voicebot)
```

---

## Option 4: Google Cloud Run

### 1. Build and Push

```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT/voicebot
```

### 2. Deploy

```bash
gcloud run deploy voicebot \
  --image gcr.io/YOUR_PROJECT/voicebot \
  --platform managed \
  --region asia-south1 \
  --set-env-vars LIVEKIT_URL=wss://...,OPENAI_API_KEY=sk-...,SCENARIO=presale \
  --no-allow-unauthenticated
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LIVEKIT_URL` | Yes | — | LiveKit server WebSocket URL |
| `LIVEKIT_API_KEY` | Yes | — | LiveKit API key |
| `LIVEKIT_API_SECRET` | Yes | — | LiveKit API secret |
| `OPENAI_API_KEY` | Yes | — | OpenAI or OpenRouter API key |
| `OPENAI_MODEL` | No | `gpt-4o` | LLM model name |
| `OPENAI_BASE_URL` | No | — | Custom OpenAI-compatible base URL |
| `DEEPGRAM_API_KEY` | Yes | — | Deepgram API key |
| `ELEVEN_API_KEY` | Yes | — | ElevenLabs API key |
| `TTS_EN_IN_VOICE_ID` | No | `9BWtsMINqrJLrRacOk9x` | ElevenLabs voice ID for English |
| `TTS_HI_VOICE_ID` | No | `9BWtsMINqrJLrRacOk9x` | ElevenLabs voice ID for Hindi |
| `SCENARIO` | No | `presale` | Bot scenario: presale, sales, marketing |
| `DEFAULT_LANGUAGE` | No | `en` | Initial greeting language |
| `LOG_DIR` | No | `logs` | Directory for conversation logs |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |
| `LIVEKIT_AGENT_PORT` | No | `0` | Worker HTTP port (0 = auto) |

---

## Scaling

- Each agent instance handles one LiveKit room at a time.
- For concurrent calls, run multiple containers behind a load balancer.
- LiveKit Cloud automatically routes participants to available agent workers.
- Target: 5+ concurrent sessions per instance on t3.medium.

---

## Health Checks

The agent logs a startup message on connection. Monitor with:

```bash
docker logs <container_id> | grep "Connected to LiveKit room"
```

For production monitoring, ship logs to a centralised service (CloudWatch, Loki, Datadog).
