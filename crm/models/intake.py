"""Intake matter models for aLEXy legal CRM.

Captures client intake submissions (matters, documents, activity timeline)
with foreign keys to the existing CRM contacts and cases tables.
"""

from ..extensions import db
from datetime import datetime


class Matter(db.Model):
    """A client intake submission — the first touchpoint in the legal pipeline.

    Each matter is created when a client submits the public intake form.
    Staff reviews it, updates statuses, and can later convert it into a
    formal CRM case (cases table) linked to a CRM contact (contacts table).

    Statuses mirror the original LexFlow intake pipeline:
      New intake → Conflict check → Lawyer review → Waiting client docs
      → Quoted → Engaged → Closed
    """

    __tablename__ = "intake_matters"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    token = db.Column(db.String(32), nullable=False, unique=True, index=True)

    # -- Client info --
    client_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    company = db.Column(db.String(255), nullable=True)

    # -- Matter details --
    practice_area = db.Column(db.String(100), nullable=False)
    urgency = db.Column(db.String(20), nullable=False, default="Medium")
    description = db.Column(db.Text, nullable=True)
    status = db.Column(
        db.String(50), nullable=False, default="New intake",
        index=True,
    )
    internal_notes = db.Column(db.Text, nullable=True, default="")

    # -- Links to CRM tables (set when staff converts) --
    contact_id = db.Column(
        db.Integer,
        db.ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    converted_to_case_id = db.Column(
        db.Integer,
        db.ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # -- Relationships --
    documents = db.relationship(
        "IntakeDocument", backref="matter", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    events = db.relationship(
        "IntakeEvent", backref="matter", lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="IntakeEvent.event_time.desc()",
    )
    contact = db.relationship("Contact", backref=db.backref("intake_matters", lazy="dynamic"))
    converted_case = db.relationship("Case", backref=db.backref("intake_matter", uselist=False))

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "token": self.token,
            "client_name": self.client_name,
            "email": self.email,
            "phone": self.phone,
            "company": self.company,
            "practice_area": self.practice_area,
            "urgency": self.urgency,
            "description": self.description,
            "status": self.status,
            "internal_notes": self.internal_notes,
            "contact_id": self.contact_id,
            "converted_to_case_id": self.converted_to_case_id,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class IntakeDocument(db.Model):
    """A document uploaded as part of an intake matter submission."""

    __tablename__ = "intake_documents"

    id = db.Column(db.Integer, primary_key=True)
    matter_id = db.Column(
        db.Integer,
        db.ForeignKey("intake_matters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stored_name = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "matter_id": self.matter_id,
            "stored_name": self.stored_name,
            "original_name": self.original_name,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


class IntakeEvent(db.Model):
    """A timeline event recording a status change or staff note on an intake matter."""

    __tablename__ = "intake_events"

    id = db.Column(db.Integer, primary_key=True)
    matter_id = db.Column(
        db.Integer,
        db.ForeignKey("intake_matters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False)
    note = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "matter_id": self.matter_id,
            "event_time": self.event_time.isoformat() if self.event_time else None,
            "status": self.status,
            "note": self.note,
        }