"""
Notifications for Tank AI.

Uses CallMeBot's free WhatsApp API (no Twilio). Notifications are sent when
events occur (e.g. a dog recording has been saved).
"""

from notifications.whatsapp import notify_recording_saved

__all__ = ["notify_recording_saved"]
