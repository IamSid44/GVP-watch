"""
GVP Watch Backend - WhatsApp Client
------------------------------------
HTTP client for sending messages via Meta WhatsApp Cloud API.

This module handles all outgoing communication with citizens and officers:
- Text messages
- Interactive buttons
- Template messages
- Location pins (future enhancement)

Reference: https://developers.facebook.com/docs/whatsapp/cloud-api/messages
"""

import httpx
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from config import WHATSAPP_TOKEN, PHONE_NUMBER_ID, WHATSAPP_API_URL
from logger_config import get_logger, log_with_context
from utils import normalize_phone

logger = get_logger(__name__)


class WhatsAppClient:
    """
    Client for communicating with Meta WhatsApp Cloud API.

    All methods return a dict with:
    - success: bool (True if message sent)
    - message_id: str (if successful)
    - error: str (if failed)
    """

    def __init__(self, token: str = WHATSAPP_TOKEN, phone_number_id: str = PHONE_NUMBER_ID):
        """
        Initialize WhatsApp client with credentials.

        Args:
            token: WhatsApp API access token
            phone_number_id: Phone number ID from Meta
        """
        self.token = token
        self.phone_number_id = phone_number_id
        self.api_url = WHATSAPP_API_URL
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def _make_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make HTTP POST request to WhatsApp API.

        Args:
            payload: Message payload dict

        Returns:
            Response dict from Meta API
        """
        try:
            with httpx.Client() as client:
                response = client.post(
                    self.api_url,
                    json=payload,
                    headers=self.headers,
                    timeout=10.0
                )

                logger.debug(f"WhatsApp API request: {payload}")
                logger.debug(f"WhatsApp API response status: {response.status_code}")

                if response.status_code in [200, 201]:
                    return response.json()
                else:
                    error_msg = response.text
                    logger.error(f"WhatsApp API error ({response.status_code}): {error_msg}")
                    return {
                        "success": False,
                        "error": f"API error {response.status_code}",
                        "detail": error_msg
                    }

        except httpx.RequestError as e:
            logger.error(f"WhatsApp API request failed: {str(e)}")
            return {
                "success": False,
                "error": "Request failed",
                "detail": str(e)
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse WhatsApp API response: {str(e)}")
            return {
                "success": False,
                "error": "Invalid response format",
                "detail": str(e)
            }

    def send_text(self, recipient_phone: str, text_body: str, ticket_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a simple text message.

        Args:
            recipient_phone: Recipient's phone number
            text_body: Message text
            ticket_id: Optional ticket ID for logging context

        Returns:
            Dict with success flag and message_id (if successful) or error
        """
        try:
            recipient_phone = normalize_phone(recipient_phone)
        except ValueError as e:
            logger.error(f"Invalid phone number: {recipient_phone}")
            return {
                "success": False,
                "error": "Invalid phone number"
            }

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_phone,
            "type": "text",
            "text": {
                "body": text_body
            }
        }

        log_with_context(
            logger,
            "INFO",
            f"Sending text message to {recipient_phone}",
            ticket_id
        )

        response = self._make_request(payload)

        if "contacts" in response or "messages" in response:
            message_id = response.get("messages", [{}])[0].get("id", "unknown")
            log_with_context(
                logger,
                "INFO",
                f"Text message sent successfully (ID: {message_id})",
                ticket_id
            )
            return {
                "success": True,
                "message_id": message_id
            }
        else:
            return {
                "success": False,
                "error": response.get("error", "Unknown error"),
                "detail": response.get("detail", "")
            }

    def send_interactive_buttons(
        self,
        recipient_phone: str,
        body_text: str,
        buttons: List[Dict[str, str]],
        header_text: Optional[str] = None,
        footer_text: Optional[str] = None,
        ticket_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an interactive message with button choices.

        Args:
            recipient_phone: Recipient's phone number
            body_text: Main message body
            buttons: List of dicts with {"id": "button_id", "title": "Button Label"}
                     Example: [
                         {"id": "report_gvp", "title": "Report GVP"},
                         {"id": "cancel", "title": "Cancel"}
                     ]
            header_text: Optional header text
            footer_text: Optional footer text
            ticket_id: Optional ticket ID for logging context

        Returns:
            Dict with success flag and message_id or error
        """
        try:
            recipient_phone = normalize_phone(recipient_phone)
        except ValueError as e:
            logger.error(f"Invalid phone number: {recipient_phone}")
            return {
                "success": False,
                "error": "Invalid phone number"
            }

        # Build button array
        button_array = [
            {
                "type": "reply",
                "reply": {
                    "id": btn["id"],
                    "title": btn["title"]
                }
            }
            for btn in buttons
        ]

        # Build interactive payload
        interactive_payload = {
            "type": "button",
            "body": {
                "text": body_text
            },
            "action": {
                "buttons": button_array
            }
        }

        if header_text:
            interactive_payload["header"] = {
                "type": "text",
                "text": header_text
            }

        if footer_text:
            interactive_payload["footer"] = {
                "text": footer_text
            }

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_phone,
            "type": "interactive",
            "interactive": interactive_payload
        }

        log_with_context(
            logger,
            "INFO",
            f"Sending interactive message with {len(buttons)} buttons to {recipient_phone}",
            ticket_id
        )

        response = self._make_request(payload)

        if "messages" in response:
            message_id = response.get("messages", [{}])[0].get("id", "unknown")
            log_with_context(
                logger,
                "INFO",
                f"Interactive message sent successfully (ID: {message_id})",
                ticket_id
            )
            return {
                "success": True,
                "message_id": message_id
            }
        else:
            return {
                "success": False,
                "error": response.get("error", "Unknown error"),
                "detail": response.get("detail", "")
            }

    def send_template(
        self,
        recipient_phone: str,
        template_name: str,
        template_language: str = "en",
        parameters: Optional[List[Dict[str, str]]] = None,
        ticket_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a pre-approved template message.

        Template must be created and approved in Meta Business Manager first.

        Args:
            recipient_phone: Recipient's phone number
            template_name: Name of approved template (e.g., "ticket_confirmation")
            template_language: Template language (default "en")
            parameters: List of parameter dicts for template variables
                       Example: [{"type": "text", "text": "value1"}]
            ticket_id: Optional ticket ID for logging context

        Returns:
            Dict with success flag and message_id or error
        """
        try:
            recipient_phone = normalize_phone(recipient_phone)
        except ValueError as e:
            logger.error(f"Invalid phone number: {recipient_phone}")
            return {
                "success": False,
                "error": "Invalid phone number"
            }

        template_payload = {
            "name": template_name,
            "language": {
                "code": template_language
            }
        }

        if parameters:
            template_payload["components"] = [
                {
                    "type": "body",
                    "parameters": parameters
                }
            ]

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_phone,
            "type": "template",
            "template": template_payload
        }

        log_with_context(
            logger,
            "INFO",
            f"Sending template '{template_name}' to {recipient_phone}",
            ticket_id
        )

        response = self._make_request(payload)

        if "messages" in response:
            message_id = response.get("messages", [{}])[0].get("id", "unknown")
            log_with_context(
                logger,
                "INFO",
                f"Template message sent successfully (ID: {message_id})",
                ticket_id
            )
            return {
                "success": True,
                "message_id": message_id
            }
        else:
            return {
                "success": False,
                "error": response.get("error", "Unknown error"),
                "detail": response.get("detail", "")
            }

    def send_location(
        self,
        recipient_phone: str,
        latitude: float,
        longitude: float,
        name: Optional[str] = None,
        address: Optional[str] = None,
        ticket_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a location/map pin.

        Args:
            recipient_phone: Recipient's phone number
            latitude: Location latitude
            longitude: Location longitude
            name: Optional location name
            address: Optional address text
            ticket_id: Optional ticket ID for logging context

        Returns:
            Dict with success flag and message_id or error
        """
        try:
            recipient_phone = normalize_phone(recipient_phone)
        except ValueError as e:
            logger.error(f"Invalid phone number: {recipient_phone}")
            return {
                "success": False,
                "error": "Invalid phone number"
            }

        location_payload = {
            "latitude": latitude,
            "longitude": longitude
        }

        if name:
            location_payload["name"] = name

        if address:
            location_payload["address"] = address

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_phone,
            "type": "location",
            "location": location_payload
        }

        log_with_context(
            logger,
            "INFO",
            f"Sending location ({latitude}, {longitude}) to {recipient_phone}",
            ticket_id
        )

        response = self._make_request(payload)

        if "messages" in response:
            message_id = response.get("messages", [{}])[0].get("id", "unknown")
            log_with_context(
                logger,
                "INFO",
                f"Location message sent successfully (ID: {message_id})",
                ticket_id
            )
            return {
                "success": True,
                "message_id": message_id
            }
        else:
            return {
                "success": False,
                "error": response.get("error", "Unknown error"),
                "detail": response.get("detail", "")
            }


# Global client instance
_whatsapp_client: Optional[WhatsAppClient] = None


def get_whatsapp_client() -> WhatsAppClient:
    """
    Get or create global WhatsApp client instance.

    Returns:
        Singleton WhatsAppClient instance
    """
    global _whatsapp_client
    if _whatsapp_client is None:
        _whatsapp_client = WhatsAppClient()
    return _whatsapp_client


if __name__ == "__main__":
    # Test WhatsApp client (requires valid credentials in .env)
    client = WhatsAppClient()
    print("WhatsApp client initialized successfully!")
