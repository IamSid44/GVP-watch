"""
GVP Watch Backend - Ticket Service Tests
------------------------------------------
Tests for ticket creation, state transitions, and business logic.
"""

import pytest
from datetime import datetime
from database import Ticket, TicketStatusEnum, ActionLog, ActionTypeEnum


class TestTicketCreation:
    """Test ticket creation flow"""

    def test_citizen_initial_message(self, ticket_service, db, sample_citizen):
        """Test citizen sending initial 'Hi' message"""
        # Mock WhatsApp client to avoid actual API calls
        result = ticket_service.handle_citizen_initial_message(sample_citizen.phone)

        assert result is True

        # Check ticket was created
        ticket = db.query(Ticket).filter(
            Ticket.citizen_phone == sample_citizen.phone
        ).first()
        assert ticket is not None
        assert ticket.status == TicketStatusEnum.INITIATED

    def test_duplicate_initial_message(self, ticket_service, db, sample_citizen):
        """Test that duplicate 'Hi' messages don't create multiple tickets"""
        # First message
        ticket_service.handle_citizen_initial_message(sample_citizen.phone)

        # Second message
        ticket_service.handle_citizen_initial_message(sample_citizen.phone)

        # Should only have one ticket
        tickets = db.query(Ticket).filter(
            Ticket.citizen_phone == sample_citizen.phone
        ).all()
        assert len(tickets) <= 1


class TestPhotoAndLocationHandling:
    """Test photo and location submission"""

    def test_photo_without_location(self, ticket_service, db, sample_citizen, sample_ward):
        """Test citizen sends photo but not location yet"""
        # Create initial ticket
        ticket_service.handle_citizen_initial_message(sample_citizen.phone)

        ticket = db.query(Ticket).filter(
            Ticket.citizen_phone == sample_citizen.phone
        ).first()

        # Manually set ward for test
        ticket.ward_id = sample_ward.ward_id
        db.commit()

        # Now send photo
        result = ticket_service.handle_photo_and_location(
            sample_citizen.phone,
            has_photo=True,
            photo_url="https://example.com/photo.jpg",
            photo_id="media_id_123"
        )

        # Ticket should still be AWAITING_PHOTO (no location yet)
        ticket_reloaded = db.query(Ticket).filter(
            Ticket.ticket_id == ticket.ticket_id
        ).first()
        assert ticket_reloaded.status == TicketStatusEnum.AWAITING_PHOTO
        assert ticket_reloaded.photo_url is not None

    def test_location_without_photo(self, ticket_service, db, sample_citizen, sample_ward):
        """Test citizen sends location but not photo yet"""
        # Create initial ticket
        ticket_service.handle_citizen_initial_message(sample_citizen.phone)

        ticket = db.query(Ticket).filter(
            Ticket.citizen_phone == sample_citizen.phone
        ).first()

        # Manually set ward for test
        ticket.ward_id = sample_ward.ward_id
        db.commit()

        # Send location
        result = ticket_service.handle_photo_and_location(
            sample_citizen.phone,
            location=(17.3850, 78.4867)
        )

        # Ticket should still be AWAITING_PHOTO (no photo yet)
        ticket_reloaded = db.query(Ticket).filter(
            Ticket.ticket_id == ticket.ticket_id
        ).first()
        assert ticket_reloaded.status == TicketStatusEnum.AWAITING_PHOTO
        assert ticket_reloaded.latitude == 17.3850
        assert ticket_reloaded.longitude == 78.4867

    def test_photo_and_location_creates_open_ticket(
        self, ticket_service, db, sample_citizen, sample_ward
    ):
        """Test that providing both photo and location creates OPEN ticket"""
        # Create initial ticket
        ticket_service.handle_citizen_initial_message(sample_citizen.phone)

        ticket = db.query(Ticket).filter(
            Ticket.citizen_phone == sample_citizen.phone
        ).first()

        # Manually set ward for test
        ticket.ward_id = sample_ward.ward_id
        db.commit()

        # Send both photo and location
        result = ticket_service.handle_photo_and_location(
            sample_citizen.phone,
            has_photo=True,
            photo_url="https://example.com/photo.jpg",
            photo_id="media_id_123",
            location=(17.3850, 78.4867)
        )

        # Should now be OPEN
        ticket_reloaded = db.query(Ticket).filter(
            Ticket.ticket_id == ticket.ticket_id
        ).first()
        assert ticket_reloaded.status == TicketStatusEnum.OPEN
        assert ticket_reloaded.photo_url is not None
        assert ticket_reloaded.latitude == 17.3850
        assert ticket_reloaded.severity_score in ["LOW", "MEDIUM", "HIGH"]


class TestOfficerResponse:
    """Test officer response handling"""

    def test_officer_marks_resolved(
        self, ticket_service, db, sample_citizen, sample_officer, sample_ward
    ):
        """Test officer marking ticket as resolved"""
        # Create and complete a ticket first
        ticket_service.handle_citizen_initial_message(sample_citizen.phone)
        ticket = db.query(Ticket).filter(
            Ticket.citizen_phone == sample_citizen.phone
        ).first()
        ticket.ward_id = sample_ward.ward_id
        ticket.status = TicketStatusEnum.OPEN
        ticket.officer_phone = sample_officer.user.phone
        db.commit()

        # Officer responds "Resolved"
        result = ticket_service.handle_officer_response(
            sample_officer.user.phone,
            ticket.ticket_id,
            "resolved"
        )

        # Check status changed to PENDING_VERIFICATION
        ticket_reloaded = db.query(Ticket).filter(
            Ticket.ticket_id == ticket.ticket_id
        ).first()
        assert ticket_reloaded.status == TicketStatusEnum.PENDING_VERIFICATION

    def test_officer_says_not_resolved(
        self, ticket_service, db, sample_citizen, sample_officer, sample_ward
    ):
        """Test officer saying ticket not resolved yet"""
        # Create and complete a ticket first
        ticket_service.handle_citizen_initial_message(sample_citizen.phone)
        ticket = db.query(Ticket).filter(
            Ticket.citizen_phone == sample_citizen.phone
        ).first()
        ticket.ward_id = sample_ward.ward_id
        ticket.status = TicketStatusEnum.OPEN
        ticket.officer_phone = sample_officer.user.phone
        db.commit()

        # Officer responds "Not Resolved"
        result = ticket_service.handle_officer_response(
            sample_officer.user.phone,
            ticket.ticket_id,
            "not_resolved"
        )

        # Should still be OPEN
        ticket_reloaded = db.query(Ticket).filter(
            Ticket.ticket_id == ticket.ticket_id
        ).first()
        assert ticket_reloaded.status == TicketStatusEnum.OPEN


class TestCitizenVerification:
    """Test citizen verification of resolution"""

    def test_citizen_confirms_resolution(
        self, ticket_service, db, sample_citizen, sample_officer, sample_ward
    ):
        """Test citizen confirming resolution"""
        # Create ticket in PENDING_VERIFICATION
        ticket_service.handle_citizen_initial_message(sample_citizen.phone)
        ticket = db.query(Ticket).filter(
            Ticket.citizen_phone == sample_citizen.phone
        ).first()
        ticket.ward_id = sample_ward.ward_id
        ticket.status = TicketStatusEnum.PENDING_VERIFICATION
        ticket.officer_phone = sample_officer.user.phone
        db.commit()

        # Citizen confirms
        result = ticket_service.handle_citizen_verification(
            sample_citizen.phone,
            ticket.ticket_id,
            verified=True
        )

        # Should be RESOLVED
        ticket_reloaded = db.query(Ticket).filter(
            Ticket.ticket_id == ticket.ticket_id
        ).first()
        assert ticket_reloaded.status == TicketStatusEnum.RESOLVED
        assert ticket_reloaded.resolved_at is not None

    def test_citizen_denies_resolution(
        self, ticket_service, db, sample_citizen, sample_officer, sample_ward
    ):
        """Test citizen denying resolution"""
        # Create ticket in PENDING_VERIFICATION
        ticket_service.handle_citizen_initial_message(sample_citizen.phone)
        ticket = db.query(Ticket).filter(
            Ticket.citizen_phone == sample_citizen.phone
        ).first()
        ticket.ward_id = sample_ward.ward_id
        ticket.status = TicketStatusEnum.PENDING_VERIFICATION
        ticket.officer_phone = sample_officer.user.phone
        db.commit()

        # Citizen denies
        result = ticket_service.handle_citizen_verification(
            sample_citizen.phone,
            ticket.ticket_id,
            verified=False
        )

        # Should stay in PENDING_VERIFICATION
        ticket_reloaded = db.query(Ticket).filter(
            Ticket.ticket_id == ticket.ticket_id
        ).first()
        assert ticket_reloaded.status == TicketStatusEnum.PENDING_VERIFICATION


class TestActionLogging:
    """Test action logging"""

    def test_status_change_logged(
        self, ticket_service, db, sample_citizen, sample_ward
    ):
        """Test that status changes are logged"""
        ticket_service.handle_citizen_initial_message(sample_citizen.phone)
        ticket = db.query(Ticket).filter(
            Ticket.citizen_phone == sample_citizen.phone
        ).first()

        # Check ActionLog
        logs = db.query(ActionLog).filter(
            ActionLog.ticket_id == ticket.ticket_id
        ).all()

        assert len(logs) > 0
        assert any(log.action_type == ActionTypeEnum.STATUS_CHANGE for log in logs)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
