"""
GVP Watch Backend - Database Models
------------------------------------
SQLAlchemy ORM models for all database tables.

Tables:
- User: Citizen & Officer profiles (with roles)
- Ward: Ward information
- Officer: Officer details with active status
- WardOfficerMapping: Many-to-many relationship between Officers and Wards
- Ticket: Core grievance tickets with state tracking
- MessageLog: All incoming/outgoing messages (audit trail)
- ActionLog: State transitions, reminders, and system actions

The schema is designed to be PostgreSQL/PostGIS-compatible in the future.
"""

from sqlalchemy import (
    create_engine, Column, String, Integer, Float, DateTime, Text,
    ForeignKey, Boolean, JSON, Enum, Table, UniqueConstraint, Index, text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from enum import Enum as PyEnum
import uuid

from config import DATABASE_URL

# ============================================================================
# DATABASE SETUP
# ============================================================================
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ============================================================================
# ENUM DEFINITIONS
# ============================================================================
class TicketStatusEnum(str, PyEnum):
    """Ticket status values"""
    INITIATED = "INITIATED"
    AWAITING_PHOTO = "AWAITING_PHOTO"
    OPEN = "OPEN"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    RESOLVED = "RESOLVED"
    UNRESPONSIVE = "UNRESPONSIVE"


class UserRoleEnum(str, PyEnum):
    """User role types"""
    CITIZEN = "CITIZEN"
    OFFICER = "OFFICER"
    ADMIN = "ADMIN"


class MessageTypeEnum(str, PyEnum):
    """Message type for logging"""
    TEXT = "TEXT"
    INTERACTIVE = "INTERACTIVE"
    LOCATION = "LOCATION"
    MEDIA = "MEDIA"


class SeverityEnum(str, PyEnum):
    """Waste severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ActionTypeEnum(str, PyEnum):
    """Audit log action types"""
    STATUS_CHANGE = "STATUS_CHANGE"
    REMINDER_SENT = "REMINDER_SENT"
    AUTO_RESOLVED = "AUTO_RESOLVED"
    OFFICER_ASSIGNED = "OFFICER_ASSIGNED"
    MESSAGE_SENT = "MESSAGE_SENT"


class MessageDirectionEnum(str, PyEnum):
    """Message direction for logging"""
    INCOMING = "INCOMING"
    OUTGOING = "OUTGOING"


class SessionStateEnum(str, PyEnum):
    """Session state for the chat planner"""
    SELECTING_LANGUAGE = "SELECTING_LANGUAGE"
    MAIN_MENU = "MAIN_MENU"
    AWAITING_TRACK_ID = "AWAITING_TRACK_ID"
    AWAITING_PHOTO = "AWAITING_PHOTO"
    AWAITING_LOCATION = "AWAITING_LOCATION"
    AWAITING_SEVERITY = "AWAITING_SEVERITY"
    AWAITING_TYPE = "AWAITING_TYPE"


# ============================================================================
# MODELS
# ============================================================================

class UserSession(Base):
    """
    Session model to track conversation state.
    """
    __tablename__ = "user_sessions"

    phone = Column(String(20), primary_key=True)
    language = Column(String(10), default="en")
    current_state = Column(String(30), default=SessionStateEnum.SELECTING_LANGUAGE)
    temp_data = Column(JSON, default=dict)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)



class User(Base):
    """
    User model for Citizens and Officers.

    Fields:
    - user_id: UUID primary key
    - phone: WhatsApp phone number (international format, +91...)
    - role: CITIZEN, OFFICER, or ADMIN
    - name: User's display name
    - is_active: Soft delete / account status
    - created_at: Account creation timestamp
    """
    __tablename__ = "users"

    user_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    phone = Column(String(20), unique=True, nullable=False, index=True)
    role = Column(String(10), nullable=False, default=UserRoleEnum.CITIZEN)
    name = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    tickets_created = relationship("Ticket", back_populates="citizen", foreign_keys="Ticket.citizen_phone")
    tickets_assigned = relationship("Ticket", back_populates="assigned_officer", foreign_keys="Ticket.officer_phone")
    officer_detail = relationship("Officer", back_populates="user", uselist=False)

    __table_args__ = (
        Index("idx_users_phone_role", "phone", "role"),
    )


class Ward(Base):
    """
    Ward model for geographic/administrative divisions.
    Extended with GHMC ward numbers, circle info, and GeoJSON boundaries.
    """
    __tablename__ = "wards"

    ward_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ward_name = Column(String(100), nullable=False, unique=True)
    ward_number = Column(Integer, nullable=True, index=True)
    circle = Column(String(100))
    zone = Column(String(100))
    description = Column(Text)
    boundary_geojson = Column(JSON)
    center_lat = Column(Float)
    center_lng = Column(Float)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    tickets = relationship("Ticket", back_populates="ward")
    officers = relationship("Officer", secondary="ward_officer_mapping", back_populates="wards")
    representatives = relationship("Representative", back_populates="ward")


class Officer(Base):
    """
    Officer model (extends User model for officers).

    Fields:
    - officer_id: UUID primary key (also user_id in users table)
    - user_id: Foreign key to User table
    - employee_id: Unique employee identifier
    - is_on_duty: Current availability status
    - created_at: Timestamp
    """
    __tablename__ = "officers"

    officer_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.user_id"), nullable=False, unique=True)
    employee_id = Column(String(50), unique=True)
    is_on_duty = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="officer_detail")
    wards = relationship("Ward", secondary="ward_officer_mapping", back_populates="officers")


# ============================================================================
# ASSOCIATION TABLE (Many-to-Many)
# ============================================================================
ward_officer_mapping = Table(
    "ward_officer_mapping",
    Base.metadata,
    Column("ward_id", String(36), ForeignKey("wards.ward_id"), primary_key=True),
    Column("officer_id", String(36), ForeignKey("officers.officer_id"), primary_key=True),
    Column("assigned_date", DateTime, nullable=False, default=datetime.utcnow)
)


class Ticket(Base):
    """
    Core Ticket model for grievance/complaint tracking.

    Key Fields:
    - ticket_id: UUID primary key
    - citizen_phone: Reference to citizen (WhatsApp phone number)
    - officer_phone: Reference to assigned officer (WhatsApp phone number)
    - ward_id: Ward where the issue was reported
    - latitude, longitude: GPS location of the issue
    - photo_url: URL/ID of uploaded photo
    - severity_score: LOW, MEDIUM, or HIGH (from image analysis)
    - status: Current state (see TicketStatusEnum)
    - created_at: When citizen sent initial "Hi"
    - photo_received_at: When photo/location received
    - officer_assigned_at: When officer was notified
    - resolved_at: When marked as RESOLVED
    - last_reminder_sent_at: When last reminder was sent (for 1-day & 2-day check)

    Foreign Keys:
    - citizen_phone -> users.phone (citizen who reported)
    - officer_phone -> users.phone (assigned officer)
    - ward_id -> wards.ward_id
    """
    __tablename__ = "tickets"

    ticket_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    citizen_phone = Column(String(20), ForeignKey("users.phone"), nullable=False, index=True)
    officer_phone = Column(String(20), ForeignKey("users.phone"), nullable=True, index=True)
    ward_id = Column(String(36), ForeignKey("wards.ward_id"), nullable=True, index=True)

    # Location data
    latitude = Column(Float)
    longitude = Column(Float)

    # Media & Analysis
    photo_url = Column(String(500))
    photo_id = Column(String(255))
    severity_score = Column(String(10))  # LOW, MEDIUM, HIGH

    # State tracking
    status = Column(String(20), nullable=False, default=TicketStatusEnum.INITIATED)

    # Web submission fields
    description = Column(Text)
    source = Column(String(10), nullable=False, default="WHATSAPP")  # WHATSAPP or WEB
    upvote_count = Column(Integer, nullable=False, default=0)
    moderation_status = Column(String(20), nullable=False, default="APPROVED")
    address = Column(Text)
    category = Column(String(50))
    reporter_name = Column(String(100))

    # Resolution verification
    resolution_photo_url = Column(String(500))  # Admin verification photo
    citizen_resolution_photo_url = Column(String(500))  # Citizen cleanup photo

    # Timestamps for timeline tracking
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    photo_received_at = Column(DateTime)
    officer_assigned_at = Column(DateTime)
    resolved_at = Column(DateTime)
    last_reminder_sent_at = Column(DateTime)  # Tracks 1-day and 2-day reminders

    # Relationships
    citizen = relationship("User", back_populates="tickets_created", foreign_keys=[citizen_phone])
    assigned_officer = relationship("User", back_populates="tickets_assigned", foreign_keys=[officer_phone])
    ward = relationship("Ward", back_populates="tickets")
    messages = relationship("MessageLog", back_populates="ticket", cascade="all, delete-orphan")
    actions = relationship("ActionLog", back_populates="ticket", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_tickets_status_created", "status", "created_at"),
        Index("idx_tickets_officer_status", "officer_phone", "status"),
    )


class MessageLog(Base):
    """
    Audit trail for all incoming and outgoing messages.

    Fields:
    - message_log_id: UUID primary key
    - ticket_id: Reference to ticket (if applicable)
    - direction: INCOMING or OUTGOING
    - sender: Phone number of sender
    - receiver: Phone number of receiver
    - message_type: TEXT, INTERACTIVE, LOCATION, MEDIA
    - payload: Full JSON payload from Meta API (or sent message)
    - created_at: Timestamp

    Used for:
    - Debugging webhook issues
    - Compliance and audit trail
    - Reconstructing conversation history
    """
    __tablename__ = "message_logs"

    message_log_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    external_message_id = Column(String(100), nullable=True, index=True)
    ticket_id = Column(String(36), ForeignKey("tickets.ticket_id"), nullable=True, index=True)
    direction = Column(String(10), nullable=False)  # INCOMING or OUTGOING
    sender = Column(String(20), nullable=False)
    receiver = Column(String(20), nullable=False)
    message_type = Column(String(20), nullable=False)  # TEXT, INTERACTIVE, LOCATION, MEDIA
    payload = Column(JSON, nullable=False)  # Full message payload
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Relationships
    ticket = relationship("Ticket", back_populates="messages")

    __table_args__ = (
        Index("idx_messages_ticket_created", "ticket_id", "created_at"),
    )


class ActionLog(Base):
    """
    Audit trail for all ticket state changes and system actions.

    Fields:
    - action_log_id: UUID primary key
    - ticket_id: Reference to ticket
    - action_type: STATUS_CHANGE, REMINDER_SENT, AUTO_RESOLVED, OFFICER_ASSIGNED
    - old_status: Previous status (for STATUS_CHANGE)
    - new_status: New status (for STATUS_CHANGE)
    - actor: WHO made the change (citizen, officer, system)
    - actor_phone: Phone number of actor (if applicable)
    - notes: Additional context (JSON for flexibility)
    - created_at: Timestamp

    Used for:
    - Complete audit trail of ticket lifecycle
    - Tracking reminder execution
    - Debugging and analytics
    """
    __tablename__ = "action_logs"

    action_log_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id = Column(String(36), ForeignKey("tickets.ticket_id"), nullable=False, index=True)
    action_type = Column(String(30), nullable=False)  # STATUS_CHANGE, REMINDER_SENT, etc.
    old_status = Column(String(20))  # For STATUS_CHANGE
    new_status = Column(String(20))  # For STATUS_CHANGE
    actor = Column(String(20), nullable=False)  # citizen, officer, system
    actor_phone = Column(String(20))
    notes = Column(JSON)  # Additional context
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Relationships
    ticket = relationship("Ticket", back_populates="actions")

    __table_args__ = (
        Index("idx_actions_ticket_created", "ticket_id", "created_at"),
        Index("idx_actions_action_type", "action_type", "created_at"),
    )


class Upvote(Base):
    """Upvote on a report (fingerprint-based, one per device)."""
    __tablename__ = "upvotes"

    upvote_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id = Column(String(36), ForeignKey("tickets.ticket_id"), nullable=False, index=True)
    fingerprint = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    ticket = relationship("Ticket")

    __table_args__ = (
        UniqueConstraint("ticket_id", "fingerprint", name="uq_upvote_ticket_fingerprint"),
    )


class Representative(Base):
    """Political/administrative representative linked to a ward or zone."""
    __tablename__ = "representatives"

    rep_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ward_id = Column(String(36), ForeignKey("wards.ward_id"), nullable=True, index=True)
    name = Column(String(100), nullable=False)
    title = Column(String(100), nullable=False)
    level = Column(String(20), nullable=False)  # WARD, CIRCLE, ZONE, CITY
    phone = Column(String(20))
    email = Column(String(100))
    party = Column(String(50))
    photo_url = Column(String(500))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    ward = relationship("Ward", back_populates="representatives")


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_db():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)
    # Add resolution_photo_url column to existing databases that predate it
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE tickets ADD COLUMN resolution_photo_url VARCHAR(500)"))
            conn.commit()
        except Exception:
            pass  # Column already exists
        try:
            conn.execute(text("ALTER TABLE tickets ADD COLUMN citizen_resolution_photo_url VARCHAR(500)"))
            conn.commit()
        except Exception:
            pass  # Column already exists


def get_db():
    """
    Dependency for FastAPI to get database session.
    Usage in routes:
        @app.get("/")
        def my_route(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    # Initialize database on direct execution
    init_db()
    print("Database tables created successfully!")
