"""
web/backend/app/api/contact_routes.py — Contact form email sending.

Sends emails via SMTP using the configured mail server (cp226.webserver.pt).
"""
from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from ..config import Settings, get_settings

router = APIRouter(prefix="/api/contact", tags=["contact"])


class ContactMessage(BaseModel):
    name: str
    email: str
    subject: str = ""
    message: str


@router.post("/send")
async def send_contact_message(
    body: ContactMessage,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Send a contact message via SMTP to the support email."""
    # Validate required fields
    if not body.name.strip() or not body.message.strip():
        raise HTTPException(status_code=422, detail="Name and message are required")
    if not body.email.strip() or "@" not in body.email:
        raise HTTPException(status_code=422, detail="A valid email is required")

    # Check SMTP is configured
    if not settings.smtp_password:
        raise HTTPException(status_code=503, detail="SMTP not configured — contact admin@constellation.com directly")

    # Build email
    msg = EmailMessage()
    msg["From"] = settings.smtp_username
    msg["To"] = settings.support_email
    msg["Reply-To"] = body.email
    msg["Subject"] = f"[ConstellaSim Contact] {body.subject}" if body.subject else "[ConstellaSim Contact] New message"

    body_text = f"""
Name: {body.name}
Email: {body.email}
---
{body.message}
---
Sent via ConstellaSim Contact Form
"""
    msg.set_content(body_text.strip())

    # Send via SMTP with SSL
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context) as server:
            server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(status_code=502, detail="SMTP authentication failed — check email password")
    except smtplib.SMTPException as e:
        raise HTTPException(status_code=502, detail=f"Failed to send email: {str(e)[:100]}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Connection error: {str(e)[:100]}")

    return {"status": "sent", "to": settings.support_email}
