# Journey

Journey is a harness-first Dash application for the 24-hour Build Challenge. It visibly separates material handling, declared guardrails, explicit checkpoints, structured alarms, and a swappable itinerary worker.

## Start Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Open `http://127.0.0.1:8050`. Deterministic mode requires no OpenAI key.

On Ubuntu/Debian, install `python3-venv` first if `ensurepip` is unavailable. A user-level fallback is to bootstrap pip into the created environment with the official `get-pip.py` script.

## Verify

```bash
pytest
ruff check .
```

Tests mock OpenAI and perform no live model requests.

## Configure OpenAI

Set these only on the server:

```env
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4.1-mini
```

The key is never included in Dash stores, worker requests, run records, logs, or client layout.

## Deploy

### Deploy to Render

The easiest way to deploy Journey is using Render's Blueprint specification:

1. Push this repository to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com/)
3. Click **New** → **Blueprint**
4. Connect your GitHub repository
5. Render will automatically detect `render.yaml` and configure the service
6. (Optional) Add your `OPENAI_API_KEY` in the Render dashboard under Environment Variables
7. Click **Apply** to deploy

The app will be available at `https://journey-harness.onrender.com` (or your assigned URL).

**Manual Render Deployment:**

If you prefer manual setup:

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **New** → **Web Service**
3. Connect your repository
4. Configure:
   - **Name:** journey-harness
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:server --bind 0.0.0.0:$PORT`
5. Add environment variables from `.env.example`
6. Click **Create Web Service**

### Deploy to Other Platforms

Deploy to any Python host that supports a WSGI command.

1. Set the runtime to Python 3.11 or newer.
2. Install with `pip install -r requirements.txt`.
3. Set `JOURNEY_WORKER=deterministic` and the other values from `.env.example`.
4. Optionally set `OPENAI_API_KEY` and `OPENAI_MODEL` server-side.
5. Start with:

```bash
gunicorn app:server --bind 0.0.0.0:${PORT:-8050}
```

MapLibre assets are vendored and the map uses a local no-tile style, so deterministic mode needs no runtime network access. No database or persistent server volume is required.

See [HARNESS.md](HARNESS.md) for architecture, controls, replay, and the demo sequence.
