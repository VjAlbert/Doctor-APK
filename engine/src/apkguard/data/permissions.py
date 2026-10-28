"""Sensitive Android permissions and their provisional severity.

Severities are starting points: M2 weighs them against the app category
(profili) so that a flashlight asking for SMS access scores far higher than a
messenger doing the same.
"""

from ..models import Severity

SENSITIVE_PERMISSIONS: dict[str, Severity] = {
    "READ_SMS": Severity.HIGH,
    "SEND_SMS": Severity.HIGH,
    "RECEIVE_SMS": Severity.HIGH,
    "SYSTEM_ALERT_WINDOW": Severity.HIGH,
    "BIND_ACCESSIBILITY_SERVICE": Severity.HIGH,
    "BIND_DEVICE_ADMIN": Severity.HIGH,
    "BIND_NOTIFICATION_LISTENER_SERVICE": Severity.HIGH,
    "REQUEST_INSTALL_PACKAGES": Severity.HIGH,
    "READ_CALL_LOG": Severity.MEDIUM,
    "READ_CONTACTS": Severity.MEDIUM,
    "RECORD_AUDIO": Severity.MEDIUM,
    "ACCESS_FINE_LOCATION": Severity.MEDIUM,
    "ACCESS_BACKGROUND_LOCATION": Severity.MEDIUM,
    "CALL_PHONE": Severity.MEDIUM,
    "PROCESS_OUTGOING_CALLS": Severity.MEDIUM,
    "MANAGE_EXTERNAL_STORAGE": Severity.MEDIUM,
    "WRITE_SETTINGS": Severity.MEDIUM,
    "CAMERA": Severity.LOW,
    "READ_PHONE_STATE": Severity.LOW,
    "RECEIVE_BOOT_COMPLETED": Severity.LOW,
    "QUERY_ALL_PACKAGES": Severity.LOW,
    "READ_EXTERNAL_STORAGE": Severity.LOW,
}
