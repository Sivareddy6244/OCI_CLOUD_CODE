#!/usr/bin/env python3
"""
GCP Backend Module for Multi-Cloud Portal
Provides GCP-specific functionality including OAuth2 authentication,
project listing, resource enumeration, and VM deployment.
Supports Google OAuth for GCP authentication.
✅ NOW WITH TAG SUPPORT: AccountNumber, Approvers, PS
"""

from fastapi import APIRouter, HTTPException, Query, Request, Depends, Body
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import json
import subprocess
import logging
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time
import traceback
import re

logger = logging.getLogger(__name__)

# On-demand Linux hourly pricing (USD) for common GCP machine types (us-central1 reference price).
# Used as a best-effort estimate; actual costs depend on region and committed-use discounts.
_GCP_MACHINE_PRICING: Dict[str, float] = {
    # E2 — cost-optimised
    "e2-micro": 0.0084, "e2-small": 0.0168, "e2-medium": 0.0336,
    "e2-standard-2": 0.0670, "e2-standard-4": 0.1341, "e2-standard-8": 0.2682,
    "e2-standard-16": 0.5363, "e2-standard-32": 1.0727,
    "e2-highcpu-2": 0.0497, "e2-highcpu-4": 0.0994, "e2-highcpu-8": 0.1988,
    "e2-highcpu-16": 0.3976, "e2-highcpu-32": 0.7952,
    "e2-highmem-2": 0.0903, "e2-highmem-4": 0.1806, "e2-highmem-8": 0.3613,
    "e2-highmem-16": 0.7225,
    # N1 — balanced
    "n1-standard-1": 0.04749, "n1-standard-2": 0.09498, "n1-standard-4": 0.18997,
    "n1-standard-8": 0.37994, "n1-standard-16": 0.75987, "n1-standard-32": 1.51975,
    "n1-standard-64": 3.03949, "n1-standard-96": 4.55924,
    "n1-highcpu-2": 0.07080, "n1-highcpu-4": 0.14160, "n1-highcpu-8": 0.28321,
    "n1-highcpu-16": 0.56642, "n1-highcpu-32": 1.13284, "n1-highcpu-64": 2.26567,
    "n1-highmem-2": 0.11878, "n1-highmem-4": 0.23757, "n1-highmem-8": 0.47514,
    "n1-highmem-16": 0.95028, "n1-highmem-32": 1.90056, "n1-highmem-64": 3.80111,
    # N2 — balanced 2nd gen
    "n2-standard-2": 0.0971, "n2-standard-4": 0.1942, "n2-standard-8": 0.3885,
    "n2-standard-16": 0.7769, "n2-standard-32": 1.5539, "n2-standard-48": 2.3309,
    "n2-standard-64": 3.1078, "n2-standard-80": 3.8847, "n2-standard-96": 4.6617,
    "n2-highcpu-2": 0.07107, "n2-highcpu-4": 0.14214, "n2-highcpu-8": 0.28428,
    "n2-highcpu-16": 0.56857, "n2-highcpu-32": 1.13714, "n2-highcpu-48": 1.70571,
    "n2-highcpu-64": 2.27428, "n2-highcpu-80": 2.84285,
    "n2-highmem-2": 0.13083, "n2-highmem-4": 0.26166, "n2-highmem-8": 0.52333,
    "n2-highmem-16": 1.04665, "n2-highmem-32": 2.09330, "n2-highmem-48": 3.13995,
    "n2-highmem-64": 4.18661, "n2-highmem-80": 5.23326,
    # N2D — AMD
    "n2d-standard-2": 0.08728, "n2d-standard-4": 0.17456, "n2d-standard-8": 0.34912,
    "n2d-standard-16": 0.69824, "n2d-standard-32": 1.39648, "n2d-standard-48": 2.09472,
    "n2d-standard-64": 2.79296, "n2d-standard-96": 4.18944, "n2d-standard-128": 5.58592,
    "n2d-highcpu-2": 0.06386, "n2d-highcpu-4": 0.12773, "n2d-highcpu-8": 0.25546,
    "n2d-highcpu-16": 0.51091, "n2d-highcpu-32": 1.02183, "n2d-highcpu-48": 1.53274,
    "n2d-highcpu-64": 2.04366, "n2d-highcpu-96": 3.06548,
    # C2 — compute-optimised
    "c2-standard-4": 0.2088, "c2-standard-8": 0.4176, "c2-standard-16": 0.8352,
    "c2-standard-30": 1.5660, "c2-standard-60": 3.1320,
    # C2D — AMD compute-optimised
    "c2d-standard-2": 0.0933, "c2d-standard-4": 0.1866, "c2d-standard-8": 0.3733,
    "c2d-standard-16": 0.7466, "c2d-standard-32": 1.4931, "c2d-standard-56": 2.6129,
    "c2d-standard-112": 5.2258,
    # M1 — memory-optimised
    "m1-megamem-96": 10.6740, "m1-ultramem-40": 6.3039, "m1-ultramem-80": 12.6078,
    "m1-ultramem-160": 25.2156,
    # M2 — memory-optimised 2nd gen
    "m2-ultramem-208": 42.186, "m2-ultramem-416": 84.371,
    "m2-megamem-416": 63.174,
}
# DB logging (non-blocking)
try:
    from db_sql import insert_portal_request_all, log_vm_action
    DB_AVAILABLE = True
except Exception as e:
    DB_AVAILABLE = False
    insert_portal_request_all = None
    log_vm_action = None
    logger.warning("DB logging disabled (db_sql import failed): %s", e)

# Import Cherwell integration
try:
    from cherwell_integration import create_post_deployment_tasks
    CHERWELL_INTEGRATION_AVAILABLE = True
except ImportError as e:
    logger.warning("Cherwell integration not available - cherwell_integration import failed: %s", e)
    CHERWELL_INTEGRATION_AVAILABLE = False
    create_post_deployment_tasks = None

# Import GCP WIF module if available
try:
    from gcp_wif import get_gcp_token_from_azure_session, GCP_PROJECT_NUMBER, GCP_WIF_POOL_ID, GCP_WIF_PROVIDER_ID
    GCP_WIF_AVAILABLE = True
except ImportError:
    logger.warning("GCP WIF module not available - falling back to Google OAuth only")
    GCP_WIF_AVAILABLE = False
    get_gcp_token_from_azure_session = None
    GCP_PROJECT_NUMBER = None
    GCP_WIF_POOL_ID = None
    GCP_WIF_PROVIDER_ID = None


def _gcp_audit(
    request: Request,
    action_type: str,
    resource_name: str = None,
    resource_id: str = None,
    project: str = None,
    zone: str = None,
    detail: str = None,
    status: str = "success",
    error_message: str = None,
) -> None:
    """Fire-and-forget wrapper that writes one GCP audit row to portal.vm_action_audit."""
    if not DB_AVAILABLE or not log_vm_action:
        return
    # Try to get the user email from the GCP session or the linked Azure AD session.
    user_email = None
    try:
        user_email = (
            request.session.get("gcp_user_email")
            or (request.session.get("user") or {}).get("email")
        )
    except Exception:
        pass
    try:
        log_vm_action(
            action_type=action_type,
            cloud_provider="gcp",
            resource_name=resource_name,
            resource_id=resource_id,
            account_or_subscription=project,
            region_or_zone=zone,
            detail=detail,
            performed_by_email=user_email,
            performed_by_oid=None,
            status=status,
            error_message=error_message,
        )
    except Exception as exc:
        logger.warning("_gcp_audit: unexpected error writing audit row: %s", exc)

# OAuth 2.0 configuration - fallback to environment variables if not provided by user
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/gcp/oauth2callback")
SCOPES = [
    'https://www.googleapis.com/auth/cloud-platform',
    'https://www.googleapis.com/auth/compute',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TERRAFORM_BIN = os.getenv("TERRAFORM_BIN", "/usr/bin/terraform")

# Shared utility function for Terraform state cleanup
def cleanup_terraform_state(module_path: str):
    """Clean up Terraform state files after successful deployment."""
    try:
        state_files = [
            os.path.join(module_path, "terraform.tfstate"),
            os.path.join(module_path, "terraform.tfstate.backup")
        ]
        for state_file in state_files:
            if os.path.exists(state_file):
                os.remove(state_file)
                logger.info(f"Cleaned up Terraform state file: {state_file}")
    except Exception as cleanup_err:
        logger.warning(f"Failed to clean up Terraform state files (non-critical): {cleanup_err}")


# Error message truncation limits
ERROR_MESSAGE_MAX_LENGTH = 1000
ERROR_MESSAGE_PREFIX_LENGTH = 500
ERROR_MESSAGE_SUFFIX_LENGTH = 500

# GCP Custom Images - dynamically fetched from project
GCP_CUSTOM_IMAGE_PROJECT = os.getenv("GCP_CUSTOM_IMAGE_PROJECT")

if not GCP_CUSTOM_IMAGE_PROJECT:
    logger.warning("GCP_CUSTOM_IMAGE_PROJECT environment variable not set. GCP custom images will not be available.")
elif GCP_CUSTOM_IMAGE_PROJECT == "YOUR_GCP_PROJECT_ID":
    logger.warning("GCP_CUSTOM_IMAGE_PROJECT is still set to placeholder value. Please set it to your actual GCP project ID.")

router = APIRouter()

oauth_sessions: Dict[str, Dict[str, Any]] = {}
azure_ad_to_gcp_link: Dict[str, Dict[str, Any]] = {}

def sanitize_gcp_label(text: str) -> str:
    """Sanitize text to be GCP label-compliant."""
    if not text:
        return ""
    sanitized = text.lower().replace(' ', '-')
    sanitized = re.sub(r'[^a-z0-9_-]', '', sanitized)
    if sanitized and not sanitized[0].isalpha():
        sanitized = 'tag-' + sanitized
    sanitized = sanitized[:63]
    sanitized = sanitized.rstrip('-_')
    return sanitized if sanitized else "tag"


def parse_gcp_tags_from_payload(payload: Dict[str, Any]) -> Dict[str, str]:
    """Parse tags from JSON payload and convert to GCP-compliant labels."""
    labels: Dict[str, str] = {}
    tags_data = payload.get('tags')
    if not tags_data:
        return labels
    if isinstance(tags_data, str):
        try:
            tags_data = json.loads(tags_data)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse tags JSON: {tags_data}")
            return labels
    if isinstance(tags_data, dict):
        if 'AccountNumber' in tags_data:
            labels['accountnumber'] = sanitize_gcp_label(str(tags_data['AccountNumber']))
        if 'Approvers' in tags_data:
            labels['approvers'] = sanitize_gcp_label(str(tags_data['Approvers']))
        if 'PS' in tags_data:
            labels['ps'] = sanitize_gcp_label(str(tags_data['PS']))
    logger.info(f"Parsed GCP labels from tags: {labels}")
    return labels


def get_account_number_from_gcp_labels(labels: Optional[Dict[str, Any]]) -> str:
    """Return the account number from GCP project/resource labels when present."""
    if not isinstance(labels, dict):
        return ""
    normalized = {str(k).strip().lower(): str(v).strip() for k, v in labels.items() if v is not None}
    return (
        normalized.get("accountnumber")
        or normalized.get("account_number")
        or normalized.get("account-number")
        or ""
    )


class OAuthCredentials(BaseModel):
    client_id: str
    client_secret: str


class FirewallRuleRequest(BaseModel):
    project: str
    name: str
    description: Optional[str] = ""
    direction: str = "INGRESS"
    action: str = "allow"
    priority: int = 1000
    protocol: str
    ports: Optional[str] = None
    source_ranges: List[str] = ["0.0.0.0/0"]
    target_tags: List[str] = []
    network: str = "default"


class DeployVMRequest(BaseModel):
    project: str
    zone: str
    vm_name: str
    machine_type: str
    image_family: str
    image_project: str
    network: str
    subnetwork: str
    disk_size: int = 120
    disk_type: str = "pd-balanced"
    external_ip: bool = True
    firewall_rules: List[str] = []
    labels: Optional[Dict[str, str]] = None
    tags: Optional[str] = None


class DeploySQLRequest(BaseModel):
    project: str
    region: str
    instance_name: str
    database_version: str = "MYSQL_8_0"
    tier: str = "db-f1-micro"
    disk_size_gb: int = 20
    root_password: Optional[str] = None
    labels: Optional[Dict[str, str]] = None


def build_compliant_gcp_vm_name(requested_vm_name: str) -> str:
    base_name = (requested_vm_name or "").strip().lower()
    if not base_name:
        raise HTTPException(status_code=400, detail="vm_name is required")
    if not re.fullmatch(r"[a-z]([a-z0-9-]*[a-z0-9])?", base_name):
        raise HTTPException(
            status_code=400,
            detail="vm_name must start with a lowercase letter and contain only lowercase letters, numbers, and hyphens",
        )
    return f"{base_name}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def get_oauth_config_from_session(request: Request) -> Dict[str, str]:
    client_id = request.session.get("gcp_client_id")
    client_secret = request.session.get("gcp_client_secret")
    if not client_id:
        client_id = GOOGLE_CLIENT_ID
    if not client_secret:
        client_secret = GOOGLE_CLIENT_SECRET
    return {"client_id": client_id, "client_secret": client_secret}


def get_credentials_from_azure_ad_link(request: Request) -> Optional[Credentials]:
    azure_user = request.session.get("user")
    if not azure_user:
        return None
    azure_oid = azure_user.get("oid")
    if not azure_oid or azure_oid not in azure_ad_to_gcp_link:
        return None
    linked_data = azure_ad_to_gcp_link[azure_oid]
    creds_info = linked_data.get("credentials")
    if not creds_info:
        return None
    creds = Credentials(
        token=creds_info.get("token"),
        refresh_token=creds_info.get("refresh_token"),
        token_uri=creds_info.get("token_uri"),
        client_id=creds_info.get("client_id"),
        client_secret=creds_info.get("client_secret"),
        scopes=creds_info.get("scopes")
    )
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(GoogleRequest())
            azure_ad_to_gcp_link[azure_oid]["credentials"] = {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": creds.scopes
            }
            logger.info(f"Refreshed GCP token for Azure AD user: {azure_user.get('email')}")
        except Exception as e:
            logger.error(f"Failed to refresh token for Azure AD user: {e}")
            del azure_ad_to_gcp_link[azure_oid]
            return None
    logger.info(f"Using linked GCP credentials for Azure AD user: {azure_user.get('email')}")
    return creds


def _build_credentials_from_info(creds_info: Dict[str, Any]) -> Optional[Credentials]:
    """Reconstruct a Credentials object from a stored credentials dict."""
    if not creds_info:
        return None
    return Credentials(
        token=creds_info.get("token"),
        refresh_token=creds_info.get("refresh_token"),
        token_uri=creds_info.get("token_uri"),
        client_id=creds_info.get("client_id"),
        client_secret=creds_info.get("client_secret"),
        scopes=creds_info.get("scopes"),
    )


def _refresh_credentials(creds: Credentials) -> bool:
    """Attempt to refresh credentials. Returns True on success, False on failure."""
    if not (creds.expired and creds.refresh_token):
        return True
    try:
        creds.refresh(GoogleRequest())
        return True
    except Exception as e:
        logger.warning(f"Token refresh failed: {e}")
        return False


def _credentials_to_dict(creds: Credentials) -> Dict[str, Any]:
    """Serialise a Credentials object to a JSON-safe dict."""
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else [],
    }


def get_credentials_from_session(request: Request) -> Optional[Credentials]:
    # 1. Azure AD-linked GCP account (highest priority)
    creds = get_credentials_from_azure_ad_link(request)
    if creds:
        return creds

    # 2. In-memory session store (fast path, populated after login)
    session_id = request.session.get("gcp_session_id")
    if session_id and session_id in oauth_sessions:
        creds_info = oauth_sessions[session_id].get("credentials")
        creds = _build_credentials_from_info(creds_info)
        if creds:
            if _refresh_credentials(creds):
                oauth_sessions[session_id]["credentials"] = _credentials_to_dict(creds)
                return creds
            # Refresh failed — fall through to session-cookie fallback below

    # 3. Session-cookie fallback: credentials stored directly in the encrypted cookie.
    #    This survives app restarts and Azure App Service instance recycling, which
    #    would otherwise empty the in-memory oauth_sessions dict and force re-login.
    stored_creds_info = request.session.get("gcp_credentials")
    if stored_creds_info:
        creds = _build_credentials_from_info(stored_creds_info)
        if creds:
            refreshed = _refresh_credentials(creds)
            if not refreshed and creds.expired:
                # Token is expired and we cannot refresh — clear stale session data
                request.session.pop("gcp_credentials", None)
                return None
            # Persist refreshed token back to session cookie and rebuild in-memory cache
            new_creds_dict = _credentials_to_dict(creds)
            request.session["gcp_credentials"] = new_creds_dict
            recovered_id = f"gcp_recovered_{datetime.now(timezone.utc).timestamp()}"
            user_info = request.session.get("gcp_user_info", {})
            oauth_sessions[recovered_id] = {"credentials": new_creds_dict, "user_info": user_info}
            request.session["gcp_session_id"] = recovered_id
            logger.info("GCP session recovered from cookie credentials (app may have restarted)")
            return creds

    return None


def require_gcp_auth(request: Request) -> Credentials:
    creds = get_credentials_from_session(request)
    if creds:
        return creds
    raise HTTPException(
        status_code=401,
        detail={
            "error": "Authentication required",
            "message": "Please log in with Google OAuth to access GCP resources.",
            "suggested_action": "gcp_login_required"
        }
    )


@router.post("/auth/set-credentials")
async def set_oauth_credentials(request: Request, credentials: OAuthCredentials):
    if not credentials.client_id or not credentials.client_secret:
        raise HTTPException(status_code=400, detail="Both client_id and client_secret are required")
    request.session["gcp_client_id"] = credentials.client_id
    request.session["gcp_client_secret"] = credentials.client_secret
    logger.info("OAuth credentials stored in session")
    return {"status": "success", "message": "OAuth credentials stored successfully"}


@router.get("/auth/login")
async def gcp_login(request: Request):
    oauth_config = get_oauth_config_from_session(request)
    if not oauth_config["client_id"] or not oauth_config["client_secret"]:
        raise HTTPException(status_code=500, detail="Google OAuth not configured. Please provide OAuth Client ID and Secret.")

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": oauth_config["client_id"],
                "client_secret": oauth_config["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )

    request.session["gcp_oauth_state"] = state

    # ✅ IMPORTANT: persist PKCE code_verifier for the callback
    request.session["gcp_code_verifier"] = getattr(flow, "code_verifier", None)

    return RedirectResponse(url=authorization_url)


@router.get("/oauth2callback")
async def oauth2callback(request: Request, code: str = Query(...), state: str = Query(...)):
    stored_state = request.session.get("gcp_oauth_state")
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # ✅ IMPORTANT: read the PKCE code_verifier saved during /auth/login
    code_verifier = request.session.get("gcp_code_verifier")
    if not code_verifier:
        raise HTTPException(
            status_code=400,
            detail="Missing PKCE code verifier in session. Session cookie may not be preserved or app restarted."
        )

    oauth_config = get_oauth_config_from_session(request)
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": oauth_config["client_id"],
                "client_secret": oauth_config["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        state=state
    )

    # ✅ CRITICAL: restore verifier onto the Flow instance
    flow.code_verifier = code_verifier

    try:
        flow.fetch_token(code=code)

        # one-time value; clear it after success
        request.session.pop("gcp_code_verifier", None)

        credentials = flow.credentials
        try:
            user_info_service = build('oauth2', 'v2', credentials=credentials, cache_discovery=False)
            user_info = user_info_service.userinfo().get().execute()
        except (HttpError, IOError, ValueError):
            # Fallback: fetch user info via authorised HTTP session (avoids discovery-cache issues)
            from google.auth.transport.requests import AuthorizedSession
            authed_session = AuthorizedSession(credentials)
            resp = authed_session.get("https://www.googleapis.com/oauth2/v2/userinfo")
            resp.raise_for_status()
            user_info = resp.json()

        session_id = f"gcp_{user_info.get('id')}_{datetime.now(timezone.utc).timestamp()}"
        credentials_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": list(credentials.scopes) if credentials.scopes else [],
        }

        oauth_sessions[session_id] = {"credentials": credentials_data, "user_info": user_info}
        request.session["gcp_session_id"] = session_id
        request.session["gcp_user_email"] = user_info.get("email")
        # Persist credentials in the session cookie so they survive app restarts /
        # Azure App Service instance recycling without forcing re-login.
        request.session["gcp_credentials"] = credentials_data
        request.session["gcp_user_info"] = {
            "id": user_info.get("id", ""),
            "email": user_info.get("email", ""),
            "name": user_info.get("name", ""),
        }

        azure_user = request.session.get("user")
        if azure_user and azure_user.get("oid"):
            azure_oid = azure_user.get("oid")
            azure_ad_to_gcp_link[azure_oid] = {
                "credentials": credentials_data,
                "gcp_user_info": user_info,
                "azure_user_email": azure_user.get("email"),
                "linked_at": datetime.now(timezone.utc).isoformat()
            }
            logger.info(f"Linked GCP account {user_info.get('email')} to Azure AD user {azure_user.get('email')}")

        return RedirectResponse(url="/")
    except Exception as e:
        logger.exception("OAuth callback failed")
        raise HTTPException(status_code=500, detail=f"OAuth failed: {str(e)}")


def get_gcp_access_token(request: Request) -> Optional[str]:
    creds = get_credentials_from_session(request)
    if creds and creds.token:
        return creds.token
    return None


@router.get("/auth/status")
async def auth_status(request: Request):
    creds = get_credentials_from_session(request)
    if creds:
        user_email = request.session.get("gcp_user_email")
        azure_user = request.session.get("user")
        if azure_user and azure_user.get("oid") in azure_ad_to_gcp_link:
            linked_data = azure_ad_to_gcp_link[azure_user.get("oid")]
            return {
                "authenticated": True,
                "method": "google_oauth_linked",
                "user_email": user_email,
                "gcp_email": linked_data.get("gcp_user_info", {}).get("email"),
                "azure_email": azure_user.get("email"),
                "linked_at": linked_data.get("linked_at"),
                "message": f"Authenticated via linked Google account. Azure AD user {azure_user.get('email')} → GCP account {user_email}"
            }
        return {
            "authenticated": True,
            "method": "google_oauth",
            "user_email": user_email,
            "message": "Authenticated via Google OAuth"
        }

    azure_user = request.session.get("user")
    if azure_user:
        azure_oid = azure_user.get("oid")
        if azure_oid and azure_oid in azure_ad_to_gcp_link:
            linked_data = azure_ad_to_gcp_link[azure_oid]
            return {
                "authenticated": True,
                "method": "google_oauth_linked",
                "user_email": azure_user.get("email"),
                "gcp_email": linked_data.get("gcp_user_info", {}).get("email"),
                "linked_at": linked_data.get("linked_at"),
                "message": f"GCP account linked. You can access GCP resources seamlessly."
            }
        return {
            "authenticated": False,
            "method": "azure_ad_needs_gcp_link",
            "user_email": azure_user.get("email"),
            "message": "You are logged in with Azure AD. To access GCP resources, please connect your Google account (one-time setup).",
            "action_required": "link_gcp_account"
        }

    return {"authenticated": False, "method": None, "message": "Not authenticated. Please log in with Google OAuth to access GCP resources."}


@router.post("/auth/logout")
async def gcp_logout(request: Request):
    session_id = request.session.get("gcp_session_id")
    if session_id and session_id in oauth_sessions:
        del oauth_sessions[session_id]
    azure_user = request.session.get("user")
    if azure_user and azure_user.get("oid") in azure_ad_to_gcp_link:
        del azure_ad_to_gcp_link[azure_user.get("oid")]
        logger.info(f"Unlinked GCP account from Azure AD user {azure_user.get('email')}")
    request.session.pop("gcp_session_id", None)
    request.session.pop("gcp_user_email", None)
    request.session.pop("gcp_oauth_state", None)
    request.session.pop("gcp_code_verifier", None)
    request.session.pop("gcp_credentials", None)
    request.session.pop("gcp_user_info", None)
    return {"status": "logged out", "message": "GCP account disconnected successfully"}


@router.get("/projects")
async def list_projects(request: Request, creds: Credentials = Depends(require_gcp_auth)):
    try:
        service = build('cloudresourcemanager', 'v1', credentials=creds)
        projects = []
        page_token = None
        while True:
            response = service.projects().list(pageToken=page_token, filter='lifecycleState:ACTIVE').execute()
            projects.extend(response.get('projects', []))
            page_token = response.get('nextPageToken')
            if not page_token:
                break
        return [
            {
                "id": p.get("projectId"),
                "name": p.get("name"),
                "number": p.get("projectNumber"),
                "labels": p.get("labels", {}) or {},
                "account_number": get_account_number_from_gcp_labels(p.get("labels", {})),
            }
            for p in projects
        ]
    except HttpError as e:
        logger.exception("Failed to list projects")
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")


# ... (all other endpoints unchanged) ...
@router.get("/zones")
async def list_zones(
    request: Request,
    project: str = Query(...),
    region: Optional[str] = Query(None),
    creds: Credentials = Depends(require_gcp_auth)
):
    """List all zones in a GCP project, optionally filtered by region."""
    try:
        service = build('compute', 'v1', credentials=creds)
        result = service.zones().list(project=project).execute()
        
        zones = result.get('items', [])
        filtered_zones = []
        
        for z in zones:
            if z.get("status") != "UP":
                continue
            
            # Extract region name from self-link or region field
            region_value = z.get("region", "")
            if region_value:
                # Handle self-link format: https://www.googleapis.com/compute/v1/projects/{project}/regions/{region}
                region_name = region_value.split('/')[-1] if '/' in region_value else region_value
            else:
                region_name = ""
            
            filtered_zones.append({
                "name": z.get("name"),
                "description": z.get("description"),
                "status": z.get("status"),
                "region": region_name
            })
        
        # If region is specified, filter zones to only those in that region
        if region:
            filtered_zones = [z for z in filtered_zones if z["region"] == region]
        
        return filtered_zones
        
    except HttpError as e:
        logger.exception("Failed to list zones")
        raise HTTPException(status_code=500, detail=f"Failed to list zones: {str(e)}")


@router.get("/networks")
async def list_networks(
    request: Request,
    project: str = Query(...),
    creds: Credentials = Depends(require_gcp_auth)
):
    """List all VPC networks in a GCP project."""
    try:
        service = build('compute', 'v1', credentials=creds)
        result = service.networks().list(project=project).execute()
        
        networks = result.get('items', [])
        return [
            {
                "id": n.get("id"),
                "name": n.get("name"),
                "selfLink": n.get("selfLink"),
                "autoCreateSubnetworks": n.get("autoCreateSubnetworks")
            }
            for n in networks
        ]
        
    except HttpError as e:
        logger.exception("Failed to list networks")
        raise HTTPException(status_code=500, detail=f"Failed to list networks: {str(e)}")


@router.get("/subnetworks")
async def list_subnetworks(
    request: Request,
    project: str = Query(...),
    region: Optional[str] = Query(None),
    network: Optional[str] = Query(None),
    creds: Credentials = Depends(require_gcp_auth)
):
    """List all subnetworks in a specific region or across all regions for a network.
    
    If region is provided, lists subnetworks in that region.
    If network is provided without region, lists all subnetworks for that network across all regions using aggregatedList for better performance.
    """
    try:
        service = build('compute', 'v1', credentials=creds)
        
        # If network is specified but region is not, fetch from all regions using aggregatedList (much faster)
        if network and not region:
            # Extract just the network name if it's a full URL
            network_name = network.split("/")[-1] if "/" in network else network
            
            all_subnetworks = []
            
            # Use aggregatedList with filter to fetch only subnets for this network
            # This makes GCP do the filtering server-side, which is much faster
            filter_param = f"network eq .*/{network_name}$"
            request_obj = service.subnetworks().aggregatedList(
                project=project,
                filter=filter_param
            )
            
            while request_obj is not None:
                result = request_obj.execute()
                
                # Process items from all regions
                for region_key, region_data in result.get('items', {}).items():
                    # region_key format: "regions/us-central1"
                    subnetworks = region_data.get('subnetworks', [])
                    
                    for s in subnetworks:
                        # Extract region from selfLink or region_key
                        subnet_region = s.get("region", "").split("/")[-1] if s.get("region") else region_key.split("/")[-1]
                        all_subnetworks.append({
                            "id": s.get("id"),
                            "name": s.get("name"),
                            "selfLink": s.get("selfLink"),
                            "ipCidrRange": s.get("ipCidrRange"),
                            "network": s.get("network"),
                            "region": subnet_region
                        })
                
                # Handle pagination if there are more results
                request_obj = service.subnetworks().aggregatedList_next(request_obj, result)
            
            return all_subnetworks
        
        # Original behavior: fetch subnetworks from a specific region
        elif region:
            result = service.subnetworks().list(
                project=project,
                region=region
            ).execute()
            
            subnetworks = result.get('items', [])
            subnet_list = []
            for s in subnetworks:
                subnet_region = s.get("region", "").split("/")[-1] if s.get("region") else region
                subnet_data = {
                    "id": s.get("id"),
                    "name": s.get("name"),
                    "selfLink": s.get("selfLink"),
                    "ipCidrRange": s.get("ipCidrRange"),
                    "network": s.get("network"),
                    "region": subnet_region
                }
                subnet_list.append(subnet_data)
            
            return subnet_list
        else:
            raise HTTPException(status_code=400, detail="Either 'region' or 'network' parameter must be provided")
        
    except HttpError as e:
        logger.exception("Failed to list subnetworks")
        raise HTTPException(status_code=500, detail=f"Failed to list subnetworks: {str(e)}")


@router.get("/firewall-rules")
async def list_firewall_rules(
    request: Request,
    project: str = Query(...),
    creds: Credentials = Depends(require_gcp_auth)
):
    """List all firewall rules in a GCP project."""
    try:
        service = build('compute', 'v1', credentials=creds)
        result = service.firewalls().list(project=project).execute()
        
        firewalls = result.get('items', [])
        return [
            {
                "id": f.get("id"),
                "name": f.get("name"),
                "network": f.get("network"),
                "direction": f.get("direction"),
                "priority": f.get("priority"),
                "targetTags": f.get("targetTags", [])
            }
            for f in firewalls
        ]
        
    except HttpError as e:
        logger.exception("Failed to list firewall rules")
        raise HTTPException(status_code=500, detail=f"Failed to list firewall rules: {str(e)}")


@router.post("/create-firewall-rule")
async def create_firewall_rule(
    request: Request,
    req: FirewallRuleRequest,
    creds: Credentials = Depends(require_gcp_auth)
):
    """Create a new firewall rule in GCP."""
    try:
        service = build('compute', 'v1', credentials=creds)
        
        # Build the firewall rule configuration
        firewall_body = {
            "name": req.name,
            "description": req.description or f"Created via Multi-Cloud Portal",
            "network": f"projects/{req.project}/global/networks/{req.network}",
            "direction": req.direction,
            "priority": req.priority,
            "targetTags": req.target_tags if req.target_tags else [],
            "sourceRanges": req.source_ranges if req.direction == "INGRESS" else [],
        }
        
        # Add allowed or denied based on action
        if req.action == "allow":
            allowed = []
            if req.protocol == "all":
                allowed.append({"IPProtocol": "all"})
            elif req.protocol == "icmp":
                allowed.append({"IPProtocol": "icmp"})
            else:
                protocol_rule = {"IPProtocol": req.protocol}
                if req.ports:
                    protocol_rule["ports"] = [req.ports]
                allowed.append(protocol_rule)
            firewall_body["allowed"] = allowed
        else:
            denied = []
            if req.protocol == "all":
                denied.append({"IPProtocol": "all"})
            elif req.protocol == "icmp":
                denied.append({"IPProtocol": "icmp"})
            else:
                protocol_rule = {"IPProtocol": req.protocol}
                if req.ports:
                    protocol_rule["ports"] = [req.ports]
                denied.append(protocol_rule)
            firewall_body["denied"] = denied
        
        logger.info(f"Creating firewall rule: {req.name} in project {req.project}")
        logger.debug(f"Firewall rule body: {firewall_body}")
        
        # Create the firewall rule
        operation = service.firewalls().insert(
            project=req.project,
            body=firewall_body
        ).execute()
        
        logger.info(f"Firewall rule creation operation: {operation.get('name')}")
        
        return {
            "status": "success",
            "name": req.name,
            "operation": operation.get("name"),
            "message": f"Firewall rule '{req.name}' is being created"
        }
        
    except HttpError as e:
        logger.exception("Failed to create firewall rule")
        error_detail = str(e)
        if hasattr(e, 'content'):
            try:
                error_detail = json.loads(e.content).get('error', {}).get('message', str(e))
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Failed to create firewall rule: {error_detail}")
    except Exception as e:
        logger.exception("Unexpected error creating firewall rule")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.get("/machine-types")
async def list_machine_types(
    request: Request,
    project: str = Query(...),
    zone: str = Query(...),
    creds: Credentials = Depends(require_gcp_auth)
):
    """List all machine types available in a zone."""
    try:
        service = build('compute', 'v1', credentials=creds)
        result = service.machineTypes().list(
            project=project,
            zone=zone
        ).execute()
        
        machine_types = result.get('items', [])
        return [
            {
                "name": mt.get("name"),
                "description": mt.get("description"),
                "guestCpus": mt.get("guestCpus"),
                "memoryMb": mt.get("memoryMb"),
                "price_per_hour": _GCP_MACHINE_PRICING.get(mt.get("name") or ""),
            }
            for mt in machine_types
        ]
        
    except HttpError as e:
        logger.exception("Failed to list machine types")
        raise HTTPException(status_code=500, detail=f"Failed to list machine types: {str(e)}")


@router.get("/images")
async def list_images(
    request: Request,
    project: Optional[str] = Query(None),
    creds: Credentials = Depends(require_gcp_auth)
):
    """
    List custom images from the GCP project.
    Only returns custom images (non-deprecated) from the specified project.
    Does NOT return public images like Ubuntu, Debian, CentOS, etc.
    
    Args:
        project: GCP project ID. If not provided, uses GCP_CUSTOM_IMAGE_PROJECT env var.
        creds: GCP credentials (automatically injected)
    
    Returns:
        List of custom images with family, project, label, and creation timestamp
    """
    try:
        # Use provided project or fall back to environment variable
        target_project = project or GCP_CUSTOM_IMAGE_PROJECT
        
        if not target_project:
            raise HTTPException(
                status_code=400,
                detail="GCP project not specified. Set GCP_CUSTOM_IMAGE_PROJECT environment variable or provide project parameter."
            )
        
        # Build the Compute Engine service
        service = build('compute', 'v1', credentials=creds)
        
        # List all images in the project
        logger.info(f"Fetching custom images from project: {target_project}")
        result = service.images().list(project=target_project).execute()
        
        images_data = result.get('items', [])
        
        if not images_data:
            logger.warning(f"No custom images found in project: {target_project}")
            return []
        
        # Filter and format custom images
        # Exclude deprecated images and organize by family
        custom_images = []
        seen_families = set()
        
        for img in images_data:
            # Skip deprecated images
            if img.get('deprecated'):
                continue
            
            # Get image family (or use image name if no family)
            family = img.get('family', img.get('name'))
            
            # Skip if we've already seen this family (keep the latest)
            if family in seen_families:
                continue
            
            seen_families.add(family)
            
            # Extract image details
            image_name = img.get('name', '')
            description = img.get('description', '')
            creation_timestamp = img.get('creationTimestamp', '')
            
            # Create a readable label
            # Use description if available, otherwise use the image name
            label = description if description else image_name
            
            custom_images.append({
                "family": family,
                "project": target_project,
                "label": label,
                "name": image_name,
                "created": creation_timestamp
            })
        
        # Sort by creation time (newest first)
        custom_images.sort(key=lambda x: x.get('created', ''), reverse=True)
        
        logger.info(f"Found {len(custom_images)} custom images in project {target_project}")
        return custom_images
        
    except HttpError as e:
        error_detail = json.loads(e.content.decode('utf-8')) if e.content else {}
        logger.error(f"Failed to list images: {error_detail}")
        
        # Check if it's a permission error
        if e.resp.status == 403:
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied. Ensure the authenticated user has 'Compute Image User' role in project {target_project}."
            )
        elif e.resp.status == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Project '{target_project}' not found or you don't have access to it."
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to list images: {error_detail.get('error', {}).get('message', str(e))}"
            )
    except Exception as e:
        logger.error(f"Unexpected error listing images: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list images: {str(e)}"
        )


@router.get("/regions")
async def list_regions(
    request: Request,
    project: str = Query(...),
    creds: Credentials = Depends(require_gcp_auth)
):
    """List all regions in a GCP project."""
    try:
        service = build('compute', 'v1', credentials=creds)
        result = service.regions().list(project=project).execute()
        
        regions = result.get('items', [])
        return [
            {
                "name": r.get("name"),
                "description": r.get("description"),
                "status": r.get("status")
            }
            for r in regions
            if r.get("status") == "UP"
        ]
        
    except HttpError as e:
        logger.exception("Failed to list regions")
        raise HTTPException(status_code=500, detail=f"Failed to list regions: {str(e)}")

def update_gcp_vms_store(new_vm_config: Dict[str, Any], unique_vm_name: str) -> Dict[str, Any]:
    vms_path = os.path.join(BASE_DIR, "gcp_vms.json")
    vms = {}
    if os.path.isfile(vms_path):
        try:
            with open(vms_path, "r") as f:
                vms = json.load(f)
        except Exception:
            vms = {}
    vms[unique_vm_name] = new_vm_config
    with open(vms_path, "w") as f:
        json.dump(vms, f, indent=2)
    return vms


def run_terraform_gcp(vms: Dict[str, Any], project: str, region: str, creds: Credentials = None, access_token: str = None) -> Dict[str, Any]:
    module_path = os.path.join(BASE_DIR, "../terraform/gcp")
    if not os.path.isdir(module_path):
        raise HTTPException(status_code=400, detail="GCP Terraform module not found")

    token = access_token
    if not token and creds:
        token = creds.token
    if not token:
        raise HTTPException(status_code=401, detail="GCP access token not available")

    env = os.environ.copy()
    env["GOOGLE_OAUTH_ACCESS_TOKEN"] = token
    env["TF_VAR_gcp_project"] = project
    env["TF_VAR_gcp_region"] = region
    env["TF_VAR_vms"] = json.dumps(vms)

    try:
        logger.info("Running terraform init in %s", module_path)
        subprocess.run([TERRAFORM_BIN, "init"], cwd=module_path, check=True, env=env, capture_output=True, text=True)
        logger.info("Running terraform apply (auto-approve)")
        result = subprocess.run([TERRAFORM_BIN, "apply", "-auto-approve"], cwd=module_path, check=True, env=env, capture_output=True, text=True)
        logger.info("Terraform apply completed successfully")
        logger.debug("Terraform output: %s", result.stdout)
        cleanup_terraform_state(module_path)
    except subprocess.CalledProcessError as e:
        error_msg = (e.stderr or e.stdout or str(e)).strip()
        logger.exception("Terraform execution failed: %s", error_msg)
        sanitized_error = sanitize_terraform_error(error_msg)
        raise HTTPException(status_code=500, detail=f"Terraform deployment failed. Please check your configuration. Error: {sanitized_error}")
    except Exception as e:
        logger.exception("Unexpected error running terraform: %s", e)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during deployment. Please contact support.")

    return {"status": "success"}


def sanitize_terraform_error(error_msg: str) -> str:
    import re
    sanitized = re.sub(r'(token|password|secret|key)["\s:=]+[^\s"]+', r'\1=***REDACTED***', error_msg, flags=re.IGNORECASE)
    sanitized = re.sub(r'/home/[^\s]+', '/***PATH_REDACTED***', sanitized)
    sanitized = re.sub(r'[A-Z]:\\[^\s]+', '***PATH_REDACTED***', sanitized)
    if len(sanitized) > ERROR_MESSAGE_MAX_LENGTH:
        sanitized = (sanitized[:ERROR_MESSAGE_PREFIX_LENGTH] + "\n... [truncated] ...\n" + sanitized[-ERROR_MESSAGE_SUFFIX_LENGTH:])
    return sanitized
def _gcp_get_instance_creation_timestamp(creds: Credentials, project: str, zone: str, instance_name: str) -> Optional[str]:
    """
    Returns the instance.creationTimestamp (string) from GCP, or None.
    creationTimestamp is typically ISO-ish like '2025-09-10T11:32:22.123-07:00'
    """
    if not creds or not project or not zone or not instance_name:
        return None
    try:
        service = build('compute', 'v1', credentials=creds)
        inst = service.instances().get(project=project, zone=zone, instance=instance_name).execute()
        return inst.get("creationTimestamp")
    except Exception as e:
        logger.warning("Failed to fetch GCP instance creationTimestamp for %s: %s", instance_name, e)
        return None


@router.post("/deploy-vm")
async def deploy_vm(request: Request, req: DeployVMRequest, creds: Credentials = Depends(require_gcp_auth)):
    """Deploy a VM in GCP with custom tags (AccountNumber, Approvers, PS)."""
    try:
        user = request.session.get("user", {})
        user_email = user.get("email") if user else None

        if not user_email:
            user_email = request.session.get("gcp_user_email")
            logger.info(f"Using GCP OAuth user email for Cherwell: {user_email}")
        else:
            logger.info(f"Using Azure AD user email for Cherwell: {user_email}")

        unique_vm_name = build_compliant_gcp_vm_name(req.vm_name)
        zone_region = '-'.join(req.zone.split('-')[:-1])
                # ---- DB logging (insert request row; non-blocking) ----
        db_request_id = None
        try:
            if DB_AVAILABLE and insert_portal_request_all:
                # Tags from portal: prefer req.tags (JSON string) else infer from req.labels
                tag_account_number = None
                tag_approvers = None
                tag_ps = None

                if req.tags:
                    try:
                        tags_obj = json.loads(req.tags) if isinstance(req.tags, str) else req.tags
                        if isinstance(tags_obj, dict):
                            tag_account_number = tags_obj.get("AccountNumber")
                            tag_approvers = tags_obj.get("Approvers")
                            tag_ps = tags_obj.get("PS")
                    except Exception:
                        pass

                # If UI sent labels instead of tags, try to map common ones
                if isinstance(req.labels, dict):
                    tag_account_number = tag_account_number or req.labels.get("accountnumber") or req.labels.get("AccountNumber")
                    tag_approvers = tag_approvers or req.labels.get("approvers") or req.labels.get("Approvers")
                    tag_ps = tag_ps or req.labels.get("ps") or req.labels.get("PS")

                payload_snapshot = {
                    "project": req.project,
                    "zone": req.zone,
                    "vm_name": req.vm_name,
                    "unique_vm_name": unique_vm_name,
                    "machine_type": req.machine_type,
                    "image_project": req.image_project,
                    "image_family": req.image_family,
                    "network": req.network,
                    "subnetwork": req.subnetwork,
                    "disk_size": req.disk_size,
                    "disk_type": req.disk_type,
                    "external_ip": req.external_ip,
                    "firewall_rules": req.firewall_rules,
                    "labels": req.labels,
                    "tags": req.tags,
                }

                db_request_id = insert_portal_request_all({
                    "cloud_provider": "gcp",
                    "user_email": user_email,
                    "user_oid": (request.session.get("user") or {}).get("oid"),
                    "vm_name_requested": req.vm_name,
                    "vm_name_final": unique_vm_name,

                    "tag_account_number": tag_account_number,
                    "tag_approvers": tag_approvers,
                    "tag_ps": tag_ps,

                    "status": "received",
                    "payload_json": payload_snapshot,

                    # GCP-specific columns
                    "gcp_project_id": req.project,
                    "gcp_region": zone_region,
                    "gcp_network": req.network,
                    "gcp_subnetwork": req.subnetwork,
                    "gcp_machine_type": req.machine_type,
                    "gcp_image_project": req.image_project,
                    "gcp_image_family": req.image_family,
                    "gcp_disk_type": req.disk_type,
                    "gcp_disk_size_gb": req.disk_size,
                    "gcp_firewall_rules_json": req.firewall_rules,
                })

                logger.info("DB logged GCP request_id=%s for vm=%s", db_request_id, unique_vm_name)
        except Exception as db_err:
            logger.warning("DB logging failed (non-blocking): %s", db_err)

        # Subnetwork normalization (unchanged)
        subnetwork_link = req.subnetwork
        if subnetwork_link.startswith('https://'):
            if 'projects/' in subnetwork_link:
                subnetwork_link = subnetwork_link.split('projects/', 1)[1]
                subnetwork_link = 'projects/' + subnetwork_link
        elif not subnetwork_link.startswith('projects/'):
            subnetwork_link = f"projects/{req.project}/regions/{zone_region}/subnetworks/{req.subnetwork}"

        # VM config
        vm_config: Dict[str, Any] = {
            "vm_name": unique_vm_name,
            "machine_type": req.machine_type,
            "zone": req.zone,
            "project": req.project,
            "image": f"projects/{req.image_project}/global/images/family/{req.image_family}",
            "subnetwork": subnetwork_link,
            "disk_size": req.disk_size,
            "disk_type": req.disk_type,
            "external_ip": req.external_ip,
            "firewall_rules": req.firewall_rules
        }

        # Labels
        gcp_labels: Dict[str, str] = {}
        if req.tags:
            parsed_labels = parse_gcp_tags_from_payload({"tags": req.tags})
            if parsed_labels:
                gcp_labels.update(parsed_labels)
        if req.labels:
            for key, value in req.labels.items():
                sanitized_key = sanitize_gcp_label(str(key))
                sanitized_value = sanitize_gcp_label(str(value))
                if sanitized_key and sanitized_value:
                    gcp_labels[sanitized_key] = sanitized_value
        if gcp_labels:
            vm_config["labels"] = gcp_labels

        # Store & terraform
        vms = update_gcp_vms_store(vm_config, unique_vm_name)
        access_token = get_gcp_access_token(request)
        if not access_token:
            raise HTTPException(status_code=401, detail="GCP access token not available")

        result = run_terraform_gcp(vms, req.project, zone_region, access_token=access_token)
        # ✅ Provisioning Start Time (GCP = instance.creationTimestamp)
        gcp_creation_ts = _gcp_get_instance_creation_timestamp(creds, req.project, req.zone, unique_vm_name)

        response = {
            "status": "success",
            "cloud": "gcp",
            "vm_name": unique_vm_name,
            "project": req.project,
            "zone": req.zone,
            "machine_type": req.machine_type,
            **result
        }

        # ✅ CHERWELL: ensure Subscription/Account passes correctly (GCP project)
        if CHERWELL_INTEGRATION_AVAILABLE and create_post_deployment_tasks:
            try:
                vm_details = {
                    "vm_name": unique_vm_name,
                    "cloud": "gcp",
                    "project": req.project,
                    "account_name_display": req.project,  # ✅ Fix for emails + ticket description
                    "zone": req.zone,
                    "region": zone_region,
                    "machine_type": req.machine_type,
                    "disk_size": req.disk_size,
                    "disk_type": req.disk_type,
                    "provisioning_start_time": gcp_creation_ts,
                }
                if gcp_labels:
                    vm_details["labels"] = gcp_labels

                cherwell_result = create_post_deployment_tasks(
                    unique_vm_name,
                    "gcp",
                    vm_details,
                    user_email=user_email
                )
                response["cherwell"] = cherwell_result
            except Exception as cherwell_err:
                logger.exception("Error creating Cherwell tasks for GCP VM (non-blocking): %s", cherwell_err)
                response["cherwell"] = {"error": str(cherwell_err)}

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("VM deployment failed")
        raise HTTPException(status_code=500, detail=f"VM deployment failed: {str(e)}")


@router.get("/sql/instances")
async def list_gcp_sql_instances(
    project: str = Query(...),
    creds: Credentials = Depends(require_gcp_auth)
):
    """List Cloud SQL instances for a project."""
    try:
        service = build("sqladmin", "v1beta4", credentials=creds, cache_discovery=False)
        resp = service.instances().list(project=project).execute()
        items = resp.get("items", []) or []
        instances = []
        for inst in items:
            settings = inst.get("settings", {}) or {}
            instances.append({
                "name": inst.get("name", ""),
                "state": inst.get("state", "unknown"),
                "database_version": inst.get("databaseVersion", ""),
                "tier": settings.get("tier", ""),
                "region": inst.get("region", ""),
                "project": project,
            })
        return {"instances": instances}
    except HttpError as e:
        logger.exception("list_gcp_sql_instances failed")
        raise HTTPException(status_code=500, detail=f"GCP SQL list failed: {str(e)}")


@router.post("/deploy-sql")
async def deploy_gcp_sql_instance(
    request: Request,
    req: DeploySQLRequest,
    creds: Credentials = Depends(require_gcp_auth),
):
    """Deploy a Cloud SQL instance in GCP."""
    if not re.match(r"^[a-z][a-z0-9-]{0,97}$", req.instance_name or ""):
        raise HTTPException(status_code=400, detail="instance_name must be 1-98 characters long, start with a lowercase letter, and contain only lowercase letters, numbers, or hyphens")
    if req.disk_size_gb < 10:
        raise HTTPException(status_code=400, detail="disk_size_gb must be at least 10 GB")
    try:
        service = build("sqladmin", "v1beta4", credentials=creds, cache_discovery=False)
        body: Dict[str, Any] = {
            "name": req.instance_name,
            "region": req.region,
            "databaseVersion": req.database_version,
            "settings": {
                "tier": req.tier,
                "dataDiskSizeGb": req.disk_size_gb,
            },
            "deletionProtectionEnabled": False,
        }
        if req.root_password:
            body["rootPassword"] = req.root_password
        if isinstance(req.labels, dict) and req.labels:
            user_labels: Dict[str, str] = {}
            for k, v in req.labels.items():
                key = sanitize_gcp_label(str(k))
                val = sanitize_gcp_label(str(v))
                if key and val:
                    user_labels[key] = val
            if user_labels:
                body["settings"]["userLabels"] = user_labels

        op = service.instances().insert(project=req.project, body=body).execute()
        _gcp_audit(
            request,
            "deploy_sql",
            resource_name=req.instance_name,
            project=req.project,
            zone=req.region,
        )
        return {
            "status": "started",
            "message": "Cloud SQL deployment initiated.",
            "instance_name": req.instance_name,
            "operation": op.get("name"),
        }
    except HttpError as e:
        logger.exception("deploy_gcp_sql_instance failed")
        _gcp_audit(
            request,
            "deploy_sql",
            resource_name=req.instance_name,
            project=req.project,
            zone=req.region,
            status="failed",
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=f"GCP SQL deployment failed: {str(e)}")


@router.delete("/sql/instance")
async def delete_gcp_sql_instance(
    request: Request,
    project: str = Query(...),
    instance_name: str = Query(...),
    creds: Credentials = Depends(require_gcp_auth),
):
    """Delete a Cloud SQL instance."""
    try:
        service = build("sqladmin", "v1beta4", credentials=creds, cache_discovery=False)
        service.instances().delete(project=project, instance=instance_name).execute()
        _gcp_audit(
            request,
            "delete_sql",
            resource_name=instance_name,
            project=project,
        )
        return {"ok": True, "message": f"Deletion initiated for Cloud SQL instance {instance_name}"}
    except HttpError as e:
        logger.exception("delete_gcp_sql_instance failed")
        _gcp_audit(
            request,
            "delete_sql",
            resource_name=instance_name,
            project=project,
            status="failed",
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=f"GCP SQL delete failed: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# GCP existing instance management
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/instances")
async def list_gcp_instances(
    request: Request,
    project: str = Query(...),
    creds: Credentials = Depends(require_gcp_auth)
):
    """List all GCP Compute instances in a project (aggregated across zones)."""
    try:
        service = build('compute', 'v1', credentials=creds)
        result = service.instances().aggregatedList(project=project).execute()
        items = result.get("items", {})
        instances = []
        for zone_data in items.values():
            for inst in zone_data.get("instances", []):
                zone_url = inst.get("zone", "")
                zone_name = zone_url.split("/")[-1] if "/" in zone_url else zone_url
                region_name = "-".join(zone_name.split("-")[:-1]) if zone_name else ""
                status = inst.get("status", "")
                machine_type_url = inst.get("machineType", "")
                machine_type = machine_type_url.split("/")[-1] if "/" in machine_type_url else machine_type_url
                labels = inst.get("labels", {})
                network_interfaces = inst.get("networkInterfaces", [])
                private_ip = network_interfaces[0].get("networkIP", "") if network_interfaces else ""
                public_ip = ""
                if network_interfaces:
                    access_configs = network_interfaces[0].get("accessConfigs", [])
                    if access_configs:
                        public_ip = access_configs[0].get("natIP", "")
                disks = inst.get("disks", [])
                disk_info = []
                for d in disks:
                    disk_info.append({
                        "name": d.get("source", "").split("/")[-1],
                        "type": d.get("type", ""),
                        "size_gb": d.get("diskSizeGb") or 0,
                        "boot": d.get("boot", False),
                        "mode": d.get("mode", ""),
                        "auto_delete": d.get("autoDelete", True),
                    })
                instances.append({
                    "instance_id": str(inst.get("id", "")),
                    "name": inst.get("name", ""),
                    "state": status.lower(),
                    "machine_type": machine_type,
                    "zone": zone_name,
                    "region": region_name,
                    "private_ip": private_ip,
                    "public_ip": public_ip,
                    "creation_timestamp": inst.get("creationTimestamp", ""),
                    "labels": labels,
                    "disks": disk_info,
                })
        return {"instances": instances}
    except HttpError as e:
        logger.exception("list_gcp_instances failed")
        raise HTTPException(status_code=500, detail=f"GCP Error: {str(e)}")


@router.get("/instance")
async def get_gcp_instance(
    request: Request,
    project: str = Query(...),
    zone: str = Query(...),
    instance_name: str = Query(...),
    creds: Credentials = Depends(require_gcp_auth)
):
    """Get details for a specific GCP Compute instance."""
    try:
        service = build('compute', 'v1', credentials=creds)
        inst = service.instances().get(project=project, zone=zone, instance=instance_name).execute()
        machine_type_url = inst.get("machineType", "")
        machine_type = machine_type_url.split("/")[-1] if "/" in machine_type_url else machine_type_url
        labels = inst.get("labels", {})
        network_interfaces = inst.get("networkInterfaces", [])
        private_ip = network_interfaces[0].get("networkIP", "") if network_interfaces else ""
        public_ip = ""
        if network_interfaces:
            access_configs = network_interfaces[0].get("accessConfigs", [])
            if access_configs:
                public_ip = access_configs[0].get("natIP", "")

        # Full network interfaces info (with NIC type, stack type, alias ranges)
        nic_details = []
        for ni in network_interfaces:
            network_url = ni.get("network", "")
            subnet_url = ni.get("subnetwork", "")
            access_cfgs = ni.get("accessConfigs", [])
            ext_ip = access_cfgs[0].get("natIP", "") if access_cfgs else ""
            tier = access_cfgs[0].get("networkTier", "") if access_cfgs else ""
            alias_ranges = [r.get("ipCidrRange", "") for r in ni.get("aliasIpRanges", []) if r.get("ipCidrRange")]
            nic_details.append({
                "name": ni.get("name", ""),
                "network": network_url.split("/")[-1] if "/" in network_url else network_url,
                "subnetwork": subnet_url.split("/")[-1] if "/" in subnet_url else subnet_url,
                "internal_ip": ni.get("networkIP", ""),
                "external_ip": ext_ip,
                "network_tier": tier,
                "nic_type": ni.get("nicType", "VIRTIO_NET"),
                "stack_type": ni.get("stackType", "IPV4_ONLY"),
                "alias_ip_ranges": alias_ranges,
            })

        disks = inst.get("disks", [])
        disk_info = []
        for d in disks:
            disk_info.append({
                "name": d.get("source", "").split("/")[-1],
                "type": d.get("type", ""),
                "size_gb": d.get("diskSizeGb") or 0,
                "boot": d.get("boot", False),
                "mode": d.get("mode", ""),
                "interface": d.get("interface", ""),
                "auto_delete": d.get("autoDelete", True),
                "device_name": d.get("deviceName", ""),
            })

        # Boot disk source image (via disks.get for the boot disk)
        boot_disk_image = ""
        boot_disk_arch = ""
        for d in disks:
            if d.get("boot", False):
                boot_disk_name = d.get("source", "").split("/")[-1]
                if boot_disk_name:
                    try:
                        disk_resource = service.disks().get(project=project, zone=zone, disk=boot_disk_name).execute()
                        source_img_url = disk_resource.get("sourceImage", "")
                        if source_img_url:
                            boot_disk_image = source_img_url.split("/")[-1]
                        boot_disk_arch = disk_resource.get("architecture", "")
                    except Exception:
                        pass
                break

        # GPUs / Accelerators
        accelerators = []
        for a in inst.get("accelerators", []):
            accel_type_url = a.get("acceleratorType", "")
            accel_type = accel_type_url.split("/")[-1] if "/" in accel_type_url else accel_type_url
            accelerators.append({
                "type": accel_type,
                "count": a.get("acceleratorCount", 0),
            })

        # Display device
        display_device = inst.get("displayDevice", {}).get("enableDisplay", False)

        # Confidential VM
        confidential_vm = inst.get("confidentialInstanceConfig", {}).get("enableConfidentialCompute", False)

        # Reservation affinity
        reservation_cfg = inst.get("reservationAffinity", {})
        reservation_affinity = reservation_cfg.get("consumeReservationType", "ANY_RESERVATION")

        scheduling = inst.get("scheduling", {})
        service_accounts = inst.get("serviceAccounts", [])
        service_account_email = service_accounts[0].get("email", "") if service_accounts else ""
        service_account_scopes = service_accounts[0].get("scopes", []) if service_accounts else []

        # Custom metadata (exclude goog-internal entries); extract SSH keys separately
        metadata_items = {}
        ssh_keys_raw = ""
        block_project_ssh = False
        for item in inst.get("metadata", {}).get("items", []):
            k = item.get("key", "")
            v = item.get("value", "")
            if k == "ssh-keys":
                ssh_keys_raw = v
            elif k == "block-project-ssh-keys":
                block_project_ssh = v.strip().lower() == "true"
            elif not k.startswith("goog-"):
                metadata_items[k] = v

        # Parse SSH key count (each line is one key)
        ssh_key_count = len([ln for ln in ssh_keys_raw.splitlines() if ln.strip()]) if ssh_keys_raw else 0

        # Machine type description (vCPUs, memory)
        machine_type_desc = machine_type
        try:
            mt = service.machineTypes().get(project=project, zone=zone, machineType=machine_type).execute()
            guest_cpus = mt.get("guestCpus", "")
            mem_mb = mt.get("memoryMb", "")
            if guest_cpus and mem_mb:
                mem_gb = round(int(mem_mb) / 1024, 2)
                mem_str = f"{int(mem_gb)} GB" if mem_gb == int(mem_gb) else f"{mem_gb} GB"
                machine_type_desc = f"{machine_type} ({guest_cpus} vCPUs, {mem_str} Memory)"
        except Exception:
            pass

        # Shielded VM config
        shielded_cfg = inst.get("shieldedInstanceConfig", {})
        shielded_vm = {
            "secure_boot": shielded_cfg.get("enableSecureBoot", False),
            "vtpm": shielded_cfg.get("enableVtpm", False),
            "integrity_monitoring": shielded_cfg.get("enableIntegrityMonitoring", False),
        } if shielded_cfg else None

        # Scheduling extended fields
        max_run_duration_secs = 0
        mrd = scheduling.get("maxRunDuration", {})
        if mrd:
            max_run_duration_secs = int(mrd.get("seconds", 0))
        max_run_duration_str = ""
        if max_run_duration_secs > 0:
            h = max_run_duration_secs // 3600
            m = (max_run_duration_secs % 3600) // 60
            s_rem = max_run_duration_secs % 60
            parts = []
            if h > 0:
                parts.append(f"{h}h")
            if m > 0:
                parts.append(f"{m}m")
            if s_rem > 0:
                parts.append(f"{s_rem}s")
            max_run_duration_str = " ".join(parts)

        network_tags = inst.get("tags", {}).get("items", [])

        return {
            "instance_id": str(inst.get("id", "")),
            "name": inst.get("name", ""),
            "description": inst.get("description", ""),
            "state": inst.get("status", "").lower(),
            "machine_type": machine_type_desc,
            "min_cpu_platform": inst.get("minCpuPlatform", ""),
            "cpu_platform": inst.get("cpuPlatform", ""),
            "display_device": display_device,
            "accelerators": accelerators,
            "confidential_vm": confidential_vm,
            "reservation_affinity": reservation_affinity,
            "zone": zone,
            "region": "-".join(zone.split("-")[:-1]),
            "private_ip": private_ip,
            "public_ip": public_ip,
            "can_ip_forward": inst.get("canIpForward", False),
            "deletion_protection": inst.get("deletionProtection", False),
            "creation_timestamp": inst.get("creationTimestamp", ""),
            "last_start_timestamp": inst.get("lastStartTimestamp", ""),
            "labels": labels,
            "tags": network_tags,
            "disks": disk_info,
            "boot_disk_image": boot_disk_image,
            "boot_disk_arch": boot_disk_arch,
            "network_interfaces": nic_details,
            "scheduling": {
                "on_host_maintenance": scheduling.get("onHostMaintenance", ""),
                "automatic_restart": scheduling.get("automaticRestart", True),
                "preemptible": scheduling.get("preemptible", False),
                "provisioning_model": scheduling.get("provisioningModel", "STANDARD"),
                "instance_termination_action": scheduling.get("instanceTerminationAction", ""),
                "max_run_duration": max_run_duration_str,
                "host_error_timeout_seconds": scheduling.get("hostErrorTimeoutSeconds"),
            },
            "service_account": service_account_email,
            "service_account_scopes": service_account_scopes,
            "ssh_key_count": ssh_key_count,
            "block_project_ssh_keys": block_project_ssh,
            "shielded_vm": shielded_vm,
            "metadata": metadata_items,
            "fingerprint": inst.get("fingerprint", ""),
        }
    except HttpError as e:
        logger.exception("get_gcp_instance failed")
        raise HTTPException(status_code=500, detail=f"GCP Error: {str(e)}")


@router.post("/instance/labels")
async def update_gcp_instance_labels(
    request: Request,
    creds: Credentials = Depends(require_gcp_auth)
):
    """Set/update labels on a GCP Compute instance."""
    body = await request.json()
    project = body.get("project")
    zone = body.get("zone")
    instance_name = body.get("instance_name")
    new_labels: Dict[str, str] = body.get("labels", {})

    if not project or not zone or not instance_name:
        raise HTTPException(status_code=400, detail="project, zone, and instance_name are required")
    try:
        service = build('compute', 'v1', credentials=creds)
        inst = service.instances().get(project=project, zone=zone, instance=instance_name).execute()
        existing_labels = inst.get("labels", {})
        existing_labels.update(new_labels)
        label_fingerprint = inst.get("labelFingerprint", "")
        service.instances().setLabels(
            project=project,
            zone=zone,
            instance=instance_name,
            body={"labels": existing_labels, "labelFingerprint": label_fingerprint}
        ).execute()
        return {"ok": True, "message": f"Labels updated on {instance_name}"}
    except HttpError as e:
        logger.exception("update_gcp_instance_labels failed")
        raise HTTPException(status_code=500, detail=f"GCP Error: {str(e)}")


@router.delete("/instance")
async def delete_gcp_instance(
    request: Request,
    project: str = Query(...),
    zone: str = Query(...),
    instance_name: str = Query(...),
    creds: Credentials = Depends(require_gcp_auth)
):
    """Delete a GCP Compute instance."""
    try:
        service = build('compute', 'v1', credentials=creds)
        service.instances().delete(project=project, zone=zone, instance=instance_name).execute()
        _gcp_audit(request, "delete_vm", resource_name=instance_name, project=project, zone=zone)
        return {"ok": True, "message": f"Deletion initiated for {instance_name}"}
    except HttpError as e:
        logger.exception("delete_gcp_instance failed")
        _gcp_audit(request, "delete_vm", resource_name=instance_name, project=project, zone=zone,
                   status="failed", error_message=str(e))
        raise HTTPException(status_code=500, detail=f"GCP Error: {str(e)}")


@router.post("/instance/restart")
async def restart_gcp_instance(
    request: Request,
    project: str = Query(...),
    zone: str = Query(...),
    instance_name: str = Query(...),
    creds: Credentials = Depends(require_gcp_auth)
):
    """Reset (hard restart) a GCP Compute instance."""
    try:
        service = build('compute', 'v1', credentials=creds)
        service.instances().reset(project=project, zone=zone, instance=instance_name).execute()
        return {"ok": True, "message": f"Reset initiated for {instance_name}"}
    except HttpError as e:
        logger.exception("restart_gcp_instance failed")
        raise HTTPException(status_code=500, detail=f"GCP Error: {str(e)}")


@router.post("/instance/power")
async def power_gcp_instance(
    request: Request,
    project: str = Query(...),
    zone: str = Query(...),
    instance_name: str = Query(...),
    action: str = Query(..., description="'start' or 'stop'"),
    creds: Credentials = Depends(require_gcp_auth)
):
    """Start or stop a GCP Compute instance."""
    action = action.lower()
    if action not in ("start", "stop"):
        raise HTTPException(status_code=400, detail="action must be 'start' or 'stop'")
    try:
        service = build('compute', 'v1', credentials=creds)
        if action == "start":
            service.instances().start(project=project, zone=zone, instance=instance_name).execute()
            msg = f"Start initiated for {instance_name}"
        else:
            service.instances().stop(project=project, zone=zone, instance=instance_name).execute()
            msg = f"Stop initiated for {instance_name}"
        return {"ok": True, "message": msg}
    except HttpError as e:
        logger.exception("power_gcp_instance failed")
        raise HTTPException(status_code=500, detail=f"GCP Error: {str(e)}")


class GcpAttachDiskRequest(BaseModel):
    disk_name: str
    size_gb: int
    disk_type: str = "pd-ssd"


class GcpSnapshotRequest(BaseModel):
    snapshot_name: str
    description: str = ""


@router.post("/instance/resize")
async def resize_gcp_instance(
    request: Request,
    project: str = Query(...),
    zone: str = Query(...),
    instance_name: str = Query(...),
    new_machine_type: str = Query(...),
    creds: Credentials = Depends(require_gcp_auth)
):
    """Resize a GCP Compute instance (stops it, changes machine type, restarts)."""
    try:
        import time
        service = build('compute', 'v1', credentials=creds)
        # Check original state before stopping
        inst = service.instances().get(project=project, zone=zone, instance=instance_name).execute()
        was_running = inst.get("status") == "RUNNING"
        if was_running:
            service.instances().stop(project=project, zone=zone, instance=instance_name).execute()
            # Poll until TERMINATED (max 5 min)
            for i in range(60):
                inst = service.instances().get(project=project, zone=zone, instance=instance_name).execute()
                if inst.get("status") == "TERMINATED":
                    break
                if i == 59:
                    raise HTTPException(status_code=504, detail=f"Timed out waiting for {instance_name} to stop before resize")
                time.sleep(5)
        machine_type_url = f"zones/{zone}/machineTypes/{new_machine_type}"
        # setMachineType is async — wait for its operation to complete before starting
        op = service.instances().setMachineType(
            project=project, zone=zone, instance=instance_name,
            body={"machineType": machine_type_url}
        ).execute()
        for i in range(60):
            op_status = service.zoneOperations().get(project=project, zone=zone, operation=op["name"]).execute()
            if op_status.get("status") == "DONE":
                if op_status.get("error"):
                    raise HTTPException(status_code=500, detail=f"Machine type change failed: {op_status['error']}")
                break
            if i == 59:
                raise HTTPException(status_code=504, detail="Timed out waiting for machine type change to complete")
            time.sleep(3)
        if was_running:
            service.instances().start(project=project, zone=zone, instance=instance_name).execute()
            return {"ok": True, "message": f"{instance_name} resized to {new_machine_type} and restarted"}
        return {"ok": True, "message": f"{instance_name} resized to {new_machine_type} (was already stopped)"}
    except HttpError as e:
        logger.exception("resize_gcp_instance failed")
        raise HTTPException(status_code=500, detail=f"GCP Error: {str(e)}")


@router.post("/instance/attach-disk")
async def attach_disk_gcp(
    request: Request,
    project: str = Query(...),
    zone: str = Query(...),
    instance_name: str = Query(...),
    body: GcpAttachDiskRequest = Body(...),
    creds: Credentials = Depends(require_gcp_auth)
):
    """Create a new persistent disk and attach it to a GCP Compute instance."""
    try:
        service = build('compute', 'v1', credentials=creds)
        disk_type_url = f"zones/{zone}/diskTypes/{body.disk_type}"
        disk_body = {
            "name": body.disk_name,
            "sizeGb": str(body.size_gb),
            "type": disk_type_url,
        }
        op = service.disks().insert(project=project, zone=zone, body=disk_body).execute()
        # Wait for disk creation (max 3 min)
        import time
        for i in range(60):
            disk_op = service.zoneOperations().get(project=project, zone=zone, operation=op["name"]).execute()
            if disk_op.get("status") == "DONE":
                if disk_op.get("error"):
                    raise HTTPException(status_code=500, detail=f"Disk creation failed: {disk_op['error']}")
                break
            if i == 59:
                raise HTTPException(status_code=504, detail="Timed out waiting for disk creation")
            time.sleep(3)
        disk_url = f"projects/{project}/zones/{zone}/disks/{body.disk_name}"
        attach_body = {"source": disk_url, "autoDelete": False}
        service.instances().attachDisk(project=project, zone=zone, instance=instance_name, body=attach_body).execute()
        return {"ok": True, "message": f"Disk {body.disk_name} ({body.size_gb} GB) attached to {instance_name}"}
    except HttpError as e:
        logger.exception("attach_disk_gcp failed")
        raise HTTPException(status_code=500, detail=f"GCP Error: {str(e)}")


@router.post("/instance/snapshot")
async def snapshot_gcp_instance(
    request: Request,
    project: str = Query(...),
    zone: str = Query(...),
    instance_name: str = Query(...),
    body: GcpSnapshotRequest = Body(...),
    creds: Credentials = Depends(require_gcp_auth)
):
    """Create a snapshot of all disks attached to a GCP Compute instance."""
    try:
        import hashlib
        service = build('compute', 'v1', credentials=creds)
        inst = service.instances().get(project=project, zone=zone, instance=instance_name).execute()
        disks = inst.get("disks", [])
        snap_names = []
        for disk in disks:
            disk_name = disk["source"].split("/")[-1]
            # Build a unique name ≤63 chars; use a 6-char hash suffix if truncation is needed
            candidate = f"{body.snapshot_name}-{disk_name}"
            if len(candidate) > 63:
                suffix = hashlib.md5(candidate.encode()).hexdigest()[:6]
                candidate = f"{body.snapshot_name[:55]}-{suffix}"
            snap_name = candidate
            snap_body = {
                "name": snap_name,
                "description": body.description or f"Snapshot of {instance_name}/{disk_name}",
            }
            service.disks().createSnapshot(project=project, zone=zone, disk=disk_name, body=snap_body).execute()
            snap_names.append(snap_name)
        _gcp_audit(
            request, "snapshot_vm",
            resource_name=instance_name, project=project, zone=zone,
            detail=f"Snapshots created: {', '.join(snap_names)}",
        )
        return {"ok": True, "message": f"Snapshots created: {', '.join(snap_names)}"}
    except HttpError as e:
        logger.exception("snapshot_gcp_instance failed")
        _gcp_audit(
            request, "snapshot_vm",
            resource_name=instance_name, project=project, zone=zone,
            status="failed", error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=f"GCP Error: {str(e)}")


@router.get("/instance/snapshots")
async def list_gcp_snapshots(
    request: Request,
    project: str = Query(...),
    zone: str = Query(...),
    instance_name: str = Query(...),
    creds: Credentials = Depends(require_gcp_auth),
):
    """List snapshots associated with disks attached to a GCP instance."""
    try:
        service = build('compute', 'v1', credentials=creds)
        inst = service.instances().get(project=project, zone=zone, instance=instance_name).execute()
        disk_names = set(d.get("source", "").split("/")[-1] for d in inst.get("disks", []) if d.get("source"))
        snaps_resp = service.snapshots().list(project=project).execute()
        result = []
        for s in snaps_resp.get("items", []):
            src_disk = s.get("sourceDisk", "").split("/")[-1]
            if src_disk in disk_names:
                result.append({
                    "name": s["name"],
                    "status": s.get("status"),
                    "creation_timestamp": s.get("creationTimestamp"),
                    "disk_size_gb": s.get("diskSizeGb"),
                    "source_disk": src_disk,
                })
        result.sort(key=lambda x: x.get("creation_timestamp") or "", reverse=True)
        return {"snapshots": result}
    except HttpError as e:
        logger.exception("list_gcp_snapshots failed")
        raise HTTPException(status_code=500, detail=f"GCP Error: {str(e)}")


@router.delete("/snapshot/{snapshot_name}")
async def delete_gcp_snapshot(
    request: Request,
    snapshot_name: str,
    project: str = Query(...),
    creds: Credentials = Depends(require_gcp_auth),
):
    """Delete a GCP snapshot by name."""
    try:
        service = build('compute', 'v1', credentials=creds)
        service.snapshots().delete(project=project, snapshot=snapshot_name).execute()
        _gcp_audit(request, "delete_snapshot", resource_name=snapshot_name, project=project)
        return {"ok": True, "message": f"Snapshot {snapshot_name} deleted"}
    except HttpError as e:
        logger.exception("delete_gcp_snapshot failed")
        _gcp_audit(request, "delete_snapshot", resource_name=snapshot_name, project=project,
                   status="failed", error_message=str(e))
        raise HTTPException(status_code=500, detail=f"GCP Error: {str(e)}")


class GcpResizeDiskRequest(BaseModel):
    new_size_gb: int


@router.post("/disk/resize")
async def resize_gcp_disk(
    request: Request,
    project: str = Query(...),
    zone: str = Query(...),
    disk_name: str = Query(...),
    body: GcpResizeDiskRequest = Body(...),
    creds: Credentials = Depends(require_gcp_auth),
):
    """Resize a GCP persistent disk (increase only)."""
    try:
        service = build('compute', 'v1', credentials=creds)
        resize_body = {"sizeGb": str(body.new_size_gb)}
        service.disks().resize(project=project, zone=zone, disk=disk_name, body=resize_body).execute()
        return {"ok": True, "message": f"Disk {disk_name} resize to {body.new_size_gb} GB initiated. Extend the file system inside the OS if needed."}
    except HttpError as e:
        logger.exception("resize_gcp_disk failed")
        raise HTTPException(status_code=500, detail=f"GCP Error: {str(e)}")


@router.delete("/instance/disk")
async def delete_gcp_disk(
    request: Request,
    project: str = Query(...),
    zone: str = Query(...),
    instance_name: str = Query(...),
    disk_name: str = Query(...),
    creds: Credentials = Depends(require_gcp_auth),
):
    """Detach a disk from a GCP instance and delete it. Boot disk cannot be deleted while VM exists."""
    try:
        service = build('compute', 'v1', credentials=creds)
        # Detach the disk from the instance
        service.instances().detachDisk(project=project, zone=zone, instance=instance_name, deviceName=disk_name).execute()
        # Wait for detach (max 2 min)
        for _ in range(40):
            instance = service.instances().get(project=project, zone=zone, instance=instance_name).execute()
            attached = [d.get("source", "").split("/")[-1] for d in instance.get("disks", [])]
            if disk_name not in attached:
                break
            time.sleep(3)
        # Delete the disk
        service.disks().delete(project=project, zone=zone, disk=disk_name).execute()
        _gcp_audit(
            request, "delete_disk",
            resource_name=disk_name, project=project, zone=zone,
            detail=f"Detached and deleted disk {disk_name} from instance {instance_name}",
        )
        return {"ok": True, "message": f"Disk {disk_name} detached and deleted successfully."}
    except HttpError as e:
        logger.exception("delete_gcp_disk failed")
        _gcp_audit(
            request, "delete_disk",
            resource_name=disk_name, project=project, zone=zone,
            status="failed", error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=f"GCP Error: {str(e)}")


@router.post("/instance/clone")
async def clone_gcp_instance(
    request: Request,
    project: str = Query(...),
    zone: str = Query(...),
    instance_name: str = Query(...),
    creds: Credentials = Depends(require_gcp_auth),
):
    """Clone a GCP Compute instance by creating a new instance with same machine type, image, and network settings."""
    body = await request.json()
    new_name = (body.get("new_name") or "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="new_name is required")
    try:
        service = build('compute', 'v1', credentials=creds)
        src = service.instances().get(project=project, zone=zone, instance=instance_name).execute()

        import hashlib
        import time

        machine_type_url = src.get("machineType", "")

        # Find boot disk and collect non-boot disks separately.
        boot_disk_source_url = None
        boot_disk_name = None
        boot_disk_size = None
        boot_disk_type_url = None
        data_disks_src = []
        for d in src.get("disks", []):
            if d.get("boot"):
                boot_disk_source_url = d.get("source", "")
                boot_disk_name = boot_disk_source_url.split("/")[-1]
                if boot_disk_name:
                    disk_res = service.disks().get(project=project, zone=zone, disk=boot_disk_name).execute()
                    boot_disk_size = disk_res.get("sizeGb")
                    boot_disk_type_url = disk_res.get("type")
            else:
                data_disks_src.append(d)

        if not boot_disk_name:
            raise HTTPException(status_code=400, detail="Could not determine source boot disk — cannot clone")

        def _wait_for_zone_operation(op_name: str, timeout_seconds: int = 900) -> None:
            end_time = time.time() + timeout_seconds
            while time.time() < end_time:
                op_status = service.zoneOperations().get(project=project, zone=zone, operation=op_name).execute()
                if op_status.get("status") == "DONE":
                    if op_status.get("error"):
                        raise HTTPException(status_code=500, detail=f"GCP operation failed: {op_status['error']}")
                    return
                time.sleep(3)
            raise HTTPException(status_code=504, detail=f"Timed out waiting for operation {op_name}")

        def _snapshot_name(prefix: str, disk_name: str) -> str:
            candidate = f"{prefix}-{disk_name}"
            if len(candidate) <= 63:
                return candidate
            hash_suffix = hashlib.sha256(candidate.encode()).hexdigest()[:8]
            max_disk_name_len = max(1, min(20, 63 - len(hash_suffix) - 2 - 1))
            disk_name_part = disk_name[:max_disk_name_len]
            trimmed = prefix[: max(1, 63 - len(disk_name_part) - len(hash_suffix) - 2)]
            return f"{trimmed}-{disk_name_part}-{hash_suffix}"[:63]

        # Clone boot disk content using a source snapshot instead of source image.
        boot_snapshot_name = _snapshot_name(f"{new_name}-boot-snap", boot_disk_name)
        boot_snap_op = service.disks().createSnapshot(
            project=project,
            zone=zone,
            disk=boot_disk_name,
            body={"name": boot_snapshot_name, "description": f"Clone boot snapshot of {instance_name}/{boot_disk_name}"},
        ).execute()
        _wait_for_zone_operation(boot_snap_op["name"])
        boot_snapshot_url = f"projects/{project}/global/snapshots/{boot_snapshot_name}"

        # Network interfaces: reuse same network/subnetwork, drop the static external IP
        network_interfaces = []
        for ni in src.get("networkInterfaces", []):
            new_ni = {
                "network": ni.get("network"),
                "subnetwork": ni.get("subnetwork"),
            }
            # Preserve access config type but omit natIP (will get new ephemeral IP)
            access_cfgs = ni.get("accessConfigs", [])
            if access_cfgs:
                new_ni["accessConfigs"] = [{"type": ac.get("type", "ONE_TO_ONE_NAT"), "name": ac.get("name", "External NAT")} for ac in access_cfgs]
            network_interfaces.append(new_ni)

        # Build boot disk init params
        boot_disk_body: dict = {
            "boot": True,
            "autoDelete": True,
            "initializeParams": {
                "sourceSnapshot": boot_snapshot_url,
            },
        }
        if boot_disk_size:
            boot_disk_body["initializeParams"]["diskSizeGb"] = boot_disk_size
        if boot_disk_type_url:
            boot_disk_body["initializeParams"]["diskType"] = boot_disk_type_url

        disks_list = [boot_disk_body]

        # Clone each additional (non-boot) data disk from snapshots so disk data is copied.
        for d in data_disks_src:
            src_disk_url = d.get("source", "")
            if not src_disk_url:
                continue
            src_disk_name = src_disk_url.split("/")[-1]
            snapshot_name = _snapshot_name(f"{new_name}-data-snap", src_disk_name)
            snap_op = service.disks().createSnapshot(
                project=project,
                zone=zone,
                disk=src_disk_name,
                body={"name": snapshot_name, "description": f"Clone data snapshot of {instance_name}/{src_disk_name}"},
            ).execute()
            _wait_for_zone_operation(snap_op["name"])
            snapshot_url = f"projects/{project}/global/snapshots/{snapshot_name}"
            data_disk_body: dict = {
                "boot": False,
                "autoDelete": d.get("autoDelete", True),
                "mode": d.get("mode", "READ_WRITE"),
                "interface": d.get("interface", "SCSI"),
                "initializeParams": {
                    "sourceSnapshot": snapshot_url,
                },
            }
            # Carry over size and type from the source disk resource if available
            try:
                src_disk_res = service.disks().get(project=project, zone=zone, disk=src_disk_name).execute()
                if src_disk_res.get("sizeGb"):
                    data_disk_body["initializeParams"]["diskSizeGb"] = src_disk_res["sizeGb"]
                if src_disk_res.get("type"):
                    data_disk_body["initializeParams"]["diskType"] = src_disk_res["type"]
            except Exception:
                pass
            disks_list.append(data_disk_body)

        instance_body = {
            "name": new_name,
            "machineType": machine_type_url,
            "disks": disks_list,
            "networkInterfaces": network_interfaces,
            "labels": dict(src.get("labels", {})),
            "metadata": src.get("metadata", {}),
            "serviceAccounts": src.get("serviceAccounts", []),
            "scheduling": src.get("scheduling", {}),
        }

        op = service.instances().insert(project=project, zone=zone, body=instance_body).execute()
        data_disk_count = len(data_disks_src)
        _gcp_audit(
            request, "clone_vm",
            resource_name=new_name, resource_id=op.get("name"),
            project=project, zone=zone,
            detail=f"Cloned from '{instance_name}'" + (f" with {data_disk_count} additional disk(s)" if data_disk_count else ""),
        )
        return {
            "ok": True,
            "operation_id": op.get("name"),
            "message": (
                f"Clone of '{instance_name}' as '{new_name}' started (operation: {op.get('name')})"
                + (f" with {data_disk_count} additional disk(s)" if data_disk_count else "")
            ),
        }
    except HttpError as e:
        logger.exception("clone_gcp_instance failed")
        _gcp_audit(
            request, "clone_vm",
            resource_name=new_name, project=project, zone=zone,
            status="failed", error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=f"GCP Error: {str(e)}")
