"""
GVP Watch Backend - Pytest Configuration
------------------------------------------
Fixtures for testing webhook, ticket service, and database operations.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import Base, SessionLocal, engine, Ticket, User, Ward, Officer
from ticket_service import TicketService
from webhook_handler import WebhookHandler
from utils import generate_uuid


@pytest.fixture(scope="function", autouse=True)
def mock_whatsapp_client(monkeypatch):
    """Mock outbound WhatsApp calls for deterministic, offline tests."""

    def _mock_send_text(recipient_phone, text_body, ticket_id=None):
        return {
            "success": True,
            "message_id": f"mock-text-{generate_uuid()[:8]}"
        }

    def _mock_send_interactive_buttons(
        recipient_phone,
        body_text,
        buttons,
        header_text=None,
        footer_text=None,
        ticket_id=None,
    ):
        return {
            "success": True,
            "message_id": f"mock-btn-{generate_uuid()[:8]}"
        }

    monkeypatch.setattr("ticket_service.whatsapp_client.send_text", _mock_send_text)
    monkeypatch.setattr(
        "ticket_service.whatsapp_client.send_interactive_buttons",
        _mock_send_interactive_buttons,
    )


@pytest.fixture(scope="function")
def db():
    """
    Create a fresh database for each test.
    Rolls back all changes after test completion.
    """
    # Create all tables
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    yield session

    # Cleanup
    session.rollback()
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def ticket_service(db):
    """Create a TicketService instance with test database"""
    return TicketService(db)


@pytest.fixture(scope="function")
def webhook_handler():
    """Create a WebhookHandler instance"""
    return WebhookHandler()


@pytest.fixture(scope="function")
def sample_ward(db):
    """Create a sample ward"""
    ward = Ward(
        ward_id=generate_uuid(),
        ward_name="Test_Ward",
        zone="Zone A"
    )
    db.add(ward)
    db.commit()
    return ward


@pytest.fixture(scope="function")
def sample_citizen(db):
    """Create a sample citizen user"""
    user = User(
        user_id=generate_uuid(),
        phone="919876543210",
        role="CITIZEN",
        name="Test Citizen",
        is_active=True
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture(scope="function")
def sample_officer(db, sample_ward):
    """Create a sample officer with ward mapping"""
    user = User(
        user_id=generate_uuid(),
        phone="919123456789",
        role="OFFICER",
        name="Test Officer",
        is_active=True
    )
    db.add(user)
    db.flush()

    officer = Officer(
        officer_id=generate_uuid(),
        user_id=user.user_id,
        employee_id="EMP001",
        is_on_duty=True
    )
    db.add(officer)

    # Add ward mapping
    officer.wards.append(sample_ward)

    db.commit()
    return officer


@pytest.fixture(scope="function")
def sample_text_message():
    """Sample WhatsApp text message payload"""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123",
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "919876543210",
                                    "id": "wamid.test1",
                                    "timestamp": "1680513234",
                                    "type": "text",
                                    "text": {"body": "Hi"}
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


@pytest.fixture(scope="function")
def sample_location_message():
    """Sample WhatsApp location message payload"""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123",
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "919876543210",
                                    "id": "wamid.test2",
                                    "timestamp": "1680513240",
                                    "type": "location",
                                    "location": {
                                        "latitude": 17.3850,
                                        "longitude": 78.4867
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


@pytest.fixture(scope="function")
def sample_image_message():
    """Sample WhatsApp image message payload"""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123",
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "919876543210",
                                    "id": "wamid.test3",
                                    "timestamp": "1680513245",
                                    "type": "image",
                                    "image": {
                                        "mime_type": "image/jpeg",
                                        "sha256": "abc123",
                                        "id": "media_id_123"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


@pytest.fixture(scope="function")
def sample_button_message():
    """Sample WhatsApp interactive button message payload"""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123",
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "919876543210",
                                    "id": "wamid.test4",
                                    "timestamp": "1680513250",
                                    "type": "interactive",
                                    "interactive": {
                                        "button_reply": {
                                            "id": "confirmed",
                                            "title": "Confirmed"
                                        }
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
