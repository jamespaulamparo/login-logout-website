import logging
from email.utils import formatdate
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)


def send_admin_alert(subject, text_body, html_body=None, recipient_list=None):
    """
    Sends an administrative alert email via configured SMTP (or locmem in tests).
    Does not crash the caller if sending fails.
    """
    if recipient_list is None:
        recipients = [
            part.strip()
            for part in str(getattr(settings, "ADMIN_EMAIL", "") or "").split(",")
            if part.strip()
        ]
    else:
        recipients = recipient_list

    if not recipients:
        logger.warning("No admin recipients configured for alert: %s", subject)
        return False

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "Foundry <no-reply@example.com>")

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=from_email,
            to=recipients,
            headers={
                "Date": formatdate(timezone.now().timestamp(), localtime=True),
            },
        )
        if html_body:
            msg.attach_alternative(html_body, "text/html")

        msg.send(fail_silently=False)
        logger.info("Admin email alert sent: %s to %s", subject, recipients)
        return True
    except Exception as exc:
        logger.error("Failed to send admin email alert '%s': %s", subject, exc)
        return False


def notify_new_entry(entry):
    """
    Alerts admin when a new workspace record is created.
    Builds absolute URL so the recipient can open the record directly.
    """
    base_url = getattr(settings, "SITE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    entry_path = reverse("entry_edit", args=[entry.pk])
    full_url = f"{base_url}{entry_path}"

    subject = f"[Foundry Alert] New record created: {entry.title}"

    text_body = (
        f"A new record has been created in Foundry.\n\n"
        f"Title: {entry.title}\n"
        f"Category: {entry.category or 'Uncategorized'}\n"
        f"Created by: {entry.created_by.username if entry.created_by else 'Unknown'}\n"
        f"Created at: {entry.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"View or edit this record:\n{full_url}\n"
    )

    html_body = f"""<!doctype html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f5f6f8; padding: 24px; color: #202631; margin: 0;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 10px; border: 1px solid #e8ebef; padding: 32px;">
    <tr>
      <td>
        <div style="font-size: 11px; font-weight: 700; letter-spacing: 1.5px; color: #5268a9; margin-bottom: 8px;">FOUNDRY WORKSPACE ALERT</div>
        <h2 style="margin: 0 0 16px; font-size: 20px; color: #202631;">New record created</h2>
        <p style="color: #596273; font-size: 14px; line-height: 1.6; margin: 0 0 20px;">A new entry was submitted that may require your review.</p>
        
        <table width="100%" cellpadding="8" cellspacing="0" style="background: #f9fafb; border-radius: 8px; border: 1px solid #edf0f5; margin-bottom: 24px; font-size: 13px;">
          <tr>
            <td width="30%" style="font-weight: 600; color: #7b8492;">Title</td>
            <td style="color: #202631; font-weight: 600;">{entry.title}</td>
          </tr>
          <tr>
            <td style="font-weight: 600; color: #7b8492;">Category</td>
            <td style="color: #202631;">{entry.category or 'Uncategorized'}</td>
          </tr>
          <tr>
            <td style="font-weight: 600; color: #7b8492;">Created By</td>
            <td style="color: #202631;">{entry.created_by.username if entry.created_by else 'Unknown'}</td>
          </tr>
          <tr>
            <td style="font-weight: 600; color: #7b8492;">Created At</td>
            <td style="color: #202631;">{entry.created_at.strftime('%Y-%m-%d %H:%M:%S')}</td>
          </tr>
        </table>
        
        <div style="text-align: center; margin: 28px 0 16px;">
          <a href="{full_url}" style="background-color: #5268a9; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 13px; display: inline-block;">Open Record in Workspace &rarr;</a>
        </div>
        
        <p style="font-size: 11px; color: #9aa2ad; margin-top: 32px; border-top: 1px solid #e8ebef; padding-top: 16px; text-align: center;">
          Foundry Django Hackathon Platform &middot; Automated Notification
        </p>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    return send_admin_alert(subject, text_body, html_body)
