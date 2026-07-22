from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..services import webhook
from ..models.webhook import WebhookSubscription

webhooks_bp = Blueprint("webhooks", __name__, url_prefix="/api/webhooks")


@webhooks_bp.post("/subscriptions")
@jwt_required()
def create_subscription():
    """Create a new webhook subscription.

    Body: {
        "name": "My Webhook",
        "url": "https://example.com/webhook",
        "events": ["task.created", "contact.created"],
        "secret": "optional-custom-secret"  // optional, random if omitted
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    name = data.get("name")
    url = data.get("url")
    events = data.get("events")
    secret = data.get("secret")

    if not name:
        return jsonify({"error": "name is required"}), 400
    if not url:
        return jsonify({"error": "url is required"}), 400
    if not events or not isinstance(events, list):
        return jsonify({"error": "events array is required"}), 400

    try:
        user_id = int(get_jwt_identity())
        sub = webhook.create_subscription(
            user_id=user_id,
            name=name,
            url=url,
            events=events,
            secret=secret,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(sub.to_dict()), 201


@webhooks_bp.get("/subscriptions")
@jwt_required()
def list_subscriptions():
    """List all active webhook subscriptions for the current user."""
    user_id = int(get_jwt_identity())
    subs = webhook.get_subscriptions(user_id)
    return jsonify([s.to_dict() for s in subs]), 200


@webhooks_bp.delete("/subscriptions/<int:sub_id>")
@jwt_required()
def delete_subscription(sub_id):
    """Delete a webhook subscription (owner only)."""
    user_id = int(get_jwt_identity())
    success = webhook.delete_subscription(sub_id, user_id)
    if not success:
        return jsonify({"error": "Subscription not found"}), 404
    return jsonify({"message": "Subscription deleted"}), 200


@webhooks_bp.post("/test")
@jwt_required()
def test_webhook():
    """Send a test webhook to a provided URL.

    Body: {
        "url": "https://example.com/webhook",
        "events": ["task.created"]
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    url = data.get("url")
    events = data.get("events")

    if not url:
        return jsonify({"error": "url is required"}), 400
    if not events or not isinstance(events, list):
        return jsonify({"error": "events array is required"}), 400

    result = webhook.send_test_webhook(url, events)
    if "error" in result:
        return jsonify(result), 400

    return jsonify({
        "message": "Test webhook sent",
        "success": result["success"],
        "status_code": result.get("status_code"),
        "retry_count": result.get("retry_count", 0),
    }), 200
