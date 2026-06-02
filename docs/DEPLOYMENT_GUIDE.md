# AI Voicebot screening project — Production Deployment Manual

This document provides a step-by-step guide to deploying your premium bilingual AI Voicebot screening project to a production environment. 

The application is built on **FastAPI (ASGI)**, communicating via high-performance, duplex WebSockets. Because it streams binary audio and has dynamic latency optimization, it must be deployed in an environment that fully supports persistent WebSockets.

---

## 🛠️ Environment Variables Config (Required)
Regardless of your deployment choice, you must configure the following environment variables in your hosting dashboard:

| Variable | Description | Recommended Value |
| :--- | :--- | :--- |
| `OPENAI_API_KEY` | OpenAI/OpenRouter API Key | `sk-or-...` or `sk-...` |
| `DEEPGRAM_API_KEY` | Deepgram Real-time Streaming STT API Key | `your-deepgram-api-key` |
| `SARVAM_API_KEY` | Sarvam.ai Premium TTS API Key | `your-sarvam-key` |
| `TTS_PROVIDER` | TTS voice synthesis engine | `sarvam` (or `edge` for free fallback) |
| `PORT` | Listening port for Uvicorn | `8000` (or host assigned port) |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

---

## 🚀 Deployment Option A: PaaS Cloud Platforms (Render or Railway)
*Recommended for ease of use. Zero devops, automatic SSL, and instant Github sync.*

### 🚂 Method A.1: Railway.app (Highly Recommended)
Railway fully supports WebSocket connections out-of-the-box and has excellent FastAPI compatibility.

1. **Sign Up:** Go to [railway.app](https://railway.app/) and sign in using your GitHub account.
2. **Create Project:** Click **New Project** → **Deploy from GitHub repo**.
3. **Select Repository:** Choose your `ai-chat-bot` or voicebot repository.
4. **Configure Variables:** Click on the **Variables** tab in the service dashboard and add all the keys listed in the *Environment Variables* table above.
5. **Start Command:** Railway automatically reads your `Dockerfile.api`. If prompted for a start command, set it to:
   ```bash
   python token_server.py
   ```
6. **Generate Domain:** In the **Settings** tab, click **Generate Domain** under the *Networking* section. Railway will assign a secure HTTPS/WSS address (e.g. `voicebot-production.up.railway.app`).
7. **Test:** Navigate to `https://<your-railway-domain>/chat` in your browser.

---

### 🎨 Method A.2: Render.com
Render is a free/cheap PaaS option. Note that persistent WebSockets are supported on Render Web Services.

1. **Sign Up:** Go to [render.com](https://render.com/) and link your GitHub.
2. **New Web Service:** Click **New +** → **Web Service**.
3. **Connect Repository:** Select your voicebot repository.
4. **Configure Settings:**
   * **Runtime:** Choose `Docker`.
   * **Docker Command:** Left blank (it defaults to `Dockerfile` or `Dockerfile.api`). To specifically use the API dockerfile, configure:
     * **Dockerfile Path:** `Dockerfile.api`
5. **Add Environment Variables:** Under the **Advanced** section, click **Add Environment Variable** and copy your API Keys.
6. **Deploy:** Click **Create Web Service**. Render will build the container and deploy the app on a secure domain (`https://<your-app-name>.onrender.com/chat`).

---

## 🐳 Deployment Option B: Containerized VPS (Docker Compose)
*Recommended for stable, isolated, cost-effective hosting on DigitalOcean, AWS EC2, GCP, or Linode.*

Since the codebase includes a pre-configured `Dockerfile.api` and `docker-compose.yml` in the root directory, Docker deployment takes less than 2 minutes:

1. **Provision VPS:** Launch a standard Ubuntu VPS (e.g., $5/mo droplet on DigitalOcean).
2. **Install Docker:** Run the installation script on your server:
   ```bash
   sudo apt update
   sudo apt install -y docker.io docker-compose
   ```
3. **Clone Repo:** Clone your project code onto the VPS:
   ```bash
   git clone <your-repo-link> /app
   cd /app/voicebot-screening-project
   ```
4. **Create `.env` File:** Create the production environment configuration:
   ```bash
   nano .env
   ```
   Paste your API keys and configuration:
   ```env
   OPENAI_API_KEY=your_openai_or_openrouter_key
   DEEPGRAM_API_KEY=your_deepgram_key
   SARVAM_API_KEY=your_sarvam_key
   TTS_PROVIDER=sarvam
   PORT=8000
   ```
5. **Build and Run:** Launch the container in detached (background) mode:
   ```bash
   sudo docker-compose up --build -d
   ```
6. **Verify:** Check logs and container status:
   ```bash
   sudo docker ps
   sudo docker-compose logs -f
   ```

---

## 🔒 Production Security Best Practices (SSL Certificates)
Browsers **strictly require HTTPS** (secure connections) to authorize microphone access (`navigator.mediaDevices.getUserMedia`). 
* If you deploy using **PaaS (Railway or Render)**, they automatically issue and manage SSL certificates for you (highly recommended!).
* If you deploy using **VPS (Option B or C)**, you must put a reverse proxy (like **Nginx**) in front of the app and secure it with **Certbot (Let's Encrypt)**.

### Nginx Secure Reverse Proxy Config Example:
```nginx
server {
    listen 80;
    server_name voicebot.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name voicebot.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/voicebot.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/voicebot.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # CRITICAL: Websocket support
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```
Use `sudo certbot --nginx -d voicebot.yourdomain.com` to provision the certificates automatically!
