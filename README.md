# GoTimeCloud WhatsApp Chatbot

AI-powered WhatsApp chatbot for GoTimeCloud (ZKTeco WFM platform). Uses Gemini Flash to understand natural language and interact with the GoTimeCloud API.

## Features

- WhatsApp integration via Meta Cloud API
- Natural language processing with Gemini Flash
- GoTimeCloud API integration (employees, punches, schedules, devices...)
- Admin dashboard for phone number → company routing
- Multi-company support (multiple GTC instances)
- Daily monitoring alerts (missing punches, late arrivals, offline devices)

## Quick Start

```bash
# Clone
git clone https://github.com/ablott976/gtc-whatsapp-bot.git
cd gtc-whatsapp-bot

# Configure
cp .env.example .env
# Edit .env with your values

# Run with Docker
docker-compose up -d
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `WHATSAPP_VERIFY_TOKEN` | Meta webhook verification token | Yes |
| `WHATSAPP_ACCESS_TOKEN` | Meta WhatsApp Cloud API token | Yes |
| `WHATSAPP_PHONE_NUMBER_ID` | Meta phone number ID | Yes |
| `GEMINI_API_KEY` | Google Gemini API key | Yes |
| `GEMINI_MODEL` | Gemini model name (default: gemini-2.5-flash) | No |
| `ADMIN_PASSWORD` | Dashboard login password | Yes |
| `DATABASE_URL` | SQLite path (default: sqlite+aiosqlite:///./gtc_bot.db) | No |

## WhatsApp Webhook Setup

1. Create a Meta app at developers.facebook.com
2. Add WhatsApp product
3. Configure webhook URL: `https://your-domain/webhook`
4. Set verify token to match `WHATSAPP_VERIFY_TOKEN`
5. Subscribe to `messages` events

## Dashboard

Access at `https://your-domain/admin` (password: `ADMIN_PASSWORD`)

Configure phone number routing:
- Phone number (with country code, no +)
- GTC company URL
- GTC company name
- GTC username
- GTC password

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/webhook` | GET | WhatsApp webhook verification |
| `/webhook` | POST | WhatsApp incoming messages |
| `/admin` | GET | Dashboard (HTML) |
| `/admin/api/routes` | GET | List routing configs |
| `/admin/api/routes` | POST | Create routing config |
| `/admin/api/routes/{id}` | PUT | Update routing config |
| `/admin/api/routes/{id}` | DELETE | Delete routing config |
| `/admin/api/login` | POST | Dashboard login |
| `/health` | GET | Health check |
| `/api/test/{phone}` | GET | Test GTC connection for a phone number |

## Architecture

```
WhatsApp Message → Webhook → Phone Lookup → GTC Client → Gemini Flash → Response
                                                  ↓
                                            GTC API (REST)
```

## License

Private - ZKTeco Europe
