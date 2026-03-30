# tracker/emailer.py
#
# Sends one HTML email per new job posting via Gmail SMTP.
# Uses an App Password — not your Gmail account password.
# Generate one at: https://myaccount.google.com/apppasswords (requires 2FA).

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from tracker.config import EMAIL_SUBJECT_PREFIX
from tracker.scrapers import Job

_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 587


def send_email(job: Job) -> None:
    """
    Send a single HTML email for the given job posting.
    Reads credentials from environment variables:
      EMAIL_SENDER       — Gmail address that sends the email
      EMAIL_APP_PASSWORD — Gmail App Password (16-char, no spaces)
      EMAIL_RECIPIENT    — address that receives the email
    """
    sender = os.environ["EMAIL_SENDER"]
    password = os.environ["EMAIL_APP_PASSWORD"]
    recipient = os.environ["EMAIL_RECIPIENT"]

    subject = f"{EMAIL_SUBJECT_PREFIX} {job['company']} — {job['title']} ({job['location']})"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    html = _build_html(job)
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())


def _build_html(job: Job) -> str:
    """Return a dark-mode HTML card for the job posting."""
    description = job["description"][:300]
    if len(job["description"]) > 300:
        description += "…"

    # Escape any HTML special chars in user-supplied strings
    def esc(s: str) -> str:
        return (
            s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&#39;")
        )

    source_colors = {
        "GitHub":     "#6e7681",
        "Greenhouse": "#3dba6e",
        "Lever":      "#1a73e8",
        "BigTech":    "#e8710a",
        "Workday":    "#0066cc",
        "HackerNews": "#ff6600",
        "YC":         "#fb651e",
        "Meta":       "#1877f2",
        "Tesla":      "#cc0000",
        "GovtCanada": "#cc0000",
        "OPS":        "#00549e",
        "OPG":        "#005a31",
        "CityToronto": "#003f7f",
    }
    badge_color = source_colors.get(job["source"], "#555")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(job['title'])}</title>
</head>
<body style="margin:0;padding:0;background:#0d1117;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0d1117;padding:32px 16px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background:#161b22;border:1px solid #30363d;border-radius:12px;overflow:hidden;max-width:600px;width:100%;">

          <!-- Header bar -->
          <tr>
            <td style="background:#21262d;padding:20px 28px;border-bottom:1px solid #30363d;">
              <span style="font-size:22px;font-weight:700;color:#e6edf3;">{esc(job['company'])}</span>
              &nbsp;
              <span style="display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;
                           background:{badge_color};color:#fff;vertical-align:middle;">{esc(job['source'])}</span>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:24px 28px;">
              <p style="margin:0 0 6px;font-size:20px;font-weight:600;color:#58a6ff;">{esc(job['title'])}</p>
              <p style="margin:0 0 16px;font-size:13px;color:#8b949e;">
                📍 {esc(job['location'])}
                &nbsp;&nbsp;|&nbsp;&nbsp;
                🗓 {esc(job['date_posted'] or 'Date unknown')}
              </p>
              <p style="margin:0 0 24px;font-size:14px;color:#c9d1d9;line-height:1.6;">
                {esc(description)}
              </p>
              <a href="{esc(job['url'])}"
                 style="display:inline-block;padding:12px 28px;background:#238636;color:#fff;
                        text-decoration:none;border-radius:8px;font-size:14px;font-weight:600;">
                Apply Now →
              </a>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:14px 28px;border-top:1px solid #30363d;">
              <p style="margin:0;font-size:11px;color:#484f58;">Sent by InternHub • <a href="{esc(job['url'])}" style="color:#58a6ff;">View posting</a></p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
