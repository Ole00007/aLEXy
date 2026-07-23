"""Intake matter routes for aLEXy legal CRM.

Ports the 7 original app.py routes into a Flask Blueprint backed by
SQLAlchemy + PostgreSQL, with auto-contact creation and FK links to
the existing CRM tables (contacts, cases).

Route mapping (old → new):
  GET  /                      →  GET  /intake         (intake form)
  POST /submit                →  POST /intake/submit  (process intake)
  GET  /status/<token>        →  GET  /status/<token> (client status page)
  GET  /admin                 →  GET  /admin          (matter list)
  GET+POST /admin/matter/<id> →  GET+POST /admin/matter/<id>
  GET  /uploads/<path>        →  GET  /uploads/<path>
  GET+POST /admin/load-demo   →  GET+POST /admin/load-demo
"""

import os
import secrets
from pathlib import Path
from datetime import datetime

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, send_from_directory, abort, current_app,
)
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models.intake import Matter, IntakeDocument, IntakeEvent
from ..models.contact import Contact

# ── Blueprint (no url_prefix — routes define their own paths) ──────────────
intake_bp = Blueprint("intake", __name__)

# ── Config ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # project root
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXT = {"pdf", "doc", "docx", "png", "jpg", "jpeg", "txt"}

# Email config (read from env — already set on Railway)
try:
    import resend
except ImportError:
    resend = None

if resend is not None:
    resend.api_key = os.environ.get("RESEND_API_KEY", "")

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "onboarding@resend.dev")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "LexFlow")
APP_URL = os.environ.get(
    "RAILWAY_PUBLIC_DOMAIN", "http://localhost:5000"
)
if not APP_URL.startswith("http"):
    APP_URL = "https://" + APP_URL

PRACTICES = [
    "Commercial", "Employment", "Real Estate", "Family",
    "Debt Collection", "Shipping / Logistics", "Other",
]
STATUSES = [
    "New intake", "Conflict check", "Lawyer review",
    "Waiting client docs", "Quoted", "Engaged", "Closed",
]


# ── Helpers ────────────────────────────────────────────────────────────────


def allowed_file(filename: str) -> bool:
    """Return True if the file extension is in the allowed set."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT
    )


def _find_or_create_contact(
    client_name: str, email: str, phone: str = "", company: str = ""
) -> int:
    """Return the id of an existing Contact by email, or create a new lead.

    Also matches by name if email is empty (fallback).
    """
    email = email.strip().lower()
    if email:
        existing = Contact.query.filter(
            db.func.lower(Contact.email) == email
        ).first()
        if existing:
            return existing.id

    # Create new lead contact
    contact = Contact(
        fullname=client_name.strip(),
        email=email or None,
        phone=phone.strip() or None,
        company=company.strip() or None,
        status="lead",
    )
    db.session.add(contact)
    db.session.flush()  # get the id without committing yet
    return contact.id


def send_intake_notification(
    matter_id: int, client_name: str, email: str,
    practice_area: str, urgency: str, token: str,
) -> None:
    """Send an email to the admin alerting them of a new intake matter."""
    if not resend or not resend.api_key or not ADMIN_EMAIL:
        current_app.logger.info(
            "Email skipped: missing RESEND_API_KEY or ADMIN_EMAIL"
        )
        return
    try:
        resend.Emails.send({
            "from": f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>",
            "to": [ADMIN_EMAIL],
            "subject": f"New intake #{matter_id} – {practice_area} ({urgency})",
            "html": f"""
                <h2>New matter received – aLEXy</h2>
                <p><strong>Matter #:</strong> {matter_id}</p>
                <p><strong>Client:</strong> {client_name}</p>
                <p><strong>Email:</strong> {email}</p>
                <p><strong>Practice:</strong> {practice_area}</p>
                <p><strong>Urgency:</strong> {urgency}</p>
                <p><strong>Token:</strong> {token}</p>
                <p>
                  <a href="{APP_URL}/admin/matter/{matter_id}"
                     style="background:#2563eb;color:#fff;padding:10px 20px;
                            border-radius:6px;text-decoration:none;">
                    Open in admin →
                  </a>
                </p>
            """,
        })
        current_app.logger.info(f"Intake email sent for matter #{matter_id}")
    except Exception as e:
        current_app.logger.error(f"Email error: {e}")


# ── Routes ─────────────────────────────────────────────────────────────────


@intake_bp.route("/intake")
def intake_form():
    """Render the public intake form."""
    return render_template("index.html", practices=PRACTICES)


@intake_bp.route("/intake/submit", methods=["POST"])
def submit_intake():
    """Process an intake form submission.

    Creates a Matter row, auto-creates (or links to) a Contact,
    logs an IntakeEvent, saves uploaded documents, and sends an
    email notification to the admin.
    """
    client_name = request.form.get("client_name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    company = request.form.get("company", "").strip()
    practice_area = request.form.get("practice_area", "").strip()
    urgency = request.form.get("urgency", "Medium").strip()
    description = request.form.get("description", "").strip()

    if not client_name or not email or not practice_area:
        flash("Name, email, and practice area are required.", "error")
        return redirect(url_for("intake.intake_form"))

    token = secrets.token_hex(8).upper()
    now = datetime.utcnow()

    # Auto-create or link Contact
    contact_id = _find_or_create_contact(client_name, email, phone, company)

    matter = Matter(
        created_at=now,
        token=token,
        client_name=client_name,
        email=email,
        phone=phone or None,
        company=company or None,
        practice_area=practice_area,
        urgency=urgency,
        description=description or None,
        status="New intake",
        internal_notes="",
        contact_id=contact_id,
    )
    db.session.add(matter)
    db.session.flush()  # get matter.id

    # Log the initial intake event
    event = IntakeEvent(
        matter_id=matter.id,
        event_time=now,
        status="New intake",
        note="Matter created from intake form.",
    )
    db.session.add(event)

    # Save uploaded documents
    for f in request.files.getlist("documents"):
        if f and f.filename and allowed_file(f.filename):
            stored = (
                f"{matter.id}_{now.strftime('%Y%m%d%H%M%S%f')}"
                f"_{secure_filename(f.filename)}"
            )
            f.save(str(UPLOAD_DIR / stored))
            doc = IntakeDocument(
                matter_id=matter.id,
                stored_name=stored,
                original_name=f.filename,
                uploaded_at=now,
            )
            db.session.add(doc)

    db.session.commit()

    send_intake_notification(
        matter.id, client_name, email, practice_area, urgency, token
    )
    return redirect(url_for("intake.check_status", token=token))


@intake_bp.route("/status/<token>")
def check_status(token):
    """Public client-facing matter status page."""
    matter = Matter.query.filter_by(token=token).first()
    if not matter:
        abort(404)

    docs = (
        IntakeDocument.query
        .filter_by(matter_id=matter.id)
        .order_by(IntakeDocument.uploaded_at.desc())
        .all()
    )
    events = (
        IntakeEvent.query
        .filter_by(matter_id=matter.id)
        .order_by(IntakeEvent.event_time.desc())
        .all()
    )
    return render_template(
        "status.html",
        matter=matter.to_dict(),
        docs=[d.to_dict() for d in docs],
        events=[e.to_dict() for e in events],
        statuses=STATUSES,
    )


@intake_bp.route("/admin")
def admin_list():
    """Staff matter list — all intake matters, newest first."""
    matters = Matter.query.order_by(Matter.created_at.desc()).all()
    return render_template("admin.html", matters=[m.to_dict() for m in matters])


@intake_bp.route("/admin/matter/<int:matter_id>", methods=["GET", "POST"])
def admin_matter(matter_id):
    """Staff matter detail — view and update status / notes."""
    matter = Matter.query.get(matter_id)
    if not matter:
        abort(404)

    if request.method == "POST":
        new_status = request.form.get("status", matter.status)
        internal_notes = request.form.get("internal_notes", "")
        event_note = (
            request.form.get("event_note", "").strip()
            or f"Status updated to {new_status}."
        )
        now = datetime.utcnow()

        matter.status = new_status
        matter.internal_notes = internal_notes
        matter.updated_at = now

        event = IntakeEvent(
            matter_id=matter.id,
            event_time=now,
            status=new_status,
            note=event_note,
        )
        db.session.add(event)
        db.session.commit()

        return redirect(url_for("intake.admin_matter", matter_id=matter_id))

    docs = (
        IntakeDocument.query
        .filter_by(matter_id=matter.id)
        .order_by(IntakeDocument.uploaded_at.desc())
        .all()
    )
    events = (
        IntakeEvent.query
        .filter_by(matter_id=matter.id)
        .order_by(IntakeEvent.event_time.desc())
        .all()
    )
    return render_template(
        "admin_matter.html",
        matter=matter.to_dict(),
        docs=[d.to_dict() for d in docs],
        events=[e.to_dict() for e in events],
        statuses=STATUSES,
    )


@intake_bp.route("/uploads/<path:filename>")
def uploaded_file(filename):
    """Serve an uploaded document."""
    return send_from_directory(str(UPLOAD_DIR), filename)


@intake_bp.route("/admin/load-demo", methods=["GET", "POST"])
def load_demo():
    """Seed demo intake matters (only if the table is empty)."""
    if Matter.query.first() is not None:
        flash("Demo data already exists.", "info")
        return redirect(url_for("intake.admin_list"))

    samples = [
        ("Giulia Conti",  "giulia.conti@example.com",  "+39 02 1234567",
         "Studio Conti",  "Shipping / Logistics", "Critical",
         "Dispute over cargo damage, port of Genova."),
        ("Marco Ferretti", "marco.ferretti@example.com", "+39 06 9876543",
         "Ferretti SRL",  "Commercial",           "High",
         "Contract review for new supplier agreement."),
        ("Sofia Marino",  "sofia.marino@example.com",  "",
         "",              "Employment",           "Medium",
         "Wrongful termination claim."),
    ]

    now = datetime.utcnow()
    for s in samples:
        token = secrets.token_hex(8).upper()
        contact_id = _find_or_create_contact(s[0], s[1], s[2], s[3])

        matter = Matter(
            created_at=now,
            token=token,
            client_name=s[0],
            email=s[1],
            phone=s[2] or None,
            company=s[3] or None,
            practice_area=s[4],
            urgency=s[5],
            description=s[6],
            status="New intake",
            internal_notes="",
            contact_id=contact_id,
        )
        db.session.add(matter)
        db.session.flush()

        event = IntakeEvent(
            matter_id=matter.id,
            event_time=now,
            status="New intake",
            note="Matter created from intake form.",
        )
        db.session.add(event)

    db.session.commit()
    flash("Demo data loaded.", "success")
    return redirect(url_for("intake.admin_list"))