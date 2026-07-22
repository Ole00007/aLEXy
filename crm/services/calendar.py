"""Calendar service for managing CalendarEvent records.

Provides CRUD operations, overlap validation, and query helpers
for the aLEXy legal CRM internal calendar.
"""

from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any

from ..extensions import db
from ..models.calendar import CalendarEvent


def get_events(user_id: int, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """Return events in the given date range for the specified user.

    Args:
        user_id: Owner of the events.
        start_date: ISO date string (YYYY-MM-DD), inclusive.
        end_date: ISO date string (YYYY-MM-DD), inclusive.

    Returns:
        List of event dicts sorted by start_time.
    """
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)

    events = (
        CalendarEvent.query
        .filter_by(user_id=user_id, is_deleted=False)
        .filter(CalendarEvent.start_time <= end_dt)
        .filter(CalendarEvent.end_time >= start_dt)
        .order_by(CalendarEvent.start_time)
        .all()
    )
    return [e.to_dict() for e in events]


def create_event(user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new calendar event, validating overlap and required fields.

    Args:
        user_id: Owner of the new event.
        data: Dict with title (required), start_time, end_time, event_type,
              description, and/or related_task_id.

    Returns:
        Created event dict.

    Raises:
        ValueError: On missing fields or overlapping time.
    """
    if not data.get("title"):
        raise ValueError("title is required")
    if not data.get("start_time"):
        raise ValueError("start_time is required")
    if not data.get("end_time"):
        raise ValueError("end_time is required")

    # Validate overlap with existing events for this user
    start_dt = datetime.fromisoformat(data["start_time"])
    end_dt = datetime.fromisoformat(data["end_time"])
    if _has_overlap(user_id, start_dt, end_dt):
        raise ValueError("Event overlaps with an existing event")

    event = CalendarEvent(
        user_id=user_id,
        title=data["title"],
        description=data.get("description"),
        start_time=start_dt,
        end_time=end_dt,
        event_type=data.get("event_type", "task"),
        related_task_id=data.get("related_task_id"),
    )
    db.session.add(event)
    db.session.commit()
    return event.to_dict()


def update_event(event_id: int, user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Partially update a calendar event owned by the given user.

    Args:
        event_id: ID of the event to update.
        user_id: Owner of the event.
        data: Dict of fields to update (any of: title, description, start_time,
              end_time, event_type, related_task_id).

    Returns:
        Updated event dict.

    Raises:
        ValueError: If event not found, not owned by user, or overlaps remain.
    """
    event = CalendarEvent.query.filter_by(id=event_id, user_id=user_id, is_deleted=False).first()
    if not event:
        raise ValueError("Event not found or not owned by this user")

    if "start_time" in data or "end_time" in data:
        start_dt = datetime.fromisoformat(data.get("start_time", event.start_time.isoformat()))
        end_dt = datetime.fromisoformat(data.get("end_time", event.end_time.isoformat()))
        if _has_overlap(user_id, start_dt, end_dt, exclude_event_id=event.id):
            raise ValueError("Event overlaps with an existing event")

    for field, value in data.items():
        if value is not None and hasattr(event, field):
            setattr(event, field, value)

    db.session.commit()
    return event.to_dict()


def delete_event(event_id: int, user_id: int) -> None:
    """Soft-delete a calendar event owned by the given user.

    Args:
        event_id: ID of the event to delete.
        user_id: Owner of the event.

    Raises:
        ValueError: If event not found or not owned by user.
    """
    event = CalendarEvent.query.filter_by(id=event_id, user_id=user_id, is_deleted=False).first()
    if not event:
        raise ValueError("Event not found or not owned by this user")
    event.is_deleted = True
    db.session.commit()


def get_upcoming(user_id: int, days: int = 7) -> List[Dict[str, Any]]:
    """Return upcoming events for the user in the next N days.

    Args:
        user_id: Owner of the events.
        days: Number of days ahead to look. Defaults to 7.

    Returns:
        List of event dicts sorted by start_time.
    """
    now = datetime.utcnow()
    until = now + timedelta(days=days)

    events = (
        CalendarEvent.query
        .filter_by(user_id=user_id, is_deleted=False)
        .filter(CalendarEvent.start_time.between(now, until))
        .order_by(CalendarEvent.start_time)
        .all()
    )
    return [e.to_dict() for e in events]


# ── Internal helpers ─────────────────────────────────────────────────────────


def _has_overlap(user_id: int, start_dt: datetime, end_dt: datetime,
                 exclude_event_id: Optional[int] = None) -> bool:
    """Check if a time range overlaps with any existing event for the user.

    Two ranges [s1, e1) and [s2, e2) overlap iff s1 < e2 and s2 < e1.
    """
    query = (
        CalendarEvent.query
        .filter_by(user_id=user_id, is_deleted=False)
        .filter(CalendarEvent.start_time < end_dt)
        .filter(CalendarEvent.end_time > start_dt)
    )
    if exclude_event_id is not None:
        query = query.filter(CalendarEvent.id != exclude_event_id)
    return query.first() is not None
