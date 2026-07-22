"""Email API routes for aLEXy legal CRM.

Provides endpoints to send test emails and inspect SMTP configuration.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..services.email import (
    SMTP_CONFIGURED,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_FROM,
    SMTP_USE_TLS,
    send_welcome_email,
)

email_bp = Blueprint("email", __name__, url_prefix="/api/email")


@email_bp.post("/send-test")
@jwt_required()
def send_test():
    """Send a test welcome email to the provided address.

    **Request body**::

        {"to_email": "user@example.com"}

    Any authenticated user may use this endpoint (useful for testing).
    """
    data = request.get_json(silent=True)
    if not data or not data.get("to_email"):
        return jsonify({"error": "to_email is required"}), 400

    to_email = data["to_email"].strip()
    if not to_email:
        return jsonify({"error": "to_email cannot be empty"}), 400

    send_welcome_email(to_email, "Test User")

    return jsonify({
        "message": f"Test email sent to {to_email}",
        "smtp_configured": SMTP_CONFIGURED,
    }), 200


@email_bp.get("/settings")
@jwt_required()
def email_settings():
    """Return current SMTP configuration (credentials are excluded).

    Admin-only — only users with role 'admin' may inspect the settings.
    """
    user_id = int(get_jwt_identity())
    from ..models.user import User

    user = User.query.get(user_id)
    if not user or user.role != "admin":
        return jsonify({"error": "Admin access required"}), 403

    return jsonify({
        "configured": SMTP_CONFIGURED,
        "host": SMTP_HOST,
        "port": SMTP_PORT,
        "from_address": SMTP_FROM,
        "use_tls": SMTP_USE_TLS,
    }), 200
