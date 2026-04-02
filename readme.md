# GVP Watch Backend

A modular, production-ready WhatsApp-based Solid Waste Management (GVP Watch) grievance system built with **FastAPI**, **SQLAlchemy**, and **Meta WhatsApp Cloud API**.

**Status:** ✅ Fully implemented prototype with comprehensive logging and audit trails.

---

## 📋 Table of Contents

1. [Architecture Overview](#-architecture-overview)
2. [Tech Stack](#-tech-stack)
3. [Setup Instructions](#-setup-instructions)
4. [Configuration](#-configuration)
5. [Running the Server](#-running-the-server)
6. [API Endpoints](#-api-endpoints)
7. [Workflow Examples](#-workflow-examples)
8. [Logging & Audit Trail](#-logging--audit-trail)
9. [Webhook Setup with Ngrok](#-webhook-setup-with-ngrok)
10. [Database Schema](#-database-schema)
11. [Testing](#-testing)
12. [Troubleshooting](#-troubleshooting)
13. [Future Enhancements](#-future-enhancements)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Meta WhatsApp Cloud API                    │
├─────────────────────────────────────────────────────────────────┤
│                              │                                   │
│                              ▼                                   │
│                   ┌──────────────────┐                           │
│                   │  Webhook Handler │ (webhook_handler.py)     │
│                   │  - Parse payload │                          │
│                   │  - Route events  │                          │
│                   └────────┬─────────┘                           │
│                            │                                     │
│     ┌──────────────────────┼──────────────────────┐              │
│     │                      │                      │              │
│     ▼                      ▼                      ▼              │
│ ┌─────────────┐  ┌──────────────────┐  ┌────────────────┐      │
│ │   Ticket    │  │WhatsApp Client   │  │  Message Log   │      │
│ │  Service    │  │ - send_text()    │  │- Audit Trail   │      │
│ │(ticket_     │  │ - send_buttons() │  └────────────────┘      │
│ │service.py)  │  │ - send_template()│                           │
│ └──────┬──────┘  └────────┬─────────┘                           │
│        │                  │                                     │
│        │                  ▼                                     │
│        │         (Meta WhatsApp API Response)                   │
│        │                                                         │
│        ▼                                                         │
│   ┌────────────────────────────────────────┐                   │
│   │     Database (SQLAlchemy + SQLite)     │                   │
│   ├────────────────────────────────────────┤                   │
│   │ - Ticket       (status, timeline)      │                   │
│   │ - User         (citizen, officer)      │                   │
│   │ - Ward         (geographic division)   │                   │
│   │ - ActionLog    (state transitions)     │                   │
│   │ - MessageLog   (message audit trail)   │                   │
│   │ - WardOffice   (many-to-many mapping)  │                   │
│   └────────────────────────────────────────┘                   │
│                    │                                            │
│                    ▼                                            │
│   ┌────────────────────────────────────────┐                   │
│   │   Reminder Service (APScheduler)       │                   │
│   │ - 1-day reminder to citizen            │                   │
│   │ - 2-day auto-resolve unresponsive      │                   │
│   └────────────────────────────────────────┘                   │
│                                                                 │
│   ┌────────────────────────────────────────┐                   │
│   │   Logger (logs/gvp-watch.log)          │                   │
│   │ - All actions logged with timestamps   │                   │
│   │ - Ticket context in every log entry    │                   │
│   │ - Rotating file handler (5MB backup)   │                   │
│   └────────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

### Key Flows

**Flow 1: Citizen Reports GVP**
```
Citizen: "Hi"
  ↓
Bot: "Click to Report GVP" (Interactive buttons)
  ↓
Citizen: Clicks "Report" + sends photo + location
  ↓
System: Analyzes photo → Calculates severity → Assigns to officer
  ↓
Officer gets notification with ticket details
```

**Flow 2: Officer Resolution & Citizen Verification**
```
Officer: "tk-xxx Resolved"
  ↓
System: Moves ticket to PENDING_VERIFICATION
  ↓
Bot asks citizen: "Confirm resolved?"
  ↓
If "Confirmed": Ticket → RESOLVED
If "Not Resolved": Ticket stays in PENDING_VERIFICATION, officer is notified again
If no response for 1 day: Send reminder
If no response for 2 days: Auto-resolve as UNRESPONSIVE
```

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Framework** | FastAPI | Async web framework for webhooks |
| **Database** | SQLite + SQLAlchemy | ORM-based database (upgradeable to PostgreSQL) |
| **API Client** | httpx | HTTP requests to Meta WhatsApp API |
| **Job Scheduler** | APScheduler | Background reminders & auto-resolution |
| **Logging** | Python logging | Structured audit logs with rotation |
| **Validation** | Pydantic | Request/response data validation |
| **Testing** | pytest | Unit and integration tests |

---

## 🚀 Setup Instructions

### Prerequisites

- **Python 3.8+** (recommended: 3.10 or 3.11)
- **pip** or **uv** (package manager)
- **Git**
- **ngrok** (for local webhook testing)
- **Meta Business Account** with WhatsApp access

### Step 1: Clone Repository & Create Virtual Environment

```bash
# Clone the repository
git clone <repository_url>
cd gvp-watch-backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your actual credentials
nano .env
# or open in your editor of choice
```

See [Configuration](#-configuration) section for detailed instructions on obtaining each value.

### Step 4: Initialize Database

```bash
python database.py
# Creates sqlite:///./gvp_watch.db with all tables
```

### Step 5: Run the Server

```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

---

## 🔧 Configuration

See `.env.example` for all environment variables needed.

### Getting WhatsApp Credentials

1. **WhatsApp Token**: Meta Business Manager > Apps > WhatsApp > System Users > Generate Token
2. **Phone Number ID**: Meta Business Manager > WhatsApp > Phone Numbers
3. **Business Account ID**: Meta Business Manager > WhatsApp > Business Accounts
4. **Verify Token**: Create any arbitrary string for webhook verification

---

## 🏃 Running the Server

```bash
# Development (with auto-reload)
python -m uvicorn main:app --reload --port 8000

# Production
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Verify
curl http://localhost:8000/health
```

**API Documentation**: http://localhost:8000/docs

---

## 📡 Webhook Setup with Ngrok

```bash
# Start ngrok tunnel
ngrok http 8000
# Outputs: http://abc123.ngrok.io

# Configure in Meta Portal
# Callback URL: http://abc123.ngrok.io/webhook
# Verify Token: (same as in .env)
```

---

## 📊 Key Endpoints

```bash
# List tickets
GET /tickets?status=OPEN

# Get ticket details
GET /tickets/tk-a1b2c3d4

# Get audit logs
GET /logs/tk-a1b2c3d4

# Webhook (auto-configured by Meta)
POST /webhook
```

---

## 📝 Logging

All logs written to `logs/gvp-watch.log`:

```bash
# Watch logs
tail -f logs/gvp-watch.log

# Search for ticket
grep "tk-a1b2c3d4" logs/gvp-watch.log

# Search by action
grep "STATUS_CHANGE" logs/gvp-watch.log
```

---

## 🗄️ Database Schema

**Main Tables:**
- `users` - Citizens and officers
- `wards` - Geographic divisions
- `officers` - Officer profiles
- `ward_officer_mapping` - Many-to-many mapping
- `tickets` - Core grievances
- `message_logs` - All incoming/outgoing messages
- `action_logs` - State changes and system actions

All with proper indexes for performance and audit trail capabilities.

---

## 🧪 Testing

```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=. --cov-report=html
```

---

## 🔮 Future Enhancements

- [ ] PostgreSQL + PostGIS for production
- [ ] Analytics dashboard
- [ ] ML-based image classification
- [ ] Multi-language support
- [ ] Kubernetes deployment

---

## 📞 Support

For issues:
1. Check `logs/gvp-watch.log`
2. Review database audit trails
3. Verify ngrok and webhook configuration

Complete documentation in the expanded README.md file.