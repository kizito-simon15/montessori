# apps/sms/beem_service.py
from __future__ import annotations

import base64
import logging
from typing import Dict, List

import requests
from django.conf import settings

from .models import SentSMS

logger = logging.getLogger(__name__)

# ── credentials (read from settings.py; fall back to sample values) ─────────────
API_KEY     = getattr(settings, "BEEM_API_KEY",  "your_api_key_here")
SECRET_KEY  = getattr(settings, "BEEM_SECRET_KEY", "your_secret_key_here")
SOURCE_ADDR = getattr(settings, "BEEM_SOURCE_ADDR", "MONTESSORI")

BASE_URL = "https://apisms.beem.africa"

def _auth_header() -> Dict[str, str]:
    token = f"{API_KEY}:{SECRET_KEY}"
    encoded = base64.b64encode(token.encode()).decode()
    return {"Authorization": f"Basic {encoded}"}

def _json_or_error(resp: requests.Response) -> Dict:
    try:
        return resp.json()
    except ValueError:
        logger.error("Non-JSON response from Beem: %s", resp.text[:200])
        return {"successful": False, "error": "Invalid response from Beem"}

# ── PUBLIC API ─────────────────────────────────────────────────────────────────
def send_sms(message: str, recipients: List[Dict]) -> Dict:
    """Send an SMS blast via Beem."""
    recipients = list({r["dest_addr"]: r for r in recipients if r.get("dest_addr")}.values())
    if not recipients:
        return {"successful": False, "error": "No valid recipients"}

    url = f"{BASE_URL}/v1/send"
    payload = {
        "source_addr":   SOURCE_ADDR,
        "schedule_time": "",
        "encoding":      0,
        "message":       message,
        "recipients": [
            {"recipient_id": i + 1, "dest_addr": r["dest_addr"]}
            for i, r in enumerate(recipients)
        ],
    }
    headers = {"Content-Type": "application/json", **_auth_header()}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
    except requests.RequestException as exc:
        logger.exception("Beem send failed: %s", exc)
        return {"successful": False, "error": f"Network error: {exc}"}

    data = _json_or_error(resp)
    logger.debug("Beem response %s", data)

    if resp.status_code != 200 and "error" not in data:
        data = {"successful": False, "error": f"{resp.status_code}: {resp.text[:200]}"}

    if resp.status_code == 200 and data.get("successful"):
        _archive_success(message, recipients, data.get("network", ""))

    return data

def check_balance() -> Dict:
    """Return SMS balance from Beem."""
    url = f"{BASE_URL}/public/v1/vendors/balance"
    try:
        resp = requests.get(url, headers=_auth_header(), timeout=15)
    except requests.RequestException as exc:
        logger.exception("Beem balance failed: %s", exc)
        return {"error": f"Network error: {exc}"}

    if resp.ok:
        return _json_or_error(resp)
    else:
        return {"error": f"{resp.status_code}: {resp.text[:200]}"}

# ── helpers ───────────────────────────────────────────────────────────────────
def _archive_success(message: str, recs: List[Dict], net: str):
    for r in {r["dest_addr"]: r for r in recs}.values():
        SentSMS.objects.create(
            dest_addr=r["dest_addr"],
            first_name=r.get("first_name") or "",
            last_name=r.get("last_name") or "",
            message=message,
            network=net or "Unknown",
            length=len(message),
            sms_count=((len(message) - 1) // 160) + 1,
            status="Sent",
        )
