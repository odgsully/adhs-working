#!/usr/bin/env python3
"""
AZDHS Notification Module

Sends notifications via Slack webhook and Gmail when new AZDHS data is available.

Environment Variables Required:
    AZDHS_SLACK_WEBHOOK_URL - Slack incoming webhook URL
    AZDHS_GMAIL_USER - Gmail address to send from
    AZDHS_GMAIL_APP_PASSWORD - Gmail app password (not regular password)
    AZDHS_NOTIFY_EMAIL - Email address to notify

Usage:
    from scripts.azdhs_notify import send_notifications
    send_notifications("Subject", "Message body", {"key": "value"})
"""

import json
import os
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional
from pathlib import Path

# Try to load .env file
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass


# ============================================================================
# Configuration
# ============================================================================

def get_config() -> dict:
    """Get notification configuration from environment."""
    return {
        "slack_webhook_url": os.getenv("AZDHS_SLACK_WEBHOOK_URL"),
        "gmail_user": os.getenv("AZDHS_GMAIL_USER"),
        "gmail_app_password": os.getenv("AZDHS_GMAIL_APP_PASSWORD"),
        "notify_email": os.getenv("AZDHS_NOTIFY_EMAIL"),
    }


# ============================================================================
# Slack Notifications
# ============================================================================

def send_slack_notification(
    title: str,
    message: str,
    data: Optional[dict] = None,
    webhook_url: Optional[str] = None
) -> bool:
    """Send notification to Slack via webhook."""
    import urllib.request
    import urllib.error

    url = webhook_url or get_config()["slack_webhook_url"]

    if not url:
        print("[SLACK] No webhook URL configured (set AZDHS_SLACK_WEBHOOK_URL)")
        return False

    # Build Slack message blocks
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📊 {title}",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": message
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            ]
        }
    ]

    # Add data details if provided
    if data:
        if "files" in data and data["files"]:
            files_text = "\n".join([f"• `{Path(f).name}`" for f in data["files"][:10]])
            if len(data["files"]) > 10:
                files_text += f"\n• _...and {len(data['files']) - 10} more_"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Downloaded Files:*\n{files_text}"
                }
            })

        if "errors" in data and data["errors"]:
            errors_text = ", ".join(data["errors"])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"⚠️ *Errors:* {errors_text}"
                }
            })

    payload = {
        "blocks": blocks,
        "text": f"{title}: {message}"  # Fallback text
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                print("[SLACK] Notification sent successfully")
                return True
            else:
                print(f"[SLACK] Failed with status {response.status}")
                return False

    except urllib.error.URLError as e:
        print(f"[SLACK] Error sending notification: {e}")
        return False


# ============================================================================
# Gmail Notifications
# ============================================================================

def send_gmail_notification(
    subject: str,
    body: str,
    data: Optional[dict] = None,
    to_email: Optional[str] = None
) -> bool:
    """Send notification via Gmail SMTP."""
    config = get_config()

    gmail_user = config["gmail_user"]
    gmail_password = config["gmail_app_password"]
    recipient = to_email or config["notify_email"]

    if not all([gmail_user, gmail_password, recipient]):
        print("[GMAIL] Missing configuration (set AZDHS_GMAIL_USER, AZDHS_GMAIL_APP_PASSWORD, AZDHS_NOTIFY_EMAIL)")
        return False

    # Build HTML email
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background: #c41230; color: white; padding: 20px; border-radius: 5px 5px 0 0; }}
            .content {{ padding: 20px; background: #f9f9f9; }}
            .files {{ background: #fff; padding: 15px; border-radius: 5px; margin: 10px 0; }}
            .file {{ font-family: monospace; padding: 3px 0; }}
            .footer {{ padding: 15px; font-size: 12px; color: #666; }}
            .error {{ color: #c41230; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>📊 {subject}</h2>
        </div>
        <div class="content">
            <p>{body}</p>
    """

    if data:
        if "files" in data and data["files"]:
            html_body += '<div class="files"><strong>Downloaded Files:</strong><br>'
            for f in data["files"]:
                html_body += f'<div class="file">✓ {Path(f).name}</div>'
            html_body += '</div>'

        if "errors" in data and data["errors"]:
            html_body += f'<p class="error"><strong>Errors:</strong> {", ".join(data["errors"])}</p>'

        if "month" in data:
            html_body += f'<p><strong>Month:</strong> {data["month"]}</p>'

    html_body += f"""
        </div>
        <div class="footer">
            <p>Sent by AZDHS Monitor at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>This is an automated message from the ADHS ETL Pipeline.</p>
        </div>
    </body>
    </html>
    """

    # Create message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[AZDHS] {subject}"
    msg["From"] = gmail_user
    msg["To"] = recipient

    # Attach plain text and HTML versions
    msg.attach(MIMEText(body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, recipient, msg.as_string())

        print(f"[GMAIL] Notification sent to {recipient}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("[GMAIL] Authentication failed. Make sure you're using an App Password.")
        print("[GMAIL] See: https://support.google.com/accounts/answer/185833")
        return False
    except Exception as e:
        print(f"[GMAIL] Error sending email: {e}")
        return False


# ============================================================================
# Combined Notification
# ============================================================================

def send_notifications(
    title: str,
    message: str,
    data: Optional[dict] = None,
    channels: Optional[list[str]] = None
) -> dict[str, bool]:
    """Send notifications via all configured channels.

    Args:
        title: Notification title/subject
        message: Main message body
        data: Optional dict with additional data (files, errors, etc.)
        channels: Optional list of channels to use ('slack', 'gmail'). Default: both.

    Returns:
        Dict with success status for each channel
    """
    if channels is None:
        channels = ["slack", "gmail"]

    results = {}

    if "slack" in channels:
        results["slack"] = send_slack_notification(title, message, data)

    if "gmail" in channels:
        results["gmail"] = send_gmail_notification(title, message, data)

    return results


# ============================================================================
# CLI for testing
# ============================================================================

def main():
    """Test notifications from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Test AZDHS notifications")
    parser.add_argument("--slack", action="store_true", help="Test Slack notification")
    parser.add_argument("--gmail", action="store_true", help="Test Gmail notification")
    parser.add_argument("--all", action="store_true", help="Test all notifications")

    args = parser.parse_args()

    test_data = {
        "month": "1.26",
        "year": 2026,
        "files": [
            "/path/to/ASSISTED_LIVING_CENTER.xlsx",
            "/path/to/BEHAVIORAL_HEALTH_RESIDENTIAL_FACILITY.xlsx",
            "/path/to/NURSING_HOME.xlsx",
        ],
        "errors": []
    }

    if args.all or (not args.slack and not args.gmail):
        channels = ["slack", "gmail"]
    else:
        channels = []
        if args.slack:
            channels.append("slack")
        if args.gmail:
            channels.append("gmail")

    print(f"Testing notifications on channels: {channels}")
    results = send_notifications(
        "Test Notification",
        "This is a test notification from the AZDHS Monitor.",
        test_data,
        channels
    )

    print(f"\nResults: {results}")


if __name__ == "__main__":
    main()
