"""SMTP email service for aLEXy legal CRM.

Sends transactional emails (welcome, task notifications, case updates,
contact alerts) via SMTP. If no SMTP is configured (dev mode), emails
are logged to console with a ``SMTP: would send to ...`` prefix.

All functions handle errors gracefully — they log and return None
instead of raising.
"""

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SMTP configuration (read from environment)
# ---------------------------------------------------------------------------

SMTP_HOST = os.environ.get("SMTP_HOST", "").strip() or None
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587") or "587")
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "").strip() or None
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "").strip() or None
SMTP_FROM = os.environ.get("SMTP_FROM", "").strip() or "noreply@alexycrm.local"
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").strip().lower() in ("true", "1", "yes")

SMTP_CONFIGURED = SMTP_HOST is not None and SMTP_USERNAME is not None


def _is_dev_mode() -> bool:
    """Return True when SMTP is not configured (development fallback)."""
    return not SMTP_CONFIGURED


def _build_message(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str,
) -> MIMEMultipart:
    """Build a multipart (text + HTML) email message."""
    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg


def _send_email(msg: MIMEMultipart, to_email: str) -> bool:
    """Actually send the email via SMTP.

    Returns True on success, False on any failure.
    """
    try:
        # SMTP_CONFIGURED is already True at this point, so HOST is non-None.
        # Type checker may not narrow it, so cast explicitly.
        _host: str = SMTP_HOST  # type: ignore[assignment]
        if SMTP_USE_TLS:
            server = smtplib.SMTP(_host, SMTP_PORT, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP(_host, SMTP_PORT, timeout=10)
            server.ehlo()

        if SMTP_USERNAME and SMTP_PASSWORD:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, [to_email], msg.as_string())
        server.quit()
        logger.info("Email sent to %s", to_email)
        return True
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to_email, exc)
        return False


# ---------------------------------------------------------------------------
# Template helpers — both plain-text and HTML
# ---------------------------------------------------------------------------

_BRAND = {
    "navy": "#0d1b2a",
    "gold": "#c9a84c",
}


def _base_html_header(subject: str) -> str:
    """Return the HTML header block shared by all branded emails."""
    return f"""\
<div style="background-color:{_BRAND['navy']};padding:24px 32px;">
    <h1 style="color:{_BRAND['gold']};margin:0;font-family:Arial,sans-serif;">
        aLEXy
    </h1>
</div>"""


def _base_html_footer() -> str:
    return f"""\
<div style="background-color:{_BRAND['navy']};padding:16px 32px;text-align:center;">
    <p style="color:#8899aa;margin:0;font-size:12px;font-family:Arial,sans-serif;">
        &copy; {datetime.utcnow().year} aLEXy Legal CRM &mdash; managed by your firm.
    </p>
</div>"""


# ---------------------------------------------------------------------------
# Public email functions
# ---------------------------------------------------------------------------


def send_welcome_email(to_email: str, name: str) -> Optional[bool]:
    """Send a welcome email to a new aLEXy user.

    Args:
        to_email: recipient email address.
        name: recipient's display name.

    Returns:
        True on success, False on failure, None if dev-mode logged only.
    """
    subject = "Benvenuto in aLEXy!"
    text = f"""\
Hello {name},

Welcome to aLEXy, the legal CRM built for your firm.

You can now manage cases, contacts, tasks, and calendar events — all in one place.

If you have any questions, feel free to reach out to your firm administrator.

Best regards,
The aLEXy Team"""

    html = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;background-color:#f4f4f4;">
{ _base_html_header(subject) }
<div style="max-width:600px;margin:32px auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
  <div style="padding:32px;">
    <h2 style="color:{_BRAND['navy']};margin-top:0;">Benvenuto in aLEXy, {name}!</h2>
    <p style="color:#333;line-height:1.6;">
        Grazie per aver scelto <strong>aLEXy</strong> — il CRM progettato
        specificamente per gli studi legali.
    </p>
    <p style="color:#333;line-height:1.6;">
        Con aLEXy puoi gestire <strong>clienti</strong>,
        <strong>pratiche</strong>, <strong>compiti</strong> e
        <strong>scadenziario</strong> in un unico luogo.
    </p>
    <p style="color:#333;line-height:1.6;">
        Se hai domande, non esitare a rivolgerti all'amministratore del tuo studio.
    </p>
    <p style="color:{_BRAND['gold']};font-weight:bold;">
        — Il team aLEXy
    </p>
  </div>
</div>
{ _base_html_footer() }
</body>
</html>"""

    return _send_to(to_email, subject, text, html)


def send_task_assigned(
    to_email: str,
    task_title: str,
    assigned_by: str,
    due_date: str,
) -> Optional[bool]:
    """Notify a user that a new task has been assigned to them.

    Args:
        to_email: recipient email address.
        task_title: title/summary of the task.
        assigned_by: name of the person who assigned the task.
        due_date: formatted due date string.

    Returns:
        True on success, False on failure, None if dev-mode logged only.
    """
    subject = f"Nuovo compito assegnato: {task_title}"
    text = f"""\
Ciao,

Un nuovo compito ti &egrave; stato assegnato:

  Titolo: {task_title}
  Assegnato da: {assigned_by}
  Scadenza: {due_date}

Accedi a aLEXy per visualizzare i dettagli.

--
aLEXy Legal CRM"""

    html = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;background-color:#f4f4f4;">
{ _base_html_header(subject) }
<div style="max-width:600px;margin:32px auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
  <div style="padding:32px;">
    <h2 style="color:{_BRAND['navy']};margin-top:0;">Nuovo compito assegnato</h2>
    <p style="color:#333;line-height:1.6;">
        Un nuovo compito ti &egrave; stato assegnato da <strong>{assigned_by}</strong>.
    </p>
    <table style="border-collapse:collapse;margin:20px 0;width:100%;">
      <tr>
        <td style="padding:8px 0;color:{_BRAND['navy']};font-weight:bold;width:140px;">Titolo</td>
        <td style="padding:8px 0;color:#333;">{task_title}</td>
      </tr>
      <tr>
        <td style="padding:8px 0;color:{_BRAND['navy']};font-weight:bold;">Assegnato da</td>
        <td style="padding:8px 0;color:#333;">{assigned_by}</td>
      </tr>
      <tr>
        <td style="padding:8px 0;color:{_BRAND['navy']};font-weight:bold;">Scadenza</td>
        <td style="padding:8px 0;color:#333;font-weight:bold;">{due_date}</td>
      </tr>
    </table>
    <p style="color:#666;font-size:13px;">Accedi a aLEXy per visualizzare i dettagli del compito.</p>
  </div>
</div>
{ _base_html_footer() }
</body>
</html>"""

    return _send_to(to_email, subject, text, html)


def send_case_update(
    to_email: str,
    case_title: str,
    update_description: str,
) -> Optional[bool]:
    """Notify a user about a case update.

    Args:
        to_email: recipient email address.
        case_title: title of the case that was updated.
        update_description: description of what changed.

    Returns:
        True on success, False on failure, None if dev-mode logged only.
    """
    subject = f"Aggiornamento pratica: {case_title}"
    text = f"""\
Ciao,

Pratica aggiornata: {case_title}

{update_description}

Accedi a aLEXy per visualizzare i dettagli.

--
aLEXy Legal CRM"""

    html = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;background-color:#f4f4f4;">
{ _base_html_header(subject) }
<div style="max-width:600px;margin:32px auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
  <div style="padding:32px;">
    <h2 style="color:{_BRAND['navy']};margin-top:0;">Aggiornamento pratica</h2>
    <p style="color:#333;line-height:1.6;">
        La pratica <strong>&laquo;{case_title}&raquo;</strong> &egrave; stata aggiornata.
    </p>
    <div style="background:#f8f8f8;border-left:4px solid {_BRAND['gold']};padding:16px;margin:20px 0;">
        <p style="color:#333;margin:0;line-height:1.6;">{update_description}</p>
    </div>
    <p style="color:#666;font-size:13px;">Accedi a aLEXy per visualizzare i dettagli della pratica.</p>
  </div>
</div>
{ _base_html_footer() }
</body>
</html>"""

    return _send_to(to_email, subject, text, html)


def send_contact_added(
    to_email: str,
    contact_name: str,
    contact_company: str = "",
) -> Optional[bool]:
    """Alert a user that a new contact has been added.

    Args:
        to_email: recipient email address.
        contact_name: full name of the new contact.
        contact_company: company/organisation name (optional, defaults to "").

    Returns:
        True on success, False on failure, None if dev-mode logged only.
    """
    company = contact_company if contact_company else "N/A"
    subject = f"Nuovo contatto: {contact_name}"
    text = f"""\
Ciao,

&Egrave; stato aggiunto un nuovo contatto:

  Nome: {contact_name}
  Azienda: {company}

Accedi a aLEXy per visualizzare i dettagli.

--
aLEXy Legal CRM"""

    html = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;background-color:#f4f4f4;">
{ _base_html_header(subject) }
<div style="max-width:600px;margin:32px auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
  <div style="padding:32px;">
    <h2 style="color:{_BRAND['navy']};margin-top:0;">Nuovo contatto aggiunto</h2>
    <p style="color:#333;line-height:1.6;">
        &Egrave; stato aggiunto un nuovo contatto a aLEXy.
    </p>
    <table style="border-collapse:collapse;margin:20px 0;width:100%;">
      <tr>
        <td style="padding:8px 0;color:{_BRAND['navy']};font-weight:bold;width:140px;">Nome</td>
        <td style="padding:8px 0;color:#333;">{contact_name}</td>
      </tr>
      <tr>
        <td style="padding:8px 0;color:{_BRAND['navy']};font-weight:bold;">Azienda</td>
        <td style="padding:8px 0;color:#333;">{company}</td>
      </tr>
    </table>
    <p style="color:#666;font-size:13px;">Accedi a aLEXy per visualizzare i dettagli del contatto.</p>
  </div>
</div>
{ _base_html_footer() }
</body>
</html>"""

    return _send_to(to_email, subject, text, html)


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _send_to(to_email: str, subject: str, text_body: str, html_body: str) -> Optional[bool]:
    """Route an email either through SMTP or dev-mode console logging.

    Args:
        to_email: recipient.
        subject: email subject.
        text_body: plain-text body.
        html_body: HTML body.

    Returns:
        True on success, False on SMTP failure, None if dev-mode logged.
    """
    if _is_dev_mode():
        # Dev-mode: print to console instead of sending
        logger.info(
            "SMTP: would send to %s | subject=%s | text=%s | html=%s",
            to_email,
            subject,
            text_body[:120],
            html_body[:120],
        )
        return None

    msg = _build_message(to_email, subject, text_body, html_body)
    return _send_email(msg, to_email)
