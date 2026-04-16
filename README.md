# GoTimeCloud WhatsApp Chatbot

AI-powered WhatsApp chatbot for GoTimeCloud (ZKTeco WFM platform). Uses Gemini Flash to understand natural language and interact with the GoTimeCloud API.

## Features

- WhatsApp integration via Meta Cloud API v21.0
- Natural language processing with Gemini Flash
- GoTimeCloud API integration (employees, punches, schedules, devices...)
- React SPA admin dashboard (TailwindCSS + Vite)
- Multi-company support (multiple GTC instances per phone number)
- Redis-based message batching (groups rapid-fire messages)
- Daily monitoring alerts (missing punches, late arrivals, early departures, offline devices)
- PostgreSQL database with asyncpg
- Multi-stage Docker build (Node for admin, Python for backend)

## Quick Start

```bash
# Clone
git clone https://github.com/ablott976/gtc-whatsapp-bot.git
cd gtc-whatsapp-bot

# Configure
cp .env.example .env
# Edit .env with your values

# Run with Docker Compose (includes PostgreSQL + Redis)
docker-compose up -d
```

## Development

```bash
# Backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Admin dashboard (separate terminal)
cd admin
npm install
npm run dev     # Dev server with HMR at localhost:5173
npm run build   # Build for production
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WHATSAPP_VERIFY_TOKEN` | Meta webhook verification token | (required) |
| `WHATSAPP_ACCESS_TOKEN` | Meta WhatsApp Cloud API token | (required) |
| `WHATSAPP_PHONE_NUMBER_ID` | Meta phone number ID | (required) |
| `WHATSAPP_APP_SECRET` | Meta app secret for signature verification | (required) |
| `GEMINI_API_KEY` | Google Gemini API key | (required) |
| `GEMINI_MODEL` | Gemini model name | `gemini-3-flash-preview` |
| `ADMIN_USER` | Admin dashboard username | `admin` |
| `ADMIN_PASSWORD` | Admin dashboard password | `admin123` |
| `ADMIN_JWT_SECRET` | JWT secret for admin auth | `change-this-secret` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://gtc:gtc@localhost:5432/gtc_bot` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `BATCH_WAIT_MS` | Message batching window (ms) | `3000` |

## WhatsApp Webhook Setup

1. Create a Meta app at developers.facebook.com
2. Add WhatsApp product
3. Configure webhook URL: `https://your-domain/webhook`
4. Set verify token to match `WHATSAPP_VERIFY_TOKEN`
5. Subscribe to `messages` events

## Admin Dashboard

Access at `https://your-domain/admin`

React SPA with TailwindCSS. Configure phone number routing:
- Phone number (with country code, no +)
- GTC company URL
- GTC company name
- GTC username
- GTC password
- UTC offset
- Language (es/en/pt)

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/webhook` | GET | WhatsApp webhook verification |
| `/webhook` | POST | WhatsApp incoming messages |
| `/admin` | GET | React SPA dashboard |
| `/admin/api/login` | POST | Dashboard login (JWT) |
| `/admin/api/routes` | GET | List routing configs |
| `/admin/api/routes` | POST | Create routing config |
| `/admin/api/routes/{id}` | PUT | Update routing config |
| `/admin/api/routes/{id}` | DELETE | Delete routing config |
| `/admin/api/stats` | GET | Dashboard statistics |
| `/admin/api/messages` | GET | Message log |
| `/health` | GET | Health check |

## Architecture

```
WhatsApp Message → /webhook → Batcher (Redis) → Phone Lookup → GTC Client → Gemini Flash → Response
                                                                          ↓
                                                                    GTC API (REST)

Admin Dashboard (React SPA) → /admin/api/* → PostgreSQL
```

## Project Structure

```
├── admin/              # React SPA dashboard
│   ├── src/            # React components + API client
│   └── dist/           # Built assets (generated)
├── app/
│   ├── main.py         # FastAPI app, routers, SPA serving
│   ├── config.py       # Pydantic Settings
│   ├── database.py     # PostgreSQL via asyncpg
│   ├── ai_engine.py    # Gemini function calling
│   ├── whatsapp.py     # Meta Cloud API v21.0
│   ├── gtc_client.py   # GoTimeCloud API client
│   ├── batcher.py      # Redis message batching
│   └── routes/
│       ├── webhook.py  # Webhook router
│       └── admin.py    # Admin API router (JWT auth)
├── sql/
│   └── init.sql        # PostgreSQL schema
├── docker-compose.yml  # PostgreSQL + Redis + Bot
├── Dockerfile          # Multi-stage (Node + Python)
└── requirements.txt    # Python dependencies
```

## License

Private - ZKTeco Europe
