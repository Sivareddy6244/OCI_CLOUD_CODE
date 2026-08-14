#!/usr/bin/env python3
"""
Cherwell Integration Module
Provides functions for creating incidents and tasks in Cherwell after VM deployment.
"""

import os
import logging
import time
import requests
import urllib3
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

# Logger setup
logger = logging.getLogger(__name__)

# HTTP verify toggle for SSL certificate verification
HTTP_VERIFY = os.getenv("HTTP_VERIFY", "true").lower() in ("1", "true", "yes")
if not HTTP_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Cherwell configuration
CHERWELL_BASE_URL = os.getenv("CHERWELL_BASE_URL", "")
CHERWELL_CLIENT_GUID = os.getenv("CHERWELL_CLIENT_GUID", "")
CHERWELL_USER = os.getenv("CHERWELL_USER", "")
CHERWELL_PASSWORD = os.getenv("CHERWELL_PASSWORD", "")
CHERWELL_ENABLED = os.getenv("CHERWELL_ENABLED", "false").lower() in ("1", "true", "yes")

# Cherwell token retry/backoff configuration
CHERWELL_TOKEN_TIMEOUT = int(os.getenv("CHERWELL_TOKEN_TIMEOUT", "30"))
CHERWELL_TOKEN_RETRIES = int(os.getenv("CHERWELL_TOKEN_RETRIES", "3"))
CHERWELL_TOKEN_BACKOFF = float(os.getenv("CHERWELL_TOKEN_BACKOFF", "1.5"))

# Cherwell Business Object IDs
INCIDENT_BUSOBID = os.getenv("INCIDENT_BUSOBID", "6dd53665c0c24cab86870a21cf6434ae")
TASK_BUSOBID = os.getenv("TASK_BUSOBID", "9355d5ed41e384ff345b014b6cb1c6e748594aea5b")
CUSTOMER_BUSOBID = os.getenv("CUSTOMER_BUSOBID", "93405caa107c376a2bd15c4c8885a900be316f3a72")

# ✅ Incident desired defaults
INCIDENT_STATUS_VALUE = os.getenv("INCIDENT_STATUS_VALUE", "In Progress")

# Priority/Impact/Urgency (fieldIds come from your Cherwell team)
INCIDENT_FIELD_PRIORITY_ID = os.getenv("INCIDENT_FIELD_PRIORITY_ID", "")
INCIDENT_PRIORITY_VALUE = os.getenv("INCIDENT_PRIORITY_VALUE", "H1")

INCIDENT_FIELD_IMPACT_ID = os.getenv("INCIDENT_FIELD_IMPACT_ID", "")
INCIDENT_IMPACT_VALUE = os.getenv("INCIDENT_IMPACT_VALUE", "Department or Small Group")

INCIDENT_FIELD_URGENCY_ID = os.getenv("INCIDENT_FIELD_URGENCY_ID", "")
INCIDENT_URGENCY_VALUE = os.getenv("INCIDENT_URGENCY_VALUE", "No Workaround")

# Cherwell Field IDs for Task creation
TASK_FIELD_PARENT_PUBLICID = os.getenv(
    "TASK_FIELD_PARENT_PUBLICID",
    "BO:9355d5ed41e384ff345b014b6cb1c6e748594aea5b,FI:9387d7efd191c18d9f954747a08ed7765b883e0925"
)
TASK_FIELD_PARENT_RECID = os.getenv(
    "TASK_FIELD_PARENT_RECID",
    "BO:9355d5ed41e384ff345b014b6cb1c6e748594aea5b,FI:9355d6d6f3d7531087eab4456482100476d46ac59b"
)
TASK_FIELD_PARENT_TYPE_NAME = os.getenv(
    "TASK_FIELD_PARENT_TYPE_NAME",
    "BO:9355d5ed41e384ff345b014b6cb1c6e748594aea5b,FI:9387d7edcd90b26af435a5407abac99d264bb2dfcb"
)
TASK_FIELD_SUBJECT = os.getenv(
    "TASK_FIELD_SUBJECT",
    "BO:9355d5ed41e384ff345b014b6cb1c6e748594aea5b,FI:93ad98a2d68a61778eda3d4d9cbb30acbfd458aea4"
)
TASK_FIELD_NOTES = os.getenv(
    "TASK_FIELD_NOTES",
    "BO:9355d5ed41e384ff345b014b6cb1c6e748594aea5b,FI:9368f144c4290cc902bcf348fba96c062b9b85e8ef"
)
TASK_FIELD_TENANT = os.getenv(
    "TASK_FIELD_TENANT",
    "BO:9355d5ed41e384ff345b014b6cb1c6e748594aea5b,FI:93d663f9eef793e4b2d3934a26b60eb4ab06eb5636"
)
TASK_FIELD_STATUS = os.getenv(
    "TASK_FIELD_STATUS",
    "BO:9355d5ed41e384ff345b014b6cb1c6e748594aea5b,FI:9368f0fb7b744108a666984c21afc932562eb7dc16"
)
TASK_FIELD_OWNED_BY_TEAM = os.getenv(
    "TASK_FIELD_OWNED_BY_TEAM",
    "BO:9355d5ed41e384ff345b014b6cb1c6e748594aea5b,FI:93cfd5a4e10af4933a573444d08cbc412da491b42e"
)
TASK_FIELD_TASKTYPE = os.getenv(
    "TASK_FIELD_TASKTYPE",
    "BO:9355d5ed41e384ff345b014b6cb1c6e748594aea5b,FI:9355d5ed6ca15a8308c5e24389b2138b3aa9b6c7fa"
)

# Cherwell field values
TASK_FIELD_PARENT_TYPE_NAME_VALUE = os.getenv("TASK_FIELD_PARENT_TYPE_NAME_VALUE", "Incident")
TASK_FIELD_TASKTYPE_VALUE = os.getenv("TASK_FIELD_TASKTYPE_VALUE", "Action")
CHERWELL_TENANT_NAME = os.getenv("CHERWELL_TENANT_NAME", "ISD-ITS")

# Incident classification values
INCIDENT_SERVICE = os.getenv("INCIDENT_SERVICE", "Cherwell Service Management Solution")
INCIDENT_CATEGORY = os.getenv("INCIDENT_CATEGORY", "Request")
INCIDENT_SUBCATEGORY = os.getenv("INCIDENT_SUBCATEGORY", "Other")
INCIDENT_SOURCE = os.getenv("INCIDENT_SOURCE", "E-mail")

# Contact and Customer Field IDs
FIELD_CONTACT_ID = os.getenv("FIELD_CONTACT_ID", "93d541bc861d632d61b3974886a46bfc2c78cd434a")
FIELD_CUSTOMER_ID = os.getenv("FIELD_CUSTOMER_ID", "933bd530833c64efbf66f84114acabb3e90c6d7b8f")

# Email Field ID in Customer/Contact Business Object
CUSTOMER_EMAIL_FIELD = os.getenv(
    "CUSTOMER_EMAIL_FIELD",
    "BO:93405caa107c376a2bd15c4c8885a900be316f3a72,FI:9337c23403da50548767c24e48aede27e5dd274521"
)

# Email settings
SMTP_SERVER = os.getenv("SMTP_SERVER", "amail.lacounty.gov")
SMTP_PORT = int(os.getenv("SMTP_PORT", "25"))
SMTP_FROM = os.getenv("SMTP_FROM", "ecloud@isd.lacounty.gov")

TEAM_EMAIL_CC = os.getenv("TEAM_EMAIL_CC", "dpulimamidi.consultant@isd.lacounty.gov")

CHERWELL_TEAM_CROWDSTRIKE = os.getenv("CHERWELL_TEAM_CROWDSTRIKE", "ISD-CGO-EPP")
CHERWELL_TEAM_SECUREWORKS = os.getenv("CHERWELL_TEAM_SECUREWORKS", "Analytics")
CHERWELL_TEAM_TANIUM = os.getenv("CHERWELL_TEAM_TANIUM", "Windows Server Engineering")
CHERWELL_TEAM_TENABLE = os.getenv("CHERWELL_TEAM_TENABLE", "ISD-CGO-Tenable")
CHERWELL_TEAM_TETRATION = os.getenv("CHERWELL_TEAM_TETRATION", "Analytics")
CHERWELL_TEAM_BACKUP = os.getenv("CHERWELL_TEAM_BACKUP", "ISD-Storage")

TEAM_EMAIL_CROWDSTRIKE = os.getenv("TEAM_EMAIL_CROWDSTRIKE", "dpulimamidi.consultant@isd.lacounty.gov")
TEAM_EMAIL_SECUREWORKS = os.getenv("TEAM_EMAIL_SECUREWORKS", "dpulimamidi.consultant@isd.lacounty.gov")
TEAM_EMAIL_TANIUM = os.getenv("TEAM_EMAIL_TANIUM", "dpulimamidi.consultant@isd.lacounty.gov")
TEAM_EMAIL_TENABLE = os.getenv("TEAM_EMAIL_TENABLE", "dpulimamidi.consultant@isd.lacounty.gov")
TEAM_EMAIL_TETRATION = os.getenv("TEAM_EMAIL_TETRATION", "dpulimamidi.consultant@isd.lacounty.gov")
TEAM_EMAIL_BACKUP = os.getenv("TEAM_EMAIL_BACKUP", "dpulimamidi.consultant@isd.lacounty.gov")

# Data protection option values (must match the frontend dropdown options)
DATA_PROTECTION_ISD_MANAGED = "isd managed backup"

HELP_DESK_PHONE = os.getenv("HELP_DESK_PHONE", "(562) 940-3305")
ECLOUD_INFO_EMAIL = os.getenv("ECLOUD_INFO_EMAIL", "ecloud@isd.lacounty.gov")
ECLOUD_PORTAL_URL = os.getenv("ECLOUD_PORTAL_URL", "https://multicloud-estore-f9dwa3fbaad8gwcx.westus2-01.azurewebsites.net/")
DEFAULT_DNS_SUFFIX = os.getenv("DEFAULT_DNS_SUFFIX", "isd.lacounty.gov")


def cherwell_get_token() -> Optional[str]:
    """Get Cherwell API access token with retry logic"""
    if not CHERWELL_ENABLED:
        logger.debug("Cherwell integration is disabled")
        return None

    if not CHERWELL_PASSWORD or not CHERWELL_CLIENT_GUID:
        logger.warning("CHERWELL_PASSWORD or CHERWELL_CLIENT_GUID not set")
        return None

    if not CHERWELL_BASE_URL:
        logger.warning("CHERWELL_BASE_URL not set")
        return None

    url = f"{CHERWELL_BASE_URL}/token"
    params = {"auth_mode": "Internal", "api_key": CHERWELL_CLIENT_GUID}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "password",
        "username": CHERWELL_USER,
        "password": CHERWELL_PASSWORD,
        "client_id": CHERWELL_CLIENT_GUID
    }

    last_exc = None

    for attempt in range(1, CHERWELL_TOKEN_RETRIES + 1):
        try:
            resp = requests.post(
                url,
                params=params,
                data=data,
                headers=headers,
                verify=HTTP_VERIFY,
                timeout=CHERWELL_TOKEN_TIMEOUT
            )
            if resp.status_code != 200:
                logger.warning(
                    "cherwell_get_token attempt %d returned %s: %s",
                    attempt, resp.status_code, resp.text[:500]
                )
                last_exc = Exception(f"Failed to get token. Status: {resp.status_code}, Response: {resp.text}")
            else:
                j = resp.json()
                token = j.get("access_token")
                if not token:
                    logger.warning("cherwell_get_token: token endpoint returned no access_token: %s", j)
                    last_exc = Exception(f"No access_token in token response: {j}")
                else:
                    logger.debug("Cherwell token acquired successfully")
                    return token
        except Exception as ex:
            last_exc = ex
            logger.warning("cherwell_get_token attempt %d failed: %s", attempt, ex)

        if attempt < CHERWELL_TOKEN_RETRIES:
            sleep_for = (CHERWELL_TOKEN_BACKOFF ** (attempt - 1))
            time.sleep(sleep_for)

    logger.error(
        "Failed to obtain Cherwell token after %d attempts. Last error: %s",
        CHERWELL_TOKEN_RETRIES, last_exc
    )
    return None


def cherwell_lookup_contact_by_email(token: str, email: str) -> Optional[str]:
    """Look up a Cherwell Contact RecID by email address"""
    if not token or not email:
        logger.warning("Cannot lookup contact: missing token or email")
        return None

    if not CUSTOMER_EMAIL_FIELD:
        logger.error("CUSTOMER_EMAIL_FIELD environment variable is not configured!")
        return None

    url = f"{CHERWELL_BASE_URL}/api/V1/getsearchresults"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    payload = {
        "busObId": CUSTOMER_BUSOBID,
        "filters": [
            {"fieldId": CUSTOMER_EMAIL_FIELD, "operator": "contains", "value": email}
        ],
        "includeAllFields": False,
        "pageNumber": 1,
        "pageSize": 1
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, verify=HTTP_VERIFY, timeout=15)
        if resp.status_code != 200:
            logger.warning("Contact lookup for %s returned %s: %s", email, resp.status_code, resp.text[:500])
            return None

        result = resp.json()
        business_objects = result.get("businessObjects", [])

        if business_objects:
            rec_id = business_objects[0].get("busObRecId")
            logger.info("Found Cherwell contact for %s: RecID=%s", email, rec_id)
            return rec_id

        logger.warning("No Cherwell contact found for email: %s", email)
        return None

    except Exception as e:
        logger.exception("Error looking up Cherwell contact for %s: %s", email, e)
        return None


def _append_incident_field(fields: List[Dict[str, Any]], display_name: str, field_id: str, name: str, value: str):
    """Append a Cherwell incident field only if field_id is configured and value is non-empty."""
    if not field_id:
        logger.warning("Missing fieldId for %s; skipping. (env var not set)", display_name)
        return
    if value is None or str(value).strip() == "":
        logger.warning("Missing value for %s; skipping.", display_name)
        return
    fields.append({
        "dirty": True,
        "displayName": display_name,
        "fieldId": field_id,
        "name": name,
        "value": value
    })


def cherwell_create_incident(
    token: str,
    description: str,
    contact_email: Optional[str] = None,
    requested_by_display: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Create an incident in Cherwell with dynamic contact lookup by email"""
    if not token or not INCIDENT_BUSOBID:
        logger.warning("Cannot create Cherwell incident: missing token or INCIDENT_BUSOBID")
        return None

    if not contact_email:
        logger.error("❌ Cannot create Cherwell incident: No user email provided")
        return None

    contact_rec_id = cherwell_lookup_contact_by_email(token, contact_email)
    if not contact_rec_id:
        logger.error("❌ Cannot create Cherwell incident: User '%s' not found in Cherwell system", contact_email)
        return None

    url = f"{CHERWELL_BASE_URL}/api/V1/savebusinessobject"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    fields: List[Dict[str, Any]] = [
        # ✅ Status = In Progress
        {"dirty": True, "displayName": "Status", "fieldId": "5eb3234ae1344c64a19819eda437f18d", "name": "Status", "value": INCIDENT_STATUS_VALUE},

        {"dirty": True, "displayName": "Description", "fieldId": "252b836fc72c4149915053ca1131d138", "name": "Description", "value": description},
        {"dirty": True, "displayName": "Call Source", "fieldId": "93670bdf8abe2cd1f92b1f490a90c7b7d684222e13", "name": "Source", "value": INCIDENT_SOURCE},
        {"dirty": True, "displayName": "Service", "fieldId": "936725cd10c735d1dd8c5b4cd4969cb0bd833655f4", "name": "Service", "value": INCIDENT_SERVICE},
        {"dirty": True, "displayName": "Category", "fieldId": "9e0b434034e94781ab29598150f388aa", "name": "Category", "value": INCIDENT_CATEGORY},
        {"dirty": True, "displayName": "SubCategory", "fieldId": "1163fda7e6a44f40bb94d2b47cc58f46", "name": "SubCategory", "value": INCIDENT_SUBCATEGORY},
        {"dirty": True, "displayName": "Tenant Name", "fieldId": "93d6566e921838c34bd38c4b23b99b4066877873ca", "name": "TenantName", "value": CHERWELL_TENANT_NAME},
    ]

    # ✅ Set Priority / Impact / Urgency
    _append_incident_field(fields, "Priority", INCIDENT_FIELD_PRIORITY_ID, "Priority", INCIDENT_PRIORITY_VALUE)
    _append_incident_field(fields, "Impact", INCIDENT_FIELD_IMPACT_ID, "Impact", INCIDENT_IMPACT_VALUE)
    _append_incident_field(fields, "Urgency", INCIDENT_FIELD_URGENCY_ID, "Urgency", INCIDENT_URGENCY_VALUE)

    # Contact + Customer
    fields.append({"dirty": True, "displayName": "Contact ID", "fieldId": FIELD_CONTACT_ID, "name": "ContactID", "value": contact_rec_id})
    fields.append({"dirty": True, "displayName": "Customer ID", "fieldId": FIELD_CUSTOMER_ID, "name": "CustomerID", "value": contact_rec_id})

    payload = {"busObId": INCIDENT_BUSOBID, "fields": fields}

    try:
        resp = requests.post(url, json=payload, headers=headers, verify=HTTP_VERIFY, timeout=20)
        if resp.status_code >= 400:
            logger.error("Failed to create Cherwell incident: %s - %s", resp.status_code, resp.text[:1000])
            return None

        result = resp.json()
        logger.info(
            "✅ Cherwell incident created: %s for user %s (Status=%s, Priority=%s, Impact=%s, Urgency=%s)",
            result.get("busObPublicId", "N/A"),
            requested_by_display or contact_email,
            INCIDENT_STATUS_VALUE,
            INCIDENT_PRIORITY_VALUE,
            INCIDENT_IMPACT_VALUE,
            INCIDENT_URGENCY_VALUE
        )
        return result
    except Exception as e:
        logger.exception("Error creating Cherwell incident: %s", e)
        return None


def cherwell_create_task(
    token: str,
    parent_publicid: str,
    parent_recid: str,
    subject: str,
    notes: str,
    owner_team: str = ""
) -> Optional[Dict[str, Any]]:
    """Create a task in Cherwell linked to a parent incident"""
    if not token or not TASK_BUSOBID:
        logger.warning("Cannot create Cherwell task: missing token or TASK_BUSOBID")
        return None

    url = f"{CHERWELL_BASE_URL}/api/V1/savebusinessobject"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    fields: List[Dict[str, Any]] = []

    if TASK_FIELD_PARENT_PUBLICID:
        fields.append({"dirty": True, "displayName": "Parent PublicID", "fieldId": TASK_FIELD_PARENT_PUBLICID, "name": "ParentPublicID", "value": parent_publicid})
    if TASK_FIELD_PARENT_RECID:
        fields.append({"dirty": True, "displayName": "Parent RecID", "fieldId": TASK_FIELD_PARENT_RECID, "name": "ParentRecID", "value": parent_recid})
    if TASK_FIELD_PARENT_TYPE_NAME:
        fields.append({"dirty": True, "displayName": "Parent Type Name", "fieldId": TASK_FIELD_PARENT_TYPE_NAME, "name": "ParentTypeName", "value": TASK_FIELD_PARENT_TYPE_NAME_VALUE})
    if TASK_FIELD_SUBJECT:
        fields.append({"dirty": True, "displayName": "Subject", "fieldId": TASK_FIELD_SUBJECT, "name": "Subject", "value": subject})
    if TASK_FIELD_NOTES:
        fields.append({"dirty": True, "displayName": "Notes", "fieldId": TASK_FIELD_NOTES, "name": "Notes", "value": notes})
    if TASK_FIELD_TENANT:
        fields.append({"dirty": True, "displayName": "Tenant Name", "fieldId": TASK_FIELD_TENANT, "name": "TenantName", "value": CHERWELL_TENANT_NAME})
    if TASK_FIELD_STATUS:
        fields.append({"dirty": True, "displayName": "Status", "fieldId": TASK_FIELD_STATUS, "name": "Status", "value": "New"})

    if TASK_FIELD_OWNED_BY_TEAM and owner_team:
        fields.append({"dirty": True, "displayName": "Owned By Team", "fieldId": TASK_FIELD_OWNED_BY_TEAM, "name": "OwnedByTeam", "value": owner_team})
        logger.debug("Assigning task '%s' to team: %s", subject, owner_team)

    if TASK_FIELD_TASKTYPE:
        fields.append({"dirty": True, "displayName": "Task Type", "fieldId": TASK_FIELD_TASKTYPE, "name": "TaskType", "value": TASK_FIELD_TASKTYPE_VALUE})

    payload = {"busObId": TASK_BUSOBID, "fields": fields}

    try:
        resp = requests.post(url, json=payload, headers=headers, verify=HTTP_VERIFY, timeout=20)
        if resp.status_code >= 400:
            logger.error("Failed to create Cherwell task: %s - %s", resp.status_code, resp.text[:1000])
            return None

        result = resp.json()
        logger.info("✅ Cherwell task created: %s (Team: %s)", result.get("busObPublicId", "N/A"), owner_team or "None")
        return result
    except Exception as e:
        logger.exception("Error creating Cherwell task: %s", e)
        return None


def _smtp_send(to_addrs: List[str], subject: str, body: str, cc_addrs: Optional[List[str]] = None):
    """Internal helper to send SMTP mail."""
    from email.mime.text import MIMEText
    import smtplib

    cc_addrs = cc_addrs or []
    to_addrs = [a for a in (to_addrs or []) if a]
    cc_addrs = [a for a in (cc_addrs or []) if a]

    if not to_addrs:
        logger.debug("No recipients provided; skipping email send. subject=%s", subject)
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = ", ".join(to_addrs)
    if cc_addrs:
        msg["Cc"] = ", ".join(cc_addrs)

    all_rcpts = list(dict.fromkeys(to_addrs + cc_addrs))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as smtp:
        smtp.sendmail(SMTP_FROM, all_rcpts, msg.as_string())
def _as_utc_string(value: Any) -> str:
    """
    Convert various time representations into a consistent UTC display string.
    Output format: YYYY-MM-DD HH:MM:SS UTC
    Accepts: datetime, ISO string, or other string.
    """
    if value is None:
        return "N/A"

    # datetime object
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_utc = dt.astimezone(timezone.utc)
        return dt_utc.strftime("%Y-%m-%d %H:%M:%S UTC")

    # string (try ISO parse)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return "N/A"
        try:
            # Handle common ISO forms: "2026-03-04T23:50:00Z" or with offset
            if s.endswith("Z"):
                s2 = s[:-1] + "+00:00"
            else:
                s2 = s
            dt = datetime.fromisoformat(s2)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt_utc = dt.astimezone(timezone.utc)
            return dt_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            # If it's not ISO, just return the raw string (better than N/A)
            return s

    # fallback
    return str(value)


def _extract_provisioning_start_time(vm_details: Dict[str, Any]) -> str:
    """
    Pull provisioning start time from multiple possible keys.
    Canonical key we will set is provisioning_start_time.
    """
    if not isinstance(vm_details, dict):
        return "N/A"

    for key in (
        "provisioning_start_time",   # canonical (snake_case)
        "provisioningStartTime",     # canonical (camelCase) - just in case
        "time_created",
        "timeCreated",
        "creationTimestamp",
        "launch_time",
        "LaunchTime",
    ):
        if key in vm_details and vm_details.get(key):
            return _as_utc_string(vm_details.get(key))

    return "N/A"


def send_team_notification_email(
    agent_name: str,
    ticket_number: str,
    cloud_provider: str,
    account_name: str,
    requestor_display: str,
    to_email: str,
    cc_email: str = TEAM_EMAIL_CC
):
    """Send email notification to the specific agent installation team (with CC)."""
    if not to_email:
        logger.debug("No team email configured for %s, skipping notification", agent_name)
        return

    try:
        subject = f"{agent_name} Installation Request - Ticket #{ticket_number}"

        body = f"""Hello Team,

An {agent_name} installation request has been submitted and linked to Cherwell ticket ID: {ticket_number}.

Provider: {cloud_provider}
Subscription/Account: {account_name}
Requestor: {requestor_display}

Please review ticket ID {ticket_number} and proceed with the required installation.

Thank you,
ISD eCloud Portal
"""

        _smtp_send([to_email], subject, body, cc_addrs=[cc_email] if cc_email else [])
        logger.info("✅ Team notification email sent to %s (CC=%s) for %s (Ticket: %s)", to_email, cc_email, agent_name, ticket_number)
    except Exception as e:
        logger.exception("Failed to send team notification email for %s: %s", agent_name, e)


def _format_onprem_style_customer_email(
    customer_display: str,
    vm_name: str,
    cloud: str,
    vm_details: Dict[str, Any],
    portal_fields: Dict[str, Any],
    ticket_number: str
) -> str:
    account_number = portal_fields.get("AccountNumber") or portal_fields.get("accountnumber") or "N/A"
    approvers = portal_fields.get("Approvers") or portal_fields.get("approvers") or "N/A"
    ps = portal_fields.get("PS") or portal_fields.get("ps") or "N/A"

    os_type = vm_details.get("os_type") or vm_details.get("os") or "N/A"
    image_name = vm_details.get("image_name") or vm_details.get("image") or vm_details.get("image_family") or "N/A"

    start_time = _extract_provisioning_start_time(vm_details)

    acct_display = (
        vm_details.get("account_name_display")
        or vm_details.get("account")
        or vm_details.get("subscription_id")
        or vm_details.get("project")
        or "N/A"
    )

    lines = []
    lines.append("Dear Customer,")
    lines.append("")
    lines.append(f"{vm_name} has been created and is ready for use.")
    lines.append("")
    lines.append("--------------")
    lines.append("The current configuration is:")
    lines.append(f"Cloud Provider: [{cloud.upper()}]")
    lines.append(f"Subscription/Account: [{acct_display}]")
    lines.append(f"Professional Services: [{ps}]")
    lines.append(f"Operating System: [{os_type}]")
    lines.append(f"Image: [{image_name}]")
    lines.append(f"Approvers: [{approvers}]")
    lines.append(f"Account Number to charge: [{account_number}]")
    lines.append("")
    lines.append(f"Cherwell Ticket Number: [{ticket_number}]")
    lines.append("")
    lines.append("--------------")
    lines.append("Provisioning Start Time: [" + str(start_time) + "]")
    lines.append("")
    lines.append("--------------")
    lines.append(
        "If you need any additional information, please feel free to contact us at "
        f"{ECLOUD_INFO_EMAIL} or visit us at {ECLOUD_PORTAL_URL}."
    )
    lines.append("")
    lines.append("Thank you,")
    lines.append("The eCloud Team")
    return "\n".join(lines)


def send_ticket_notification_to_customer(
    customer_email: str,
    customer_display: str,
    vm_name: str,
    cloud: str,
    ticket_number: str,
    vm_details: Dict[str, Any]
):
    if not customer_email:
        logger.debug("No customer email provided, skipping notification")
        return

    try:
        subject = f"{vm_name} has been created and is ready for use"

        portal_fields = {}
        if isinstance(vm_details.get("tags"), dict):
            portal_fields = vm_details.get("tags", {})
        elif isinstance(vm_details.get("labels"), dict):
            portal_fields = vm_details.get("labels", {})
        elif isinstance(vm_details.get("portal_tags"), dict):
            portal_fields = vm_details.get("portal_tags", {})

        body = _format_onprem_style_customer_email(
            customer_display=customer_display,
            vm_name=vm_name,
            cloud=cloud,
            vm_details=vm_details,
            portal_fields=portal_fields,
            ticket_number=ticket_number
        )

        _smtp_send([customer_email], subject, body, cc_addrs=[])
        logger.info("✅ Ticket notification email sent to customer: %s (Ticket: %s)", customer_email, ticket_number)
    except Exception as e:
        logger.exception("Failed to send ticket notification email to customer: %s", e)


def _requested_by_display(user_email: Optional[str], user_name: Optional[str] = None) -> str:
    email = user_email or "Unknown"
    name = (user_name or "").strip()
    if name:
        return f"{name} ({email})"
    return f"{email} ({email})"


def _extract_account_display(vm_details: Dict[str, Any], cloud: str) -> str:
    for k in ("account_name_display", "subscription_account", "subscription_name", "account_name", "account", "subscription_id", "project"):
        v = vm_details.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return "Unknown"


def create_post_deployment_tasks(vm_name: str, cloud: str, vm_details: Dict[str, Any], user_email: Optional[str] = None) -> Dict[str, Any]:
    if not CHERWELL_ENABLED:
        logger.debug("Cherwell integration disabled, skipping task creation")
        return {"cherwell_enabled": False}

    result: Dict[str, Any] = {"cherwell_enabled": True, "tasks_created": []}

    try:
        token = cherwell_get_token()
        if not token:
            result["error"] = "Failed to get Cherwell token"
            return result

        requestor_display = _requested_by_display(user_email)
        account_display = _extract_account_display(vm_details, cloud)
        data_protection = str(vm_details.get("data_protection", "") or "").strip()
        include_backup_task = data_protection.lower() == DATA_PROTECTION_ISD_MANAGED

        incident_description = (
            "Unanimous ticket created by eCloud Portal\n"
            f"Requested by: {requestor_display}\n"
            f"Subscription/Account: {account_display}\n\n"
            "This ticket will have the following tasks created in sequence:\n"
            "1) Install CrowdStrike Agent\n"
            "2) Install SecureWorks Agent\n"
            "3) Install Tanium Agent\n"
            "4) Install Tenable Agent\n"
            "5) Install Tetration Agent\n"
        )
        if include_backup_task:
            incident_description += "6) Configure ISD Managed Backup\n"

        incident = cherwell_create_incident(
            token,
            incident_description,
            contact_email=user_email,
            requested_by_display=requestor_display
        )

        if not incident:
            result["error"] = f"Failed to create Cherwell incident - User '{user_email}' not found in Cherwell."
            return result

        incident_publicid = incident.get("busObPublicId", "")
        incident_recid = incident.get("busObRecId", "")
        result["incident_id"] = incident_publicid

        os_type = str(vm_details.get("os_type", "") or "").lower()
        image_name = str(vm_details.get("image_name", "") or vm_details.get("image", "") or "").lower()

        is_windows = False
        is_linux = False

        if "windows" in os_type or "win" in image_name:
            is_windows = True
        elif "linux" in os_type or any(keyword in image_name for keyword in ["rhel", "ubuntu", "centos", "debian", "amazon", "linux"]):
            is_linux = True
        else:
            is_linux = True
            is_windows = True

        os_display = "Windows" if is_windows and not is_linux else "Linux" if is_linux and not is_windows else "Windows/Linux"
        cloud_provider_display = cloud.upper()

        tasks_to_create: List[Dict[str, str]] = [
            {
                "agent_name": "CrowdStrike Agent",
                "subject": f"Install CrowdStrike Agent ({os_display})",
                "notes": (
                    "Please install the CrowdStrike agent on this VM.\n\n"
                    f"VM Name: {vm_name}\n"
                    f"Cloud: {cloud_provider_display}\n"
                    f"OS Type: {os_display}\n"
                    f"Subscription/Account: {account_display}\n"
                    f"Incident: {incident_publicid}\n"
                ),
                "team": CHERWELL_TEAM_CROWDSTRIKE,
                "team_email": TEAM_EMAIL_CROWDSTRIKE
            },
            {
                "agent_name": "SecureWorks Agent",
                "subject": f"Install SecureWorks Agent ({os_display})",
                "notes": (
                    "Please install the SecureWorks agent on this VM.\n\n"
                    f"VM Name: {vm_name}\n"
                    f"Cloud: {cloud_provider_display}\n"
                    f"OS Type: {os_display}\n"
                    f"Subscription/Account: {account_display}\n"
                    f"Incident: {incident_publicid}\n"
                ),
                "team": CHERWELL_TEAM_SECUREWORKS,
                "team_email": TEAM_EMAIL_SECUREWORKS
            },
            {
                "agent_name": "Tanium Agent",
                "subject": f"Install Tanium Agent ({os_display})",
                "notes": (
                    "Please install the Tanium agent on this VM.\n\n"
                    f"VM Name: {vm_name}\n"
                    f"Cloud: {cloud_provider_display}\n"
                    f"OS Type: {os_display}\n"
                    f"Subscription/Account: {account_display}\n"
                    f"Incident: {incident_publicid}\n"
                ),
                "team": CHERWELL_TEAM_TANIUM,
                "team_email": TEAM_EMAIL_TANIUM
            },
            {
                "agent_name": "Tenable Agent",
                "subject": f"Install Tenable Agent ({os_display})",
                "notes": (
                    "Please install the Tenable agent on this VM.\n\n"
                    f"VM Name: {vm_name}\n"
                    f"Cloud: {cloud_provider_display}\n"
                    f"OS Type: {os_display}\n"
                    f"Subscription/Account: {account_display}\n"
                    f"Incident: {incident_publicid}\n"
                ),
                "team": CHERWELL_TEAM_TENABLE,
                "team_email": TEAM_EMAIL_TENABLE
            },
            {
                "agent_name": "Tetration Agent",
                "subject": f"Install Tetration Agent ({os_display})",
                "notes": (
                    "Please install the Tetration agent on this VM.\n\n"
                    f"VM Name: {vm_name}\n"
                    f"Cloud: {cloud_provider_display}\n"
                    f"OS Type: {os_display}\n"
                    f"Subscription/Account: {account_display}\n"
                    f"Incident: {incident_publicid}\n"
                ),
                "team": CHERWELL_TEAM_TETRATION,
                "team_email": TEAM_EMAIL_TETRATION
            }
        ]

        if include_backup_task:
            tasks_to_create.append({
                "agent_name": "ISD Managed Backup",
                "subject": f"Configure ISD Managed Backup ({os_display})",
                "notes": (
                    "Please configure ISD Managed Backup for this VM.\n\n"
                    f"VM Name: {vm_name}\n"
                    f"Cloud: {cloud_provider_display}\n"
                    f"OS Type: {os_display}\n"
                    f"Subscription/Account: {account_display}\n"
                    f"Data Protection: ISD Managed Backup\n"
                    f"Incident: {incident_publicid}\n"
                ),
                "team": CHERWELL_TEAM_BACKUP,
                "team_email": TEAM_EMAIL_BACKUP
            })

        for task_info in tasks_to_create:
            task = cherwell_create_task(
                token=token,
                parent_publicid=incident_publicid,
                parent_recid=incident_recid,
                subject=task_info["subject"],
                notes=task_info["notes"],
                owner_team=task_info["team"]
            )

            if task:
                result["tasks_created"].append({
                    "agent_name": task_info["agent_name"],
                    "subject": task_info["subject"],
                    "task_id": task.get("busObPublicId", "N/A"),
                    "team": task_info["team"]
                })

                send_team_notification_email(
                    agent_name=task_info["agent_name"],
                    ticket_number=incident_publicid,
                    cloud_provider=cloud_provider_display,
                    account_name=account_display,
                    requestor_display=requestor_display,
                    to_email=task_info["team_email"],
                    cc_email=TEAM_EMAIL_CC
                )

        if user_email and incident_publicid:
            send_ticket_notification_to_customer(
                customer_email=user_email,
                customer_display=requestor_display,
                vm_name=vm_name,
                cloud=cloud,
                ticket_number=incident_publicid,
                vm_details=vm_details
            )

    except Exception as e:
        logger.exception("Error in create_post_deployment_tasks: %s", e)
        result["error"] = str(e)

    return result
