"""
GVP Watch Backend - Configuration Module
-----------------------------------------
Centralized configuration management for the GVP Watch system.
Loads environment variables from .env file and provides constants used across the application.

Environment variables required:
- WHATSAPP_TOKEN: Meta WhatsApp Cloud API access token
- VERIFY_TOKEN: Webhook verification token (arbitrary string, must match in Meta settings)
- PHONE_NUMBER_ID: Meta WABA phone number ID
- BUSINESS_ACCOUNT_ID: Meta WABA business account ID
- DATABASE_URL: SQLite connection string (default: sqlite:///./gvp_watch.db)
- LOG_LEVEL: Logging level (INFO, DEBUG, WARNING, ERROR)
- REMINDER_CHECK_INTERVAL_HOURS: How often to check for reminders (default: 1)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# ============================================================================
# WHATSAPP API CONFIGURATION
# ============================================================================
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "test-verify-token")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")
BUSINESS_ACCOUNT_ID = os.getenv("BUSINESS_ACCOUNT_ID", "")
OFFICER_PHONE_DEFAULT = os.getenv("OFFICER_PHONE_DEFAULT", "")

# Meta WhatsApp Cloud API endpoint
WHATSAPP_API_URL = "https://graph.instagram.com/v18.0/me/messages"
WHATSAPP_UPLOAD_API_URL = "https://graph.instagram.com/v18.0/me/media"

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./gvp_watch.db")

# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = LOGS_DIR / "gvp-watch.log"

# ============================================================================
# REMINDER & SCHEDULER CONFIGURATION
# ============================================================================
REMINDER_CHECK_INTERVAL_HOURS = int(os.getenv("REMINDER_CHECK_INTERVAL_HOURS", "1"))

# Timeline for auto-resolution (in days)
FIRST_REMINDER_DAYS = 1    # Send first reminder after 1 day
AUTO_RESOLVE_DAYS = 2      # Auto-resolve after 2 days (total)
AWAITING_PHOTO_REMINDER_HOURS = int(os.getenv("AWAITING_PHOTO_REMINDER_HOURS", "2"))

# ============================================================================
# WHATSAPP MESSAGE TEMPLATES & CONSTANTS
# ============================================================================

# Discrete severity labels
SEVERITY_LABELS = {
    "LOW": "Low",
    "MEDIUM": "Medium",
    "HIGH": "High"
}

# Ticket status enum values
TICKET_STATUS = {
    "INITIATED": "INITIATED",           # Citizen sent "Hi"
    "AWAITING_PHOTO": "AWAITING_PHOTO", # Waiting for photo & location
    "OPEN": "OPEN",                     # Ticket created, assigned to officer
    "PENDING_VERIFICATION": "PENDING_VERIFICATION",  # Officer marked resolved
    "RESOLVED": "RESOLVED",             # Citizen confirmed resolution
    "UNRESPONSIVE": "UNRESPONSIVE"      # Auto-resolved due to inactivity
}

# Message types for logging
MESSAGE_TYPES = {
    "TEXT": "TEXT",
    "INTERACTIVE": "INTERACTIVE",
    "LOCATION": "LOCATION",
    "MEDIA": "MEDIA"
}

# Action types for audit log
ACTION_TYPES = {
    "STATUS_CHANGE": "STATUS_CHANGE",
    "REMINDER_SENT": "REMINDER_SENT",
    "AUTO_RESOLVED": "AUTO_RESOLVED",
    "OFFICER_ASSIGNED": "OFFICER_ASSIGNED",
    "MESSAGE_SENT": "MESSAGE_SENT"
}

# ============================================================================
# VALIDATION CONSTANTS
# ============================================================================
MAX_PHONE_LENGTH = 20
MIN_PHONE_LENGTH = 10
LATITUDE_MIN, LATITUDE_MAX = -90.0, 90.0
LONGITUDE_MIN, LONGITUDE_MAX = -180.0, 180.0

# ============================================================================
# DEBUG MODE
# ============================================================================
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

if __name__ == "__main__":
    # Print loaded config (sanitize sensitive values)
    print("GVP Watch Backend - Configuration Loaded")
    print(f"Database: {DATABASE_URL}")
    print(f"Log Level: {LOG_LEVEL}")
    print(f"WhatsApp Token: {'*' * len(WHATSAPP_TOKEN) if WHATSAPP_TOKEN else 'NOT SET'}")
    print(f"Verify Token: {VERIFY_TOKEN}")
    print(f"Phone Number ID: {PHONE_NUMBER_ID}")
