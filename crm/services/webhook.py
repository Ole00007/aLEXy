"""Webhook subscription and delivery service.

Manages webhook subscriptions per user, dispatches events to subscribed
URLs with retry logic (3 attempts with exponential backoff), and records
delivery attempts for observability.
"""

import hashlib
import hmac
import json
import logging
import os
import random
import time
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from flask import current_app
from ..extensions import db
from ..models.webhook import WebhookSubscription, WebhookDelivery

logger = logging.getLogger(__name__)

# Valid event types
VALID_EVENTS = [
    "task.created", "task.updated", "task.deleted",
    "contact.created", "contact.deleted",
    "case.created",
]

# Exponential backoff delays in seconds: 1s, 5s, 25s
RETRY_DELAYS = [1, 5, 25]
MAX_RETRIES = 3

# URL validation regex
URL_PATTERN = re.compile(
    r'^https?://'  # http:// or https://
    r'[^\s/$.?#].[^\s]*$'  # rest of URL
)


def _is_valid_url(url: str) -> bool:
    """Validate that the URL has correct format."""
    if not url or not isinstance(url, str):
        return False
    return bool(URL_PATTERN.match(url))


def _hash_secret(secret: str) -> str:
    """Hash a secret with SHA-256 and return hex string."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _generate_secret() -> str:
    """Generate a random 32-character hex string as a secret."""
    return random.randbytes(16).hex()


def _build_payload(event_type: str, payload: Dict[str, Any], secret: str) -> Dict[str, Any]:
    """Build the webhook payload envelope with signature.
    
    Returns dict with event_type, data, timestamp, and signature.
    """
    data = {
        "event_type": event_type,
        "data": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    # Compute HMAC-SHA256 signature over the JSON body
    payload_json = json.dumps(data, separators=(",", ":"))
    signature = hmac.new(
        secret.encode("utf-8"),
        payload_json.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    data["signature"] = signature
    return data


def _send_with_retry(
    url: str,
    payload: Dict[str, Any],
    secret: str,
    event_type: str,
    max_retries: int = MAX_RETRIES,
) -> Dict[str, Any]:
    """Internal helper: POST payload to URL with retry and exponential backoff.
    
    Returns dict with success, status_code, error_message, retry_count.
    """
    import requests

    envelope = _build_payload(event_type, payload, secret)
    retries = 0

    while retries <= max_retries:
        try:
            resp = requests.post(
                url,
                json=envelope,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Event": event_type,
                    "X-Webhook-Signature": envelope["signature"],
                },
                timeout=10,
            )
            success = 200 <= resp.status_code < 300
            return {
                "success": success,
                "status_code": resp.status_code,
                "error_message": None if success else resp.text[:500],
                "retry_count": retries,
            }
        except requests.exceptions.RequestException as e:
            logger.warning(
                "Webhook attempt %d/%d failed for %s: %s",
                retries + 1, max_retries, url, str(e),
            )
            if retries < max_retries:
                delay = RETRY_DELAYS[min(retries, len(RETRY_DELAYS) - 1)]
                time.sleep(delay)
            retries += 1

    return {
        "success": False,
        "status_code": None,
        "error_message": "Max retries exceeded",
        "retry_count": retries,
    }


def create_subscription(
    user_id: int,
    name: str,
    url: str,
    events: List[str],
    secret: Optional[str] = None,
) -> WebhookSubscription:
    """Create a new webhook subscription.
    
    Args:
        user_id: ID of the user owning this subscription.
        name: Human-readable name for the subscription.
        url: URL to POST webhook events to.
        events: List of event type strings (e.g. ["task.created"]).
        secret: Optional raw secret (if None, a random one is generated).
    
    Returns:
        The created WebhookSubscription.
    
    Raises:
        ValueError: If URL is invalid or events contain unknown types.
    """
    if not _is_valid_url(url):
        raise ValueError(f"Invalid URL format: {url}")

    # Validate event types
    for event in events:
        if event not in VALID_EVENTS:
            raise ValueError(f"Unknown event type: {event}")

    raw_secret = secret or _generate_secret()
    hashed_secret = _hash_secret(raw_secret)

    subscription = WebhookSubscription(
        name=name,
        url=url,
        events=events,
        secret=hashed_secret,
        created_by=user_id,
    )
    db.session.add(subscription)
    db.session.commit()
    return subscription


def delete_subscription(subscription_id: int, user_id: int) -> bool:
    """Delete a webhook subscription. Only the owner can delete.
    
    Returns True if deleted, False if not found or not owner.
    """
    subscription = WebhookSubscription.query.filter_by(
        id=subscription_id,
        created_by=user_id,
    ).first()

    if not subscription:
        return False

    db.session.delete(subscription)
    db.session.commit()
    return True


def get_subscriptions(user_id: int) -> List[WebhookSubscription]:
    """List all active subscriptions for a user."""
    return WebhookSubscription.query.filter_by(
        created_by=user_id,
        active=True,
    ).order_by(WebhookSubscription.created_at.desc()).all()


def get_active_subscriptions_for_event(event_type: str) -> List[WebhookSubscription]:
    """Get all active subscriptions that listen for the given event type."""
    return WebhookSubscription.query.filter(
        WebhookSubscription.active == True,
        WebhookSubscription.events.contains([event_type]),
    ).all()


def trigger_webhook(event_type: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Trigger webhooks for a given event type across all matching subscriptions.
    
    Args:
        event_type: Event type string (e.g. "task.created").
        payload: Dict of the event data.
    
    Returns:
        List of result dicts from _send_with_retry for each subscription.
    """
    subscriptions = get_active_subscriptions_for_event(event_type)
    results = []

    for sub in subscriptions:
        # Build a minimal envelope with event info
        event_payload = dict(payload)
        event_payload["event_type"] = event_type

        # Create a pending delivery record
        delivery = WebhookDelivery(
            subscription_id=sub.id,
            url=sub.url,
            payload=event_payload,
            status="pending",
            retry_count=0,
        )
        db.session.add(delivery)

        result = _send_with_retry(sub.url, event_payload, sub.secret, event_type)
        delivery.http_status_code = result["status_code"]
        delivery.retry_count = result["retry_count"]
        delivery.last_attempt_at = datetime.now(timezone.utc)
        delivery.error_message = result["error_message"]
        delivery.status = "success" if result["success"] else "failed"
        results.append(result)

    db.session.commit()
    return results


def send_test_webhook(url: str, events: List[str]) -> Dict[str, Any]:
    """Send a test webhook to a URL for debugging.
    
    Returns result dict from _send_with_retry.
    """
    if not _is_valid_url(url):
        return {"success": False, "error": "Invalid URL format"}

    if not events:
        return {"success": False, "error": "At least one event type required"}

    # Generate a dummy secret for the test
    secret = _generate_secret()
    payload = {
        "event_type": events[0],
        "data": {"test": True, "message": "This is a test webhook"},
    }

    result = _send_with_retry(url, payload, secret, events[0])
    return result
