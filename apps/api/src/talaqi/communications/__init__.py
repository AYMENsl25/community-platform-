"""In-app notification projection, preferences, and inbox API."""

from talaqi.communications.repository import NotificationRepository
from talaqi.communications.service import NotificationProjectionHandler

__all__ = ["NotificationProjectionHandler", "NotificationRepository"]
