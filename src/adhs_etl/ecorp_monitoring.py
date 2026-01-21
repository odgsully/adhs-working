"""Ecorp scraper monitoring and alerting.

This module provides monitoring functionality for the Ecorp scraper,
including Slack alerts for CAPTCHA detection, rate limiting, and other
failure conditions.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


def send_slack_alert(
    webhook_url: str,
    event_type: str,
    details: Dict[str, Any],
    severity: str = "warning",
) -> bool:
    """Send alert to Slack webhook.

    Parameters
    ----------
    webhook_url : str
        Slack incoming webhook URL
    event_type : str
        Type of event (e.g., "CAPTCHA detected", "Rate limited")
    details : dict
        Additional details about the event
    severity : str
        Alert severity: "error", "warning", or "info"

    Returns
    -------
    bool
        True if alert was sent successfully, False otherwise
    """
    emoji_map = {
        "error": ":x:",
        "warning": ":warning:",
        "info": ":information_source:",
    }
    color_map = {
        "error": "danger",
        "warning": "warning",
        "info": "good",
    }

    emoji = emoji_map.get(severity, ":bell:")
    color = color_map.get(severity, "warning")

    # Format details for display
    detail_str = "\n".join(f"- {k}: {v}" for k, v in details.items())

    payload = {
        "text": f"{emoji} *Ecorp Scraper Alert*",
        "attachments": [
            {
                "color": color,
                "fields": [
                    {"title": "Event", "value": event_type, "short": True},
                    {"title": "Severity", "value": severity.upper(), "short": True},
                    {
                        "title": "Time",
                        "value": datetime.now().isoformat(),
                        "short": True,
                    },
                    {"title": "Details", "value": detail_str, "short": False},
                ],
            }
        ],
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info(f"Slack alert sent: {event_type}")
            return True
        else:
            logger.warning(f"Failed to send Slack alert: HTTP {response.status_code}")
            return False
    except requests.RequestException as e:
        logger.warning(f"Failed to send Slack alert: {e}")
        return False


def send_alert(
    event_type: str,
    details: Dict[str, Any],
    settings: Optional[Any] = None,
    severity: str = "warning",
) -> bool:
    """Send alert via configured channels.

    Parameters
    ----------
    event_type : str
        Type of event
    details : dict
        Event details
    settings : EcorpSettings, optional
        Ecorp settings with webhook URL
    severity : str
        Alert severity

    Returns
    -------
    bool
        True if any alert was sent successfully
    """
    alert_sent = False

    if settings and settings.slack_webhook_url and settings.enable_monitoring:
        # Check if we should alert for this event type
        should_alert = True
        if "captcha" in event_type.lower() and not settings.alert_on_captcha:
            should_alert = False
        if "rate" in event_type.lower() and not settings.alert_on_rate_limit:
            should_alert = False

        if should_alert:
            alert_sent = send_slack_alert(
                settings.slack_webhook_url, event_type, details, severity
            )

    # Always log the event locally
    log_level = logging.ERROR if severity == "error" else logging.WARNING
    logger.log(log_level, f"{event_type}: {details}")

    return alert_sent


def alert_captcha_detected(
    record_info: Dict[str, Any],
    settings: Optional[Any] = None,
) -> bool:
    """Send alert for CAPTCHA detection.

    Parameters
    ----------
    record_info : dict
        Information about the current record being processed
    settings : EcorpSettings, optional
        Ecorp settings

    Returns
    -------
    bool
        True if alert was sent
    """
    details = {
        "record_index": record_info.get("index", "unknown"),
        "owner_name": record_info.get("owner_name", "unknown"),
        "url": record_info.get("url", "unknown"),
        "action_required": "Manual intervention needed",
    }
    return send_alert("CAPTCHA Detected", details, settings, severity="error")


def alert_rate_limited(
    record_info: Dict[str, Any],
    settings: Optional[Any] = None,
    retry_after: Optional[int] = None,
) -> bool:
    """Send alert for rate limiting detection.

    Parameters
    ----------
    record_info : dict
        Information about the current record
    settings : EcorpSettings, optional
        Ecorp settings
    retry_after : int, optional
        Seconds to wait before retry

    Returns
    -------
    bool
        True if alert was sent
    """
    details = {
        "record_index": record_info.get("index", "unknown"),
        "owner_name": record_info.get("owner_name", "unknown"),
        "retry_after": f"{retry_after} seconds" if retry_after else "unknown",
        "recommendation": "Wait before resuming",
    }
    return send_alert("Rate Limited", details, settings, severity="warning")


def alert_consecutive_failures(
    failure_count: int,
    record_info: Dict[str, Any],
    settings: Optional[Any] = None,
) -> bool:
    """Send alert for consecutive lookup failures.

    Parameters
    ----------
    failure_count : int
        Number of consecutive failures
    record_info : dict
        Information about the current record
    settings : EcorpSettings, optional
        Ecorp settings

    Returns
    -------
    bool
        True if alert was sent
    """
    details = {
        "consecutive_failures": failure_count,
        "last_record_index": record_info.get("index", "unknown"),
        "last_owner_name": record_info.get("owner_name", "unknown"),
        "recommendation": "Check connection and site status",
    }
    return send_alert(
        f"{failure_count} Consecutive Failures", details, settings, severity="error"
    )


def alert_scraper_completed(
    month_code: str,
    records_processed: int,
    duration_seconds: float,
    settings: Optional[Any] = None,
) -> bool:
    """Send alert when scraper completes successfully.

    Parameters
    ----------
    month_code : str
        Month being processed
    records_processed : int
        Number of records processed
    duration_seconds : float
        Total processing time
    settings : EcorpSettings, optional
        Ecorp settings

    Returns
    -------
    bool
        True if alert was sent
    """
    minutes = duration_seconds / 60
    details = {
        "month": month_code,
        "records_processed": records_processed,
        "duration": f"{minutes:.1f} minutes",
        "rate": (
            f"{records_processed / minutes:.1f} records/min" if minutes > 0 else "N/A"
        ),
    }
    return send_alert("Scraper Completed", details, settings, severity="info")


def alert_checkpoint_saved(
    checkpoint_path: str,
    record_index: int,
    total_records: int,
    settings: Optional[Any] = None,
) -> bool:
    """Send alert when checkpoint is saved (useful for long runs).

    Parameters
    ----------
    checkpoint_path : str
        Path to checkpoint file
    record_index : int
        Current record index
    total_records : int
        Total records to process
    settings : EcorpSettings, optional
        Ecorp settings

    Returns
    -------
    bool
        True if alert was sent
    """
    progress_pct = (record_index / total_records * 100) if total_records > 0 else 0
    details = {
        "progress": f"{record_index}/{total_records} ({progress_pct:.1f}%)",
        "checkpoint_file": checkpoint_path,
    }
    # Only send checkpoint alerts for significant progress (every 25%)
    if progress_pct % 25 < 5:  # Within 5% of a 25% milestone
        return send_alert("Progress Checkpoint", details, settings, severity="info")
    return False
