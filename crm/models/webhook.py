from ..extensions import db
from datetime import datetime, timezone


class WebhookSubscription(db.Model):
    __tablename__ = "webhook_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    events = db.Column(db.JSON, nullable=False)  # e.g. ["task.created", "task.updated"]
    secret = db.Column(db.String(64), nullable=False)  # sha256-hashed secret
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False)

    deliveries = db.relationship("WebhookDelivery", backref="subscription", lazy="dynamic",
                                 cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "events": self.events,
            "active": self.active,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WebhookDelivery(db.Model):
    __tablename__ = "webhook_deliveries"

    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    payload = db.Column(db.JSON, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending | success | failed
    http_status_code = db.Column(db.Integer, nullable=True)
    retry_count = db.Column(db.Integer, nullable=False, default=0)
    last_attempt_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "subscription_id": self.subscription_id,
            "url": self.url,
            "payload": self.payload,
            "status": self.status,
            "http_status_code": self.http_status_code,
            "retry_count": self.retry_count,
            "last_attempt_at": self.last_attempt_at.isoformat() if self.last_attempt_at else None,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
