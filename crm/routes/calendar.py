"""Calendar API routes for the aLEXy legal CRM.

All endpoints require JWT authentication via @jwt_required().
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..services.calendar import (
    get_events as svc_get_events,
    create_event as svc_create_event,
    update_event as svc_update_event,
    delete_event as svc_delete_event,
    get_upcoming as svc_get_upcoming,
)

calendar_bp = Blueprint("calendar", __name__, url_prefix="/api/calendar")


# ── List events ──────────────────────────────────────────────────────────────


@calendar_bp.get("/events")
@jwt_required()
def list_events():
    """Return calendar events within a date range.

    Query params:
        start (str):  Start date  YYYY-MM-DD (default today)
        end   (str):  End date    YYYY-MM-DD (default today+30)
        type  (str):  Optional event_type filter
    """
    user_id = int(get_jwt_identity())
    start = request.args.get("start", None)
    end = request.args.get("end", None)

    if not start:
        from datetime import date
        start = date.today().isoformat()
    if not end:
        from datetime import date, timedelta
        end = (date.today() + timedelta(days=30)).isoformat()

    events = svc_get_events(user_id, start, end)
    return jsonify(events), 200


# ── Upcoming events ──────────────────────────────────────────────────────────


@calendar_bp.get("/upcoming")
@jwt_required()
def upcoming_events():
    """Return upcoming events for the next N days (default 7).

    Query param: days (int, default 7)
    """
    user_id = int(get_jwt_identity())
    days = request.args.get("days", 7, type=int)

    events = svc_get_upcoming(user_id, days)
    return jsonify(events), 200


# ── Create event ─────────────────────────────────────────────────────────────


@calendar_bp.post("/events")
@jwt_required()
def create_event():
    """Create a new calendar event.

    Body: title (required), start_time (required), end_time (required),
          event_type (default "task"), description, related_task_id
    """
    user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    try:
        event = svc_create_event(user_id, data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(event), 201


# ── Update event ─────────────────────────────────────────────────────────────


@calendar_bp.patch("/events/<int:event_id>")
@jwt_required()
def update_event(event_id):
    """Partially update a calendar event.

    Body: any subset of {title, start_time, end_time, event_type,
                         description, related_task_id}
    """
    user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    try:
        event = svc_update_event(event_id, user_id, data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(event), 200


# ── Delete event ─────────────────────────────────────────────────────────────


@calendar_bp.delete("/events/<int:event_id>")
@jwt_required()
def delete_event(event_id):
    """Soft-delete a calendar event."""
    user_id = int(get_jwt_identity())

    try:
        svc_delete_event(event_id, user_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"message": "Event deleted"}), 200
