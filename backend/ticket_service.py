"""
GVP Watch Backend - Ticket Service
-----------------------------------
Business logic for ticket creation, state transitions, and officer assignment.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import and_
from sqlalchemy.orm import Session

from config import (
    AUTO_RESOLVE_DAYS,
    AWAITING_PHOTO_REMINDER_HOURS,
    FIRST_REMINDER_DAYS,
    OFFICER_PHONE_DEFAULT,
)
from database import (
    ActionLog,
    ActionTypeEnum,
    MessageLog,
    Officer,
    Ticket,
    TicketStatusEnum,
    User,
    Ward,
    UserSession,
    SessionStateEnum,
)
from logger_config import get_logger, log_ticket_action
from utils import analyze_image, generate_uuid, normalize_phone
from whatsapp_client import get_whatsapp_client

logger = get_logger(__name__)
whatsapp_client = get_whatsapp_client()


class TicketService:
    def __init__(self, db: Session):
        self.db = db

    def _commit(self) -> bool:
        try:
            self.db.commit()
            return True
        except Exception as exc:
            self.db.rollback()
            logger.error(f"Database transaction failed: {exc}", exc_info=True)
            return False

    def _add_action_log(
        self,
        ticket_id: str,
        action_type: str,
        actor: str,
        old_status: Optional[str] = None,
        new_status: Optional[str] = None,
        actor_phone: Optional[str] = None,
        notes: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.db.add(
            ActionLog(
                action_log_id=generate_uuid(),
                ticket_id=ticket_id,
                action_type=action_type,
                old_status=old_status,
                new_status=new_status,
                actor=actor,
                actor_phone=actor_phone,
                notes=notes,
                created_at=datetime.utcnow(),
            )
        )

    def _log_outgoing_message(
        self,
        receiver: str,
        message_type: str,
        payload: Dict[str, Any],
        ticket_id: Optional[str],
        response: Dict[str, Any],
        sender: str = "BOT",
    ) -> None:
        self.db.add(
            MessageLog(
                message_log_id=generate_uuid(),
                external_message_id=response.get("message_id"),
                ticket_id=ticket_id,
                direction="OUTGOING",
                sender=sender,
                receiver=receiver,
                message_type=message_type,
                payload={
                    "request": payload,
                    "response": response,
                },
                created_at=datetime.utcnow(),
            )
        )

    def _send_text(self, to_phone: str, text: str, ticket_id: Optional[str] = None) -> Dict[str, Any]:
        result = whatsapp_client.send_text(to_phone, text, ticket_id=ticket_id)
        self._log_outgoing_message(
            receiver=to_phone,
            message_type="TEXT",
            payload={"text": text},
            ticket_id=ticket_id,
            response=result,
        )
        self._commit()
        return result

    def _send_buttons(
        self,
        to_phone: str,
        body_text: str,
        buttons,
        ticket_id: Optional[str] = None,
        header_text: Optional[str] = None,
        footer_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        result = whatsapp_client.send_interactive_buttons(
            to_phone,
            body_text,
            buttons,
            header_text=header_text,
            footer_text=footer_text,
            ticket_id=ticket_id,
        )
        self._log_outgoing_message(
            receiver=to_phone,
            message_type="INTERACTIVE",
            payload={
                "body": body_text,
                "buttons": buttons,
                "header": header_text,
                "footer": footer_text,
            },
            ticket_id=ticket_id,
            response=result,
        )
        self._commit()
        return result

    def _has_reminder_with_stage(self, ticket_id: str, stage: str) -> bool:
        actions = (
            self.db.query(ActionLog)
            .filter(
                ActionLog.ticket_id == ticket_id,
                ActionLog.action_type == ActionTypeEnum.REMINDER_SENT,
            )
            .all()
        )
        for action in actions:
            if isinstance(action.notes, dict) and action.notes.get("stage") == stage:
                return True
        return False

    def process_user_input(self, sender_phone: str, event: dict) -> bool:
        try:
            sender_phone = normalize_phone(sender_phone)
        except ValueError as exc:
            logger.error(f"Invalid phone: {sender_phone} | Error: {exc}")
            return False

        text_body = event.get('content', '').strip().lower() if event.get('message_type') == 'text' else ''
        session = self.db.query(UserSession).filter(UserSession.phone == sender_phone).first()

        if text_body in ['hi', 'hello', 'hey', 'start']:
            if session:
                self.db.delete(session)
                self._commit()
            session = None

        if not session:
            session = UserSession(phone=sender_phone, current_state=SessionStateEnum.SELECTING_LANGUAGE, temp_data={})
            self.db.add(session)
            self._commit()
            
            self._send_buttons(
                sender_phone,
                "Welcome to GVP Watch! Please select your language:",
                [
                    {"id": "lang_en", "title": "English"},
                    {"id": "lang_te", "title": "Telugu"},
                    {"id": "lang_hi", "title": "Hindi"}
                ],
                header_text="Language"
            )
            return True

        message_type = event.get("message_type")
        state = session.current_state

        if state == SessionStateEnum.SELECTING_LANGUAGE:
            if message_type == "interactive" and event.get("button_reply") in ["lang_en", "lang_te", "lang_hi"]:
                session.language = event.get("button_reply").replace("lang_", "")
                session.current_state = SessionStateEnum.MAIN_MENU
                self._commit()
                self._send_buttons(
                    sender_phone,
                    "Please select an option below:",
                    [
                        {"id": "menu_report", "title": "Report GVP"},
                        {"id": "menu_track", "title": "Track Ticket"},
                        {"id": "menu_website", "title": "Open Website"}
                    ],
                    header_text="Main Menu"
                )
            else:
                self._send_buttons(
                    sender_phone,
                    "Welcome to GVP Watch! Please select your language:",
                    [
                        {"id": "lang_en", "title": "English"},
                        {"id": "lang_te", "title": "Telugu"},
                        {"id": "lang_hi", "title": "Hindi"}
                    ],
                    header_text="Language"
                )

        elif state == SessionStateEnum.MAIN_MENU:
            if message_type == "interactive":
                btn_id = event.get("button_reply")
                if btn_id == "menu_report":
                    session.current_state = SessionStateEnum.AWAITING_PHOTO
                    self._commit()
                    self._send_text(sender_phone, "Please upload a photo of the garbage/waste.")
                elif btn_id == "menu_track":
                    session.current_state = SessionStateEnum.AWAITING_TRACK_ID
                    self._commit()
                    self._send_text(sender_phone, "Please enter your Ticket ID to track its status.")
                elif btn_id == "menu_website":
                    self._send_text(sender_phone, "Visit our website for more information: https://gvpwatch.example.com\n\nThank you!")
                    self.db.delete(session)
                    self._commit()
            else:
                self._send_buttons(
                    sender_phone,
                    "Please select an option below:",
                    [
                        {"id": "menu_report", "title": "Report GVP"},
                        {"id": "menu_track", "title": "Track Ticket"},
                        {"id": "menu_website", "title": "Open Website"}
                    ],
                    header_text="Main Menu"
                )

        elif state == SessionStateEnum.AWAITING_TRACK_ID:
            if message_type == "text":
                ticket_id = event.get("content", "").strip()
                ticket = self.db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
                if ticket:
                    self._send_text(sender_phone, f"Ticket: {ticket.ticket_id}\nStatus: {ticket.status}\nSeverity: {ticket.severity_score}\nLocation: {ticket.latitude}, {ticket.longitude}")
                else:
                    self._send_text(sender_phone, "Ticket not found. Please check the ID and try again, or type 'Hi' to restart.")
                self.db.delete(session)
                self._commit()

        elif state == SessionStateEnum.AWAITING_PHOTO:
            if message_type == "image":
                tmp = session.temp_data.copy() if session.temp_data else {}
                tmp["photo_id"] = event.get("media", {}).get("id")
                tmp["photo_url"] = event.get("media", {}).get("url")
                session.temp_data = tmp
                session.current_state = SessionStateEnum.AWAITING_LOCATION
                self._commit()
                self._send_text(sender_phone, "Photo received! Now, please send a location pin.")
            else:
                self._send_text(sender_phone, "Please upload an image/photo of the waste.")

        elif state == SessionStateEnum.AWAITING_LOCATION:
            if message_type == "location":
                loc = event.get("location", {})
                tmp = session.temp_data.copy() if session.temp_data else {}
                tmp["latitude"] = loc.get("latitude")
                tmp["longitude"] = loc.get("longitude")
                session.temp_data = tmp
                session.current_state = SessionStateEnum.AWAITING_SEVERITY
                self._commit()
                self._send_buttons(
                    sender_phone,
                    "How severe is this issue?",
                    [
                        {"id": "sev_low", "title": "Low"},
                        {"id": "sev_medium", "title": "Medium"},
                        {"id": "sev_high", "title": "High"}
                    ]
                )
            else:
                self._send_text(sender_phone, "Please send a location pin.")

        elif state == SessionStateEnum.AWAITING_SEVERITY:
            if message_type == "interactive" and event.get("button_reply") in ["sev_low", "sev_medium", "sev_high"]:
                tmp = session.temp_data.copy() if session.temp_data else {}
                tmp["severity"] = event.get("button_reply").replace("sev_", "").upper()
                session.temp_data = tmp
                session.current_state = SessionStateEnum.AWAITING_TYPE
                self._commit()
                self._send_text(sender_phone, "Great. Finally, please type any additional info or the type of waste.")
            else:
                self._send_buttons(
                    sender_phone,
                    "Please select the severity:",
                    [
                        {"id": "sev_low", "title": "Low"},
                        {"id": "sev_medium", "title": "Medium"},
                        {"id": "sev_high", "title": "High"}
                    ]
                )

        elif state == SessionStateEnum.AWAITING_TYPE:
            if message_type == "text":
                tmp = session.temp_data.copy() if session.temp_data else {}
                tmp["info"] = event.get("content", "").strip()
                
                citizen_user = self.db.query(User).filter(User.phone == sender_phone).first()
                if not citizen_user:
                    citizen_user = User(user_id=generate_uuid(), phone=sender_phone, role=UserRoleEnum.CITIZEN)
                    self.db.add(citizen_user)

                ticket_id = "TKT-" + generate_uuid()[:8].upper()
                new_ticket = Ticket(
                    ticket_id=ticket_id,
                    citizen_phone=sender_phone,
                    status=TicketStatusEnum.OPEN,
                    severity_score=tmp.get("severity"),
                    latitude=tmp.get("latitude"),
                    longitude=tmp.get("longitude"),
                    photo_url=tmp.get("photo_url") or tmp.get("photo_id"),
                    created_at=datetime.utcnow(),
                    photo_received_at=datetime.utcnow()
                )
                self.db.add(new_ticket)
                self._commit()
                
                self._send_text(sender_phone, f"Thank you! Your report has been submitted.\nYour ticket ID is: {ticket_id}\nWe will review it shortly.")
                
                self.db.delete(session)
                self._commit()

        return True


    def handle_citizen_initial_message(self, citizen_phone: str) -> bool:
        try:
            citizen_phone = normalize_phone(citizen_phone)
        except ValueError as exc:
            logger.error(f"Invalid citizen phone: {citizen_phone} | Error: {exc}")
            return False

        existing_ticket = (
            self.db.query(Ticket)
            .filter(
                and_(
                    Ticket.citizen_phone == citizen_phone,
                    Ticket.status.in_(
                        [
                            TicketStatusEnum.INITIATED,
                            TicketStatusEnum.AWAITING_PHOTO,
                            TicketStatusEnum.OPEN,
                            TicketStatusEnum.PENDING_VERIFICATION,
                        ]
                    ),
                )
            )
            .order_by(Ticket.created_at.desc())
            .first()
        )

        if existing_ticket:
            if existing_ticket.status in [TicketStatusEnum.OPEN, TicketStatusEnum.PENDING_VERIFICATION]:
                self._send_text(
                    citizen_phone,
                    "You already have an active report. Please wait for status updates.",
                    ticket_id=existing_ticket.ticket_id,
                )
                return True
            if existing_ticket.status == TicketStatusEnum.AWAITING_PHOTO:
                self._send_text(
                    citizen_phone,
                    "Please send one photo and your live location to continue.",
                    ticket_id=existing_ticket.ticket_id,
                )
                return True
            self._send_buttons(
                citizen_phone,
                "Click Report a GVP to continue with your complaint.",
                [
                    {"id": "report_gvp", "title": "Report a GVP"},
                    {"id": "cancel", "title": "Cancel"},
                ],
                header_text="GVP Watch",
                ticket_id=existing_ticket.ticket_id,
            )
            return True

        citizen_user = self.db.query(User).filter(User.phone == citizen_phone).first()
        if not citizen_user:
            self.db.add(
                User(
                    user_id=generate_uuid(),
                    phone=citizen_phone,
                    role="CITIZEN",
                    name="Citizen",
                    is_active=True,
                )
            )

        ticket = Ticket(
            ticket_id=f"tk-{generate_uuid()[:8]}",
            citizen_phone=citizen_phone,
            status=TicketStatusEnum.INITIATED,
            created_at=datetime.utcnow(),
        )
        self.db.add(ticket)
        self._add_action_log(
            ticket_id=ticket.ticket_id,
            action_type=ActionTypeEnum.STATUS_CHANGE,
            old_status=None,
            new_status=TicketStatusEnum.INITIATED,
            actor="SYSTEM",
            actor_phone=citizen_phone,
        )

        if not self._commit():
            return False

        log_ticket_action(
            logger,
            "STATUS_CHANGE",
            ticket.ticket_id,
            {"from": "NONE", "to": TicketStatusEnum.INITIATED, "actor": "citizen"},
        )

        self._send_buttons(
            citizen_phone,
            "Hello! We help you report Garbage Vulnerable Points (GVPs) in your area.",
            [
                {"id": "report_gvp", "title": "Report a GVP"},
                {"id": "cancel", "title": "Cancel"},
            ],
            header_text="GVP Watch",
            ticket_id=ticket.ticket_id,
        )
        return True

    def start_citizen_report(self, citizen_phone: str) -> bool:
        try:
            citizen_phone = normalize_phone(citizen_phone)
        except ValueError as exc:
            logger.error(f"Invalid citizen phone: {citizen_phone} | Error: {exc}")
            return False

        ticket = (
            self.db.query(Ticket)
            .filter(
                and_(
                    Ticket.citizen_phone == citizen_phone,
                    Ticket.status.in_(
                        [
                            TicketStatusEnum.INITIATED,
                            TicketStatusEnum.AWAITING_PHOTO,
                            TicketStatusEnum.OPEN,
                            TicketStatusEnum.PENDING_VERIFICATION,
                        ]
                    ),
                )
            )
            .order_by(Ticket.created_at.desc())
            .first()
        )

        if not ticket:
            return self.handle_citizen_initial_message(citizen_phone)

        if ticket.status == TicketStatusEnum.INITIATED:
            ticket.status = TicketStatusEnum.AWAITING_PHOTO
            self._add_action_log(
                ticket_id=ticket.ticket_id,
                action_type=ActionTypeEnum.STATUS_CHANGE,
                old_status=TicketStatusEnum.INITIATED,
                new_status=TicketStatusEnum.AWAITING_PHOTO,
                actor="CITIZEN",
                actor_phone=citizen_phone,
            )
            if not self._commit():
                return False

        self._send_text(
            citizen_phone,
            "Please send one photo of the issue and your live location.",
            ticket_id=ticket.ticket_id,
        )
        return True

    def handle_photo_and_location(
        self,
        citizen_phone: str,
        has_photo: bool = False,
        photo_url: Optional[str] = None,
        photo_id: Optional[str] = None,
        location: Optional[Tuple[float, float]] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> bool:
        try:
            citizen_phone = normalize_phone(citizen_phone)
        except ValueError:
            logger.error(f"Invalid citizen phone: {citizen_phone}")
            return False

        ticket = (
            self.db.query(Ticket)
            .filter(
                and_(
                    Ticket.citizen_phone == citizen_phone,
                    Ticket.status.in_([TicketStatusEnum.INITIATED, TicketStatusEnum.AWAITING_PHOTO]),
                )
            )
            .order_by(Ticket.created_at.desc())
            .first()
        )

        if not ticket:
            self._send_text(citizen_phone, "Please send 'Hi' and start a new report.")
            return False

        if ticket.status == TicketStatusEnum.INITIATED:
            ticket.status = TicketStatusEnum.AWAITING_PHOTO
            self._add_action_log(
                ticket_id=ticket.ticket_id,
                action_type=ActionTypeEnum.STATUS_CHANGE,
                old_status=TicketStatusEnum.INITIATED,
                new_status=TicketStatusEnum.AWAITING_PHOTO,
                actor="SYSTEM",
                actor_phone=citizen_phone,
            )

        if location:
            latitude, longitude = location

        if has_photo:
            ticket.photo_received_at = datetime.utcnow()
            if photo_url:
                ticket.photo_url = photo_url
            if photo_id:
                ticket.photo_id = photo_id
            severity_source = photo_id or photo_url
            if severity_source:
                ticket.severity_score = analyze_image(severity_source)

        if latitude is not None and longitude is not None:
            ticket.latitude = latitude
            ticket.longitude = longitude

        has_photo_data = bool(ticket.photo_url or ticket.photo_id)
        has_location_data = ticket.latitude is not None and ticket.longitude is not None

        if has_photo_data and has_location_data:
            return self._create_and_assign_ticket(ticket, citizen_phone)

        if not self._commit():
            return False

        missing = []
        if not has_photo_data:
            missing.append("a photo")
        if not has_location_data:
            missing.append("your live location")

        self._send_text(
            citizen_phone,
            f"Thanks. Please send {' and '.join(missing)} to complete the report.",
            ticket_id=ticket.ticket_id,
        )
        return True

    def _create_and_assign_ticket(self, ticket: Ticket, citizen_phone: str) -> bool:
        ward = None
        if ticket.ward_id:
            ward = self.db.query(Ward).filter(Ward.ward_id == ticket.ward_id).first()
        if not ward:
            ward = self.db.query(Ward).first()

        if not ward:
            logger.error("No wards configured. Cannot assign ticket.")
            self._add_action_log(
                ticket_id=ticket.ticket_id,
                action_type=ActionTypeEnum.OFFICER_ASSIGNED,
                actor="SYSTEM",
                notes={"error": "no_ward_configured"},
            )
            if not self._commit():
                return False
            self._send_text(
                citizen_phone,
                "Your complaint is received but ward configuration is missing. The admin has been alerted.",
                ticket_id=ticket.ticket_id,
            )
            if OFFICER_PHONE_DEFAULT:
                self._send_text(
                    OFFICER_PHONE_DEFAULT,
                    f"ALERT: Ticket {ticket.ticket_id} could not be assigned because no ward exists.",
                    ticket_id=ticket.ticket_id,
                )
            return False

        old_status = ticket.status
        ticket.status = TicketStatusEnum.OPEN
        ticket.ward_id = ward.ward_id
        ticket.officer_assigned_at = datetime.utcnow()

        self._add_action_log(
            ticket_id=ticket.ticket_id,
            action_type=ActionTypeEnum.STATUS_CHANGE,
            old_status=old_status,
            new_status=TicketStatusEnum.OPEN,
            actor="SYSTEM",
            notes={"ward_id": ward.ward_id, "severity": ticket.severity_score},
        )

        officers = (
            self.db.query(Officer)
            .filter(
                and_(
                    Officer.user.has(is_active=True),
                    Officer.is_on_duty,
                    Officer.wards.any(Ward.ward_id == ward.ward_id),
                )
            )
            .all()
        )

        if not officers:
            logger.warning(f"No active officers found for ward {ward.ward_name}")
            self._add_action_log(
                ticket_id=ticket.ticket_id,
                action_type=ActionTypeEnum.OFFICER_ASSIGNED,
                actor="SYSTEM",
                notes={"ward_id": ward.ward_id, "no_active_officer": True},
            )
            if not self._commit():
                return False
            self._send_text(
                citizen_phone,
                "Your report is created, but no active ward officer is currently available. Admin has been alerted.",
                ticket_id=ticket.ticket_id,
            )
            if OFFICER_PHONE_DEFAULT:
                self._send_text(
                    OFFICER_PHONE_DEFAULT,
                    f"ALERT: No active officer for ward {ward.ward_name}. Ticket {ticket.ticket_id} needs manual assignment.",
                    ticket_id=ticket.ticket_id,
                )
            return True

        for officer in officers:
            officer_phone = officer.user.phone
            details = (
                f"New Ticket: {ticket.ticket_id}\n"
                f"Location: {ticket.latitude:.6f}, {ticket.longitude:.6f}\n"
                f"Severity: {ticket.severity_score}\n"
                f"Ward: {ward.ward_name}\n"
                "Reply with '<ticket_id> resolved' after fixing the issue."
            )
            self._send_text(officer_phone, details, ticket_id=ticket.ticket_id)
            self._add_action_log(
                ticket_id=ticket.ticket_id,
                action_type=ActionTypeEnum.OFFICER_ASSIGNED,
                actor="SYSTEM",
                actor_phone=officer_phone,
                notes={"ward_id": ward.ward_id},
            )
            if not ticket.officer_phone:
                ticket.officer_phone = officer_phone

        if not self._commit():
            return False

        log_ticket_action(
            logger,
            "STATUS_CHANGE",
            ticket.ticket_id,
            {
                "from": old_status,
                "to": TicketStatusEnum.OPEN,
                "officers_assigned": len(officers),
                "severity": ticket.severity_score,
            },
        )

        self._send_text(
            citizen_phone,
            "Your report has been created and shared with ward officers.",
            ticket_id=ticket.ticket_id,
        )
        return True

    def handle_officer_response(self, officer_phone: str, ticket_id_param: str, action: str) -> bool:
        try:
            officer_phone = normalize_phone(officer_phone)
        except ValueError:
            logger.error(f"Invalid officer phone: {officer_phone}")
            return False

        ticket = self.db.query(Ticket).filter(Ticket.ticket_id == ticket_id_param).first()
        if not ticket:
            self._send_text(officer_phone, f"Ticket {ticket_id_param} not found.")
            return False

        normalized_action = action.lower().strip()
        if normalized_action == "resolved":
            old_status = ticket.status
            ticket.status = TicketStatusEnum.PENDING_VERIFICATION
            ticket.officer_phone = officer_phone
            ticket.last_reminder_sent_at = None

            self._add_action_log(
                ticket_id=ticket.ticket_id,
                action_type=ActionTypeEnum.STATUS_CHANGE,
                old_status=old_status,
                new_status=TicketStatusEnum.PENDING_VERIFICATION,
                actor="OFFICER",
                actor_phone=officer_phone,
            )
            if not self._commit():
                return False

            self._send_buttons(
                ticket.citizen_phone,
                "The officer marked your complaint as resolved. Please confirm.",
                [
                    {"id": "confirmed", "title": "Confirmed"},
                    {"id": "not_resolved", "title": "Not Resolved"},
                ],
                ticket_id=ticket.ticket_id,
            )
            self._send_text(
                officer_phone,
                f"Ticket {ticket.ticket_id} moved to verification. Waiting for citizen confirmation.",
                ticket_id=ticket.ticket_id,
            )
            return True

        if normalized_action == "not_resolved":
            self._send_text(
                officer_phone,
                f"Noted. Continue working on {ticket.ticket_id}.",
                ticket_id=ticket.ticket_id,
            )
            self._add_action_log(
                ticket_id=ticket.ticket_id,
                action_type=ActionTypeEnum.MESSAGE_SENT,
                actor="OFFICER",
                actor_phone=officer_phone,
                notes={"message": "officer_not_resolved"},
            )
            self._commit()
            return True

        self._send_text(
            officer_phone,
            "Invalid response format. Reply with '<ticket_id> resolved' or '<ticket_id> not resolved'.",
            ticket_id=ticket.ticket_id,
        )
        return False

    def handle_citizen_verification(self, citizen_phone: str, ticket_id_param: str, verified: bool) -> bool:
        try:
            citizen_phone = normalize_phone(citizen_phone)
        except ValueError:
            logger.error(f"Invalid citizen phone: {citizen_phone}")
            return False

        ticket = (
            self.db.query(Ticket)
            .filter(
                and_(
                    Ticket.ticket_id == ticket_id_param,
                    Ticket.citizen_phone == citizen_phone,
                )
            )
            .first()
        )
        if not ticket:
            logger.warning(f"Ticket {ticket_id_param} not found for citizen {citizen_phone}")
            return False

        if verified:
            old_status = ticket.status
            ticket.status = TicketStatusEnum.RESOLVED
            ticket.resolved_at = datetime.utcnow()

            self._add_action_log(
                ticket_id=ticket.ticket_id,
                action_type=ActionTypeEnum.STATUS_CHANGE,
                old_status=old_status,
                new_status=TicketStatusEnum.RESOLVED,
                actor="CITIZEN",
                actor_phone=citizen_phone,
            )
            if not self._commit():
                return False

            self._send_text(
                citizen_phone,
                "Thanks for confirming. The ticket is now closed.",
                ticket_id=ticket.ticket_id,
            )
            if ticket.officer_phone:
                self._send_text(
                    ticket.officer_phone,
                    f"Citizen confirmed {ticket.ticket_id} as resolved.",
                    ticket_id=ticket.ticket_id,
                )
            return True

        ticket.last_reminder_sent_at = None
        self._add_action_log(
            ticket_id=ticket.ticket_id,
            action_type=ActionTypeEnum.MESSAGE_SENT,
            actor="CITIZEN",
            actor_phone=citizen_phone,
            notes={"message": "citizen_not_resolved_keep_pending_verification"},
        )
        if not self._commit():
            return False

        self._send_text(
            citizen_phone,
            "Noted. The assigned officer has been informed.",
            ticket_id=ticket.ticket_id,
        )
        if ticket.officer_phone:
            self._send_text(
                ticket.officer_phone,
                f"Citizen marked {ticket.ticket_id} as not resolved. Please revisit and reply once resolved.",
                ticket_id=ticket.ticket_id,
            )
        return True

    def _get_pending_verification_start(self, ticket_id: str) -> Optional[datetime]:
        action = (
            self.db.query(ActionLog)
            .filter(
                ActionLog.ticket_id == ticket_id,
                ActionLog.action_type == ActionTypeEnum.STATUS_CHANGE,
                ActionLog.new_status == TicketStatusEnum.PENDING_VERIFICATION,
            )
            .order_by(ActionLog.created_at.desc())
            .first()
        )
        if action:
            return action.created_at
        return None

    def check_and_send_reminders(self) -> int:
        now = datetime.utcnow()
        reminder_count = 0

        tickets = self.db.query(Ticket).filter(Ticket.status == TicketStatusEnum.PENDING_VERIFICATION).all()
        for ticket in tickets:
            try:
                if ticket.last_reminder_sent_at is not None:
                    continue

                pending_since = self._get_pending_verification_start(ticket.ticket_id) or ticket.created_at
                if pending_since > (now - timedelta(days=FIRST_REMINDER_DAYS)):
                    continue

                result = self._send_text(
                    ticket.citizen_phone,
                    f"Reminder: Please confirm status for ticket {ticket.ticket_id}.",
                    ticket_id=ticket.ticket_id,
                )
                if result.get("success"):
                    ticket.last_reminder_sent_at = now
                    self._add_action_log(
                        ticket_id=ticket.ticket_id,
                        action_type=ActionTypeEnum.REMINDER_SENT,
                        actor="SYSTEM",
                        notes={"stage": "PENDING_VERIFICATION", "day": FIRST_REMINDER_DAYS},
                    )
                    if self._commit():
                        reminder_count += 1
                        log_ticket_action(
                            logger,
                            "REMINDER_SENT",
                            ticket.ticket_id,
                            {"stage": "PENDING_VERIFICATION", "day": FIRST_REMINDER_DAYS},
                        )
            except Exception as exc:
                self.db.rollback()
                logger.error(f"Error sending reminder for {ticket.ticket_id}: {exc}", exc_info=True)

        return reminder_count

    def check_and_auto_resolve(self) -> int:
        now = datetime.utcnow()
        days_after_reminder = max(AUTO_RESOLVE_DAYS - FIRST_REMINDER_DAYS, 1)
        threshold = now - timedelta(days=days_after_reminder)
        resolve_count = 0

        tickets = (
            self.db.query(Ticket)
            .filter(
                Ticket.status == TicketStatusEnum.PENDING_VERIFICATION,
                Ticket.last_reminder_sent_at.isnot(None),
                Ticket.last_reminder_sent_at <= threshold,
            )
            .all()
        )

        for ticket in tickets:
            try:
                old_status = ticket.status
                ticket.status = TicketStatusEnum.UNRESPONSIVE
                ticket.resolved_at = now

                self._add_action_log(
                    ticket_id=ticket.ticket_id,
                    action_type=ActionTypeEnum.AUTO_RESOLVED,
                    old_status=old_status,
                    new_status=TicketStatusEnum.UNRESPONSIVE,
                    actor="SYSTEM",
                    notes={"reason": "no_citizen_response_after_reminder"},
                )

                if not self._commit():
                    continue

                resolve_count += 1
                if ticket.officer_phone:
                    self._send_text(
                        ticket.officer_phone,
                        f"Ticket {ticket.ticket_id} auto-resolved due to no citizen response.",
                        ticket_id=ticket.ticket_id,
                    )
            except Exception as exc:
                self.db.rollback()
                logger.error(f"Error auto-resolving {ticket.ticket_id}: {exc}", exc_info=True)

        return resolve_count

    def check_and_send_awaiting_photo_reminders(self) -> int:
        now = datetime.utcnow()
        threshold = now - timedelta(hours=AWAITING_PHOTO_REMINDER_HOURS)
        reminder_count = 0

        tickets = (
            self.db.query(Ticket)
            .filter(
                Ticket.status == TicketStatusEnum.AWAITING_PHOTO,
                Ticket.created_at <= threshold,
            )
            .all()
        )

        for ticket in tickets:
            try:
                if self._has_reminder_with_stage(ticket.ticket_id, "AWAITING_PHOTO"):
                    continue

                missing = []
                if not (ticket.photo_url or ticket.photo_id):
                    missing.append("a photo")
                if ticket.latitude is None or ticket.longitude is None:
                    missing.append("your location")

                result = self._send_text(
                    ticket.citizen_phone,
                    f"Reminder: please send {' and '.join(missing)} to continue ticket {ticket.ticket_id}.",
                    ticket_id=ticket.ticket_id,
                )
                if result.get("success"):
                    self._add_action_log(
                        ticket_id=ticket.ticket_id,
                        action_type=ActionTypeEnum.REMINDER_SENT,
                        actor="SYSTEM",
                        notes={
                            "stage": "AWAITING_PHOTO",
                            "timeout_hours": AWAITING_PHOTO_REMINDER_HOURS,
                            "missing": missing,
                        },
                    )
                    if self._commit():
                        reminder_count += 1
            except Exception as exc:
                self.db.rollback()
                logger.error(
                    f"Error sending awaiting-photo reminder for {ticket.ticket_id}: {exc}",
                    exc_info=True,
                )

        return reminder_count


if __name__ == "__main__":
    print("Ticket Service module loaded successfully!")
