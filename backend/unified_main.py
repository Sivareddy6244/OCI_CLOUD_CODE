# Complete backend for Multi-Cloud Portal (unified_main.py)
# FIXED: AMI IDs are now fetched dynamically from AWS accounts (no hardcoded AMI_MAP)
# FIXED: Tags work for AWS, Azure, and GCP

from fastapi import FastAPI, HTTPException, Form, Query, Request, Body, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import subprocess
import json
import os
import shutil
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config as BotocoreConfig
from datetime import datetime, timezone
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.mgmt.subscription import SubscriptionClient
try:
    from azure.mgmt.resource import ResourceManagementClient
except ImportError:
    from azure.mgmt.resource.resources import ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network.models import (
    NetworkInterface, NetworkInterfaceIPConfiguration,
    NetworkSecurityGroup, SecurityRule, SubResource,
)
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.compute.models import (
    RunCommandInput, RunCommandInputParameter,
    VirtualMachine, HardwareProfile, StorageProfile, ImageReference,
    OSDisk, ManagedDiskParameters, DataDisk,
    OSProfile, NetworkProfile, NetworkInterfaceReference,
    SecurityProfile, UefiSettings,
    CreationData, Snapshot, Disk, DiskSku, DiskUpdate,
)
from azure.core.exceptions import HttpResponseError
import requests
import traceback
import logging
import base64
import time
import shlex
import urllib3
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from typing import Optional, Dict, Any, List, Set, Tuple, NoReturn
from concurrent.futures import ThreadPoolExecutor, as_completed
from cachetools import TTLCache, cached
import ipaddress
import re
import threading
import uuid
import csv
import io

# Basic logger configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("multi-cloud-portal")
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.identity").setLevel(logging.WARNING)
logging.getLogger("azure.mgmt").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Import GCP backend router
try:
    from gcp_backend import router as gcp_router
    GCP_AVAILABLE = True
except ImportError as e:
    logger.warning("GCP backend not available: %s", e)
    GCP_AVAILABLE = False
    gcp_router = None
# DB logging (non-blocking)
try:
    from db_sql import (
    insert_portal_request_all,
    get_billing_approver_emails_csv,
    get_resources_by_department,
    is_admin_by_email,
    upsert_deployment_status as db_upsert_deployment_status,
    get_deployment_status_db,
    get_azure_vm_sizes as db_get_azure_vm_sizes,
    get_aws_account_number_from_db,
    update_latest_portal_request_vm_outcome,
    get_isd_subscriptions_for_email,
    log_vm_action,
    )
    DB_AVAILABLE = True
except Exception as e:
    DB_AVAILABLE = False
    insert_portal_request_all = None
    get_billing_approver_emails_csv = None
    get_resources_by_department = None
    is_admin_by_email = None
    db_upsert_deployment_status = None
    get_deployment_status_db = None
    db_get_azure_vm_sizes = None
    get_aws_account_number_from_db = None
    update_latest_portal_request_vm_outcome = None
    get_isd_subscriptions_for_email = None
    log_vm_action = None
    logger.warning("DB logging disabled (db_sql import failed): %s", e)

# Import Azure AD auth router
try:
    from azure_ad_auth import router as azure_ad_router
    AZURE_AD_AUTH_AVAILABLE = True
except ImportError as e:
    logger.warning("Azure AD auth not available: %s", e)
    AZURE_AD_AUTH_AVAILABLE = False
    azure_ad_router = None

# Import GCP WIF router
try:
    from gcp_wif import router as gcp_wif_router
    GCP_WIF_AVAILABLE = True
except ImportError as e:
    logger.warning("GCP WIF not available: %s", e)
    GCP_WIF_AVAILABLE = False
    gcp_wif_router = None

# Import OCI backend helpers
try:
    from oci_backend import (
        is_oci_enabled as oci_is_enabled,
        list_tenancy_summaries as oci_list_tenancy_summaries,
        list_availability_domains as oci_list_availability_domains,
        list_compartments as oci_list_compartments,
        list_vcns as oci_list_vcns,
        list_subnets as oci_list_subnets,
        list_nsgs as oci_list_nsgs,
        list_images as oci_list_images,
        list_shapes as oci_list_shapes,
        launch_instance as oci_launch_instance,
        get_tenancy_config as oci_get_tenancy_config,
    )
    OCI_AVAILABLE = True
except ImportError as e:
    logger.warning("OCI backend not available: %s", e)
    OCI_AVAILABLE = False
    oci_is_enabled = None
    oci_list_tenancy_summaries = None
    oci_list_availability_domains = None
    oci_list_compartments = None
    oci_list_vcns = None
    oci_list_subnets = None
    oci_list_nsgs = None
    oci_list_images = None
    oci_list_shapes = None
    oci_launch_instance = None
    oci_get_tenancy_config = None

# Import Cherwell integration
try:
    from cherwell_integration import (
        create_post_deployment_tasks,
        cherwell_get_token,
        cherwell_create_incident,
        cherwell_create_task,
        CHERWELL_ENABLED
    )
    CHERWELL_INTEGRATION_AVAILABLE = True
    logger.info("✅ Cherwell integration loaded successfully")
except ImportError as e:
    logger.warning("Cherwell integration not available: %s", e)
    CHERWELL_INTEGRATION_AVAILABLE = False
    create_post_deployment_tasks = None
    CHERWELL_ENABLED = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_PATH = os.path.join(BASE_DIR, "../frontend/static/unified_index.html")
OCI_CLOUD_OPTION_PATTERN = re.compile(
    r'<option\b(?=[^>]*\bvalue=["\']oci["\'])[^>]*>[^<]*</option>',
    re.IGNORECASE,
)
NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


def _render_frontend_html():
    if not os.path.isfile(FRONTEND_PATH):
        return None
    with open(FRONTEND_PATH, "r", encoding="utf-8") as f:
        html = f.read()
    return OCI_CLOUD_OPTION_PATTERN.sub(
        '<option value="oci">OCI (Oracle Cloud Infrastructure)</option>',
        html,
        count=1,
    )

TERRAFORM_COMMON_PATHS = [
    "/usr/bin/terraform",
    "/usr/local/bin/terraform",
    "/opt/terraform/terraform"
]

def find_terraform_binary():
    """Find Terraform binary in common locations."""
    env_path_raw = os.getenv("TERRAFORM_BIN")
    env_var_set = env_path_raw is not None
    env_path = env_path_raw if env_path_raw else "/usr/bin/terraform"
    
    if os.path.isfile(env_path) and os.access(env_path, os.X_OK):
        return env_path
    
    which_result = shutil.which("terraform")
    
    search_paths = TERRAFORM_COMMON_PATHS.copy()
    if which_result and which_result not in search_paths:
        search_paths.append(which_result)
    
    for path in search_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            if env_var_set:
                logger.info(f"Found Terraform binary at: {path} (TERRAFORM_BIN env var was set to '{env_path}' but does not exist)")
            else:
                logger.info(f"Using Terraform binary at: {path} (TERRAFORM_BIN env var not set, using default search)")
            return path
    
    if env_var_set:
        logger.warning(f"Terraform binary not found. TERRAFORM_BIN env var is set to '{env_path}' but does not exist. Checked: {search_paths}")
    else:
        logger.warning(f"Terraform binary not found. TERRAFORM_BIN env var not set. Checked: {search_paths}")
    return env_path

TERRAFORM_BIN = find_terraform_binary()

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

TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")

# Password for the svc_ecloudadmin service account created on every Azure VM post-deployment.
# Set this in the App Service application settings (never hard-code in source).
SVC_ECLOUDADMIN_PASSWORD = os.getenv("SVC_ECLOUDADMIN_PASSWORD", "")

AWS_SSO_INSTANCE_ARN = os.getenv("AWS_SSO_INSTANCE_ARN")

ALLOW_ASSUME_ROLE_FALLBACK = os.getenv("ALLOW_ASSUME_ROLE_FALLBACK", "true").lower() in ("1", "true", "yes")

HTTP_VERIFY = os.getenv("HTTP_VERIFY", "true").lower() in ("1", "true", "yes")

AZURE_SQL_MI_KNOWN_POLLER_OK_STATUS_ERROR = "invalid status 'OK'"
AZURE_SDK_ERROR_CONTENT_SEPARATOR = "Content:"
AZURE_SQL_MI_API_VERSION = "2021-11-01-preview"
AZURE_MANAGEMENT_SCOPE = "https://management.azure.com/.default"

if not HTTP_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# --- BASIS billing validation (allowlist + external validate call) ---

BASIS_TEST_URL = os.getenv("BASIS_TEST_URL", "https://api-test.basis.isd.lacounty.gov")
BASIS_TEST_CLIENT_ID = os.getenv("BASIS_TEST_CLIENT_ID", "")
BASIS_TEST_KEY = os.getenv("BASIS_TEST_KEY", "")
BASIS_PROD_URL = os.getenv("BASIS_PROD_URL", "https://api.basis.isd.lacounty.gov")
BASIS_PROD_CLIENT_ID = os.getenv("BASIS_PROD_CLIENT_ID", "")
BASIS_PROD_KEY = os.getenv("BASIS_PROD_KEY", "")
BASIS_DEFAULT_VALIDATE_PATH = "/api/v1/billing/accounts/get"
BASIS_SEARCH_VALIDATE_PATH = "/api/v1/billing/accounts/search"
BASIS_LEGACY_VALIDATE_PATH = "/accounts/{account}/status"
BASIS_VALIDATE_PATH = os.getenv("BASIS_VALIDATE_PATH", BASIS_DEFAULT_VALIDATE_PATH)
BASIS_ACCOUNT_QUERY_PARAM = os.getenv("BASIS_ACCOUNT_QUERY_PARAM", "billingAccountNumber")
BASIS_FISCAL_YEAR_QUERY_PARAM = os.getenv("BASIS_FISCAL_YEAR_QUERY_PARAM", "fiscalYear")
BASIS_FISCAL_YEAR = os.getenv("BASIS_FISCAL_YEAR", "")
BASIS_REQUEST_TIMEOUT = int(os.getenv("BASIS_REQUEST_TIMEOUT", "8"))
BASIS_API_KEY_HEADER = os.getenv("BASIS_API_KEY_HEADER", "")
BASIS_CLIENT_ID_HEADER = os.getenv("BASIS_CLIENT_ID_HEADER", "ClientId")

BASIS_ALLOWED_LIST_RAW = os.getenv("BASIS_ALLOWED_LIST", """A1159012000
A1020024019
A1020021203
P1343091233
A1557524007
P1343091230
P1333591230
P1318391290
P1355891200
A2679200110
A2000007161
A2679200112
A6150039412
A1910051203
A2590191100
A2590192900
P1333318406
A2791014032
A1120151808
P1333891081
A1009122400
P1333991200
P1312710801
P13127110703
P1356091260
P1355422005
P1317690040
P1319591233
A5579539320
A1500002028
P1355791272
A2781023047
P1355991201
A1520014592
A3347497651
P1355491230
P1356091260
P1356101230
A5730000015
A4790000012
A1130092315
A1130043035
A1710072008
A4120000464
A2650063165
A1935039360
P1333700003
A1130097017
A1130097011
P1355891200
A1020024019
P1355491234
A1010024012
A1520014592
A1520014593
A1520014594
A1095080018
A1001025002
A1070018468
A8362000001
A1010024036
A1095087051
P131759318
A5710001099
A1020021203
A1369023005
A1010015012
A1105039332
A2679200278
A2000020300
A1403034002
A2050080975
A4042821001
A1080008100
P1312710701
A1120151809
A1080011100
P1334094561
P1319591235
A2304381031
P1356101230
A1312701000
A2000007151
NCC131313030002
A2050080997
A1710000183
A3347497651
A4120003762
""")

def _normalize_basis_acct(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"[^0-9A-Za-z]", "", s).upper().strip()

def _mask_basis_account_for_log(account: str) -> str:
    n = _normalize_basis_acct(account)
    if not n:
        return "<empty>"
    if len(n) <= 4:
        return "*" * len(n)
    return f"{n[:2]}***{n[-2:]}"

def _parse_basis_keys(raw_keys: str) -> List[str]:
    keys = []
    seen = set()
    for key in re.split(r"[\n,;]+", raw_keys or ""):
        k = (key or "").strip()
        if k and k not in seen:
            keys.append(k)
            seen.add(k)
    return keys

def _parse_basis_account_for_search(account: str) -> Optional[Dict[str, str]]:
    """Parse a BASIS account like A1009122400 into BillingIndicator/MainAccount/SubAccount.

    Account format: 1 alpha char (BillingIndicator) + 5 digits (MainAccount) + 5 digits (SubAccount).
    E.g. A1009122400 → BillingIndicator=A, MainAccount=10091, SubAccount=22400.
    """
    acct = _normalize_basis_acct(account)
    m = re.match(r'^([A-Z])(\d{5})(\d{5})$', acct)
    if m:
        return {
            "billing_indicator": m.group(1),
            "main_account": m.group(2),
            "sub_account": m.group(3),
        }
    return None

def _build_basis_search_candidate(base_url: str, account: str) -> Optional[str]:
    """Build the /api/v1/billing/accounts/search URL for a parseable account number."""
    parts = _parse_basis_account_for_search(account)
    if not parts:
        return None
    params = urlencode({
        "BillingIndicator": parts["billing_indicator"],
        "MainAccount": parts["main_account"],
        "SubAccount": parts["sub_account"],
    })
    return base_url.rstrip("/") + BASIS_SEARCH_VALIDATE_PATH + "?" + params

def _basis_search_response_has_results(raw: Any) -> Optional[bool]:
    """Return True if a BASIS search response contains matching records, False if none, None if not a search response."""
    if not isinstance(raw, dict):
        return None
    if "items" not in raw or "totalRecords" not in raw:
        return None
    total = raw.get("totalRecords")
    items = raw.get("items")
    try:
        total = int(total)
    except (TypeError, ValueError):
        total = -1
    if isinstance(items, list):
        # Prioritise actual items in the page; fall back to totalRecords as a secondary signal.
        return len(items) > 0 or total > 0
    return total > 0

def _basis_response_contains_account(raw: Any, account: str) -> bool:
    target = _normalize_basis_acct(account)
    if not target:
        return False
    stack = [raw]
    seen = set()
    inspected = 0
    while stack:
        item = stack.pop()
        inspected += 1
        if inspected > 2048:
            return False
        if isinstance(item, dict):
            marker = id(item)
            if marker in seen:
                continue
            seen.add(marker)
            for k, v in item.items():
                if isinstance(v, (dict, list, tuple, set)):
                    stack.append(v)
                    continue
                key_name = str(k).strip().lower()
                if key_name in ("account", "accountnumber", "account_number", "billingaccount", "billing_account", "billing_account_number"):
                    if _normalize_basis_acct(str(v)) == target:
                        return True
                if isinstance(v, str):
                    for tok in re.findall(r"[0-9A-Za-z-]+", v):
                        if _normalize_basis_acct(tok) == target:
                            return True
        elif isinstance(item, (list, tuple, set)):
            stack.extend(item)
        elif item is not None:
            for tok in re.findall(r"[0-9A-Za-z-]+", str(item)):
                if _normalize_basis_acct(tok) == target:
                    return True
    return False

def _parse_basis_allowed(raw: str) -> set:
    items = re.split(r"[\n,;]+", raw or "")
    normalized = set()
    for it in items:
        it = it.strip()
        if not it:
            continue
        it = it.replace("and", " ").replace("*", " ")
        n = _normalize_basis_acct(it)
        if n:
            normalized.add(n)
    return normalized

BASIS_ALLOWED_SET = _parse_basis_allowed(BASIS_ALLOWED_LIST_RAW)

def is_basis_account_allowlisted(account: str) -> bool:
    if not account:
        return False
    n = _normalize_basis_acct(account)
    return n in BASIS_ALLOWED_SET

def _resolve_basis_fiscal_year() -> str:
    """Return configured fiscal year or fall back to current UTC year."""
    fy = (BASIS_FISCAL_YEAR or "").strip()
    if fy:
        return fy
    return str(datetime.now(timezone.utc).year)

def _append_basis_validate_query_params(url: str, account: str) -> str:
    """Append BASIS account/fiscal-year query parameters when configured."""
    fiscal_year = _resolve_basis_fiscal_year()
    acct_param = (BASIS_ACCOUNT_QUERY_PARAM or "").strip()
    fy_param = (BASIS_FISCAL_YEAR_QUERY_PARAM or "").strip()
    if not acct_param and not fy_param:
        return url

    parsed_url = urlsplit(url)
    query = dict(parse_qsl(parsed_url.query, keep_blank_values=True))
    if acct_param and acct_param not in query:
        query[acct_param] = account
    if fy_param and fy_param not in query:
        query[fy_param] = fiscal_year
    return urlunsplit((parsed_url.scheme, parsed_url.netloc, parsed_url.path, urlencode(query), parsed_url.fragment))

def _build_basis_validate_url(base_url: str, account: str, path_template: Optional[str] = None, include_query_params: bool = True) -> str:
    """Build a BASIS validation URL for one request style."""
    fiscal_year = _resolve_basis_fiscal_year()
    safe_path = BASIS_VALIDATE_PATH if path_template is None else (path_template or "")
    try:
        safe_path = safe_path.format(account=account, fiscal_year=fiscal_year)
    except (KeyError, ValueError, IndexError):
        safe_path = safe_path.replace("{account}", account).replace("{fiscal_year}", fiscal_year)
    full_url = base_url.rstrip("/") + safe_path
    if include_query_params:
        full_url = _append_basis_validate_query_params(full_url, account)
    return full_url

def _build_basis_validate_candidates(base_url: str, account: str) -> List[Tuple[str, str]]:
    """Build ordered candidate URLs to tolerate BASIS path/query variations."""
    candidates: List[Tuple[str, str]] = []
    seen = set()

    def add(label: str, url: str) -> None:
        if url and url not in seen:
            seen.add(url)
            candidates.append((label, url))

    # Prefer the search endpoint (BillingIndicator/MainAccount/SubAccount) when the
    # account number matches the standard format (e.g. A1009122400).
    search_url = _build_basis_search_candidate(base_url, account)
    if search_url:
        add("search", search_url)

    add("configured", _build_basis_validate_url(base_url, account))
    add("configured-path-only", _build_basis_validate_url(base_url, account, include_query_params=False))

    configured_path = (BASIS_VALIDATE_PATH or "").strip()
    if configured_path != BASIS_DEFAULT_VALIDATE_PATH:
        add("default-query-fallback", _build_basis_validate_url(base_url, account, path_template=BASIS_DEFAULT_VALIDATE_PATH, include_query_params=True))
        add("default-path-only-fallback", _build_basis_validate_url(base_url, account, path_template=BASIS_DEFAULT_VALIDATE_PATH, include_query_params=False))
    if configured_path != BASIS_LEGACY_VALIDATE_PATH:
        add("legacy-query-fallback", _build_basis_validate_url(base_url, account, path_template=BASIS_LEGACY_VALIDATE_PATH, include_query_params=True))
        add("legacy-path-only-fallback", _build_basis_validate_url(base_url, account, path_template=BASIS_LEGACY_VALIDATE_PATH, include_query_params=False))
    add("query-only-fallback", _build_basis_validate_url(base_url, account, path_template="", include_query_params=True))

    return candidates

def _sanitize_basis_url_for_log(url: str, account: str) -> str:
    masked = _mask_basis_account_for_log(account)
    safe_url = str(url or "")
    for token in filter(None, {account, _normalize_basis_acct(account)}):
        safe_url = safe_url.replace(token, masked)
    return safe_url

BASIS_LOG_MAX_EXCERPT = 1200
BASIS_LOG_MAX_HINT_VALUE = 120
BASIS_LOG_MAX_HINTS = 6
BASIS_LOG_MAX_INSPECTED_NODES = 2048
BASIS_LOG_MAX_KEY_PREVIEW = 12
BASIS_LOG_MAX_ITEM_PREVIEW = 3
BASIS_INTERESTING_ACCOUNT_KEYS = {"account", "accountnumber", "account_number", "billingaccount", "billing_account", "billing_account_number"}
BASIS_ACCOUNT_TOKEN_PATTERN = r"[0-9A-Za-z-]+"
BASIS_STATUS_INDICATOR_KEYS = {"statusindicator", "status_indicator"}
BASIS_STATUS_INDICATOR_DETAILS = {
    "1": {"meaning": "ACCOUNT IS OPEN (ALLOWED LIST)", "ui_state": "success"},
    "2": {"meaning": "ACCOUNT IS PENDING CLOSURE", "ui_state": "error"},
    "3": {"meaning": "ACCOUNT IS CLOSED", "ui_state": "error"},
    "4": {"meaning": "ACCOUNT IS VALID, BUT WILL BE CLOSED IN THE NEXT FISCAL YEAR", "ui_state": "warning"},
    "5": {"meaning": "ACCOUNT IS CLOSED CURR FY-OPEN NEXT FY", "ui_state": "error"},
}
BASIS_STATUS_INDICATOR_PASS_SET = {"1", "4"}
BASIS_STATUS_INDICATOR_BLOCK_SET = {"2", "3", "5"}

def _sanitize_basis_payload_for_log(payload: Any, account: str, max_len: int = BASIS_LOG_MAX_EXCERPT) -> str:
    if payload is None:
        return ""
    try:
        text = payload if isinstance(payload, str) else json.dumps(payload, default=str, ensure_ascii=False)
    except Exception:
        text = str(payload)
    text = _sanitize_basis_url_for_log(text, account)
    if len(text) > max_len:
        text = text[:max_len] + "...(truncated)"
    return text

def _basis_find_account_hints_for_log(raw: Any, account: str, max_hints: int = BASIS_LOG_MAX_HINTS) -> List[str]:
    target = _normalize_basis_acct(account)
    if not target:
        return []
    hints: List[str] = []
    stack: List[Tuple[str, Any]] = [("$", raw)]
    seen = set()
    inspected = 0

    while stack and len(hints) < max_hints:
        path, item = stack.pop()
        inspected += 1
        if inspected > BASIS_LOG_MAX_INSPECTED_NODES:
            break
        if isinstance(item, dict):
            marker = id(item)
            if marker in seen:
                continue
            seen.add(marker)
            for k, v in item.items():
                child_path = f"{path}.{k}"
                key_name = str(k).strip().lower()
                if key_name in BASIS_INTERESTING_ACCOUNT_KEYS:
                    value_text = str(v or "").strip()
                    hints.append(f"{child_path}(match={_normalize_basis_acct(value_text) == target})")
                elif key_name in BASIS_STATUS_INDICATOR_KEYS:
                    value_text = str(v or "").strip()
                    hints.append(f"{child_path}(status_indicator={value_text})")
                if len(hints) >= max_hints:
                    break
                stack.append((child_path, v))
        elif isinstance(item, (list, tuple, set)):
            for idx, v in enumerate(item):
                stack.append((f"{path}[{idx}]", v))
        elif isinstance(item, str):
            matches = re.findall(BASIS_ACCOUNT_TOKEN_PATTERN, item)
            if any(_normalize_basis_acct(tok) == target for tok in matches):
                hints.append(f"{path}(embedded_match=True)")
    return hints

def _basis_summarize_payload_for_log(raw: Any, account: str) -> str:
    parts = [f"type={type(raw).__name__}"]
    if isinstance(raw, dict):
        keys = [str(k) for k in raw.keys()]
        parts.append(f"key_count={len(keys)}")
        parts.append(f"keys={keys[:BASIS_LOG_MAX_KEY_PREVIEW]}")
    elif isinstance(raw, (list, tuple, set)):
        items = list(raw)
        parts.append(f"item_count={len(items)}")
        preview = []
        for item in items[:BASIS_LOG_MAX_ITEM_PREVIEW]:
            if isinstance(item, dict):
                preview.append(f"dict:{[str(k) for k in list(item.keys())[:BASIS_LOG_MAX_KEY_PREVIEW]]}")
            else:
                preview.append(type(item).__name__)
        parts.append(f"preview={preview}")
    elif raw is not None:
        text = _sanitize_basis_payload_for_log(str(raw), account, max_len=BASIS_LOG_MAX_HINT_VALUE)
        if text:
            parts.append(f"text={text}")
    return "; ".join(parts)

def _basis_response_indicates_missing_account(raw: Any, reason: str = "") -> bool:
    stack = [reason, raw]
    seen = set()
    inspected = 0
    while stack:
        item = stack.pop()
        inspected += 1
        if inspected > 2048:
            return False
        if isinstance(item, dict):
            marker = id(item)
            if marker in seen:
                continue
            seen.add(marker)
            stack.extend(item.values())
        elif isinstance(item, (list, tuple, set)):
            stack.extend(item)
        elif item is not None:
            text = str(item).strip().lower()
            if "invalid account" in text or "unknown account" in text:
                return True
            if ("not found" in text or "notfound" in text) and ("account" in text or "billing" in text):
                return True
    return False

def _extract_basis_status_indicator(raw: Any) -> str:
    stack = [raw]
    seen = set()
    inspected = 0
    while stack:
        item = stack.pop()
        inspected += 1
        # Keep recursive payload inspection bounded so unusual BASIS payloads
        # cannot consume excessive CPU/memory during logging/field extraction.
        if inspected > 2048:
            return ""
        if isinstance(item, dict):
            marker = id(item)
            if marker in seen:
                continue
            seen.add(marker)
            for key, value in item.items():
                key_name = str(key).strip().lower()
                if key_name in BASIS_STATUS_INDICATOR_KEYS and value is not None:
                    return str(value).strip()
                if isinstance(value, (dict, list, tuple, set)):
                    stack.append(value)
        elif isinstance(item, (list, tuple, set)):
            stack.extend(item)
    return ""

def _get_basis_status_indicator_details(indicator: str) -> Dict[str, str]:
    return BASIS_STATUS_INDICATOR_DETAILS.get(str(indicator or "").strip(), {})

def _call_basis_validate(base_url: str, client_id: str, client_key: str, account: str, timeout: Optional[int] = None) -> dict:
    if not base_url:
        return {"ok": False, "error": "no_base_url_configured"}
    timeout = timeout or BASIS_REQUEST_TIMEOUT
    url_candidates = _build_basis_validate_candidates(base_url, account)

    headers_template = {"Accept": "application/json"}
    preferred_header = (BASIS_API_KEY_HEADER or "").strip() or "ApiKey"
    candidate_headers = []
    for h in [preferred_header, "ApiKey", "X-API-Key", "Ocp-Apim-Subscription-Key", "Subscription-Key"]:
        if h and h not in candidate_headers:
            candidate_headers.append(h)

    client_id_headers = []
    preferred_client_id_header = (BASIS_CLIENT_ID_HEADER or "").strip() or "ClientId"
    for h in [preferred_client_id_header, "ClientId", "X-Client-Id", "ClientID"]:
        if h and h not in client_id_headers:
            client_id_headers.append(h)
    if not client_id_headers:
        client_id_headers.append("ClientId")

    key_candidates = _parse_basis_keys(client_key)

    def execute_request(url_style: str, url: str, headers: Dict[str, str], used_header: str = "", used_client_id_header: str = "") -> dict:
        resp = requests.get(url, headers=headers, timeout=timeout, verify=HTTP_VERIFY)
        text = resp.text or ""
        try:
            data = resp.json()
        except Exception:
            data = {"raw_text": text}
        return {
            "ok": True,
            "status_code": resp.status_code,
            "data": data,
            "used_header": used_header,
            "used_client_id_header": used_client_id_header,
            "request_url": url,
            "url_style": url_style,
        }

    last_exc = None
    last_response = None
    if not key_candidates:
        for idx, (url_style, url) in enumerate(url_candidates):
            is_last_candidate = idx == len(url_candidates) - 1
            saw_response = False
            all_not_found = True
            for client_id_header in client_id_headers:
                headers = dict(headers_template)
                if client_id:
                    headers[client_id_header] = client_id
                try:
                    result = execute_request(url_style, url, headers, "", client_id_header if client_id else "")
                    saw_response = True
                    status = result["status_code"]
                    if status == 404 and not is_last_candidate:
                        last_response = result
                        continue
                    all_not_found = False
                    return result
                except Exception as ex:
                    last_exc = ex
            if saw_response and all_not_found and not is_last_candidate:
                continue
    else:
        for idx, (url_style, url) in enumerate(url_candidates):
            is_last_candidate = idx == len(url_candidates) - 1
            saw_response = False
            all_not_found = True
            for key_value in key_candidates:
                for client_id_header in client_id_headers:
                    for header_name in candidate_headers:
                        headers = dict(headers_template)
                        if client_id:
                            headers[client_id_header] = client_id
                        headers[header_name] = key_value
                        try:
                            result = execute_request(
                                url_style,
                                url,
                                headers,
                                header_name,
                                client_id_header if client_id else "",
                            )
                            saw_response = True
                            status = result["status_code"]
                            # Continue trying all configured key/header combinations on auth errors.
                            # Some BASIS environments accept only a specific header or key.
                            if status in (401, 403):
                                last_response = result
                                all_not_found = False
                                continue
                            if status == 404 and not is_last_candidate:
                                last_response = result
                                continue
                            all_not_found = False
                            return result
                        except Exception as ex:
                            last_exc = ex
                            time.sleep(0.3)
            if saw_response and all_not_found and not is_last_candidate:
                continue
        if last_response:
            return last_response
    return {"ok": False, "error": str(last_exc)}

def _validate_billing_account_value(account: str, env: str = "test") -> Dict[str, Any]:
    acct = (account or "").strip()
    env = (env or "test").lower()
    acct_log = _mask_basis_account_for_log(acct)
    if not acct:
        logger.warning("BASIS validation skipped: empty account (env=%s)", env)
        return {"ok": False, "valid": False, "error": "Billing account number is required"}

    if is_basis_account_allowlisted(acct):
        return {
            "ok": True,
            "valid": True,
            "reason": "allowlisted",
            "raw": {"allowlisted": True},
            "matched_in_response": True,
        }

    if env == "prod":
        base_url = os.getenv("BASIS_PROD_URL", BASIS_PROD_URL)
        client_id = os.getenv("BASIS_PROD_CLIENT_ID", BASIS_PROD_CLIENT_ID)
        client_key = os.getenv("BASIS_PROD_KEY", BASIS_PROD_KEY)
    else:
        base_url = os.getenv("BASIS_TEST_URL", BASIS_TEST_URL)
        client_id = os.getenv("BASIS_TEST_CLIENT_ID", BASIS_TEST_CLIENT_ID)
        client_key = os.getenv("BASIS_TEST_KEY", BASIS_TEST_KEY)

    if not base_url:
        logger.warning("BASIS validation unavailable: missing base URL (env=%s account=%s)", env, acct_log)
        return {"ok": False, "valid": False, "error": "Billing validation service URL is not configured"}

    candidate_urls = _build_basis_validate_candidates(base_url, acct)
    request_context_log = (
        f"fiscal_year={_resolve_basis_fiscal_year()}; "
        f"account_query_param={(BASIS_ACCOUNT_QUERY_PARAM or '').strip()}; "
        f"fiscal_year_query_param={(BASIS_FISCAL_YEAR_QUERY_PARAM or '').strip()}; "
        f"configured_path={(BASIS_VALIDATE_PATH or '').strip()}; "
        f"candidate_url_styles={[label for label, _ in candidate_urls]}; "
        f"candidate_urls={[_sanitize_basis_url_for_log(url, acct) for _, url in candidate_urls]}; "
        f"client_id_present={bool(client_id)}; "
        f"preferred_client_id_header={(BASIS_CLIENT_ID_HEADER or '').strip() or 'ClientId'}; "
        f"api_key_count={len(_parse_basis_keys(client_key))}; "
        f"preferred_api_key_header={(BASIS_API_KEY_HEADER or '').strip() or 'ApiKey'}"
    )
    logger.info(
        "BASIS validation started (env=%s account=%s request_context=%s)",
        env,
        acct_log,
        request_context_log,
    )
    res = _call_basis_validate(base_url, client_id, client_key, acct)
    if not res.get("ok"):
        request_error_log = _sanitize_basis_payload_for_log(res.get("error"), acct, max_len=400)
        logger.warning(
            "BASIS validation request failed (env=%s account=%s error=%s request_context=%s)",
            env,
            acct_log,
            request_error_log,
            request_context_log,
        )
        return {"ok": False, "valid": False, "error": res.get("error"), "raw": res.get("data")}

    raw = res.get("data", {})
    valid = None
    reason = ""
    matched_in_response = _basis_response_contains_account(raw, acct)
    status_indicator = _extract_basis_status_indicator(raw)
    status_indicator_details = _get_basis_status_indicator_details(status_indicator)
    confirmed_by_status_indicator = False
    response_indicates_missing_account = False
    payload_summary = _basis_summarize_payload_for_log(raw, acct)
    account_hints = _basis_find_account_hints_for_log(raw, acct)
    payload_summary_log = payload_summary
    account_hints_log = ", ".join(account_hints) if account_hints else "none"

    if isinstance(raw, dict):
        if "valid" in raw:
            valid = bool(raw.get("valid"))
        elif "isValid" in raw:
            valid = bool(raw.get("isValid"))
        elif "status" in raw:
            st = str(raw.get("status")).lower()
            if st in ("valid", "active", "ok", "true"):
                valid = True
            elif st in ("invalid", "notfound", "false", "error"):
                valid = False

        for k in ("message", "reason", "detail", "description"):
            if k in raw:
                reason = str(raw.get(k))
                break

    # Handle BASIS search response format: {"items": [...], "totalRecords": N, ...}
    # Only apply when no explicit valid/isValid/status field was found in the response.
    # A 200 with totalRecords==0 / empty items means the account does not exist.
    if valid is None:
        search_has_results = _basis_search_response_has_results(raw)
        if search_has_results is not None:
            valid = search_has_results
            if not search_has_results and not reason:
                reason = "not_found"

    response_indicates_missing_account = _basis_response_indicates_missing_account(raw, reason)

    sc = res.get("status_code", 0)
    normalized_indicator = str(status_indicator or "").strip()
    if normalized_indicator in BASIS_STATUS_INDICATOR_BLOCK_SET:
        valid = False
    elif normalized_indicator in BASIS_STATUS_INDICATOR_PASS_SET and sc in (200, 201):
        valid = True
    elif normalized_indicator:
        logger.info("BASIS validation returned unrecognized status indicator: %s", normalized_indicator)

    if valid is None:
        if sc in (200, 201):
            valid = True
        elif sc in (404, 422):
            valid = False
        elif 400 <= sc < 500:
            valid = False
        else:
            valid = False

    confirmed_by_status_indicator = bool(status_indicator_details) and sc in (200, 201)

    if sc == 404 and not valid and not matched_in_response and not response_indicates_missing_account:
        logger.warning(
            "BASIS validation endpoint returned 404 (env=%s account=%s url_style=%s url=%s client_header=%s header=%s payload_summary=%s account_hints=%s)",
            env,
            acct_log,
            res.get("url_style") or "",
            _sanitize_basis_url_for_log(res.get("request_url"), acct),
            res.get("used_client_id_header") or "",
            res.get("used_header") or "",
            payload_summary_log,
            account_hints_log,
        )
        return {
            "ok": False,
            "valid": False,
            "error": "Billing validation service is unavailable",
            "reason": "basis_validation_endpoint_not_found",
            "raw": raw,
            "matched_in_response": False,
        }

    if sc in (200, 201) and valid and not matched_in_response and not reason:
        reason = "validation_passed_but_account_not_echoed_in_response"
    elif confirmed_by_status_indicator and not reason:
        reason = "account_confirmed_by_status_indicator"
    elif matched_in_response and not reason:
        reason = "account_found_in_basis_response"

    logger.info(
        "BASIS validation finished (env=%s account=%s status=%s valid=%s matched=%s confirmed_by_status_indicator=%s missing_account_hint=%s reason=%s status_indicator=%s status_indicator_meaning=%s status_indicator_ui_state=%s url_style=%s url=%s client_header=%s header=%s payload_summary=%s account_hints=%s)",
        env,
        acct_log,
        sc,
        bool(valid),
        matched_in_response,
        confirmed_by_status_indicator,
        response_indicates_missing_account,
        reason or "",
        status_indicator or "",
        status_indicator_details.get("meaning", ""),
        status_indicator_details.get("ui_state", ""),
        res.get("url_style") or "",
        _sanitize_basis_url_for_log(res.get("request_url"), acct),
        res.get("used_client_id_header") or "",
        res.get("used_header") or "",
        payload_summary_log,
        account_hints_log,
    )

    return {
        "ok": True,
        "valid": bool(valid),
        "reason": reason,
        "raw": raw,
        "matched_in_response": matched_in_response,
        "confirmed_by_status_indicator": confirmed_by_status_indicator,
        "status_indicator": status_indicator or "",
        "status_indicator_meaning": status_indicator_details.get("meaning", ""),
        "status_indicator_ui_state": status_indicator_details.get("ui_state", ""),
    }

def _extract_billing_account_from_tags(tags: Any) -> str:
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = {}

    if not isinstance(tags, dict):
        return ""

    normalized = {
        str(k).strip().lower(): str(v).strip()
        for k, v in tags.items()
        if v is not None and str(v).strip()
    }
    return (
        normalized.get("accountnumber")
        or normalized.get("account_number")
        or normalized.get("account-number")
        or ""
    )

def _require_valid_billing_account(account: str, env: str = "test") -> Dict[str, Any]:
    result = _validate_billing_account_value(account, env=env)
    if not result.get("ok"):
        error = str(result.get("error") or "validation_failed")
        if error == "Billing account number is required":
            raise HTTPException(status_code=400, detail="Billing account number is required. VM deployment blocked.")
        raise HTTPException(status_code=400, detail=f"Billing account validation failed: {error}. VM deployment blocked.")
    if not result.get("valid"):
        reason = str(result.get("reason") or "Billing account not found")
        raise HTTPException(status_code=400, detail=f"Billing account not found or invalid: {reason}. VM deployment blocked.")
    return result

def _extract_and_validate_billing_account(tags: Any, env: str = "test") -> Dict[str, Any]:
    account = _extract_billing_account_from_tags(tags)
    if not account:
        return {
            "ok": True,
            "valid": True,
            "reason": "no_billing_account_provided",
            "raw": {},
        }
    return _require_valid_billing_account(account, env=env)

ANSI_RE = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
def strip_ansi(s: str) -> str:
    if not s:
        return s
    return ANSI_RE.sub('', s)

# ✅ REMOVED: Hardcoded AMI_MAP - AMIs are now fetched dynamically from AWS accounts

AZURE_SHARED_IMAGE_SUBSCRIPTION_ID = os.getenv("AZURE_SHARED_IMAGE_SUBSCRIPTION_ID", "ef41a7a7-df63-46b8-83ec-a397b194a107")
AZURE_SHARED_IMAGE_RESOURCE_GROUP = os.getenv("AZURE_SHARED_IMAGE_RESOURCE_GROUP", "ISD-eCloud")
AZURE_SHARED_IMAGE_GALLERY = os.getenv("AZURE_SHARED_IMAGE_GALLERY", "eCloud_Images")
AZURE_BAD_REQUEST_CODE = "badrequest"
AZURE_SHARED_IMAGES = [
    {"name": "linux_rhel86", "label": "Linux RHEL 8.6", "os_type": "Linux", "hyper_v_generation": "V2"},
    {"name": "Linux-RHEL-96", "label": "Linux RHEL 9.6", "os_type": "Linux", "hyper_v_generation": "V2"},
    {"name": "Linux-RHEL-10", "label": "Linux RHEL 10", "os_type": "Linux", "hyper_v_generation": "V2"},
    {"name": "Win2k19-Azure-ISD", "label": "Windows Server 2019", "os_type": "Windows", "hyper_v_generation": "V2"},
    {"name": "Win2k22-Azure-ISD", "label": "Windows Server 2022", "os_type": "Windows", "hyper_v_generation": "V2"},
]

ADMIN_EMAILS = [
    "EFlores@isd.lacounty.gov",
    "MSalihue@isd.lacounty.gov",
    "SAttoti@isd.lacounty.gov",
    "BChacko@isd.lacounty.gov",
    "yjin@isd.lacounty.gov",
    "aalmuhajab@isd.lacounty.gov",
    "anavarro.consultant@isd.lacounty.gov",
    "jyang@isd.lacounty.gov",
    "jcanchola@isd.lacounty.gov",
    "kzhang2@isd.lacounty.gov",
    "klake@isd.lacounty.gov",
    "nnguyen@isd.lacounty.gov",
    "raryal@isd.lacounty.gov",
    "ragi.consultant@isd.lacounty.gov",
    "umohammed.consultant@isd.lacounty.gov",
    "ebarbosadasilva.consultant@isd.lacounty.gov",
    "epetrosy@isd.lacounty.gov",
    "hnguyen2@isd.lacounty.gov",
    "tlee2@isd.lacounty.gov",
    "uvydyula@isd.lacounty.gov",
    "hche@isd.lacounty.gov",
    "tpoon@isd.lacounty.gov",
    "esangalang@isd.lacounty.gov",
    "vle@isd.lacounty.gov",
    "aoyewumi.consultant@isd.lacounty.gov",
    "hwong@isd.lacounty.gov",
    "rkolmi@isd.lacounty.gov",
    "ctum@isd.lacounty.gov",
    "dgan@isd.lacounty.gov",
    "elopez3@isd.lacounty.gov",
    "rabrahamian.consultant@isd.lacounty.gov",
    "rkwong2@isd.lacounty.gov",
    "schauhan@isd.lacounty.gov",
    "sshiri@isd.lacounty.gov",
    "smihlar@isd.lacounty.gov",
    "sbuickians@isd.lacounty.gov",
    "wli@isd.lacounty.gov",
    "tchen2@isd.lacounty.gov",
    "cwilliamsjr@isd.lacounty.gov",
    "dsargsyan2@isd.lacounty.gov",
    "fchang@isd.lacounty.gov",
    "gyiu@isd.lacounty.gov",
    "jsuzara@isd.lacounty.gov",
    "ktou@isd.lacounty.gov",
    "mperez2@isd.lacounty.gov",
    "nchea@isd.lacounty.gov",
    "phuon@isd.lacounty.gov",
    "rparker@isd.lacounty.gov",
    "axu@isd.lacounty.gov",
    "acheng@isd.lacounty.gov",
    "dsuh@isd.lacounty.gov",
    "halmuhajab@isd.lacounty.gov",
    "fpuyatjr@isd.lacounty.gov",
    "jaguiling@isd.lacounty.gov",
    "msudarshanam@isd.lacounty.gov",
    "mdelarosa@isd.lacounty.gov",
    "msudarshanam@isd.lacounty.gov",
    "cchang@isd.lacounty.gov",
    "sperez3@isd.lacounty.gov",
    "achung@isd.lacounty.gov",
    "mgonzalez2@isd.lacounty.gov",
    "mle2@isd.lacounty.gov",
    "rlanzuela@isd.lacounty.gov",
    "wgan@isd.lacounty.gov"
]

ALLOWED_AWS_ACCOUNTS = [
    {"account_id": "792294445508", "account_name": "Animal Care"},
    {"account_id": "919672611458", "account_name": "APD-AWS1"},
    {"account_id": "443914036196", "account_name": "Assessor"},
    {"account_id": "332070355516", "account_name": "Audit"},
    {"account_id": "761763126862", "account_name": "AWS CONNECT"},
    {"account_id": "280928810037", "account_name": "AWS Connect - CleanLA"},
    {"account_id": "533267447517", "account_name": "AWS_CEO-Mimi"},
    {"account_id": "011528284338", "account_name": "AWS-AAB_CONNECT-DEV"},
    {"account_id": "017820666232", "account_name": "AWS-AAB_CONNECT-PROD"},
    {"account_id": "017820666235", "account_name": "AWS-AAB_CONNECT-TEST"},
    {"account_id": "058264242063", "account_name": "AWS-ASESSOR_DEV"},
    {"account_id": "533266964199", "account_name": "AWS-ASESSOR_PROD"},
    {"account_id": "339713154018", "account_name": "AWS-ASESSOR_TEST"},
    {"account_id": "589636153376", "account_name": "AWS-ASESSOR_Veeam"},
    {"account_id": "888577053709", "account_name": "AWS-AUDITOR_CONNECT-DEV"},
    {"account_id": "221082201026", "account_name": "AWS-AUDITOR_CONNECT-PROD"},
    {"account_id": "061039762682", "account_name": "AWS-AUDITOR_CONNECT-TEST"},
    {"account_id": "905418462075", "account_name": "AWS-CaaS_Rancher_Production"},
    {"account_id": "149536492733", "account_name": "AWS-ECRC_CONNECT-DEV"},
    {"account_id": "820242947574", "account_name": "AWS-ECRC_CONNECT-PROD"},
    {"account_id": "607104513569", "account_name": "AWS-FIRE-DEV"},
    {"account_id": "221082194031", "account_name": "AWS-FIRE-PROD"},
    {"account_id": "932757390505", "account_name": "AWS-IRSD_BeOn"},
    {"account_id": "686255971863", "account_name": "AWS-ISD-CGO_CSA_IR"},
    {"account_id": "992382632216", "account_name": "AWS-Monitoring"},
    {"account_id": "971334862800", "account_name": "AWS-PaloAlto-Ingress"},
    {"account_id": "960881837580", "account_name": "AWS-PubLib-MediaArchive"},
    {"account_id": "730335175640", "account_name": "AWS-PUBLIC_DEFENDER _CONNECT-PROD"},
    {"account_id": "905418230151", "account_name": "AWS-PUBLIC_DEFENDER_CONNECT-DEV"},
    {"account_id": "654654420792", "account_name": "AWS-PUBLIC_DEFENDER_CONNECT-TEST"},
    {"account_id": "728394805904", "account_name": "AWS-PW_DISPATCH_CONNECT"},
    {"account_id": "637423425224", "account_name": "AWS-RRCC_DW_ELECTION-POC"},
    {"account_id": "412116382044", "account_name": "AWS-SECURITY_PaloAltoPOC"},
    {"account_id": "347363593519", "account_name": "AWS-SECURITY_PaloAltoPROD"},
    {"account_id": "783764586537", "account_name": "AWS-TD_OSS_LPS"},
    {"account_id": "137068222216", "account_name": "AWS-TDEIS-TEST"},
    {"account_id": "340752794809", "account_name": "AWS-TREASURY_TAX"},
    {"account_id": "730335308135", "account_name": "AWS-TREASURY_TAX _CONNECT-PROD"},
    {"account_id": "339712831907", "account_name": "AWS-TREASURY_TAX_CONNECT-DEV"},
    {"account_id": "851725198835", "account_name": "AWS-TREASURY_TAX_CONNECT-TEST"},
    {"account_id": "621476030081", "account_name": "CaaS ECM EKS Project"},
    {"account_id": "942917258976", "account_name": "CaaS-Rancher-Non-prod"},
    {"account_id": "321391860655", "account_name": "CED-ESE"},
    {"account_id": "482153932133", "account_name": "Consumer & Business Affairs"},
    {"account_id": "005595088033", "account_name": "Coroner"},
    {"account_id": "526648353896", "account_name": "County of Los Angeles, DPSS"},
    {"account_id": "069872218693", "account_name": "DCFS"},
    {"account_id": "872017552827", "account_name": "DCFS Dev"},
    {"account_id": "014085571870", "account_name": "DEO AWS"},
    {"account_id": "059659026606", "account_name": "DHS_AWS_Enterprise"},
    {"account_id": "527399475385", "account_name": "DHS_Private_5G_Dev"},
    {"account_id": "562401457670", "account_name": "DHS-VMC"},
    {"account_id": "509807155577", "account_name": "District Attorney"},
    {"account_id": "077973199198", "account_name": "District_Attorney-AWS_Connect"},
    {"account_id": "619375803757", "account_name": "DLT LA County"},
    {"account_id": "472110193540", "account_name": "DPSS"},
    {"account_id": "487836127787", "account_name": "DPSS ITD Network Management"},
    {"account_id": "013637809067", "account_name": "DPSS-AWS-Connect"},
    {"account_id": "351451326486", "account_name": "eGIS_ArcGIS_Enterprise"},
    {"account_id": "914286927211", "account_name": "ENTERPRISE AUDITING"},
    {"account_id": "754405460525", "account_name": "ENTERPRISE INFRASTRUCTURE"},
    {"account_id": "590075511264", "account_name": "ENTERPRISE NETWORKING"},
    {"account_id": "060127551817", "account_name": "ENTERPRISE SECURITY"},
    {"account_id": "487954424959", "account_name": "GIS_Cloud_Platform"},
    {"account_id": "653674545758", "account_name": "Human Resources"},
    {"account_id": "404142233", "account_name": "IDD GIS Caltrap"},
    {"account_id": "398284229904", "account_name": "IDD Websites"},
    {"account_id": "330217625594", "account_name": "ISAB"},
    {"account_id": "168395994234", "account_name": "ISD GGSD"},
    {"account_id": "023800203545", "account_name": "ISD IDD"},
    {"account_id": "451808593858", "account_name": "ISD IDD Managed"},
    {"account_id": "549344408264", "account_name": "ISD MCD"},
    {"account_id": "242013862987", "account_name": "ISD Openshift"},
    {"account_id": "196049140327", "account_name": "ISD Secure Access Engineering"},
    {"account_id": "600198011871", "account_name": "ISD TD eCloud"},
    {"account_id": "025217829020", "account_name": "ISD Telecom"},
    {"account_id": "598041321384", "account_name": "ISD-CAB"},
    {"account_id": "743524583132", "account_name": "ISD-GGSD-ISDHR"},
    {"account_id": "564310997153", "account_name": "ISD-ITS-CAB-GGSD-Data-Management"},
    {"account_id": "476553995083", "account_name": "ISD-SSB-CSI"},
    {"account_id": "021335304183", "account_name": "ITSS AppStream"},
    {"account_id": "693718126367", "account_name": "ITSS_Share"},
    {"account_id": "211125782991", "account_name": "lac-abc-primary"},
    {"account_id": "318500746392", "account_name": "LACERA"},
    {"account_id": "428780238092", "account_name": "LACERA_Dev"},
    {"account_id": "081468143510", "account_name": "LACJCOD_SUB_AWS"},
    {"account_id": "536874876417", "account_name": "LACounty Diversion"},
    {"account_id": "365643788452", "account_name": "LACountyISD_Workspaces"},
    {"account_id": "192752785889", "account_name": "LAISD - Backup Storage"},
    {"account_id": "964116004563", "account_name": "Library"},
    {"account_id": "514044800693", "account_name": "Log archive"},
    {"account_id": "061499950385", "account_name": "magostinelliWDACS"},
    {"account_id": "726203495796", "account_name": "Mainframe_VTS"},
    {"account_id": "682625837619", "account_name": "Military_and_Veterans_Affairs"},
    {"account_id": "906514578947", "account_name": "Planning"},
    {"account_id": "750294788650", "account_name": "Probation"},
    {"account_id": "283661260993", "account_name": "PUBLIC DEFENDER"},
    {"account_id": "013611718990", "account_name": "Public Defender IT Agency"},
    {"account_id": "743309932854", "account_name": "Public Health"},
    {"account_id": "030708491905", "account_name": "Public Health - Pinpoint"},
    {"account_id": "789082305884", "account_name": "PUBLIC INFRASTRUCTURE SERVICES"},
    {"account_id": "875510801412", "account_name": "PUBLIC SERVICES POC"},
    {"account_id": "559265186679", "account_name": "PUBLIC WORKS"},
    {"account_id": "762576794010", "account_name": "RRCC - AWS Connect"},
    {"account_id": "632732354594", "account_name": "RRCC - AWS Connect Elections"},
    {"account_id": "328705060255", "account_name": "RRCC - LAVOTE ELECTION RESULTS"},
    {"account_id": "742156547861", "account_name": "RRCC_DEV_TEST"},
    {"account_id": "150197995471", "account_name": "RRCC-ACGR"},
    {"account_id": "062006678460", "account_name": "RRCC-AWS-S3"},
    {"account_id": "429686675059", "account_name": "SharedServices"},
    {"account_id": "992557151693", "account_name": "SSB EGIS CAMS"},
    {"account_id": "534978226835", "account_name": "SSB-EGIS"},
    {"account_id": "353922334669", "account_name": "AWS-DCFS-Oracle"},
    {"account_id": "245805261858", "account_name": "AWS-DMZ-Web-test-1"},
    {"account_id": "228656903909", "account_name": "AWS-RRCC_VSD_SANDBOX"},
    {"account_id": "897768183437", "account_name": "AWS-RRCC_ADMIN_SANDBOX"},
    {"account_id": "617973292335", "account_name": "AWS-DPW-PROJECT_SANDBOX"}
]

# Pre-computed id→name map for O(1) lookups (ALLOWED_AWS_ACCOUNTS is static)
_ALLOWED_AWS_MAP: Dict[str, str] = {a["account_id"]: a["account_name"] for a in ALLOWED_AWS_ACCOUNTS}
# Pre-computed name→id map (lowercase key) for registration name lookup
_ALLOWED_AWS_NAME_MAP: Dict[str, str] = {a["account_name"].lower(): a["account_id"] for a in ALLOWED_AWS_ACCOUNTS}

# On-demand Linux hourly pricing (USD) for common EC2 instance types (us-east-1 reference price).
# Used as a best-effort estimate; actual costs depend on region and negotiated rates.
_AWS_INSTANCE_PRICING: Dict[str, float] = {
    "t2.nano": 0.0058, "t2.micro": 0.0116, "t2.small": 0.023, "t2.medium": 0.0464,
    "t2.large": 0.0928, "t2.xlarge": 0.1856, "t2.2xlarge": 0.3712,
    "t3.nano": 0.0052, "t3.micro": 0.0104, "t3.small": 0.0208, "t3.medium": 0.0416,
    "t3.large": 0.0832, "t3.xlarge": 0.1664, "t3.2xlarge": 0.3328,
    "t3a.nano": 0.0047, "t3a.micro": 0.0094, "t3a.small": 0.0188, "t3a.medium": 0.0376,
    "t3a.large": 0.0752, "t3a.xlarge": 0.1504, "t3a.2xlarge": 0.3008,
    "m5.large": 0.096, "m5.xlarge": 0.192, "m5.2xlarge": 0.384, "m5.4xlarge": 0.768,
    "m5.8xlarge": 1.536, "m5.12xlarge": 2.304, "m5.16xlarge": 3.072, "m5.24xlarge": 4.608,
    "m5a.large": 0.086, "m5a.xlarge": 0.172, "m5a.2xlarge": 0.344, "m5a.4xlarge": 0.688,
    "m6i.large": 0.096, "m6i.xlarge": 0.192, "m6i.2xlarge": 0.384, "m6i.4xlarge": 0.768,
    "m6i.8xlarge": 1.536, "m6i.12xlarge": 2.304, "m6i.16xlarge": 3.072, "m6i.24xlarge": 4.608,
    "m6a.large": 0.0864, "m6a.xlarge": 0.1728, "m6a.2xlarge": 0.3456, "m6a.4xlarge": 0.6912,
    "c3.large": 0.105, "c3.xlarge": 0.21, "c3.2xlarge": 0.42, "c3.4xlarge": 0.84, "c3.8xlarge": 1.68,
    "c4.large": 0.1, "c4.xlarge": 0.199, "c4.2xlarge": 0.398, "c4.4xlarge": 0.796, "c4.8xlarge": 1.591,
    "c5.large": 0.085, "c5.xlarge": 0.17, "c5.2xlarge": 0.34, "c5.4xlarge": 0.68,
    "c5.9xlarge": 1.53, "c5.12xlarge": 2.04, "c5.18xlarge": 3.06, "c5.24xlarge": 4.08, "c5.metal": 4.08,
    "c5a.large": 0.077, "c5a.xlarge": 0.154, "c5a.2xlarge": 0.308, "c5a.4xlarge": 0.616,
    "c5a.8xlarge": 1.232, "c5a.12xlarge": 1.848, "c5a.16xlarge": 2.464, "c5a.24xlarge": 3.696,
    "c6i.large": 0.085, "c6i.xlarge": 0.17, "c6i.2xlarge": 0.34, "c6i.4xlarge": 0.68,
    "c6a.large": 0.0765, "c6a.xlarge": 0.153, "c6a.2xlarge": 0.306, "c6a.4xlarge": 0.612,
    "r5.large": 0.126, "r5.xlarge": 0.252, "r5.2xlarge": 0.504, "r5.4xlarge": 1.008,
    "r5.8xlarge": 2.016, "r5.12xlarge": 3.024, "r5.16xlarge": 4.032, "r5.24xlarge": 6.048,
    "r6i.large": 0.126, "r6i.xlarge": 0.252, "r6i.2xlarge": 0.504, "r6i.4xlarge": 1.008,
    "r6a.large": 0.1134, "r6a.xlarge": 0.2268, "r6a.2xlarge": 0.4536, "r6a.4xlarge": 0.9072,
    "p3.2xlarge": 3.06, "p3.8xlarge": 12.24, "p3.16xlarge": 24.48,
    "p4d.24xlarge": 32.7726,
    "g4dn.xlarge": 0.526, "g4dn.2xlarge": 0.752, "g4dn.4xlarge": 1.204, "g4dn.8xlarge": 2.264,
    "i3.large": 0.156, "i3.xlarge": 0.312, "i3.2xlarge": 0.624, "i3.4xlarge": 1.248,
    "i3en.large": 0.226, "i3en.xlarge": 0.452, "i3en.2xlarge": 0.904, "i3en.3xlarge": 1.356,
}

# Live AWS EC2 pricing cache - populated in a background thread at server startup.
# When populated it takes precedence over the static _AWS_INSTANCE_PRICING table above.
_aws_pricing_live: Dict[str, float] = {}


def _load_aws_pricing_background() -> None:
    """Fetch live on-demand Linux EC2 pricing (us-east-1) from the public AWS
    Bulk Pricing endpoint (no authentication required). Runs once in a background
    thread at server startup so it never blocks request handling.

    The AWS CSV has ~5 metadata rows before the real column-header row.  We scan
    for the header row that contains both "Instance Type" and "PricePerUnit" and
    then use the standard csv.DictReader to extract only the rows that represent:
      TermType=OnDemand, Operating System=Linux, Tenancy=Shared,
      Pre Installed S/W=NA, Unit=Hrs.

    On success, _aws_pricing_live is populated and _get_aws_instance_price()
    returns live prices. On any failure the static _AWS_INSTANCE_PRICING table
    continues to be used unchanged.
    """
    _AWS_PRICING_FETCH_TIMEOUT = 120   # seconds to wait for the pricing CSV download
    _AWS_HEADER_SCAN_ROWS = 10         # max metadata rows to scan before the real header

    global _aws_pricing_live
    url = (
        "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/"
        "AmazonEC2/current/us-east-1/index.csv"
    )
    try:
        logger.info("Loading live AWS EC2 pricing from %s", url)
        resp = requests.get(url, timeout=_AWS_PRICING_FETCH_TIMEOUT)
        resp.raise_for_status()
        lines = resp.text.splitlines()
        # Find the real header row (contains both landmark column names).
        header_idx: Optional[int] = None
        for i, line in enumerate(lines[:_AWS_HEADER_SCAN_ROWS]):
            if "Instance Type" in line and "PricePerUnit" in line:
                header_idx = i
                break
        if header_idx is None:
            logger.warning("AWS EC2 pricing CSV: header row not found; using static table")
            return
        reader = csv.DictReader(lines[header_idx:])
        pricing: Dict[str, float] = {}
        for row in reader:
            if (
                row.get("TermType", "").strip() == "OnDemand"
                and row.get("Operating System", "").strip() == "Linux"
                and row.get("Tenancy", "").strip() == "Shared"
                and row.get("Pre Installed S/W", "").strip() == "NA"
                and row.get("Unit", "").strip() == "Hrs"
            ):
                itype = row.get("Instance Type", "").strip().strip('"')
                price_str = row.get("PricePerUnit", "0").strip().strip('"')
                if itype and price_str:
                    try:
                        price = float(price_str)
                        if price > 0:
                            pricing[itype] = price
                    except ValueError:
                        pass
        if pricing:
            _aws_pricing_live = pricing
            logger.info(
                "Live AWS EC2 pricing loaded: %d instance types (us-east-1 reference)",
                len(pricing),
            )
        else:
            logger.warning("AWS EC2 pricing CSV yielded no entries; using static table")
    except Exception as exc:
        logger.warning(
            "Live AWS EC2 pricing fetch failed (static table remains active): %s", exc
        )


def _get_aws_instance_price(instance_type: str) -> Optional[float]:
    """Return the best available on-demand Linux price/hr for *instance_type*.

    Checks the live cache (populated at startup from the AWS Bulk Pricing API)
    first; falls back to the static _AWS_INSTANCE_PRICING table when the live
    cache has not yet been loaded or does not contain the requested type.
    """
    price = _aws_pricing_live.get(instance_type)
    return price if price is not None else _AWS_INSTANCE_PRICING.get(instance_type)


# ── Azure supported VM sizes (hardcoded curated list) ─────────────────────────
# Only sizes in this list are shown to users. Add or remove entries here to
# control which sizes are offered in the portal. Each entry: (name, vCPUs, memoryInMB).
# All entries are Gen2-compatible x64 sizes suitable for RHEL/Windows images.
AZURE_SUPPORTED_VM_SIZES: List[tuple] = [
    # Burstable B-series
    ("Standard_B2s",    2,  4096),
    ("Standard_B2ms",   2,  8192),
    ("Standard_B4ms",   4, 16384),
    ("Standard_B8ms",   8, 32768),
    # General Purpose D-series v3
    ("Standard_D2s_v3",  2,   8192),
    ("Standard_D4s_v3",  4,  16384),
    ("Standard_D8s_v3",  8,  32768),
    ("Standard_D16s_v3", 16,  65536),
    ("Standard_D32s_v3", 32, 131072),
    ("Standard_D64s_v3", 64, 262144),
    # General Purpose D-series v4 Intel
    ("Standard_D2s_v4",  2,   8192),
    ("Standard_D4s_v4",  4,  16384),
    ("Standard_D8s_v4",  8,  32768),
    ("Standard_D16s_v4", 16,  65536),
    ("Standard_D32s_v4", 32, 131072),
    # General Purpose D-series v4 AMD
    ("Standard_D2as_v4",  2,   8192),
    ("Standard_D4as_v4",  4,  16384),
    ("Standard_D8as_v4",  8,  32768),
    ("Standard_D16as_v4", 16,  65536),
    ("Standard_D32as_v4", 32, 131072),
    ("Standard_D64as_v4", 64, 262144),
    # General Purpose D-series v5 Intel
    ("Standard_D2s_v5",  2,   8192),
    ("Standard_D4s_v5",  4,  16384),
    ("Standard_D8s_v5",  8,  32768),
    ("Standard_D16s_v5", 16,  65536),
    ("Standard_D32s_v5", 32, 131072),
    # General Purpose D-series v5 AMD
    ("Standard_D2as_v5",  2,   8192),
    ("Standard_D4as_v5",  4,  16384),
    ("Standard_D8as_v5",  8,  32768),
    ("Standard_D16as_v5", 16,  65536),
    ("Standard_D32as_v5", 32, 131072),
    ("Standard_D64as_v5", 64, 262144),
    # Memory Optimized E-series v3
    ("Standard_E2s_v3",  2,   16384),
    ("Standard_E4s_v3",  4,   32768),
    ("Standard_E8s_v3",  8,   65536),
    ("Standard_E16s_v3", 16, 131072),
    ("Standard_E32s_v3", 32, 262144),
    # Memory Optimized E-series v4 AMD
    ("Standard_E2as_v4",  2,   16384),
    ("Standard_E4as_v4",  4,   32768),
    ("Standard_E8as_v4",  8,   65536),
    ("Standard_E16as_v4", 16, 131072),
    ("Standard_E32as_v4", 32, 262144),
    # Memory Optimized E-series v5 AMD
    ("Standard_E2as_v5",  2,   16384),
    ("Standard_E4as_v5",  4,   32768),
    ("Standard_E8as_v5",  8,   65536),
    ("Standard_E16as_v5", 16, 131072),
    ("Standard_E32as_v5", 32, 262144),
    # Compute Optimized F-series v2
    ("Standard_F2s_v2",  2,  4096),
    ("Standard_F4s_v2",  4,  8192),
    ("Standard_F8s_v2",  8, 16384),
    ("Standard_F16s_v2", 16, 32768),
    ("Standard_F32s_v2", 32, 65536),
]
# Quick name→(vcpus, memoryInMB) lookup
_AZURE_SUPPORTED_SIZES_MAP: Dict[str, tuple] = {
    name: (vcpus, mem) for name, vcpus, mem in AZURE_SUPPORTED_VM_SIZES
}

# In-memory cache for Azure VM pricing keyed by location (lower-case).
# Each entry is a dict of {sku_name_lower: price_per_hour}.
_azure_pricing_cache: Dict[str, Dict[str, float]] = {}

def _get_azure_vm_pricing(location: str) -> Dict[str, float]:
    """
    Fetch on-demand Linux VM pricing for a given Azure region from the public
    Azure Retail Prices API. Results are cached in-memory per location.
    Returns a dict keyed by lower-case SKU name (e.g. 'd2 v3') → price/hr USD.
    """
    key = location.lower()
    if key in _azure_pricing_cache:
        return _azure_pricing_cache[key]
    pricing: Dict[str, float] = {}
    try:
        url = (
            "https://prices.azure.com/api/retail/prices"
            f"?$filter=serviceName eq 'Virtual Machines'"
            f" and armRegionName eq '{key}'"
            f" and priceType eq 'Consumption'"
            f" and type eq 'Consumption'"
        )
        # Paginate up to 10 pages (each page has up to 100 items → up to 1000 entries).
        # Results are cached per region so this only runs once per location per process lifetime.
        max_pages = 10
        page_count = 0
        while url and page_count < max_pages:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("Items", []):
                sku = (item.get("skuName") or "").lower()
                product = (item.get("productName") or "").lower()
                # Keep only Linux (no Windows, no Spot, no Low Priority)
                if "windows" in product:
                    continue
                if "spot" in sku or "low priority" in sku:
                    continue
                price = item.get("retailPrice") or item.get("unitPrice") or 0.0
                if sku and price > 0 and sku not in pricing:
                    pricing[sku] = price
            url = data.get("NextPageLink") or data.get("nextPageLink")
            page_count += 1
    except Exception as e:
        logger.warning("Azure VM pricing fetch failed for %s: %s", location, e)
    _azure_pricing_cache[key] = pricing
    return pricing

def _azure_size_to_sku(vm_size: str) -> str:
    """
    Convert an Azure VM size name (e.g. 'Standard_D2_v3') to the pricing API
    SKU name format (e.g. 'd2 v3') used in the Retail Prices API response.
    """
    for prefix in ("Standard_", "Basic_", "SQLDEV_", "SQLENTR_", "SQLSTD_", "SQLWEB_"):
        if vm_size.startswith(prefix):
            return vm_size[len(prefix):].replace("_", " ").lower()
    return vm_size.replace("_", " ").lower()

def decode_jwt_no_verify(token: str) -> Dict[str, Any]:
    try:
        parts = token.split('.')
        if len(parts) < 2:
            return {}
        payload_b64 = parts[1]
        padding = '=' * (-len(payload_b64) % 4)
        payload_b64 += padding
        payload_bytes = base64.urlsafe_b64decode(payload_b64.encode('utf-8'))
        payload = json.loads(payload_bytes.decode('utf-8'))
        return payload
    except Exception as e:
        logger.debug("Failed to decode JWT: %s", e)
        return {}

def get_easyauth_access_token(request: Request) -> Optional[str]:
    return request.headers.get("X-MS-TOKEN-AAD-ACCESS-TOKEN") or request.headers.get("X-MS-TOKEN-AAD-ID-TOKEN")

def get_easyauth_client_principal(request: Request) -> Optional[Dict[str, Any]]:
    raw = request.headers.get("X-MS-CLIENT-PRINCIPAL")
    if not raw:
        return None
    try:
        decoded = base64.b64decode(raw).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        try:
            return json.loads(raw)
        except Exception:
            logger.debug("Could not decode X-MS-CLIENT-PRINCIPAL header")
            return None

def _extract_from_token_claims(claims: Dict[str, Any]) -> Dict[str, Any]:
    email = claims.get("preferred_username") or claims.get("upn") or claims.get("email") or None
    oid = claims.get("oid") or claims.get("objectId") or claims.get("sub") or None
    if isinstance(email, list) and email:
        email = email[0]
    return {"email": email, "oid": oid}

def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    cp = get_easyauth_client_principal(request)
    if cp:
        email = cp.get("userDetails") or None
        oid = None
        claims = cp.get("claims") or cp.get("user_claims") or []
        if isinstance(claims, list):
            for c in claims:
                typ = c.get("typ") or c.get("type") or ""
                val = c.get("val") or c.get("value") or c.get("v")
                if not oid and ("oid" in typ or typ.endswith("/oid") or "objectidentifier" in typ):
                    oid = val
                if not email and ("preferred_username" in typ or typ.endswith("/preferred_username") or "upn" in typ or "email" in typ):
                    email = val
        elif isinstance(claims, dict):
            email = email or (claims.get("preferred_username") or claims.get("upn") or claims.get("email"))
            oid = oid or (claims.get("oid") or claims.get("objectId"))
        if oid or email:
            return {"email": email, "oid": oid}
    token = get_easyauth_access_token(request)
    if token:
        try:
            claims = decode_jwt_no_verify(token)
            extracted = _extract_from_token_claims(claims)
            if extracted.get("email") or extracted.get("oid"):
                return {"email": extracted.get("email"), "oid": extracted.get("oid")}
        except Exception as e:
            logger.debug("Failed to decode AAD token from headers: %s", e)
    session_user = request.session.get("user") if hasattr(request, "session") else None
    if session_user:
        return session_user
    return None

def is_admin(user: Optional[Dict[str, Any]]) -> bool:
    if not user:
        return False
    email = (user.get("email") or "").lower()
    if not email:
        return False
    # DB-backed check: query portal.portal_admins (status = 'Active')
    if DB_AVAILABLE and is_admin_by_email:
        try:
            if is_admin_by_email(email):
                return True
        except Exception as e:
            logger.warning("DB is_admin_by_email check failed, falling back to ADMIN_EMAILS list: %s", e)
    # Fallback: hardcoded list (used when DB is unavailable or query fails)
    return email in [a.lower() for a in ADMIN_EMAILS]


def _audit(
    request: Request,
    action_type: str,
    cloud_provider: str,
    resource_name: str = None,
    resource_id: str = None,
    account_or_subscription: str = None,
    region_or_zone: str = None,
    detail: str = None,
    status: str = "success",
    error_message: str = None,
) -> None:
    """
    Fire-and-forget wrapper that writes one row to portal.vm_action_audit.
    Silently skips when DB logging is unavailable.
    """
    if not DB_AVAILABLE or not log_vm_action:
        return
    user = get_current_user(request)
    email = (user.get("email") if user else None)
    oid = (user.get("oid") if user else None)
    try:
        log_vm_action(
            action_type=action_type,
            cloud_provider=cloud_provider,
            resource_name=resource_name,
            resource_id=resource_id,
            account_or_subscription=account_or_subscription,
            region_or_zone=region_or_zone,
            detail=detail,
            performed_by_email=email,
            performed_by_oid=oid,
            status=status,
            error_message=error_message,
        )
    except Exception as exc:
        logger.warning("_audit: unexpected error writing audit row: %s", exc)

def get_azure_credentials_service_principal() -> ClientSecretCredential:
    """Get Azure service principal credentials."""
    if not (TENANT_ID and CLIENT_ID and CLIENT_SECRET):
        raise RuntimeError("Azure service principal credentials not set in environment variables.")
    return ClientSecretCredential(tenant_id=TENANT_ID, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)

def get_azure_credentials() -> Any:
    """Get Azure credentials (DefaultAzureCredential or ClientSecretCredential)."""
    try:
        cred = DefaultAzureCredential()
        try:
            _ = cred.get_token("https://management.azure.com/.default")
            logger.debug("Using DefaultAzureCredential for Azure calls")
            return cred
        except Exception as e:
            logger.debug("DefaultAzureCredential not usable: %s", e)
    except Exception as e:
        logger.debug("DefaultAzureCredential construction failed: %s", e)

    if TENANT_ID and CLIENT_ID and CLIENT_SECRET:
        try:
            cred = ClientSecretCredential(tenant_id=TENANT_ID, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
            try:
                _ = cred.get_token("https://management.azure.com/.default")
                logger.debug("Using ClientSecretCredential for Azure calls")
                return cred
            except Exception as e:
                logger.error("ClientSecretCredential token acquisition failed: %s", e)
                raise RuntimeError("ClientSecretCredential token acquisition failed: " + str(e))
        except Exception as e:
            logger.exception("Failed to create ClientSecretCredential: %s", e)
            raise RuntimeError("Failed to create ClientSecretCredential: " + str(e))

    raise RuntimeError("No usable Azure credentials found.")

def get_graph_app_token() -> Optional[str]:
    if not (TENANT_ID and CLIENT_ID and CLIENT_SECRET):
        logger.debug("Graph app token requested but no client creds configured")
        return None
    token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "scope": "https://graph.microsoft.com/.default", "grant_type": "client_credentials"}
    try:
        r = requests.post(token_url, data=data, timeout=10)
        r.raise_for_status()
        return r.json().get("access_token")
    except Exception as e:
        logger.exception("Failed to obtain Graph app token: %s", e)
        return None

SP_SUBS_CACHE_TTL = int(os.getenv("SP_SUBS_CACHE_TTL", "300"))
USER_SUBS_CACHE_TTL = int(os.getenv("USER_SUBS_CACHE_TTL", "180"))
SUBS_RG_CACHE_TTL = int(os.getenv("SUBS_RG_CACHE_TTL", "120"))

sp_subs_cache = TTLCache(maxsize=1, ttl=SP_SUBS_CACHE_TTL)
user_subs_cache = TTLCache(maxsize=5000, ttl=USER_SUBS_CACHE_TTL)
subs_rg_cache = TTLCache(maxsize=2000, ttl=SUBS_RG_CACHE_TTL)
user_groups_cache = TTLCache(maxsize=5000, ttl=USER_SUBS_CACHE_TTL)

# Cache AWS instance types per region for 10 minutes to avoid repeated describe_instance_types
# calls that exhaust the boto3 connection pool.
_aws_instance_types_cache: TTLCache = TTLCache(maxsize=50, ttl=600)
_aws_instance_types_lock = threading.Lock()

@cached(user_groups_cache)
def get_user_groups_graph_app(user_oid: str) -> List[Dict[str, str]]:
    if not user_oid:
        return []
    token = get_graph_app_token()
    if not token:
        logger.debug("No graph token available for group lookup")
        return []
    url = f"https://graph.microsoft.com/v1.0/users/{user_oid}/memberOf?$select=id,displayName"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            logger.warning("Graph group lookup returned %s: %s", resp.status_code, resp.text)
            return []
        groups = []
        for g in resp.json().get("value", []):
            display_name = g.get("displayName")
            object_id = g.get("id")
            if display_name and object_id:
                groups.append({"name": display_name, "id": object_id})
        return groups
    except Exception as e:
        logger.exception("Error fetching user groups from Graph: %s", e)
        return []

def extract_department_from_email(email: str) -> Optional[str]:
    """
    Extract the department name from a lacounty.gov email address.

    Examples:
      'ADahbashi@dhs.lacounty.gov'    -> 'dhs'
      'CLANZA@auditor.lacounty.gov'   -> 'auditor'
      'JHatami@ceo.lacounty.gov'      -> 'ceo'
      'EFlores@isd.lacounty.gov'      -> 'isd'

    Returns None if the email does not follow the
    <user>@<department>.lacounty.gov pattern.
    """
    if not email:
        return None
    try:
        parts = email.split("@", 1)
        if len(parts) < 2:
            return None
        domain = parts[1].lower()
        domain_parts = domain.split(".")
        # Expect at least: <department>.lacounty.gov  (3 parts)
        if len(domain_parts) >= 3 and domain_parts[-2] == "lacounty" and domain_parts[-1] == "gov":
            return domain_parts[-3]
    except Exception:
        pass
    return None


def parse_subscription_ids_from_scope(scope: str) -> Optional[str]:
    try:
        parts = scope.split("/")
        for i, p in enumerate(parts):
            if p.lower() == "subscriptions" and i + 1 < len(parts):
                return parts[i + 1]
    except Exception:
        pass
    return None

def _get_user_subscription_ids_from_tenant(user_oid: str) -> Set[str]:
    if not user_oid:
        return set()
    try:
        creds = get_azure_credentials()
        arm_token = creds.get_token("https://management.azure.com/.default").token
    except Exception as e:
        logger.exception("Could not acquire ARM token via credential: %s", e)
        return set()
    mg_scope = f"/providers/Microsoft.Management/managementGroups/{TENANT_ID}"
    base_url = f"https://management.azure.com{mg_scope}/providers/Microsoft.Authorization/roleAssignments"
    api_version = "2022-04-01"
    headers = {"Authorization": f"Bearer {arm_token}"}
    def fetch_for_principal(principal_id: str) -> Set[str]:
        subs: Set[str] = set()
        url = f"{base_url}?api-version={api_version}&$filter=principalId eq '{principal_id}'"
        while url:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                logger.warning("ARM roleAssignments query failed (%s): %s", resp.status_code, resp.text)
                return set()
            payload = resp.json()
            for item in payload.get("value", []):
                scope = (item.get("properties", {}) or {}).get("scope", "") or ""
                sid = parse_subscription_ids_from_scope(scope)
                if sid:
                    subs.add(sid)
            url = payload.get("nextLink")
        return subs
    subs = fetch_for_principal(user_oid)
    for g in get_user_groups_graph_app(user_oid):
        gid = g.get("id")
        if gid:
            subs |= fetch_for_principal(gid)
    return subs

@cached(user_subs_cache)
def get_user_subscription_ids_cached(user_oid: str) -> Set[str]:
    return _get_user_subscription_ids_from_tenant(user_oid)

def get_aws_accounts_for_user(user: Dict[str, Any]) -> List[Dict[str, Any]]:
    if is_admin(user):
        return ALLOWED_AWS_ACCOUNTS
    email = (user or {}).get("email", "")
    # Department-based path: look up accounts pre-loaded for the user's department
    if email and DB_AVAILABLE and get_resources_by_department:
        department = extract_department_from_email(email)
        if department:
            try:
                dept_rows = get_resources_by_department(department, "aws")
                if dept_rows:
                    return [
                        {
                            "account_id": r["subscription_id"],
                            "account_name": r.get("subscription_name") or r["subscription_id"]
                        }
                        for r in dept_rows if r.get("subscription_id")
                    ]
            except Exception as e:
                logger.warning("DB get_aws_accounts_for_user (dept) failed for %s: %s", email, e)
    # SSO path (fallback when DB is unavailable)
    user_oid = (user or {}).get("oid")
    if not user_oid:
        logger.debug("Missing user OID for AWS mapping")
        return []
    if not AWS_SSO_INSTANCE_ARN:
        logger.debug("AWS_SSO_INSTANCE_ARN not configured")
        return []
    sso_admin = boto3.client("sso-admin")
    accounts = []
    try:
        resp = sso_admin.list_account_assignments(InstanceArn=AWS_SSO_INSTANCE_ARN, PrincipalType="USER", PrincipalId=user_oid)
        for aa in resp.get("AccountAssignments", []):
            accounts.append({'account_id': aa.get('AccountId'), 'permission_set': aa.get('PermissionSetArn'), 'principal_type': 'USER'})
    except Exception as e:
        logger.exception("SSO USER lookup failed: %s", e)
    groups = get_user_groups_graph_app(user_oid)
    for group in groups:
        try:
            resp = sso_admin.list_account_assignments(InstanceArn=AWS_SSO_INSTANCE_ARN, PrincipalType="GROUP", PrincipalId=group["id"])
            for aa in resp.get("AccountAssignments", []):
                accounts.append({'account_id': aa.get('AccountId'), 'permission_set': aa.get('PermissionSetArn'), 'group': group["name"], 'principal_type': 'GROUP'})
        except Exception as e:
            logger.exception("SSO GROUP lookup failed for %s: %s", group.get("id"), e)
    logger.debug("Resolved AWS accounts for user %s: %s", user_oid, accounts)
    return accounts

def assume_role(account_id: str):
    role_arn = f"arn:aws:iam::{account_id}:role/MultiCloudAccessRole"
    sts_client = boto3.client("sts")
    try:
        response = sts_client.assume_role(RoleArn=role_arn, RoleSessionName="multicloud-session")
        creds = response["Credentials"]
        session = boto3.Session(
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"]
        )
        return session
    except Exception as e:
        logger.warning("AssumeRole failed for %s: %s", account_id, e)
        if ALLOW_ASSUME_ROLE_FALLBACK:
            logger.warning("Falling back to local boto3.Session() because ALLOW_ASSUME_ROLE_FALLBACK is true.")
            try:
                return boto3.Session()
            except Exception:
                logger.exception("No fallback session available.")
                raise HTTPException(status_code=403, detail=f"STS AssumeRole failed for account {account_id}: {str(e)}")
        else:
            raise HTTPException(status_code=403, detail=f"STS AssumeRole failed for account {account_id}: {str(e)}")

def session_credentials_for_env(session: boto3.Session) -> Dict[str, str]:
    creds = session.get_credentials()
    if creds is None:
        return {}
    frozen = creds.get_frozen_credentials()
    return {"AWS_ACCESS_KEY_ID": frozen.access_key or "", "AWS_SECRET_ACCESS_KEY": frozen.secret_key or "", "AWS_SESSION_TOKEN": frozen.token or ""}

def is_account_allowed(request: Request, account_id: str) -> bool:
    user = get_current_user(request)
    if is_admin(user):
        return True
    email = (user or {}).get("email", "")
    # ISD-specific path: fine-grained per-user AWS account access control
    if email and DB_AVAILABLE and get_isd_subscriptions_for_email:
        department = extract_department_from_email(email)
        if department and department.lower() == "isd":
            try:
                allowed = get_isd_subscriptions_for_email(email, cloud="aws")
                if allowed is not None:
                    return account_id in allowed
                # Email not found in any ISD table — deny access
                logger.info(
                    "ISD user %s not found in any ISD access table; denying account %s",
                    email, account_id,
                )
                return False
            except Exception as e:
                logger.warning(
                    "DB is_account_allowed (ISD) check failed for %s: %s", email, e
                )
    # Department-based path: check if account is pre-loaded for user's department
    if email and DB_AVAILABLE and get_resources_by_department:
        department = extract_department_from_email(email)
        if department:
            try:
                dept_rows = get_resources_by_department(department, "aws")
                if any(r.get("subscription_id") == account_id for r in dept_rows):
                    return True
            except Exception as e:
                logger.warning("DB is_account_allowed (dept) check failed for %s: %s", email, e)
    allowed_accounts = get_aws_accounts_for_user(user)
    return any(acc.get("account_id") == account_id for acc in allowed_accounts)

def is_subscription_allowed(request: Request, subscription_id: str) -> bool:
    user = get_current_user(request)
    if is_admin(user):
        return True
    email = (user or {}).get("email", "")
    # ISD-specific path: fine-grained per-user subscription access control
    if email and DB_AVAILABLE and get_isd_subscriptions_for_email:
        department = extract_department_from_email(email)
        if department and department.lower() == "isd":
            try:
                allowed = get_isd_subscriptions_for_email(email)
                if allowed is not None:
                    return subscription_id in allowed
                # Email not found in any ISD table — deny access
                logger.info(
                    "ISD user %s not found in any ISD access table; denying subscription %s",
                    email, subscription_id,
                )
                return False
            except Exception as e:
                logger.warning(
                    "DB is_subscription_allowed (ISD) check failed for %s: %s", email, e
                )
    # Department-based path: check if subscription is pre-loaded for user's department
    if email and DB_AVAILABLE and get_resources_by_department:
        department = extract_department_from_email(email)
        if department:
            try:
                dept_rows = get_resources_by_department(department, "azure")
                if any(r.get("subscription_id") == subscription_id for r in dept_rows):
                    return True
            except Exception as e:
                logger.warning("DB is_subscription_allowed (dept) check failed for %s: %s", email, e)
    if user:
        user_oid = (user or {}).get("oid")
        if not user_oid:
            return False
        subs = get_user_subscription_ids_cached(user_oid)
        return subscription_id in subs
    try:
        sp_subs = get_azure_subscriptions_sp_cached()
        sp_ids = {s["id"] for s in sp_subs}
        return subscription_id in sp_ids
    except Exception:
        return False


def _normalize_oci_access_value(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "").strip()).lower()


def _is_oci_runtime_enabled() -> bool:
    return bool(OCI_AVAILABLE and oci_is_enabled and oci_is_enabled())


def get_oci_tenancies_for_user(user: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    if not _is_oci_runtime_enabled() or not oci_list_tenancy_summaries:
        return []

    tenancies = oci_list_tenancy_summaries()
    if not user:
        return []
    if is_admin(user):
        return tenancies

    email = (user.get("email") or "").strip()
    if email and DB_AVAILABLE and get_resources_by_department:
        department = extract_department_from_email(email)
        if department:
            try:
                dept_rows = get_resources_by_department(department, "oci")
                if dept_rows:
                    allowed_values = set()
                    for row in dept_rows:
                        allowed_values.add(_normalize_oci_access_value(row.get("subscription_id")))
                        allowed_values.add(_normalize_oci_access_value(row.get("subscription_name")))
                    filtered = [
                        item for item in tenancies
                        if _normalize_oci_access_value(item.get("key")) in allowed_values
                        or _normalize_oci_access_value(item.get("name")) in allowed_values
                        or _normalize_oci_access_value(item.get("tenancy_ocid")) in allowed_values
                    ]
                    return filtered
            except Exception as exc:
                logger.warning("DB OCI tenancy filter failed for %s: %s", email, exc)

    return tenancies


def is_oci_tenancy_allowed(request: Request, tenancy_key: str) -> bool:
    user = get_current_user(request)
    return any(item.get("key") == tenancy_key for item in get_oci_tenancies_for_user(user))


def _ensure_oci_access(request: Request, tenancy_key: str) -> Dict[str, str]:
    if not _is_oci_runtime_enabled():
        raise HTTPException(status_code=503, detail="OCI support is not enabled")
    if not is_oci_tenancy_allowed(request, tenancy_key):
        raise HTTPException(status_code=403, detail="Not allowed to access this OCI tenancy")
    try:
        return oci_get_tenancy_config(tenancy_key).summary()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _resolve_oci_image_source(requested_tenancy_summary: Dict[str, str]) -> Tuple[str, str, bool]:
    requested_tenancy_key = (requested_tenancy_summary.get("key") or "").strip()
    requested_image_compartment = (requested_tenancy_summary.get("image_compartment_ocid") or "").strip()
    source_tenancy_key = (os.getenv("OCI_SHARED_IMAGE_TENANCY_KEY", "") or "").strip() or "isdecloud"
    source_compartment = (os.getenv("OCI_SHARED_IMAGE_COMPARTMENT_OCID", "") or "").strip()
    using_shared_source = source_tenancy_key != requested_tenancy_key

    try:
        source_summary = oci_get_tenancy_config(source_tenancy_key).summary()
        source_compartment = source_compartment or (source_summary.get("image_compartment_ocid") or "").strip()
        if source_tenancy_key.lower() == "isdecloud" and source_compartment == (source_summary.get("tenancy_ocid") or "").strip():
            try:
                source_compartment = next(
                    (
                        (item.get("id") or "").strip()
                        for item in oci_list_compartments(source_tenancy_key)
                        if (item.get("name") or "").strip().lower() == "lac-certifiedimages"
                        or "/ lac-certifiedimages" in (item.get("path") or "").strip().lower()
                    ),
                    source_compartment,
                )
            except Exception as exc:
                logger.warning(
                    "Unable to auto-resolve OCI shared image compartment 'lac-certifiedimages' in tenancy '%s': %s",
                    source_tenancy_key,
                    exc,
                )
        return source_tenancy_key, source_compartment, using_shared_source
    except Exception:
        if using_shared_source:
            logger.warning(
                "Falling back to requested OCI tenancy '%s' for image lookup because shared image source tenancy '%s' is not configured",
                requested_tenancy_key,
                source_tenancy_key,
            )
        return requested_tenancy_key, requested_image_compartment, False


def _raise_oci_lookup_http_error(resource_name: str, tenancy_key: str, exc: Exception) -> NoReturn:
    if isinstance(exc, HTTPException):
        raise exc
    status = int(getattr(exc, "status", 0) or 0)
    code = str(getattr(exc, "code", "") or "")
    if status == 401 and code == "NotAuthenticated":
        logger.warning(
            "OCI %s lookup rejected by OCI auth for tenancy '%s' (status=%s code=%s)",
            resource_name,
            tenancy_key,
            status,
            code,
        )
        raise HTTPException(
            status_code=502,
            detail=(
                f"OCI {resource_name} lookup failed for tenancy '{tenancy_key}' because OCI rejected the API signature "
                "(401 NotAuthenticated). This is usually a tenancy credential mismatch. Verify USER_OCID, TENANCY_OCID, "
                "the uploaded private key, and that the API key fingerprint in OCI matches the signer fingerprint shown in logs."
            ),
        ) from exc
    logger.exception("OCI %s lookup failed for %s: %s", resource_name, tenancy_key, exc)
    raise HTTPException(status_code=500, detail=f"Failed to load OCI {resource_name}: {exc}") from exc


def _list_resource_groups_for_subscription(subscription_id: str) -> List[Dict[str, Any]]:
    client = ResourceManagementClient(get_azure_credentials(), subscription_id)
    groups = list(client.resource_groups.list())
    return [{"id": g.id, "name": g.name, "location": g.location} for g in groups]

@cached(subs_rg_cache)
def get_resource_groups_cached(subscription_id: str) -> List[Dict[str, Any]]:
    try:
        return _list_resource_groups_for_subscription(subscription_id)
    except Exception as e:
        logger.exception("list_resource_groups failed (cached): %s", e)
        return []

def list_rgs_parallel(subscription_ids: List[str], max_workers: int = 8) -> Dict[str, Any]:
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(get_resource_groups_cached, sid): sid for sid in subscription_ids}
        for f in as_completed(futures):
            sid = futures[f]
            try:
                results[sid] = f.result()
            except Exception as e:
                results[sid] = {"error": str(e)}
    return results

def update_vms_store(new_vm_config: Dict[str, Any], unique_vm_name: str) -> Dict[str, Any]:
    vms_path = os.path.join(BASE_DIR, "aws_vms.json")
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

def remove_vm_from_store(vm_name: str) -> Dict[str, Any]:
    vms_path = os.path.join(BASE_DIR, "aws_vms.json")
    vms = {}
    if os.path.isfile(vms_path):
        try:
            with open(vms_path, "r") as f:
                vms = json.load(f)
        except Exception:
            vms = {}
    if vm_name in vms:
        del vms[vm_name]
        with open(vms_path, "w") as f:
            json.dump(vms, f, indent=2)
    return vms

def validate_cidrs_list(cidrs: List[str]) -> List[str]:
    clean = []
    for c in cidrs:
        s = c.strip()
        if not s:
            continue
        try:
            network = ipaddress.ip_network(s, strict=False)
            clean.append(str(network))
        except Exception:
            raise ValueError(f"Invalid CIDR: {s}")
    return clean

# ✅ CRITICAL FIX: Parse tags from URL-encoded form data
def parse_tags_from_payload(payload: Dict[str, Any]) -> Dict[str, str]:
    """Parse tags from form payload (handles both JSON string and dict)."""
    tags_data = payload.get("tags", {})
    
    if isinstance(tags_data, str):
        try:
            tags_data = json.loads(tags_data)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse tags JSON: {tags_data}")
            return {}
    
    if isinstance(tags_data, dict):
        # Ensure all values are strings
        return {k: str(v) for k, v in tags_data.items() if v}
    
    return {}
def _aws_earliest_launch_time_utc(instances: List[Dict[str, Any]]) -> Optional[str]:
    """
    instances: list of AWS EC2 instance dicts OR simplified dicts.
    Tries to find earliest LaunchTime and returns ISO UTC string.
    """
    if not instances:
        return None

    launch_times = []

    for inst in instances:
        if not isinstance(inst, dict):
            continue

        lt = inst.get("LaunchTime")
        # If you only have simplified dicts without LaunchTime, skip.
        if not lt:
            continue

        # boto3 returns datetime with tzinfo
        if isinstance(lt, datetime):
            dt = lt.astimezone(timezone.utc) if lt.tzinfo else lt.replace(tzinfo=timezone.utc)
            launch_times.append(dt)
        elif isinstance(lt, str):
            s = lt.strip()
            if not s:
                continue
            try:
                # "Z" -> "+00:00"
                if s.endswith("Z"):
                    s = s[:-1] + "+00:00"
                dt = datetime.fromisoformat(s)
                dt = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
                launch_times.append(dt)
            except Exception:
                continue

    if not launch_times:
        return None

    earliest = min(launch_times)
    return earliest.strftime("%Y-%m-%dT%H:%M:%SZ")

def _build_user_data_base64(os_type: str, username: str, password: str) -> str:
    """Generate a base64-encoded user_data script that creates a local OS user at first boot.

    Linux (RHEL / Amazon Linux):  creates the user, sets password, adds to wheel (sudoers),
                                   and enables password-based SSH authentication.
    Windows:                       creates a local user and adds them to Administrators and
                                   Remote Desktop Users groups via PowerShell.

    Values are properly escaped to prevent shell/script injection:
    - Linux: shlex.quote() produces POSIX-safe single-quoted strings.
    - Windows: single-quotes inside PowerShell single-quoted strings are escaped as ''.
    """
    import re
    # Allow only safe characters for the username (alphanumeric + _ -)
    safe_user = re.sub(r"[^A-Za-z0-9_\-]", "", username)[:32]

    if os_type and os_type.lower() == "windows":
        # In PowerShell single-quoted strings, escape ' as ''
        ps_pass = password.replace("'", "''")
        ps_user = safe_user  # already restricted to alphanumeric + _-
        script = (
            "<powershell>\n"
            f"$username = '{ps_user}'\n"
            # $password holds a SecureString; the plain-text value is only held momentarily
            f"$password = ConvertTo-SecureString '{ps_pass}' -AsPlainText -Force\n"
            "try {\n"
            "    # PasswordNeverExpires $true + UserMayNotChangePassword $true matches portal policy\n"
            "    New-LocalUser -Name $username -Password $password "
            "-PasswordNeverExpires:$true -UserMayNotChangePassword:$true -ErrorAction Stop\n"
            "} catch {\n"
            "    Set-LocalUser -Name $username -Password $password "
            "-PasswordNeverExpires $true -UserMayNotChangePassword:$true -ErrorAction SilentlyContinue\n"
            "}\n"
            "try { Add-LocalGroupMember -Group 'Administrators' "
            "-Member $username -ErrorAction SilentlyContinue } catch {}\n"
            "try { Add-LocalGroupMember -Group 'Remote Desktop Users' "
            "-Member $username -ErrorAction SilentlyContinue } catch {}\n"
            "</powershell>\n"
        )
    else:
        # Linux / RHEL — use shlex.quote() for safe POSIX shell embedding
        quoted_user = shlex.quote(safe_user)
        quoted_pass = shlex.quote(password)
        # Helper: patch or append a key=value pair in /etc/ssh/sshd_config (and drop-in dir).
        # We patch: PasswordAuthentication, ChallengeResponseAuthentication (OpenSSH < 9),
        # KbdInteractiveAuthentication (OpenSSH >= 9, renamed), and UsePAM.
        script = (
            "#!/bin/bash\n"
            f"USERNAME={quoted_user}\n"
            f"PASSWORD={quoted_pass}\n"
            "id \"$USERNAME\" &>/dev/null || useradd -m -s /bin/bash \"$USERNAME\"\n"
            "echo \"$USERNAME:$PASSWORD\" | chpasswd\n"
            "usermod -aG wheel \"$USERNAME\" 2>/dev/null; "
            "usermod -aG sudo \"$USERNAME\" 2>/dev/null; true\n"
            "mkdir -p /etc/sudoers.d\n"
            "echo \"$USERNAME ALL=(ALL) NOPASSWD:ALL\" > \"/etc/sudoers.d/$USERNAME\"\n"
            "chmod 440 \"/etc/sudoers.d/$USERNAME\"\n"
            # ---- Enable password-based SSH in the main sshd_config ----
            # PasswordAuthentication
            "sed -i 's/^[[:space:]]*#*[[:space:]]*PasswordAuthentication.*/PasswordAuthentication yes/' "
            "/etc/ssh/sshd_config\n"
            "grep -q '^PasswordAuthentication yes' /etc/ssh/sshd_config || "
            "echo 'PasswordAuthentication yes' >> /etc/ssh/sshd_config\n"
            # ChallengeResponseAuthentication (OpenSSH < 9 / Amazon Linux 2 & 2023 / RHEL 8)
            "sed -i 's/^[[:space:]]*#*[[:space:]]*ChallengeResponseAuthentication.*/ChallengeResponseAuthentication yes/' "
            "/etc/ssh/sshd_config\n"
            "grep -q '^ChallengeResponseAuthentication yes' /etc/ssh/sshd_config || "
            "echo 'ChallengeResponseAuthentication yes' >> /etc/ssh/sshd_config\n"
            # KbdInteractiveAuthentication (renamed in OpenSSH 9.x / RHEL 9)
            "sed -i 's/^[[:space:]]*#*[[:space:]]*KbdInteractiveAuthentication.*/KbdInteractiveAuthentication yes/' "
            "/etc/ssh/sshd_config\n"
            "grep -q '^KbdInteractiveAuthentication yes' /etc/ssh/sshd_config || "
            "echo 'KbdInteractiveAuthentication yes' >> /etc/ssh/sshd_config\n"
            # UsePAM — required for PAM-based password auth
            "sed -i 's/^[[:space:]]*#*[[:space:]]*UsePAM.*/UsePAM yes/' /etc/ssh/sshd_config\n"
            "grep -q '^UsePAM yes' /etc/ssh/sshd_config || "
            "echo 'UsePAM yes' >> /etc/ssh/sshd_config\n"
            # ---- If AllowUsers is configured, ensure our created user is allowed ----
            # Some hardened images set "AllowUsers ..." at end of sshd_config; if our user
            # is not listed, SSH login is denied even when PasswordAuthentication=yes.
            "ALLOW_FILE=\"\"\n"
            "if grep -qiE '^[[:space:]]*AllowUsers[[:space:]]+' /etc/ssh/sshd_config 2>/dev/null; then\n"
            "  ALLOW_FILE=\"/etc/ssh/sshd_config\"\n"
            "elif [ -d /etc/ssh/sshd_config.d ]; then\n"
            "  ALLOW_FILE=\"$(grep -RilE '^[[:space:]]*AllowUsers[[:space:]]+' /etc/ssh/sshd_config.d 2>/dev/null | head -n 1)\"\n"
            "fi\n"
            "if [ -n \"$ALLOW_FILE\" ]; then\n"
            "  if ! grep -qiE \"^[[:space:]]*AllowUsers[[:space:]].*(^|[[:space:]])${USERNAME}([[:space:]]|$)\" \"$ALLOW_FILE\"; then\n"
            "    sed -i -E \"0,/^[[:space:]]*AllowUsers[[:space:]]+/ s//&${USERNAME} /\" \"$ALLOW_FILE\"\n"
            "  fi\n"
            "fi\n"
            # ---- Patch drop-in override files (Amazon Linux 2023 / Ubuntu) ----
            # These files can re-disable password auth after the main config.
            # Use '*' instead of '*.conf' to cover all extensions:
            #   Ubuntu: 60-cloudimg-settings.conf
            #   Amazon Linux 2023: 50-cloud-init.cfg
            # The [ -f ] guard skips directories/non-files, and 'sed 2>/dev/null || true'
            # is a no-op on files that don't contain any of the targeted directives.
            "if [ -d /etc/ssh/sshd_config.d ]; then\n"
            "  for f in /etc/ssh/sshd_config.d/*; do\n"
            # Guard against unmatched globs or directories: skip if not a regular file
            "    [ -f \"$f\" ] || continue\n"
            "    sed -i 's/^[[:space:]]*#*[[:space:]]*PasswordAuthentication.*/PasswordAuthentication yes/' "
            "\"$f\" 2>/dev/null || true\n"
            "    sed -i 's/^[[:space:]]*#*[[:space:]]*ChallengeResponseAuthentication.*/ChallengeResponseAuthentication yes/' "
            "\"$f\" 2>/dev/null || true\n"
            "    sed -i 's/^[[:space:]]*#*[[:space:]]*KbdInteractiveAuthentication.*/KbdInteractiveAuthentication yes/' "
            "\"$f\" 2>/dev/null || true\n"
            "  done\n"
            "fi\n"
            # Validate sshd config before restart (avoid locking yourself out)
            "sshd -t 2>/dev/null || true\n"
            "systemctl restart sshd 2>/dev/null || systemctl restart ssh 2>/dev/null || "
            "service sshd restart 2>/dev/null || true\n"
        )

    return base64.b64encode(script.encode("utf-8")).decode("utf-8")


# ✅ FIXED: Terraform runner now accepts AMI IDs directly (no AMI_MAP lookup)
def run_terraform(cloud: str, account: str, vpc_id: str, subnet_id: str, security_group: str,
                  vm_name: str, ami_id_or_name: str, os_type: str, instance_type: str,
                  key_pair_name: Optional[str], vms: Dict[str, Any], user_email: Optional[str] = None,
                  data_protection: str = "",
                  vm_username: Optional[str] = None, vm_password: Optional[str] = None):
    """Run Terraform to deploy AWS VMs.
    
    FIXED: Now accepts AMI ID directly from the frontend (no hardcoded AMI_MAP lookup).
    The ami_id_or_name parameter should be the actual AMI ID from AWS (e.g., ami-0123456789abcdef0).
    When vm_username and vm_password are provided, a user_data script is generated to create
    the account inside the VM at first boot (Linux: RHEL sudoers; Windows: local user + Admin/RDP groups).
    """
    module_path = os.path.join(BASE_DIR, f"../terraform/{cloud.lower()}")
    def record_vm_outcome(status_value: str, error_text: str = None):
        _sync_portal_request_vm_outcome(cloud.lower(), vm_name, status_value, error_text)

    if not os.path.isdir(module_path):
        record_vm_outcome("failed", f"No module found for cloud: {cloud}")
        return JSONResponse(status_code=400, content={"error": f"No module found for cloud: {cloud}"})
    
    env = os.environ.copy()

    env["SSL_CERT_FILE"] = "/etc/ssl/certs/ca-certificates.crt"
    env["REQUESTS_CA_BUNDLE"] = "/etc/ssl/certs/ca-certificates.crt"
    env["CURL_CA_BUNDLE"] = "/etc/ssl/certs/ca-certificates.crt"
    env["GODEBUG"] = "x509ignoreCN=0"

    try:
         session = assume_role(account)
         creds = session_credentials_for_env(session)
         env.update(creds)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception("Assume role before terraform failed: %s", e)
        return JSONResponse(status_code=500, content={"error": "AssumeRole failed", "detail": str(e)})
    
    if not isinstance(vms, dict):
        record_vm_outcome("failed", "Invalid vms structure; expected map")
        return JSONResponse(status_code=400, content={"error": "Invalid vms structure; expected map"})
    
    target_vms_store = {k: v for k, v in vms.items() if isinstance(v, dict) and str(v.get("account") or "") == str(account)}
    
    if vm_name not in target_vms_store:
        maybe_cfg = vms.get(vm_name)
        if maybe_cfg and maybe_cfg.get("account") == account:
            target_vms_store[vm_name] = maybe_cfg
        else:
            target_vms_store[vm_name] = {
                "ami_id": ami_id_or_name,  # ✅ Use the AMI ID directly from frontend
                "instance_type": instance_type,
                "subnet_id": subnet_id,
                "security_group_ids": [security_group] if security_group else [],
                "key_pair_name": key_pair_name,
                "vm_name": vm_name,
                "account": account
            }
    
    # ✅ Use the AMI ID directly (no AMI_MAP lookup)
    ami_id = ami_id_or_name
    
    # Validate that it looks like an AMI ID (starts with "ami-")
    if not ami_id or not ami_id.startswith("ami-"):
        record_vm_outcome("failed", f"Invalid AMI ID: {ami_id}")
        return JSONResponse(status_code=400, content={
            "error": "Invalid AMI ID",
            "detail": f"AMI ID must start with 'ami-'. Received: {ami_id}"
        })
    
    region = os.getenv("TF_VAR_region", "us-west-2")
    env["TF_VAR_region"] = region
    env["TF_VAR_account"] = account
    env["TF_VAR_vpc_id"] = vpc_id or ""
    env["TF_VAR_subnet_id"] = subnet_id or ""
    env["TF_VAR_vm_name"] = vm_name
    env["TF_VAR_ami_id"] = ami_id  # ✅ Pass the actual AMI ID to Terraform
    env["TF_VAR_os_type"] = os_type or ""
    env["TF_VAR_instance_type"] = instance_type or ""
    env["TF_VAR_key_pair_name"] = key_pair_name or ""
    env["TF_VAR_security_group_ids"] = json.dumps([security_group]) if security_group else json.dumps([])
    
    ec2 = session.client("ec2", region_name=region)
    
    def find_public_amzn2_ami() -> Optional[str]:
        try:
            resp = ec2.describe_images(Owners=["amazon"], Filters=[{"Name": "name", "Values": ["amzn2-ami-hvm-*-x86_64-gp2"]}])
            images = resp.get("Images", [])
            if not images:
                return None
            images_sorted = sorted(images, key=lambda x: x.get("CreationDate", ""), reverse=True)
            return images_sorted[0].get("ImageId")
        except Exception as e:
            logger.warning("Could not lookup public Amazon Linux 2 AMI in %s: %s", region, e)
            return None
    
    normalized_vms = {}
    replacements = {}
    overrides = {}
    
    for k, cfg in target_vms_store.items():
        normalized = dict(cfg) if isinstance(cfg, dict) else {"vm_name": str(k)}
        vm_ami = normalized.get("ami_id") or ami_id
        
        if vm_ami:
            try:
                resp = ec2.describe_images(ImageIds=[vm_ami])
                imgs = resp.get("Images", [])
                if not imgs:
                    fallback = find_public_amzn2_ami()
                    if fallback:
                        replacements[k] = {"old_ami": vm_ami, "new_ami": fallback}
                        vm_ami = fallback
                    else:
                        return JSONResponse(status_code=400, content={"error": "AMI not accessible and fallback lookup failed", "detail": f"AMI {vm_ami} not accessible in region {region}"})
            except ClientError as ce:
                logger.warning("AMI validation ClientError for %s: %s", vm_ami, ce)
                fallback = find_public_amzn2_ami()
                if fallback:
                    replacements[k] = {"old_ami": vm_ami, "new_ami": fallback}
                    vm_ami = fallback
                else:
                    return JSONResponse(status_code=400, content={"error": "AMI validation failed", "detail": str(ce)})
            except Exception as e:
                logger.exception("Unexpected error validating AMI %s: %s", vm_ami, e)
                fallback = find_public_amzn2_ami()
                if fallback:
                    replacements[k] = {"old_ami": vm_ami, "new_ami": fallback}
                    vm_ami = fallback
                else:
                    return JSONResponse(status_code=500, content={"error": "Unexpected error validating AMI", "detail": str(e)})
        else:
            fallback = find_public_amzn2_ami()
            if fallback:
                vm_ami = fallback
                replacements[k] = {"old_ami": None, "new_ami": fallback}
            else:
                return JSONResponse(status_code=400, content={"error": "No AMI specified and no public fallback found"})
        
        normalized["ami_id"] = vm_ami
        
        sg = normalized.get("security_group_ids")
        if sg is None:
            normalized["security_group_ids"] = []
        elif isinstance(sg, str):
            try:
                parsed = json.loads(sg)
                normalized["security_group_ids"] = parsed if isinstance(parsed, list) else [parsed]
            except Exception:
                normalized["security_group_ids"] = [sg]
        
        if not normalized.get("vm_name"):
            normalized["vm_name"] = k
        
        # Ensure tags field exists (empty dict if not present)
        if "tags" not in normalized:
            normalized["tags"] = {}
        
        # Ensure Terraform optional fields exist on every VM entry
        normalized["key_pair_name"] = normalized.get("key_pair_name") or ""
        normalized["user_data_base64"] = normalized.get("user_data_base64") or ""
        
        s_id = normalized.get("subnet_id") or subnet_id or ""
        if s_id:
            try:
                _resp = ec2.describe_subnets(SubnetIds=[s_id])
                subnets = _resp.get("Subnets", [])
                if not subnets:
                    return JSONResponse(status_code=400, content={"error": "Subnet not found", "detail": f"The subnet ID '{s_id}' was not found in account {account} region {region}."})
            except ClientError as ce:
                code = ce.response.get("Error", {}).get("Code", "")
                msg = ce.response.get("Error", {}).get("Message", str(ce))
                logger.warning("Subnet validation failed for %s: %s - %s", s_id, code, msg)
                if "InvalidSubnetID.NotFound" in msg or "InvalidSubnetID.NotFound" in code:
                    return JSONResponse(status_code=400, content={"error": "Subnet not found", "detail": f"The subnet ID '{s_id}' was not found in account {account} region {region}."})
                else:
                    return JSONResponse(status_code=400, content={"error": "Subnet validation failed", "detail": f"AWS error validating subnet {s_id}: {code} - {msg}"})
            except Exception as e:
                logger.exception("Unexpected error validating subnet %s: %s", s_id, e)
                return JSONResponse(status_code=500, content={"error": "Unexpected subnet validation error", "detail": str(e)})
        
        for sgid in normalized.get("security_group_ids", []):
            if not sgid:
                continue
            try:
                _resp = ec2.describe_security_groups(GroupIds=[sgid])
                groups = _resp.get("SecurityGroups", [])
                if not groups:
                    return JSONResponse(status_code=400, content={"error": "Security group not found", "detail": f"Security group {sgid} not found in account {account} region {region}."})
            except ClientError as ce:
                code = ce.response.get("Error", {}).get("Code", "")
                msg = ce.response.get("Error", {}).get("Message", str(ce))
                logger.warning("SG validation failed for %s: %s - %s", sgid, code, msg)
                if "InvalidGroup.NotFound" in msg or "InvalidGroup.NotFound" in code:
                    return JSONResponse(status_code=400, content={"error": "Security group not found", "detail": f"Security group {sgid} not found in account {account} region {region}."})
                else:
                    return JSONResponse(status_code=400, content={"error": "Security group validation failed", "detail": f"AWS error validating security group {sgid}: {code} - {msg}"})
            except Exception as e:
                logger.exception("Unexpected SG validation error: %s", e)
                return JSONResponse(status_code=500, content={"error": "Unexpected SG validation error", "detail": str(e)})
        
        normalized_vms[k] = normalized
    
    # Inject user_data for the VM being deployed if username/password provided
    if vm_name in normalized_vms and vm_username and vm_password:
        normalized_vms[vm_name]["user_data_base64"] = _build_user_data_base64(
            os_type or "", vm_username, vm_password
        )
        # Tag the instance with the portal-created username so the VM list
        # connect dialog can pre-fill the correct SSH/RDP username later.
        if not isinstance(normalized_vms[vm_name].get("tags"), dict):
            normalized_vms[vm_name]["tags"] = {}
        normalized_vms[vm_name]["tags"]["PortalUsername"] = vm_username

    env["TF_VAR_vms"] = json.dumps(normalized_vms)
    
    notes = {}
    if replacements:
        notes["ami_replacements"] = replacements
        logger.info("AMI replacements performed before terraform: %s", replacements)
    if overrides:
        notes["resource_overrides"] = overrides
        logger.info("Resource overrides applied: %s", overrides)
    
    try:
        logger.info("Terraform binary: %s", TERRAFORM_BIN)
        logger.info("Running terraform init in %s", module_path)
        init_proc = subprocess.run([TERRAFORM_BIN, "init"], cwd=module_path, check=True, env=env, capture_output=True, text=True)
        logger.info("Terraform init stdout: %s", strip_ansi(init_proc.stdout))
        logger.info("Running terraform apply (auto-approve)")
        apply_proc = subprocess.run([TERRAFORM_BIN, "apply", "-auto-approve"], cwd=module_path, check=True, env=env, capture_output=True, text=True)
        logger.info("Terraform apply stdout: %s", strip_ansi(apply_proc.stdout))
        
        cleanup_terraform_state(module_path)
        
    except FileNotFoundError as e:
        error_msg = (
            f"Terraform binary not found at '{TERRAFORM_BIN}'. "
            f"Please ensure Terraform is installed. "
            f"Common locations checked: {', '.join(TERRAFORM_COMMON_PATHS)}. "
            f"Set TERRAFORM_BIN environment variable to the correct path."
        )
        logger.exception("Error running terraform: %s", error_msg)
        record_vm_outcome("failed", error_msg)
        return JSONResponse(status_code=500, content={
            "error": "Terraform not found",
            "detail": error_msg,
            "terraform_bin_configured": TERRAFORM_BIN,
            "module_path": module_path
        })
    except subprocess.CalledProcessError as e:
        stdout = strip_ansi(e.stdout or "")
        stderr = strip_ansi(e.stderr or "")
        error_msg = stderr or stdout or str(e)
        logger.exception("Terraform execution failed: %s", error_msg)
        try:
            filters = [{"Name": "tag:Name", "Values": [vm_name]}, {"Name": "instance-state-name", "Values": ["pending", "running", "stopped", "stopping"]}]
            resp = ec2.describe_instances(Filters=filters)
            instances = []
            for r in resp.get("Reservations", []):
                for inst in r.get("Instances", []):
                    instances.append({
                        "InstanceId": inst.get("InstanceId"),
                        "State": inst.get("State", {}).get("Name"),
                        "PublicIpAddress": inst.get("PublicIpAddress"),
                        "PrivateIpAddress": inst.get("PrivateIpAddress"),
                        "ImageId": inst.get("ImageId"),
                        "LaunchTime": inst.get("LaunchTime")
                    })
            if instances:
                result = {
                    "status": "partial_success",
                    "message": "Terraform failed, but an EC2 instance with the requested Name tag was found.",
                    "terraform_error": error_msg,
                    "terraform_stdout": stdout,
                    "terraform_stderr": stderr,
                    "instances": instances,
                    "vm_name": vm_name,
                    "account": account
                }
                if notes:
                    result["notes"] = notes
                record_vm_outcome("partial_success", error_msg)
                return JSONResponse(status_code=207, content=result)
        except Exception as e2:
            logger.exception("Failed to inspect EC2 instances after terraform error: %s", e2)
        resp_payload = {"error": "Terraform error", "detail": error_msg, "stdout": stdout, "stderr": stderr, "vm_name": vm_name, "account": account}
        if notes:
            resp_payload["notes"] = notes
        record_vm_outcome("failed", error_msg)
        return JSONResponse(status_code=500, content=resp_payload)
    except Exception as e:
        logger.exception("Unexpected error running terraform: %s", e)
        resp_payload = {"error": "Internal Server Error", "detail": str(e), "traceback": traceback.format_exc(), "vm_name": vm_name, "account": account}
        if notes:
            resp_payload["notes"] = notes
        record_vm_outcome("failed", str(e))
        return JSONResponse(status_code=500, content=resp_payload)
    
    try:
        filters = [{"Name": "tag:Name", "Values": [vm_name]}, {"Name": "instance-state-name", "Values": ["pending", "running", "stopped", "stopping"]}]
        resp = ec2.describe_instances(Filters=filters)
        instances = []
        for r in resp.get("Reservations", []):
            for inst in r.get("Instances", []):
                instances.append({
                    "InstanceId": inst.get("InstanceId"),
                    "State": inst.get("State", {}).get("Name"),
                    "PublicIpAddress": inst.get("PublicIpAddress"),
                    "PrivateIpAddress": inst.get("PrivateIpAddress"),
                    "ImageId": inst.get("ImageId"),
                    "LaunchTime": inst.get("LaunchTime")
                })
        result = {"status": "success", "cloud": cloud, "vm_name": vm_name, "account": account, "region": region, "vpc_id": vpc_id, "subnet_id": subnet_id, "security_group": security_group, "os_type": os_type, "instance_type": instance_type, "instances": instances}
        if vm_username:
            result["vm_username"] = vm_username
            result["user_created"] = True
            result["user_created_msg"] = (
                f"User '{vm_username}' will be created at first boot via user_data "
                f"({'sudoers added to wheel group' if (os_type or '').lower() != 'windows' else 'added to Administrators and Remote Desktop Users groups'})."
            )
        if notes:
            result["notes"] = notes
        logger.info("Terraform apply complete; instances found for %s: %s", vm_name, [i.get("InstanceId") for i in instances])
        record_vm_outcome("success", None)
        
        try:
            vm_details = {
                "vm_name": vm_name,
                "cloud": cloud,
                "account": account,
                "account_name_display": account,  # ✅ ensures email/account not Unknown
                "region": region,
                "instance_type": instance_type,
                "os_type": os_type,
                "ami_id": ami_id,
                "instances": instances,
                "data_protection": data_protection,
            }
            # ✅ include portal tags for customer email
            cfg = normalized_vms.get(vm_name, {})
            if isinstance(cfg, dict) and isinstance(cfg.get("tags"), dict):
                vm_details["tags"] = cfg.get("tags", {})
            vm_details["provisioning_start_time"] = _aws_earliest_launch_time_utc(instances)
            cherwell_result = create_post_deployment_tasks(vm_name, cloud, vm_details, user_email=user_email)
            result["cherwell"] = cherwell_result
        except Exception as cherwell_err:
            logger.exception("Error creating Cherwell tasks (non-blocking): %s", cherwell_err)
            result["cherwell"] = {"error": str(cherwell_err)}

        return result
    except Exception as e:
        logger.exception("Failed to lookup instances after successful apply: %s", e)
        result = {"status": "success", "cloud": cloud, "vm_name": vm_name, "account": account, "region": region, "note": "Apply succeeded but instance lookup failed", "lookup_error": str(e)}
        if notes:
            result["notes"] = notes
        record_vm_outcome("success", None)
        
        try:
            vm_details = {
                "vm_name": vm_name,
                "cloud": cloud,
                "account": account,
                "account_name_display": account,
                "region": region,
                "instance_type": instance_type,
                "os_type": os_type,
                "ami_id": ami_id,
                "note": "Instance lookup failed after deployment",
                "data_protection": data_protection,
            }
            cfg = normalized_vms.get(vm_name, {})
            if isinstance(cfg, dict) and isinstance(cfg.get("tags"), dict):
                vm_details["tags"] = cfg.get("tags", {})

            cherwell_result = create_post_deployment_tasks(vm_name, cloud, vm_details, user_email=user_email)
            result["cherwell"] = cherwell_result
        except Exception as cherwell_err:
            logger.exception("Error creating Cherwell tasks (non-blocking): %s", cherwell_err)
            result["cherwell"] = {"error": str(cherwell_err)}
        
        return JSONResponse(status_code=200, content=result)

deployment_status_store = TTLCache(maxsize=1000, ttl=3600)
deployment_lock = threading.Lock()
# Retained longer than deployment_status_store so delayed background completion/failure
# callbacks can still map deployment_id -> portal_request_all row.
deployment_request_context = TTLCache(maxsize=1000, ttl=86400)

def _sync_portal_request_vm_outcome(cloud_provider: str, vm_name_final: str, status: str, error_log: str = None):
    if not DB_AVAILABLE or not update_latest_portal_request_vm_outcome:
        return
    try:
        update_latest_portal_request_vm_outcome(cloud_provider, vm_name_final, status, error_log)
    except Exception as db_err:
        logger.debug("DB portal_request_all VM outcome update failed (non-blocking): %s", db_err)

def update_deployment_status(deployment_id: str, status: str, message: str = "", vm_id: str = None, error: str = None):
    """Update deployment status in the tracking store and persist to DB."""
    entry = {
        "status": status,
        "message": message,
        "vm_id": vm_id,
        "error": error,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    with deployment_lock:
        deployment_status_store[deployment_id] = entry
    log_detail = message or error or ""
    logger.info(f"Deployment {deployment_id} status updated: {status} - {log_detail}")
    # Persist to DB so status survives server restarts (best-effort, non-blocking)
    if DB_AVAILABLE:
        try:
            db_upsert_deployment_status(deployment_id, status, message, vm_id, error)
        except Exception as db_err:
            logger.debug("DB deployment status persist failed (non-blocking): %s", db_err)
    if status in ("completed", "failed"):
        with deployment_lock:
            # Context can be missing here if TTL expired or entry was never created.
            ctx = deployment_request_context.pop(deployment_id, None) or {}
        if not ctx:
            logger.debug("No deployment request context found for deployment_id=%s", deployment_id)
        cloud_provider = ctx.get("cloud_provider")
        vm_name_final = ctx.get("vm_name_final")
        if cloud_provider and vm_name_final:
            vm_status = "success" if status == "completed" else "failed"
            _sync_portal_request_vm_outcome(cloud_provider, vm_name_final, vm_status, error)

def get_deployment_status(deployment_id: str):
    """Get deployment status from the in-memory store, falling back to DB on miss."""
    with deployment_lock:
        result = deployment_status_store.get(deployment_id)
    if result is not None:
        return result
    # Fall back to DB (e.g. after a server restart cleared the in-memory store)
    if DB_AVAILABLE:
        try:
            return get_deployment_status_db(deployment_id)
        except Exception as db_err:
            logger.debug("DB deployment status lookup failed: %s", db_err)
    return None

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
SESSION_SECRET = os.getenv("SESSION_SECRET", "your-very-strong-random-secret-key")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)

# Kick off AWS pricing fetch in background so it does not block startup.
threading.Thread(
    target=_load_aws_pricing_background, daemon=True, name="aws-pricing-loader"
).start()
if os.path.isdir(os.path.join(BASE_DIR, "../frontend/static")):
    app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "../frontend/static")), name="static")

if GCP_AVAILABLE:
    logger.info("Registering GCP backend router")
    app.include_router(gcp_router, prefix="/api/gcp", tags=["gcp"])

if AZURE_AD_AUTH_AVAILABLE:
    logger.info("Registering Azure AD auth router")
    app.include_router(azure_ad_router, prefix="", tags=["azure-ad-auth"])

if GCP_WIF_AVAILABLE:
    logger.info("Registering GCP WIF router")
    app.include_router(gcp_wif_router, prefix="/api", tags=["gcp-wif"])

@app.post("/api/validate-billing-account")
async def validate_billing_account(payload: dict):
    """
    Validate BASIS billing account number.

    Returns:
      - ok: bool
      - valid: bool
      - reason: str ("allowlisted" / message / etc)
      - raw: any (BASIS response)
    """
    try:
        acct = (payload.get("billing_account") or "").strip()
        env = payload.get("env") or "test"
        result = _validate_billing_account_value(acct, env=env)
        if not result.get("ok"):
            safe_error = str(result.get("error") or "Billing account validation failed")
            if safe_error not in (
                "Billing account number is required",
                "Billing validation service URL is not configured",
            ):
                safe_error = "Billing validation service is unavailable"
            return {"ok": False, "valid": False, "error": safe_error}
        if result.get("reason") == "allowlisted":
            return {"ok": True, "valid": True, "reason": "allowlisted"}
        return {
            "ok": True,
            "valid": bool(result.get("valid")),
            "reason": str(result.get("reason") or ("valid" if result.get("valid") else "not found")),
            "matched_in_response": result.get("matched_in_response"),
            "confirmed_by_status_indicator": result.get("confirmed_by_status_indicator"),
            "status_indicator": result.get("status_indicator") or "",
            "status_indicator_meaning": result.get("status_indicator_meaning") or "",
            "status_indicator_ui_state": result.get("status_indicator_ui_state") or "",
        }
    except Exception as ex:
        logger.exception("validate-billing-account failed: %s", ex)
        raise HTTPException(status_code=500, detail="Billing account validation failed")

@app.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    html = _render_frontend_html()
    if html is not None:
        return HTMLResponse(content=html, headers=NO_CACHE_HEADERS)
    return HTMLResponse(
        "<html><body><h1>Multi-Cloud Portal</h1><p>Frontend not found.</p></body></html>",
        headers=NO_CACHE_HEADERS,
    )
@app.get("/api/billing-approver")
async def billing_approver_lookup(billing_account: str = Query(...)):
    """
    Look up approver email(s) by billing account number.
    Returns:
      { ok: true, found: bool, approvers: string|null }
    """
    if not DB_AVAILABLE or not get_billing_approver_emails_csv:
        return {"ok": True, "found": False, "approvers": None, "db_available": False}

    acct = (billing_account or "").strip()
    if not acct:
        return {"ok": True, "found": False, "approvers": None, "db_available": True}

    try:
        approvers = get_billing_approver_emails_csv(acct)
        return {"ok": True, "found": bool(approvers), "approvers": approvers, "db_available": True}
    except Exception as e:
        logger.exception("billing_approver_lookup failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to lookup billing approver")

@app.get("/debug/session")
async def debug_session(request: Request):
    user = get_current_user(request)
    effective_token = get_easyauth_access_token(request)
    token_source = "easyauth_header" if effective_token else None
    return {"user": user, "has_token": bool(effective_token), "token_source": token_source}

@app.get("/debug/terraform-check")
def debug_terraform_check():
    import shutil
    terraform_path = shutil.which("terraform") or TERRAFORM_BIN
    exists = os.path.exists(terraform_path) if terraform_path else False
    executable = os.access(terraform_path, os.X_OK) if exists else False
    
    try:
        result = subprocess.run([terraform_path, "version"], capture_output=True, text=True, timeout=5)
        version_output = result.stdout
    except Exception as e:
        version_output = f"Error: {str(e)}"
    
    return {
        "terraform_bin_env": os.getenv("TERRAFORM_BIN"),
        "terraform_path": terraform_path,
        "exists": exists,
        "executable": executable,
        "version_output": version_output,
        "ssl_cert_file_env": os.getenv("SSL_CERT_FILE"),
        "ssl_cert_exists": os.path.exists("/etc/ssl/certs/ca-certificates.crt"),
        "ca_bundle_env": os.getenv("REQUESTS_CA_BUNDLE")
    }

@app.get("/api/user-cloud-check")
async def user_cloud_check(request: Request, cloud: str = Query(...)):
    """
    Check whether the currently authenticated user has department resources
    configured for the given cloud ('aws' or 'azure').

    Resources are looked up exclusively from portal.portal_department_resources
    using the department extracted from the user's email domain.
    Manual per-user registration is no longer supported.

    Returns:
      {
        "authenticated": bool,
        "email": str | null,
        "oid": str | null,
        "registered": bool,                  // True if department has ≥1 active row for this cloud
        "resources": [str],                  // list of subscription_ids / account_ids
        "db_available": bool,
        "department_not_configured": bool,   // True when registered=False (department missing from table)
        "department": str                    // department extracted from email, or "unknown"
      }
    """
    user = get_current_user(request)
    if not user:
        return {"authenticated": False, "email": None, "oid": None, "registered": False,
                "resources": [], "db_available": DB_AVAILABLE}
    oid = user.get("oid")
    email = (user.get("email") or "").strip()
    if not email:
        return {"authenticated": True, "email": None, "oid": oid, "registered": False,
                "resources": [], "db_available": DB_AVAILABLE}
    if not DB_AVAILABLE or not get_resources_by_department:
        # DB unavailable — treat ADMIN_EMAILS users as registered for any cloud
        in_list = email.lower() in [a.lower() for a in ADMIN_EMAILS]
        return {"authenticated": True, "email": email, "oid": oid, "registered": in_list,
                "resources": [], "db_available": False}
    # ADMIN_EMAILS users are always considered registered
    if email.lower() in [a.lower() for a in ADMIN_EMAILS]:
        return {"authenticated": True, "email": email, "oid": oid, "registered": True,
                "resources": [], "db_available": True}
    try:
        # Department-based lookup — the only supported path
        department = extract_department_from_email(email)
        if department:
            try:
                dept_rows = get_resources_by_department(department, cloud)
                if dept_rows:
                    dept_ids = [r["subscription_id"] for r in dept_rows if r.get("subscription_id")]
                    return {"authenticated": True, "email": email, "oid": oid, "registered": True,
                            "resources": dept_ids, "db_available": True, "source": "department"}
            except Exception as e:
                logger.warning("user_cloud_check dept lookup failed for %s: %s", email, e)

        # Department not found or has no configured resources — registration form is not used
        return {
            "authenticated": True,
            "email": email,
            "oid": oid,
            "registered": False,
            "resources": [],
            "db_available": True,
            "department_not_configured": True,
            "department": department or "unknown",
            "source": "none"
        }
    except Exception as e:
        logger.exception("user_cloud_check DB error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to check user cloud access")


@app.get("/api/oci/config")
async def get_oci_config(request: Request):
    user = get_current_user(request)
    return {
        "enabled": _is_oci_runtime_enabled(),
        "authenticated": bool(user),
        "tenancies": get_oci_tenancies_for_user(user),
    }


@app.get("/api/oci/tenancies")
async def get_oci_tenancies(request: Request):
    if not _is_oci_runtime_enabled():
        return {"tenancies": []}
    user = get_current_user(request)
    if not user:
        return {"tenancies": []}
    return {"tenancies": get_oci_tenancies_for_user(user)}


@app.get("/api/oci/availability-domains")
async def get_oci_availability_domains(request: Request, tenancy_key: str = Query(...)):
    _ensure_oci_access(request, tenancy_key)
    try:
        return {"availability_domains": oci_list_availability_domains(tenancy_key)}
    except Exception as exc:
        _raise_oci_lookup_http_error("availability domains", tenancy_key, exc)


@app.get("/api/oci/compartments")
async def get_oci_compartments(request: Request, tenancy_key: str = Query(...)):
    _ensure_oci_access(request, tenancy_key)
    try:
        return {"compartments": oci_list_compartments(tenancy_key)}
    except Exception as exc:
        _raise_oci_lookup_http_error("compartments", tenancy_key, exc)


@app.get("/api/oci/vcns")
async def get_oci_vcns(request: Request, tenancy_key: str = Query(...), compartment_id: str = Query(...)):
    _ensure_oci_access(request, tenancy_key)
    try:
        return {"vcns": oci_list_vcns(tenancy_key, compartment_id)}
    except Exception as exc:
        logger.exception("OCI VCN lookup failed for %s/%s: %s", tenancy_key, compartment_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to load OCI networks: {exc}")


@app.get("/api/oci/subnets")
async def get_oci_subnets(
    request: Request,
    tenancy_key: str = Query(...),
    compartment_id: str = Query(...),
    vcn_id: str = Query(...),
):
    _ensure_oci_access(request, tenancy_key)
    try:
        return {"subnets": oci_list_subnets(tenancy_key, compartment_id, vcn_id)}
    except Exception as exc:
        logger.exception("OCI subnet lookup failed for %s/%s/%s: %s", tenancy_key, compartment_id, vcn_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to load OCI subnets: {exc}")


@app.get("/api/oci/nsgs")
async def get_oci_nsgs(
    request: Request,
    tenancy_key: str = Query(...),
    compartment_id: str = Query(...),
    vcn_id: str = Query(...),
):
    _ensure_oci_access(request, tenancy_key)
    try:
        return {"nsgs": oci_list_nsgs(tenancy_key, compartment_id, vcn_id)}
    except Exception as exc:
        logger.exception("OCI NSG lookup failed for %s/%s/%s: %s", tenancy_key, compartment_id, vcn_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to load OCI network security groups: {exc}")


@app.get("/api/oci/images")
async def get_oci_images(request: Request, tenancy_key: str = Query(...)):
    tenancy_summary = _ensure_oci_access(request, tenancy_key)
    image_source_tenancy_key, image_source_compartment_ocid, using_shared_image_source = _resolve_oci_image_source(tenancy_summary)
    try:
        response_payload = {
            "images": oci_list_images(
                image_source_tenancy_key,
                compartment_id=image_source_compartment_ocid,
            ),
            "using_shared_image_source": using_shared_image_source,
        }
        if using_shared_image_source:
            response_payload["image_source_tenancy_key"] = image_source_tenancy_key
        return response_payload
    except Exception as exc:
        logger.exception(
            "OCI image lookup failed for requested tenancy %s using source %s/%s: %s",
            tenancy_key,
            image_source_tenancy_key,
            image_source_compartment_ocid,
            exc,
        )
        raise HTTPException(status_code=500, detail=f"Failed to load OCI images: {exc}")


@app.get("/api/oci/shapes")
async def get_oci_shapes(
    request: Request,
    tenancy_key: str = Query(...),
    compartment_id: str = Query(...),
    image_id: str = Query(...),
):
    tenancy_summary = _ensure_oci_access(request, tenancy_key)
    lookup_tenancy_key = tenancy_key
    lookup_compartment_id = compartment_id
    try:
        source_tenancy_key, source_compartment_ocid, _using_shared_image_source = _resolve_oci_image_source(tenancy_summary)
        if source_tenancy_key and source_compartment_ocid:
            lookup_tenancy_key = source_tenancy_key
            lookup_compartment_id = source_compartment_ocid
    except Exception as exc:
        logger.warning("OCI shape lookup source resolution failed for tenancy %s: %s", tenancy_key, exc)
    try:
        return {"shapes": oci_list_shapes(lookup_tenancy_key, lookup_compartment_id, image_id)}
    except Exception as source_exc:
        if lookup_tenancy_key != tenancy_key or lookup_compartment_id != compartment_id:
            logger.warning(
                "OCI shape lookup failed for resolved image source %s/%s; retrying with requested tenancy scope %s/%s: %s",
                lookup_tenancy_key,
                lookup_compartment_id,
                tenancy_key,
                compartment_id,
                source_exc,
            )
            try:
                return {"shapes": oci_list_shapes(tenancy_key, compartment_id, image_id)}
            except Exception as requested_scope_exc:
                logger.exception(
                    "OCI shape lookup failed for requested tenancy %s/%s after source-scope failure",
                    tenancy_key,
                    compartment_id,
                )
                raise HTTPException(
                    status_code=500,
                    detail="Failed to load OCI shapes from both shared-image scope and requested tenancy scope.",
                ) from requested_scope_exc
        logger.exception(
            "OCI shape lookup failed for requested tenancy %s using source %s/%s",
            tenancy_key,
            lookup_tenancy_key,
            lookup_compartment_id,
        )
        raise HTTPException(status_code=500, detail="Failed to load OCI shapes.") from source_exc


@app.post("/api/oci/ssh-keypair")
async def generate_oci_ssh_keypair(request: Request):
    if not get_current_user(request):
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        key_size = 2048
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")
        public_key_openssh = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH,
        ).decode("utf-8")
        return JSONResponse(
            content={
                "algorithm": "RSA",
                "key_size": key_size,
                "public_key": public_key_openssh,
                "private_key_pem": private_key_pem,
            },
            headers={
                "Cache-Control": "no-store",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    except Exception as exc:
        logger.exception("OCI SSH keypair generation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate OCI SSH keypair")

class DeployRequest(BaseModel):
    cloud: str
    account: str
    vpc_id: Optional[str] = None
    subnet_id: Optional[str] = None
    security_group: Optional[str] = None
    vm_name: str
    ami_name: Optional[str] = None
    instance_type: Optional[str] = None
    key_pair_name: Optional[str] = None
    os_type: Optional[str] = None
    vm_username: Optional[str] = None
    vm_password: Optional[str] = None
    tags: Optional[Any] = None


class OciDeployRequest(BaseModel):
    tenancy_key: str
    compartment_id: str
    availability_domain: str
    subnet_id: str
    image_id: str
    shape: str
    vm_name: str
    assign_public_ip: bool = True
    nsg_ids: Optional[List[str]] = None
    ssh_public_key: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None
    data_protection: Optional[str] = None


@app.post("/api/oci/deploy")
async def deploy_oci_vm(request: Request, req: OciDeployRequest):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required for OCI deployment")

    tenancy_summary = _ensure_oci_access(request, req.tenancy_key)
    vm_name_input = (req.vm_name or "").strip()
    if not vm_name_input:
        raise HTTPException(status_code=400, detail="OCI VM name is required")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,29}", vm_name_input):
        raise HTTPException(
            status_code=400,
            detail="OCI VM name must start with a letter or number and contain only letters, numbers, and hyphens (max 30 characters)",
        )
    if not req.compartment_id or not req.availability_domain or not req.subnet_id or not req.image_id or not req.shape:
        raise HTTPException(status_code=400, detail="Missing required OCI deployment fields")

    user_email = (user or {}).get("email")
    unique_vm_name = f"{vm_name_input}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    parsed_tags = {
        str(key): str(value)
        for key, value in (req.tags or {}).items()
        if key and value not in (None, "")
    }
    if req.data_protection and "DataProtection" not in parsed_tags:
        parsed_tags["DataProtection"] = req.data_protection

    request_id = None
    try:
        if DB_AVAILABLE and insert_portal_request_all:
            request_id = insert_portal_request_all({
                "cloud_provider": "oci",
                "user_email": user_email,
                "user_oid": (user or {}).get("oid"),
                "vm_name_requested": vm_name_input,
                "vm_name_final": unique_vm_name,
                "tag_account_number": parsed_tags.get("AccountNumber"),
                "tag_approvers": parsed_tags.get("Approvers"),
                "tag_ps": parsed_tags.get("PS"),
                "status": "received",
                "payload_json": {
                    "cloud": "oci",
                    "tenancy_key": req.tenancy_key,
                    "compartment_id": req.compartment_id,
                    "availability_domain": req.availability_domain,
                    "subnet_id": req.subnet_id,
                    "image_id": req.image_id,
                    "shape": req.shape,
                    "vm_name": vm_name_input,
                    "unique_vm_name": unique_vm_name,
                    "assign_public_ip": req.assign_public_ip,
                    "nsg_ids": req.nsg_ids or [],
                    "ssh_public_key_provided": bool((req.ssh_public_key or "").strip()),
                    "tags": parsed_tags,
                    "data_protection": req.data_protection or "",
                },
            })
    except Exception as db_err:
        logger.warning("OCI DB logging failed (non-blocking): %s", db_err)

    try:
        launch_result = oci_launch_instance(
            req.tenancy_key,
            compartment_id=req.compartment_id,
            availability_domain=req.availability_domain,
            subnet_id=req.subnet_id,
            image_id=req.image_id,
            shape=req.shape,
            vm_name=unique_vm_name,
            assign_public_ip=bool(req.assign_public_ip),
            nsg_ids=req.nsg_ids or [],
            ssh_public_key=(req.ssh_public_key or "").strip() or None,
            tags=parsed_tags or None,
        )

        response: Dict[str, Any] = {
            "status": "success",
            "cloud": "oci",
            "vm_name": launch_result.get("vm_name") or unique_vm_name,
            "instance_id": launch_result.get("instance_id"),
            "lifecycle_state": launch_result.get("lifecycle_state"),
            "availability_domain": launch_result.get("availability_domain") or req.availability_domain,
            "tenancy_key": req.tenancy_key,
            "tenancy_name": tenancy_summary.get("name") or req.tenancy_key,
            "region": tenancy_summary.get("region"),
            "compartment_id": req.compartment_id,
            "subnet_id": req.subnet_id,
            "shape": req.shape,
            "image_id": req.image_id,
        }

        try:
            _sync_portal_request_vm_outcome("oci", unique_vm_name, "launched", None)
        except Exception:
            pass

        _audit(
            request,
            action_type="create",
            cloud_provider="oci",
            resource_name=response["vm_name"],
            resource_id=response.get("instance_id"),
            account_or_subscription=req.tenancy_key,
            region_or_zone=tenancy_summary.get("region"),
            detail=f"OCI VM launched in compartment {req.compartment_id}",
            status="success",
        )

        if CHERWELL_INTEGRATION_AVAILABLE and create_post_deployment_tasks:
            try:
                vm_details = {
                    "vm_name": response["vm_name"],
                    "cloud": "oci",
                    "account": req.tenancy_key,
                    "account_name_display": tenancy_summary.get("name") or req.tenancy_key,
                    "region": tenancy_summary.get("region"),
                    "instance_type": req.shape,
                    "image_id": req.image_id,
                    "availability_domain": response.get("availability_domain"),
                    "compartment_id": req.compartment_id,
                    "data_protection": req.data_protection or "",
                    "tags": parsed_tags,
                }
                response["cherwell"] = create_post_deployment_tasks(response["vm_name"], "oci", vm_details, user_email=user_email)
            except Exception as cherwell_err:
                logger.exception("OCI Cherwell task creation failed (non-blocking): %s", cherwell_err)
                response["cherwell"] = {"error": str(cherwell_err)}

        if request_id:
            response["request_id"] = request_id
        return response
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("OCI deployment failed for tenancy %s: %s", req.tenancy_key, exc)
        try:
            _sync_portal_request_vm_outcome("oci", unique_vm_name, "failed", str(exc))
        except Exception:
            pass
        _audit(
            request,
            action_type="create",
            cloud_provider="oci",
            resource_name=unique_vm_name,
            account_or_subscription=req.tenancy_key,
            region_or_zone=tenancy_summary.get("region"),
            detail=f"OCI VM launch failed in compartment {req.compartment_id}",
            status="failed",
            error_message=str(exc),
        )
        raise HTTPException(status_code=500, detail=f"OCI deployment failed: {exc}")

@app.get("/accounts/aws")
async def get_aws_accounts(request: Request):
    user = get_current_user(request)
    if not user:
        logger.warning("Unauthenticated access attempt to /accounts/aws")
        return {"accounts": []}
    try:
        user_email = user.get("email", "Unknown User")
        if is_admin(user):
            logger.info(f"Admin access granted for {user_email}. Returning all {len(ALLOWED_AWS_ACCOUNTS)} accounts.")
            return {"accounts": ALLOWED_AWS_ACCOUNTS}
        email = user.get("email", "")
        # ISD-specific path: fine-grained per-user AWS account access control
        if email and DB_AVAILABLE and get_isd_subscriptions_for_email:
            department = extract_department_from_email(email)
            if department and department.lower() == "isd":
                try:
                    allowed_ids = get_isd_subscriptions_for_email(email, cloud="aws")
                    if allowed_ids is not None:
                        allowed_map = {a["account_id"]: a["account_name"] for a in ALLOWED_AWS_ACCOUNTS}
                        return {"accounts": [
                            {"account_id": aid, "account_name": allowed_map.get(aid, aid)}
                            for aid in allowed_ids
                        ]}
                    # Email not found in any ISD table
                    logger.info(
                        "ISD user %s not found in any ISD access table; returning empty AWS account list",
                        email,
                    )
                    raise HTTPException(
                        status_code=403,
                        detail=(
                            "Your ISD account is not yet configured for AWS access. "
                            "Please contact your ISD administrator to be added to the "
                            "appropriate access group."
                        ),
                    )
                except HTTPException:
                    raise
                except Exception as e:
                    logger.warning("DB ISD AWS account filter failed for %s: %s", email, e)
        raw_assignments = get_aws_accounts_for_user(user)
        allowed_map = {a["account_id"]: a["account_name"] for a in ALLOWED_AWS_ACCOUNTS}
        user_accessible_accounts = []
        found_ids = set()
        for assignment in raw_assignments:
            aid = assignment.get("account_id")
            if aid in allowed_map and aid not in found_ids:
                user_accessible_accounts.append({"account_id": aid, "account_name": allowed_map[aid]})
                found_ids.add(aid)
        return {"accounts": user_accessible_accounts}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in get_aws_accounts: %s", e)
        return {"accounts": []}

# ✅ FIXED: Deploy endpoint now accepts AMI ID and parses tags correctly
@app.post("/deploy")
async def deploy_vm_form(
    request: Request,
    cloud: str = Form(...),
    account: str = Form(...),
    vpc_id: str = Form(...),
    subnet_id: str = Form(...),
    security_group: str = Form(...),
    vm_name: str = Form(...),
    ami_name: str = Form(...),  # ✅ This is now the AMI ID (e.g., ami-0123456789abcdef0)
    os_type: str = Form(...),
    instance_type: str = Form(...),
    key_pair_name: Optional[str] = Form(None),
    vm_username: Optional[str] = Form(None),
    vm_password: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # ✅ Tags as JSON string
    data_protection: Optional[str] = Form(None)
):
    if not is_account_allowed(request, account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    if not instance_type:
        raise HTTPException(status_code=400, detail="Instance type is required")
    
    user = get_current_user(request)
    user_email = user.get("email") if user else None
    
    unique_vm_name = f"{vm_name}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    # ✅ Parse tags from JSON string
    parsed_tags = {}
    if tags:
        try:
            parsed_tags = json.loads(tags)
            logger.info(f"Parsed custom tags for {vm_name}: {parsed_tags}")
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse tags JSON: {tags}")

    _extract_and_validate_billing_account(parsed_tags)
    
    # ✅ Use AMI ID directly (no AMI_MAP lookup)
    ami_id = ami_name  # The frontend now sends the actual AMI ID
    
    if not ami_id or not ami_id.startswith("ami-"):
        raise HTTPException(status_code=400, detail=f"Invalid AMI ID: {ami_id}. Expected format: ami-XXXXXXXXXXXX")
        # ---- DB logging for AWS (non-blocking) ----
    try:
        if DB_AVAILABLE and insert_portal_request_all:
            tag_account_number = (parsed_tags or {}).get("AccountNumber")
            tag_approvers = (parsed_tags or {}).get("Approvers")
            tag_ps = (parsed_tags or {}).get("PS")

            payload_snapshot = {
                "cloud": cloud,
                "account": account,
                "vpc_id": vpc_id,
                "subnet_id": subnet_id,
                "security_group": security_group,
                "vm_name": vm_name,
                "unique_vm_name": unique_vm_name,
                "ami_id": ami_id,
                "os_type": os_type,
                "instance_type": instance_type,
                "vm_username": vm_username,
                "tags": parsed_tags,
            }

            insert_portal_request_all({
                "cloud_provider": "aws",
                "user_email": user_email,
                "user_oid": (user or {}).get("oid"),

                "vm_name_requested": vm_name,
                "vm_name_final": unique_vm_name,

                "tag_account_number": tag_account_number,
                "tag_approvers": tag_approvers,
                "tag_ps": tag_ps,

                "status": "received",
                "payload_json": payload_snapshot,

                "aws_account_id": account,
                "aws_region": os.getenv("TF_VAR_region", "us-west-2"),
                "aws_vpc_id": vpc_id,
                "aws_subnet_id": subnet_id,
                "aws_ami_id": ami_id,
                "aws_os_type": os_type,
                "aws_instance_type": instance_type,
                "aws_security_group_id": security_group,
                "aws_key_pair_name": key_pair_name or "",
            })
    except Exception as db_err:
        logger.warning("DB logging failed (non-blocking): %s", db_err)
    
    new_vm_config = {
        "ami_id": ami_id,  # ✅ Direct AMI ID
        "instance_type": instance_type,
        "subnet_id": subnet_id,
        "security_group_ids": [security_group] if security_group else [],
        "key_pair_name": key_pair_name or "",
        "vm_name": unique_vm_name,
        "account": account,
    }
    
    # ✅ Add tags to VM config
    if parsed_tags:
        new_vm_config["tags"] = parsed_tags
    
    update_vms_store(new_vm_config, unique_vm_name)
    # Only pass the current VM to Terraform — passing the full store would cause
    # every previously-deployed VM to be re-created (duplicates) because state is
    # wiped after each run via cleanup_terraform_state().
    single_vm = {unique_vm_name: new_vm_config}
    return run_terraform(cloud, account, vpc_id, subnet_id, security_group, unique_vm_name, ami_id, os_type, instance_type, key_pair_name or "", single_vm, user_email=user_email, data_protection=data_protection or "", vm_username=vm_username, vm_password=vm_password)

@app.post("/api/deploy")
async def deploy_vm_json(request: Request, req: DeployRequest):
    if not is_account_allowed(request, req.account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    if not req.instance_type:
        raise HTTPException(status_code=400, detail="Instance type is required")
    
    user = get_current_user(request)
    user_email = user.get("email") if user else None
    
    unique_vm_name = f"{req.vm_name}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    parsed_tags = parse_tags_from_payload({"tags": req.tags})
    _extract_and_validate_billing_account(parsed_tags)
    
    # ✅ Use AMI ID directly
    ami_id = req.ami_name
    
    if not ami_id or not ami_id.startswith("ami-"):
        raise HTTPException(status_code=400, detail=f"Invalid AMI ID: {ami_id}")
        # ---- DB logging for AWS (JSON endpoint; non-blocking) ----
    try:
        if DB_AVAILABLE and insert_portal_request_all:
            payload_snapshot = {
                "cloud": req.cloud,
                "account": req.account,
                "vpc_id": req.vpc_id,
                "subnet_id": req.subnet_id,
                "security_group": req.security_group,
                "vm_name": req.vm_name,
                "unique_vm_name": unique_vm_name,
                "ami_id": ami_id,
                "os_type": req.os_type,
                "instance_type": req.instance_type,
                "key_pair_name": req.key_pair_name,
                "tags": parsed_tags,
            }

            insert_portal_request_all({
                "cloud_provider": "aws",
                "user_email": user_email,
                "user_oid": (user or {}).get("oid"),

                "vm_name_requested": req.vm_name,
                "vm_name_final": unique_vm_name,

                "status": "received",
                "payload_json": payload_snapshot,

                "aws_account_id": req.account,
                "aws_region": os.getenv("TF_VAR_region", "us-west-2"),
                "aws_vpc_id": req.vpc_id,
                "aws_subnet_id": req.subnet_id,
                "aws_ami_id": ami_id,
                "aws_os_type": req.os_type,
                "aws_instance_type": req.instance_type,
                "aws_security_group_id": req.security_group,
                "aws_key_pair_name": req.key_pair_name,
            })
    except Exception as db_err:
        logger.warning("DB logging failed (non-blocking): %s", db_err)
    
    new_vm_config = {
        "ami_id": ami_id,
        "instance_type": req.instance_type,
        "subnet_id": req.subnet_id,
        "security_group_ids": [req.security_group] if req.security_group else [],
        "key_pair_name": req.key_pair_name or "",
        "vm_name": unique_vm_name,
        "account": req.account,
    }
    if parsed_tags:
        new_vm_config["tags"] = parsed_tags
    update_vms_store(new_vm_config, unique_vm_name)
    # Only pass the current VM to Terraform — passing the full store would cause
    # every previously-deployed VM to be re-created (duplicates) because state is
    # wiped after each run via cleanup_terraform_state().
    single_vm = {unique_vm_name: new_vm_config}
    return run_terraform(req.cloud, req.account, req.vpc_id, req.subnet_id, req.security_group, unique_vm_name, ami_id, req.os_type, req.instance_type, req.key_pair_name or "", single_vm, user_email=user_email, vm_username=req.vm_username, vm_password=req.vm_password)

@app.get("/vpcs/aws")
async def get_aws_vpcs(request: Request, account: str = Query(...), region: str = Query(...)):
    if not is_account_allowed(request, account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    session = assume_role(account)
    ec2 = session.client("ec2", region_name=region)
    try:
        vpcs = ec2.describe_vpcs().get("Vpcs", [])
        return {"vpcs": [{"vpc_id": v.get("VpcId"), "cidr_block": v.get("CidrBlock", "")} for v in vpcs]}
    except ClientError as e:
        logger.exception("EC2 describe_vpcs failed: %s", e)
        raise HTTPException(status_code=500, detail=f"AWS Error: {str(e)}")

@app.get("/subnets/aws")
async def get_aws_subnets(request: Request, vpc_id: str = Query(...), account: str = Query(...), region: str = Query(...)):
    if not is_account_allowed(request, account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    session = assume_role(account)
    ec2 = session.client("ec2", region_name=region)
    try:
        subnets = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]).get("Subnets", [])
        result_subnets = []
        for sn in subnets:
            result_subnets.append({
                "subnet_id": sn.get("SubnetId"), 
                "cidr_block": sn.get("CidrBlock"),
                "availability_zone": sn.get("AvailabilityZone", "")
            })
        return {"subnets": result_subnets}
    except ClientError as e:
        logger.exception("EC2 describe_subnets failed: %s", e)
        raise HTTPException(status_code=500, detail=f"AWS Error: {str(e)}")

@app.get("/security-groups/aws")
async def get_aws_security_groups(request: Request, vpc_id: str = Query(...), account: str = Query(...)):
    if not is_account_allowed(request, account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    session = assume_role(account)
    ec2 = session.client("ec2")
    try:
        groups = ec2.describe_security_groups(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]).get("SecurityGroups", [])
        return {"security_groups": [{"group_id": sg.get("GroupId"), "group_name": sg.get("GroupName")} for sg in groups]}
    except ClientError as e:
        logger.exception("EC2 describe_security_groups failed: %s", e)
        raise HTTPException(status_code=500, detail=f"AWS Error: {str(e)}")

# ✅ FIXED: AMI endpoint now returns actual AMI IDs (not names)
@app.get("/amis/aws")
async def get_shared_amis(request: Request, account: str = Query(...), region: str = Query(...)):
    """Get AMIs from the AWS account (dynamically fetched, not hardcoded).
    
    Returns AMI ID and Name so frontend can display name but submit ID.
    """
    if not is_account_allowed(request, account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    session = assume_role(account)
    ec2 = session.client("ec2", region_name=region)
    try:
        # Fetch images owned by the ISD account (476553995083) or change this to match your AMI owner
        images = ec2.describe_images(Owners=["476553995083"]).get("Images", [])
        sorted_images = sorted(images, key=lambda x: x.get("CreationDate", ""), reverse=True)
        
        # ✅ Return both ami_id and name so frontend can display name but submit ID
        return {"amis": [
            {
                "ami_id": img.get("ImageId"),  # ✅ Actual AMI ID (e.g., ami-0123456789abcdef0)
                "name": img.get("Name", img.get("ImageId"))  # Display name
            } 
            for img in sorted_images
        ]}
    except ClientError as e:
        logger.exception("describe_images failed: %s", e)
        raise HTTPException(status_code=500, detail=f"AMI fetch error: {str(e)}")

@app.get("/instance-types/aws")
async def get_aws_instance_types(request: Request, account: str = Query(...), region: str = Query(...)):
    if not is_account_allowed(request, account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    cache_key = f"{account}:{region}"
    with _aws_instance_types_lock:
        cached_result = _aws_instance_types_cache.get(cache_key)
    if cached_result is not None:
        return {"instance_types": cached_result}
    session = assume_role(account)
    # Increase max_pool_connections to avoid "Connection pool is full" warnings
    ec2 = session.client("ec2", region_name=region, config=BotocoreConfig(max_pool_connections=25))
    try:
        paginator = ec2.get_paginator('describe_instance_types')
        instance_types = []
        for page in paginator.paginate():
            instance_types.extend(page.get('InstanceTypes', []))
        types_detailed = []
        for it in instance_types:
            if 'InstanceType' in it:
                name = it.get('InstanceType')
                types_detailed.append({
                    'name': name,
                    'vcpus': it.get('VCpuInfo', {}).get('DefaultVCpus', 0),
                    'memory': it.get('MemoryInfo', {}).get('SizeInMiB', 0),
                    'price_per_hour': _get_aws_instance_price(name),
                })
        types_detailed.sort(key=lambda x: x['name'])
        with _aws_instance_types_lock:
            _aws_instance_types_cache[cache_key] = types_detailed
        return {"instance_types": types_detailed}
    except ClientError as e:
        logger.exception("describe_instance_types failed: %s", e)
        raise HTTPException(status_code=500, detail=f"AWS Error fetching instance types: {str(e)}")

@app.post("/create-keypair/aws")
async def create_key_pair(request: Request, account: str = Query(...)):
    if not is_account_allowed(request, account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    session = assume_role(account)
    ec2 = session.client("ec2")
    key_name = f"auto-key-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    try:
        key_pair = ec2.create_key_pair(KeyName=key_name)
        return {"key_pair_name": key_name, "message": "Key pair created.", "private_key": key_pair.get('KeyMaterial')}
    except ClientError as e:
        logger.exception("create_key_pair failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Key pair error: {str(e)}")

@app.post("/security-groups/aws/create")
async def create_aws_security_group(request: Request):
    payload = await request.json()
    account = payload.get("account")
    vpc_id = payload.get("vpc_id")
    raw_name = payload.get("name") or ""
    description = payload.get("description") or "Created by Multi-Cloud Portal"
    rules = payload.get("rules", [])
    if not account or not vpc_id:
        raise HTTPException(status_code=400, detail="Missing required fields: account and vpc_id")
    if not is_account_allowed(request, account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    user = get_current_user(request)
    owner_email = (user or {}).get("email") or "unknown"
    effective_name = raw_name.strip() or f"mc-sg-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    sanitized = False
    if effective_name.lower().startswith("sg-"):
        effective_name = "mc-" + effective_name[3:]
        sanitized = True
    if len(effective_name) > 255:
        raise HTTPException(status_code=400, detail="Security group name too long (max 255 characters).")
    parsed_rules = []
    try:
        for r in rules:
            proto = (r.get("protocol") or "tcp").lower()
            port = int(r.get("port")) if r.get("port") is not None else None
            direction = (r.get("direction") or "ingress").lower()
            cidrs = r.get("cidrs") or []
            if isinstance(cidrs, str):
                cidrs = [c.strip() for c in cidrs.split(",") if c.strip()]
            if not isinstance(cidrs, list):
                raise ValueError("cidrs must be a list or comma-separated string")
            cidrs_clean = validate_cidrs_list(cidrs)
            if port is None:
                raise ValueError("port is required for each rule")
            if direction not in ("ingress", "egress"):
                raise ValueError("direction must be 'ingress' or 'egress'")
            parsed_rules.append({"protocol": proto, "port": port, "direction": direction, "cidrs": cidrs_clean})
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    try:
        session = assume_role(account)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception("Assume role failed for create SG: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    ec2 = session.client("ec2")
    try:
        resp = ec2.create_security_group(Description=description, GroupName=effective_name[:255], VpcId=vpc_id)
        group_id = resp.get("GroupId")
        logger.info("Created security group %s (name=%s) in account %s vpc %s", group_id, effective_name, account, vpc_id)
    except ClientError as e:
        code = getattr(e, "response", {}).get("Error", {}).get("Code", "")
        msg = getattr(e, "response", {}).get("Error", {}).get("Message", str(e))
        suggested = None
        if "InvalidParameterValue" in str(code) or "Group names may not be in the format sg-" in str(msg):
            suggested = ("mc-" + (raw_name[3:] if raw_name.lower().startswith("sg-") else raw_name)).strip() or (f"mc-sg-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
            raise HTTPException(status_code=400, detail=f"AWS rejected provided name. Suggested effective name: '{suggested}'. Original error: {msg}")
        logger.exception("create_security_group failed: %s", e)
        raise HTTPException(status_code=500, detail=f"AWS Error creating security group: {str(e)}")
    try:
        ec2.create_tags(Resources=[group_id], Tags=[{"Key": "Project", "Value": "MultiCloudPortal"}, {"Key": "Owner", "Value": owner_email}])
    except ClientError as e:
        logger.warning("Failed to tag security group %s: %s", group_id, e)
    for r in parsed_rules:
        ip_ranges = [{"CidrIp": c} for c in r["cidrs"]]
        ip_permission = {"IpProtocol": r["protocol"], "FromPort": r["port"], "ToPort": r["port"], "IpRanges": ip_ranges}
        try:
            if r["direction"] == "ingress":
                try:
                    ec2.authorize_security_group_ingress(GroupId=group_id, IpPermissions=[ip_permission])
                except ClientError as ce:
                    code = getattr(ce, "response", {}).get("Error", {}).get("Code", "")
                    if code and "InvalidPermission.Duplicate" in code:
                        logger.debug("Duplicate ingress rule for SG %s ignored", group_id)
                    else:
                        raise
            else:
                try:
                    ec2.authorize_security_group_egress(GroupId=group_id, IpPermissions=[ip_permission])
                except ClientError as ce:
                    code = getattr(ce, "response", {}).get("Error", {}).get("Code", "")
                    if code and "InvalidPermission.Duplicate" in code:
                        logger.debug("Duplicate egress rule for SG %s ignored", group_id)
                    else:
                        raise
        except ClientError as e:
            logger.exception("Failed to authorize security group rule on %s: %s", group_id, e)
            raise HTTPException(status_code=500, detail=f"Failed to add rule: {str(e)}")
    return {"group_id": group_id, "group_name": effective_name, "original_name": raw_name, "effective_name": effective_name, "sanitized": sanitized}

def _list_sp_subscriptions_internal() -> List[Dict[str, str]]:
    creds = get_azure_credentials()
    client = SubscriptionClient(creds)
    subs = []
    for s in client.subscriptions.list():
        subs.append({"id": s.subscription_id, "name": s.display_name})
    return subs

@cached(sp_subs_cache)
def get_azure_subscriptions_sp_cached() -> List[Dict[str, str]]:
    try:
        return _list_sp_subscriptions_internal()
    except Exception as e:
        logger.exception("SP subscription listing failed (cached): %s", e)
        raise RuntimeError("Could not list subscriptions: " + str(e))

@app.get("/api/azure/subscriptions")
def list_subscriptions(request: Request):
    user = get_current_user(request)
    try:
        sp_subs = get_azure_subscriptions_sp_cached()
    except Exception as e:
        logger.exception("Could not list subscriptions: %s", e)
        raise HTTPException(status_code=500, detail="Could not list subscriptions")
    if user:
        if is_admin(user):
            return sp_subs
        email = (user or {}).get("email", "")
        # ISD-specific path: fine-grained per-user subscription access control
        if email and DB_AVAILABLE and get_isd_subscriptions_for_email:
            department = extract_department_from_email(email)
            if department and department.lower() == "isd":
                try:
                    allowed_ids = get_isd_subscriptions_for_email(email)
                    if allowed_ids is not None:
                        sp_map = {s["id"]: s for s in sp_subs}
                        result = [
                            sp_map.get(sid) or {"id": sid, "name": sid}
                            for sid in allowed_ids
                        ]
                        return [s for s in result if s]
                    # Email not found in any ISD table
                    logger.info(
                        "ISD user %s not found in any ISD access table; returning empty subscription list",
                        email,
                    )
                    raise HTTPException(
                        status_code=403,
                        detail=(
                            "Your ISD account is not yet configured for Azure access. "
                            "Please contact your ISD administrator to be added to the "
                            "appropriate access group."
                        ),
                    )
                except HTTPException:
                    raise
                except Exception as e:
                    logger.warning("DB ISD subscription filter failed for %s: %s", email, e)
        # Department-based path: return subscriptions pre-loaded for user's department
        if email and DB_AVAILABLE and get_resources_by_department:
            department = extract_department_from_email(email)
            if department:
                try:
                    dept_rows = get_resources_by_department(department, "azure")
                    if dept_rows:
                        dept_ids = {r["subscription_id"] for r in dept_rows if r.get("subscription_id")}
                        dept_name_map = {r["subscription_id"]: r["subscription_name"] for r in dept_rows}
                        sp_map = {s["id"]: s for s in sp_subs}
                        dept_subs = [
                            sp_map.get(sid) or {"id": sid, "name": dept_name_map.get(sid, sid)}
                            for sid in dept_ids
                        ]
                        return [s for s in dept_subs if s]
                except Exception as e:
                    logger.warning("DB dept subscription filter failed for %s: %s", email, e)
            # Department not found or has no configured Azure subscriptions
            logger.info("No department resources configured for %s (dept=%s) on azure", email, department or "unknown")
            dept_label = f" ({department})" if department else ""
            raise HTTPException(
                status_code=403,
                detail=f"Your department{dept_label} is not yet configured for Azure access. "
                       f"Please contact your administrator to have your department added."
            )
        # Fallback: OID-based assignment (for non-lacounty.gov or when DB unavailable)
        user_oid = (user or {}).get("oid")
        if not user_oid:
            raise HTTPException(status_code=401, detail="Not authenticated")
        allowed_ids = get_user_subscription_ids_cached(user_oid)
        visible = [s for s in sp_subs if s["id"] in allowed_ids]
        return visible
    else:
        return sp_subs

@app.get("/api/azure/resource-groups")
def list_resource_groups(request: Request, subscription_id: str = Query(...)):
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        groups = get_resource_groups_cached(subscription_id)
        return groups
    except Exception as e:
        logger.exception("list_resource_groups failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/azure/subscription-tags")
def get_subscription_tags(request: Request, subscription_id: str = Query(...)):
    """Return the tags on an Azure subscription (e.g. AccountNumber)."""
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        creds = get_azure_credentials_service_principal()
        tags = {}
        # Primary: use ResourceManagementClient.tags.get_at_scope() — works across
        # all azure-mgmt-resource versions and avoids the SDK-version-dependent
        # 'Subscription' object attribute issue.
        try:
            rc = ResourceManagementClient(creds, subscription_id)
            scope = f"/subscriptions/{subscription_id}"
            tags_resource = rc.tags.get_at_scope(scope)
            if tags_resource and tags_resource.properties:
                tags = dict(tags_resource.properties.tags or {})
        except Exception as tags_scope_err:
            logger.debug("get_at_scope tags failed, trying Subscription object: %s", tags_scope_err)
            # Fallback: try the Subscription object (SDK version dependent)
            try:
                sub_client = SubscriptionClient(creds)
                sub = sub_client.subscriptions.get(subscription_id)
                raw = getattr(sub, "tags", None)
                if raw is None:
                    raw = (getattr(sub, "additional_properties", None) or {}).get("tags")
                tags = dict(raw or {})
            except Exception as sub_tags_err:
                logger.debug("Subscription.tags fallback also failed: %s", sub_tags_err)
                tags = {}
        return {"tags": tags}
    except Exception as e:
        logger.exception("get_subscription_tags failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/azure/vnets")
def list_vnets(request: Request, subscription_id: str = Query(...)):
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        client = NetworkManagementClient(get_azure_credentials_service_principal(), subscription_id)
        vnets = client.virtual_networks.list_all()
        return [
            {"id": vnet.id, "name": vnet.name, "resource_group": vnet.id.split("/")[4] if "/" in vnet.id else None, "location": vnet.location}
            for vnet in vnets
        ]
    except Exception as e:
        logger.exception("list_vnets failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/azure/nsgs")
def list_nsgs(request: Request, subscription_id: str = Query(...), resource_group: str = Query(...)):
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        client = NetworkManagementClient(get_azure_credentials_service_principal(), subscription_id)
        nsgs = client.network_security_groups.list(resource_group)
        return [{"id": nsg.id, "name": nsg.name} for nsg in nsgs]
    except Exception as e:
        logger.exception("list_nsgs failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/azure/subnets")
def list_subnets(request: Request, subscription_id: str = Query(...), resource_group: str = Query(...), vnet_name: str = Query(...)):
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        client = NetworkManagementClient(get_azure_credentials_service_principal(), subscription_id)
        subnets = client.subnets.list(resource_group, vnet_name)
        result = []
        for s in subnets:
            unsupported_reasons = []

            # Check delegations (e.g. Microsoft.Web/serverFarms, Microsoft.ContainerInstance/containerGroups)
            delegations = getattr(s, "delegations", None) or []
            delegation_services = [d.service_name for d in delegations if getattr(d, "service_name", None)]
            if delegation_services:
                unsupported_reasons.append("delegated to: " + ", ".join(delegation_services))

            # Check resource navigation links — set when subnet is owned by an external resource
            # (e.g. AKS node pools, Azure HDInsight, SQL Managed Instance)
            resource_nav_links = getattr(s, "resource_navigation_links", None) or []
            nav_link_names = [
                getattr(lnk, "linked_resource_type", None) or getattr(lnk, "name", None)
                for lnk in resource_nav_links
                if lnk is not None
            ]
            nav_link_names = [n for n in nav_link_names if n]
            if nav_link_names:
                unsupported_reasons.append("has external resource links: " + ", ".join(nav_link_names))

            # Check service association links — set by services like SQL Managed Instance, Azure Bastion
            service_assoc_links = getattr(s, "service_association_links", None) or []
            assoc_link_names = [
                getattr(lnk, "linked_resource_type", None) or getattr(lnk, "name", None)
                for lnk in service_assoc_links
                if lnk is not None
            ]
            assoc_link_names = [n for n in assoc_link_names if n]
            if assoc_link_names:
                unsupported_reasons.append("used by service: " + ", ".join(assoc_link_names))

            supported = len(unsupported_reasons) == 0
            warning = None
            if not supported:
                warning = "The selected subnet is not supported — " + "; ".join(unsupported_reasons)

            result.append({
                "id": s.id,
                "name": s.name,
                "address_prefix": getattr(s, "address_prefix", None) or getattr(s, "addressPrefixes", None),
                "supported": supported,
                "warning": warning,
            })
        return result
    except Exception as e:
        logger.exception("list_subnets failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

def _parse_azure_subnet_resource_id(subnet_id: str) -> Optional[Dict[str, str]]:
    match = re.match(
        r"^/subscriptions/(?P<subscription_id>[^/]+)/resourceGroups/(?P<resource_group>[^/]+)/providers/Microsoft\.Network/virtualNetworks/(?P<vnet_name>[^/]+)/subnets/(?P<subnet_name>[^/]+)$",
        (subnet_id or "").strip(),
        re.IGNORECASE,
    )
    return match.groupdict() if match else None

def _parse_azure_resource_group_from_resource_id(resource_id: str) -> str:
    match = re.search(r"/resourceGroups/(?P<resource_group>[^/]+)/", (resource_id or "").strip(), re.IGNORECASE)
    return match.group("resource_group") if match else ""

def _clean_azure_error_message(error_message: str) -> str:
    error_message = str(error_message or "").strip()
    if AZURE_SDK_ERROR_CONTENT_SEPARATOR in error_message:
        error_message = error_message.split(AZURE_SDK_ERROR_CONTENT_SEPARATOR, 1)[0].strip()
    return error_message

def _get_azure_resource_properties(resource: Any) -> Dict[str, Any]:
    properties = getattr(resource, "properties", None)
    if isinstance(properties, dict):
        return properties
    if properties is not None and hasattr(properties, "as_dict"):
        try:
            return properties.as_dict()
        except Exception:
            return {}
    return {}

def _extract_azure_status_message(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    status_message = payload.get("statusMessage") or payload.get("status_message")
    if isinstance(status_message, str):
        try:
            status_message = json.loads(status_message)
        except Exception:
            return status_message
    if isinstance(status_message, dict):
        error_obj = status_message.get("error") if isinstance(status_message.get("error"), dict) else status_message
        message = error_obj.get("message") or error_obj.get("details")
        if isinstance(message, list):
            message = "; ".join(str(item) for item in message if item)
        if message:
            return str(message)
    error_obj = payload.get("error")
    if isinstance(error_obj, dict) and error_obj.get("message"):
        return str(error_obj["message"])
    if payload.get("message"):
        return str(payload["message"])
    return ""

def _raise_if_azure_resource_failed(resource: Any, resource_name: str) -> None:
    properties = _get_azure_resource_properties(resource)
    provisioning_state = (
        properties.get("provisioningState")
        or properties.get("provisioning_state")
        or getattr(resource, "provisioning_state", None)
        or ""
    )
    if str(provisioning_state).lower() != "failed":
        return
    status_message = _extract_azure_status_message(properties)
    detail = status_message or f"Azure resource '{resource_name}' provisioning state is Failed."
    raise HTTPException(status_code=500, detail=f"Azure SQL Managed Instance deployment failed: {detail}")

def _get_sql_managed_instance_state(resource: Any) -> Tuple[str, str]:
    properties = _get_azure_resource_properties(resource)
    provisioning_state = (
        properties.get("provisioningState")
        or properties.get("provisioning_state")
        or getattr(resource, "provisioning_state", None)
        or ""
    )
    state = properties.get("state") or properties.get("status") or ""
    return str(provisioning_state), str(state)

def _sql_managed_instance_is_ready(resource: Any) -> bool:
    provisioning_state, state = _get_sql_managed_instance_state(resource)
    provisioning_state = provisioning_state.lower()
    state = state.lower()
    return provisioning_state == "succeeded" and (not state or state in ("ready", "online"))

def _wait_for_sql_managed_instance_ready(
    resource_client: ResourceManagementClient,
    data: Dict[str, Any],
    managed_instance_name: str,
    deployment_id: str,
    resource_id: str,
) -> Any:
    deadline = time.time() + (8 * 60 * 60)
    last_message = ""
    while time.time() < deadline:
        resource = resource_client.resources.get(
            resource_group_name=data["resource_group"],
            resource_provider_namespace="Microsoft.Sql",
            parent_resource_path="",
            resource_type="managedInstances",
            resource_name=managed_instance_name,
            api_version=AZURE_SQL_MI_API_VERSION,
        )
        _raise_if_azure_resource_failed(resource, managed_instance_name)
        if _sql_managed_instance_is_ready(resource):
            return resource
        provisioning_state, state = _get_sql_managed_instance_state(resource)
        message = (
            f"Azure SQL Managed Instance {managed_instance_name} is still provisioning"
            f" (provisioningState={provisioning_state or 'unknown'}, state={state or 'unknown'})."
        )
        if message != last_message:
            update_deployment_status(deployment_id, "running", message, vm_id=getattr(resource, "id", None) or resource_id)
            last_message = message
        time.sleep(60)
    raise TimeoutError(f"Timed out waiting for Azure SQL Managed Instance {managed_instance_name} to become ready.")

def _check_sql_managed_instance_name_available(creds: Any, subscription_id: str, name: str) -> None:
    try:
        token = creds.get_token(AZURE_MANAGEMENT_SCOPE).token
        url = (
            f"https://management.azure.com/subscriptions/{subscription_id}"
            f"/providers/Microsoft.Sql/checkNameAvailability?api-version={AZURE_SQL_MI_API_VERSION}"
        )
        payload = {"name": name, "type": "Microsoft.Sql/managedInstances"}
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
            timeout=15,
            verify=HTTP_VERIFY,
        )
        if resp.status_code >= 400:
            logger.warning("SQL MI name availability check failed (%s): %s", resp.status_code, resp.text)
            return
        body = resp.json()
        if body.get("nameAvailable") is False:
            message = body.get("message") or body.get("reason") or f"The managed instance name '{name}' is not available."
            raise HTTPException(status_code=409, detail=message)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("SQL MI name availability check could not be completed: %s", exc)

def _deploy_sql_managed_instance_background(
    deployment_id: str,
    data: Dict[str, Any],
    location: str,
    managed_instance_name: str,
    params: Dict[str, Any],
    require_entra_auth: bool,
    auth_method: str,
    entra_admin_login: str,
    entra_admin_object_id: str,
    resource_id: str,
) -> None:
    try:
        update_deployment_status(
            deployment_id,
            "running",
            f"Azure SQL Managed Instance {managed_instance_name} provisioning is in progress. This can take a while.",
            vm_id=resource_id,
        )
        creds = get_azure_credentials()
        resource_client = ResourceManagementClient(creds, data["subscription_id"])
        poller = resource_client.resources.begin_create_or_update(
            resource_group_name=data["resource_group"],
            resource_provider_namespace="Microsoft.Sql",
            parent_resource_path="",
            resource_type="managedInstances",
            resource_name=managed_instance_name,
            api_version=AZURE_SQL_MI_API_VERSION,
            parameters=params,
        )
        result = None
        try:
            result = poller.result()
        except HttpResponseError as poller_err:
            poller_err_text = str(poller_err)
            if AZURE_SQL_MI_KNOWN_POLLER_OK_STATUS_ERROR not in poller_err_text:
                raise
            logger.warning(
                "Managed Instance create returned unexpected polling status; reading final resource state: %s",
                poller_err_text,
                exc_info=True,
            )
            result = resource_client.resources.get(
                resource_group_name=data["resource_group"],
                resource_provider_namespace="Microsoft.Sql",
                parent_resource_path="",
                resource_type="managedInstances",
                resource_name=managed_instance_name,
                api_version=AZURE_SQL_MI_API_VERSION,
            )

        final_resource_id = getattr(result, "id", None) or resource_id
        _raise_if_azure_resource_failed(result, managed_instance_name)
        if not _sql_managed_instance_is_ready(result):
            result = _wait_for_sql_managed_instance_ready(
                resource_client,
                data,
                managed_instance_name,
                deployment_id,
                final_resource_id,
            )
            final_resource_id = getattr(result, "id", None) or final_resource_id

        if require_entra_auth:
            update_deployment_status(
                deployment_id,
                "running",
                f"Azure SQL Managed Instance {managed_instance_name} is provisioned. Assigning Microsoft Entra admin.",
                vm_id=final_resource_id,
            )
            aad_admin_params: Dict[str, Any] = {
                "properties": {
                    "administratorType": "ActiveDirectory",
                    "login": entra_admin_login,
                    "sid": entra_admin_object_id,
                    "tenantId": TENANT_ID,
                    "principalType": (data.get("entra_admin_principal_type") or "Group").strip(),
                    "azureADOnlyAuthentication": auth_method == "entra_only",
                }
            }
            aad_poller = resource_client.resources.begin_create_or_update(
                resource_group_name=data["resource_group"],
                resource_provider_namespace="Microsoft.Sql",
                parent_resource_path=f"managedInstances/{managed_instance_name}",
                resource_type="administrators",
                resource_name="ActiveDirectory",
                api_version=AZURE_SQL_MI_API_VERSION,
                parameters=aad_admin_params,
            )
            try:
                aad_poller.result()
            except HttpResponseError as aad_err:
                aad_error_obj = getattr(aad_err, "error", None)
                aad_error_code = getattr(aad_error_obj, "code", None) if aad_error_obj else None
                aad_error_text = aad_error_code or str(aad_err)
                if "ServicePrincipalLookupInAadFailed" not in aad_error_text:
                    raise
                # Azure AD can take several minutes to propagate the MI's newly created system-assigned
                # managed identity. Wait 2 minutes and retry once before giving up.
                logger.warning(
                    "Entra admin assignment for SQL MI %s failed on first attempt "
                    "(ServicePrincipalLookupInAadFailed); waiting 120s for Azure AD identity propagation "
                    "then retrying.",
                    managed_instance_name,
                )
                update_deployment_status(
                    deployment_id,
                    "running",
                    f"Azure SQL Managed Instance {managed_instance_name}: Microsoft Entra admin assignment "
                    "requires Azure AD to propagate the managed identity. Waiting 2 minutes before retrying...",
                    vm_id=final_resource_id,
                )
                time.sleep(120)
                try:
                    aad_retry_poller = resource_client.resources.begin_create_or_update(
                        resource_group_name=data["resource_group"],
                        resource_provider_namespace="Microsoft.Sql",
                        parent_resource_path=f"managedInstances/{managed_instance_name}",
                        resource_type="administrators",
                        resource_name="ActiveDirectory",
                        api_version=AZURE_SQL_MI_API_VERSION,
                        parameters=aad_admin_params,
                    )
                    aad_retry_poller.result()
                    logger.info(
                        "Entra admin assignment for SQL MI %s succeeded on retry.",
                        managed_instance_name,
                    )
                    # Retry succeeded — fall through to the azureADOnlyAuthentications step below.
                except HttpResponseError:
                    # Both attempts failed. Handle based on auth mode.
                    logger.warning(
                        "Entra admin assignment for SQL MI %s failed after retry "
                        "(ServicePrincipalLookupInAadFailed): the managed identity needs the "
                        "'Directory Readers' role in Azure AD. The MI was created but Entra admin "
                        "was not configured.",
                        managed_instance_name,
                    )
                    if auth_method == "entra_only":
                        # Entra-only mode with no Entra admin means no login method works at all.
                        update_deployment_status(
                            deployment_id,
                            "failed",
                            error=(
                                f"Azure SQL Managed Instance {managed_instance_name} was provisioned but "
                                "Microsoft Entra admin could not be assigned because the managed identity has not "
                                "been granted the 'Directory Readers' role in Azure AD. Login will not work. "
                                "To resolve: ask your Azure AD admin to grant the 'Directory Readers' role to "
                                "this MI's system-assigned identity in Azure portal "
                                "(Azure AD > Roles and Administrators > Directory Readers), then re-assign the "
                                "Entra admin from the MI's Settings > Microsoft Entra admin page. "
                                "Alternatively, delete this MI and re-deploy after granting the role."
                            ),
                            vm_id=final_resource_id,
                        )
                    else:
                        # 'both' mode: SQL admin login still works, but Entra login will not.
                        sql_admin_user = (data.get("server_admin_username") or "").strip()
                        update_deployment_status(
                            deployment_id,
                            "completed",
                            f"Azure SQL Managed Instance {managed_instance_name} deployed successfully. "
                            "Note: Microsoft Entra admin could not be assigned because the managed identity "
                            "has not been granted the 'Directory Readers' role in Azure AD. "
                            f"You can connect using SQL Server Authentication with username '{sql_admin_user}' "
                            "and the SQL admin password you set during deployment. "
                            "To enable Microsoft Entra (email/UPN) login: ask your Azure AD admin to grant the "
                            "'Directory Readers' role to this MI's system-assigned identity, then re-assign the "
                            "Entra admin from the MI's Settings > Microsoft Entra admin page in the Azure portal.",
                            vm_id=final_resource_id,
                        )
                    return

            # Entra admin assigned successfully. For 'both' mode, explicitly ensure SQL authentication
            # remains enabled by calling the azureADOnlyAuthentications/Default sub-resource.
            if auth_method == "both":
                try:
                    aad_only_params: Dict[str, Any] = {
                        "properties": {
                            "azureADOnlyAuthentication": False,
                        }
                    }
                    aad_only_poller = resource_client.resources.begin_create_or_update(
                        resource_group_name=data["resource_group"],
                        resource_provider_namespace="Microsoft.Sql",
                        parent_resource_path=f"managedInstances/{managed_instance_name}",
                        resource_type="azureADOnlyAuthentications",
                        resource_name="Default",
                        api_version=AZURE_SQL_MI_API_VERSION,
                        parameters=aad_only_params,
                    )
                    aad_only_poller.result()
                    logger.info(
                        "SQL MI %s: azureADOnlyAuthentication explicitly set to false for 'both' auth mode.",
                        managed_instance_name,
                    )
                except HttpResponseError as aad_only_err:
                    # Non-fatal: if this fails, the administrators assignment already set azureADOnlyAuthentication=false.
                    logger.warning(
                        "SQL MI %s: could not explicitly disable azureADOnlyAuthentication via sub-resource: %s",
                        managed_instance_name,
                        aad_only_err,
                    )

        sql_admin_user = (data.get("server_admin_username") or "").strip()
        if auth_method == "both":
            success_msg = (
                f"Azure SQL Managed Instance {managed_instance_name} deployed successfully. "
                f"SQL Server Authentication: connect using username '{sql_admin_user}' with SQL Server Authentication. "
                f"Microsoft Entra Authentication: connect using '{entra_admin_login}' with Azure Active Directory authentication in your SQL client (e.g. SSMS: Authentication = 'Azure Active Directory - Password' or 'Azure Active Directory - MFA')."
            )
        elif auth_method == "entra_only":
            success_msg = (
                f"Azure SQL Managed Instance {managed_instance_name} deployed successfully. "
                f"Only Microsoft Entra authentication is enabled. "
                f"Connect using '{entra_admin_login}' with Azure Active Directory authentication in your SQL client "
                "(e.g. SSMS: Authentication = 'Azure Active Directory - Password' or 'Azure Active Directory - MFA'). "
                "SQL Server Authentication (username/password) is disabled for this instance."
            )
        else:
            success_msg = (
                f"Azure SQL Managed Instance {managed_instance_name} deployed successfully. "
                f"Connect using SQL Server Authentication with username '{sql_admin_user}' and the password you set during deployment."
            )
        update_deployment_status(
            deployment_id,
            "completed",
            success_msg,
            vm_id=final_resource_id,
        )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else json.dumps(exc.detail)
        update_deployment_status(deployment_id, "failed", error=detail, vm_id=resource_id)
    except HttpResponseError as exc:
        error_message = _clean_azure_error_message(str(exc))
        update_deployment_status(
            deployment_id,
            "failed",
            error=f"Azure SQL Managed Instance deployment failed: {error_message}",
            vm_id=resource_id,
        )
    except Exception as exc:
        logger.exception("SQL Managed Instance background deployment failed: %s", exc)
        update_deployment_status(
            deployment_id,
            "failed",
            error=f"Azure SQL Managed Instance deployment failed: {str(exc)}",
            vm_id=resource_id,
        )

def _get_sql_mi_subnet_validation_errors(subnet: Any) -> List[str]:
    errors: List[str] = []
    delegations = getattr(subnet, "delegations", None) or []
    delegation_services = [
        getattr(d, "service_name", None)
        for d in delegations
        if getattr(d, "service_name", None)
    ]
    delegation_services_lower = [svc.lower() for svc in delegation_services]
    sql_mi_delegation = "microsoft.sql/managedinstances"

    if sql_mi_delegation not in delegation_services_lower:
        errors.append("subnet must be delegated to Microsoft.Sql/managedInstances")
    else:
        extra_delegations = [
            delegation_services[idx]
            for idx, svc in enumerate(delegation_services_lower)
            if svc != sql_mi_delegation
        ]
        if extra_delegations:
            errors.append("subnet has unsupported delegations: " + ", ".join(extra_delegations))

    prefixes: List[str] = []
    if getattr(subnet, "address_prefix", None):
        prefixes.append(subnet.address_prefix)
    prefixes.extend([p for p in (getattr(subnet, "address_prefixes", None) or []) if p])

    if not prefixes:
        errors.append("subnet is missing an address prefix")
    else:
        invalid_prefixes: List[str] = []
        too_small_prefixes: List[str] = []
        for prefix in prefixes:
            try:
                network = ipaddress.ip_network(prefix, strict=False)
                if network.version != 4 or network.prefixlen > 27:
                    too_small_prefixes.append(prefix)
            except ValueError:
                invalid_prefixes.append(prefix)
        if invalid_prefixes:
            errors.append("subnet has invalid address prefixes: " + ", ".join(invalid_prefixes))
        if too_small_prefixes:
            errors.append("subnet address range must be /27 or larger: " + ", ".join(too_small_prefixes))

    return errors

@app.get("/api/azure/sql-mi-subnets")
def list_sql_mi_subnets(
    request: Request,
    subscription_id: str = Query(...),
    resource_group: str = Query(""),
    location: str = Query(""),
):
    """List supported subnet resource IDs in a subscription for SQL Managed Instance."""
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        client = NetworkManagementClient(get_azure_credentials_service_principal(), subscription_id)
        result: List[Dict[str, Any]] = []
        requested_rg = (resource_group or "").strip().lower()
        requested_location = (location or "").strip().lower()
        vnets = client.virtual_networks.list_all()
        for vnet in vnets:
            vnet_name = getattr(vnet, "name", None)
            if not vnet_name:
                continue
            vnet_rg = _parse_azure_resource_group_from_resource_id(getattr(vnet, "id", "") or "")
            if not vnet_rg:
                continue
            vnet_location = (getattr(vnet, "location", None) or "").strip().lower()
            if requested_location and vnet_location and vnet_location != requested_location:
                continue
            for s in client.subnets.list(vnet_rg, vnet_name):
                if _get_sql_mi_subnet_validation_errors(s):
                    continue
                address_prefixes = [p for p in (getattr(s, "address_prefixes", None) or []) if p]
                address_prefix = getattr(s, "address_prefix", None) or ", ".join(address_prefixes)
                result.append({
                    "id": s.id,
                    "name": s.name,
                    "resource_group": vnet_rg,
                    "vnet_name": vnet_name,
                    "address_prefix": address_prefix,
                })
        result.sort(
            key=lambda x: (
                0 if requested_rg and (x.get("resource_group") or "").lower() == requested_rg else 1,
                (x.get("resource_group") or "").lower(),
                (x.get("vnet_name") or "").lower(),
                (x.get("name") or "").lower(),
            )
        )
        return result
    except Exception as e:
        logger.exception("list_sql_mi_subnets failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/azure/vm-sizes")
def list_vm_sizes(
    request: Request,
    subscription_id: str = Query(...),
    location: str = Query(...),
    image_subscription_id: str = Query(None),
    image_resource_group: str = Query(None),
    gallery_name: str = Query(None),
    image_name: str = Query(None),
    hyper_v_generation: str = Query(None),
):
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    if not location:
        raise HTTPException(status_code=400, detail="Missing location parameter")
    # Validate location to only allow simple Azure region identifiers (alphanumeric)
    if not location.replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid location value")
    try:
        pricing = _get_azure_vm_pricing(location)

        # Try to load VM sizes from DB table; fall back to the hardcoded curated list when
        # the DB is unavailable or the table has not been seeded yet.
        sizes_source = AZURE_SUPPORTED_VM_SIZES  # default: hardcoded fallback
        sizes_from_db = False
        if DB_AVAILABLE and db_get_azure_vm_sizes is not None:
            try:
                db_sizes = db_get_azure_vm_sizes()
                if db_sizes:
                    sizes_source = db_sizes
                    sizes_from_db = True
                    logger.debug(
                        "list_vm_sizes: loaded %d sizes from portal.azure_vm_sizes DB table",
                        len(db_sizes),
                    )
                else:
                    logger.debug(
                        "list_vm_sizes: portal.azure_vm_sizes empty or missing — using hardcoded list"
                    )
            except Exception as _db_err:
                logger.warning("list_vm_sizes: DB size lookup failed (%s) — using hardcoded list", _db_err)

        result = []
        for name, vcpus, memory_mb in sizes_source:
            sku_key = _azure_size_to_sku(name)
            price = pricing.get(sku_key)
            result.append({
                "name": name,
                "numberOfCores": vcpus,
                "memoryInMB": memory_mb,
                "price_per_hour": price,
            })
        logger.info(
            "[VM-SIZES] Returning %d sizes for sub=%s location=%s (source=%s): %s",
            len(result), subscription_id, location,
            "DB" if sizes_from_db else "hardcoded",
            ", ".join(r["name"] for r in result)
        )
        return result
    except Exception as e:
        logger.exception("list_vm_sizes failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/azure/image-definitions")
def list_image_definitions():
    return [
        {
            "name": img["name"],
            "label": img.get("label", img["name"]),
            "gallery": AZURE_SHARED_IMAGE_GALLERY,
            "subscription_id": AZURE_SHARED_IMAGE_SUBSCRIPTION_ID,
            "resource_group": AZURE_SHARED_IMAGE_RESOURCE_GROUP,
            "os_type": img["os_type"],
            "hyper_v_generation": img.get("hyper_v_generation", "")
        }
        for img in AZURE_SHARED_IMAGES
    ]

# ... image versions endpoints unchanged ...

@app.post("/api/azure/nsgs/create")
async def create_azure_nsg(request: Request):
    payload = await request.json()
    subscription_id = payload.get("subscription_id")
    resource_group = payload.get("resource_group")
    nsg_name = payload.get("nsg_name")
    description = payload.get("description", "")
    location = payload.get("location")
    rules = payload.get("rules", [])
    if not subscription_id or not resource_group or not nsg_name:
        raise HTTPException(status_code=400, detail="Missing required fields: subscription_id, resource_group, nsg_name")
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        creds = get_azure_credentials()
    except Exception as e:
        logger.exception("Azure credentials missing: %s", e)
        raise HTTPException(status_code=500, detail="Azure credentials not configured")
    net_client = NetworkManagementClient(creds, subscription_id)
    security_rules = []
    priority = 1000
    for r in rules:
        try:
            name = (r.get("name") or "").strip()
            if not name:
                raise ValueError("Each rule must have a name")
            protocol = (r.get("protocol") or "*")
            direction = r.get("direction", "Inbound")
            if direction not in ("Inbound", "Outbound"):
                raise ValueError("direction must be 'Inbound' or 'Outbound'")
            port = int(r.get("port"))
            access = r.get("access", "Allow")
            if access not in ("Allow", "Deny"):
                access = "Allow"
            source_prefix = r.get("source") or ("0.0.0.0/0" if direction == "Inbound" else "*")
            destination_prefix = r.get("destination") or ("*" if direction == "Inbound" else "0.0.0.0/0")
            security_rules.append(SecurityRule(
                name=name,
                protocol=protocol,
                source_port_range="*",
                destination_port_range=str(port),
                source_address_prefix=source_prefix,
                destination_address_prefix=destination_prefix,
                access=access,
                priority=priority,
                direction=direction,
            ))
            priority += 10
        except Exception as e:
            logger.exception("Invalid NSG rule: %s", e)
            raise HTTPException(status_code=400, detail=f"Invalid rule specification: {str(e)}")
    if not location:
        try:
            rg_client = ResourceManagementClient(creds, subscription_id)
            rg = rg_client.resource_groups.get(resource_group)
            location = rg.location
        except Exception:
            location = None
    if not location:
        raise HTTPException(status_code=400, detail="Missing location and could not determine resource group location")
    nsg_params = NetworkSecurityGroup(location=location, security_rules=security_rules)
    if description:
        nsg_params.tags = {"Description": description}
    try:
        poller = net_client.network_security_groups.begin_create_or_update(resource_group_name=resource_group, network_security_group_name=nsg_name, parameters=nsg_params)
        nsg_result = poller.result()
        return {"nsg_id": nsg_result.id, "nsg_name": nsg_result.name}
    except HttpResponseError as he:
        logger.exception("Azure NSG create HttpResponseError: %s", he)
        raise HTTPException(status_code=500, detail=f"Azure NSG creation failed: {str(he)}")
    except Exception as e:
        logger.exception("Azure NSG create failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Azure NSG creation failed: {str(e)}")

# ✅ UPDATED: Azure VM deployment with TAG SUPPORT + Cherwell account display fix
@app.post("/api/azure/deploy-vm")
async def deploy_vm_azure(request: Request):
    """Start Azure VM deployment asynchronously with custom tags support."""
    data = await request.json()
    required_keys = ["subscription_id", "resource_group", "vnet_name", "subnet_id", "gallery_name", "image_name", "image_version", "vm_size", "location", "vm_name", "admin_username", "admin_password"]
    for key in required_keys:
        if not data.get(key):
            raise HTTPException(status_code=400, detail=f"Missing field: {key}")
    if not is_subscription_allowed(request, data["subscription_id"]):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    _extract_and_validate_billing_account(data.get("tags"))

    deployment_id = f"{data['vm_name']}-{uuid.uuid4().hex[:12]}"
    with deployment_lock:
        deployment_request_context[deployment_id] = {
            "cloud_provider": "azure",
            "vm_name_final": data["vm_name"],
        }
    update_deployment_status(deployment_id, "starting", f"Initiating deployment of VM {data['vm_name']}")

    if "tags" in data and data["tags"]:
        try:
            custom_tags = parse_tags_from_payload(data)
            if custom_tags:
                data["tags"] = custom_tags
                logger.info(f"Azure deployment with tags: {custom_tags}")
        except Exception as e:
            logger.warning(f"Failed to parse Azure tags: {e}")

    user = get_current_user(request)
    user_email = user.get("email") if user else None
        # ---- DB logging for Azure (non-blocking) ----
    try:
        if DB_AVAILABLE and insert_portal_request_all:
            tags_obj = data.get("tags") or {}
            if isinstance(tags_obj, str):
                try:
                    tags_obj = json.loads(tags_obj)
                except Exception:
                    tags_obj = {}

            tag_account_number = tags_obj.get("AccountNumber") if isinstance(tags_obj, dict) else None
            tag_approvers = tags_obj.get("Approvers") if isinstance(tags_obj, dict) else None
            tag_ps = tags_obj.get("PS") if isinstance(tags_obj, dict) else None

            payload_snapshot = dict(data)
            if "admin_password" in payload_snapshot:
                payload_snapshot["admin_password"] = "***REDACTED***"

            insert_portal_request_all({
                "cloud_provider": "azure",
                "user_email": user_email,
                "user_oid": (user or {}).get("oid") if user else None,

                "vm_name_requested": data.get("vm_name"),
                "vm_name_final": data.get("vm_name"),

                "tag_account_number": tag_account_number,
                "tag_approvers": tag_approvers,
                "tag_ps": tag_ps,

                "status": "received",
                "payload_json": payload_snapshot,

                "azure_subscription_id": data.get("subscription_id"),
                "azure_resource_group": data.get("resource_group"),
                "azure_virtual_network": data.get("vnet_name"),
                "azure_subnet_id": data.get("subnet_id"),
                "azure_image_definition": data.get("image_name"),
                "azure_vm_size": data.get("vm_size"),
                "azure_os_disk_type": data.get("os_disk_type"),
                "azure_location": data.get("location"),
                "azure_availability_zone": data.get("availability_zone"),
                "azure_nsg_id": data.get("nsg_id"),
                "azure_admin_username": data.get("admin_username"),
                "azure_admin_password_provided": 1 if (data.get("admin_password") or "").strip() else 0,
                "azure_accelerated_networking": 1 if data.get("accelerated_networking") else 0,
                "azure_use_managed_disks": 1 if data.get("use_managed_disks") else 0,
            })
    except Exception as db_err:
        logger.warning("DB logging failed (non-blocking): %s", db_err)

    thread = threading.Thread(target=_deploy_vm_azure_background, args=(deployment_id, data, user_email), daemon=False)
    thread.start()

    return {
        "status": "started",
        "deployment_id": deployment_id,
        "vm_name": data["vm_name"],
        "message": "VM deployment started. Use /api/deployment-status/{deployment_id} to check progress."
    }

def _deploy_vm_azure_background(deployment_id: str, data: dict, user_email: str = None):
    """Background function to deploy Azure VM with custom tags."""
    subscription_id = data["subscription_id"]
    try:
        update_deployment_status(deployment_id, "preparing", "Getting Azure credentials")
        credentials = get_azure_credentials()
    except Exception as e:
        update_deployment_status(deployment_id, "failed", error=f"Azure credentials not configured: {str(e)}")
        return
    
    compute_client = ComputeManagementClient(credentials, subscription_id)
    network_client = NetworkManagementClient(credentials, subscription_id)

    # NIC create
    try:
        update_deployment_status(deployment_id, "creating_nic", f"Creating network interface for {data['vm_name']}")
        nic_name = f"{data['vm_name']}-nic"
        # Use camelCase dict body directly to guarantee correct REST serialisation
        # regardless of azure-mgmt-network SDK version installed on the server.
        nic_body: Dict[str, Any] = {
            "location": data["location"],
            "properties": {
                "ipConfigurations": [{
                    "name": "ipconfig1",
                    "properties": {
                        "subnet": {"id": data["subnet_id"]},
                        "privateIPAllocationMethod": "Dynamic",
                    },
                }],
                "enableAcceleratedNetworking": data.get("accelerated_networking", False),
            },
        }
        # NSG must be set on the NIC itself (top-level), not inside ipConfigurations.
        if data.get("nsg_id"):
            nic_body["properties"]["networkSecurityGroup"] = {"id": data["nsg_id"]}
        nic_poller = network_client.network_interfaces.begin_create_or_update(data["resource_group"], nic_name, nic_body)
        nic = nic_poller.result()
    except Exception as e:
        update_deployment_status(deployment_id, "failed", error=f"NIC creation failed: {str(e)}")
        return

    # Resolve image version — "latest" is NOT a valid ARM resource ID segment;
    # resolve to the actual newest version number.
    image_version = data.get("image_version", "")
    image_resource_group = data.get("image_resource_group") or AZURE_SHARED_IMAGE_RESOURCE_GROUP
    gallery_name_resolved = data.get("gallery_name") or AZURE_SHARED_IMAGE_GALLERY
    image_subscription_id = data.get("image_subscription_id") or AZURE_SHARED_IMAGE_SUBSCRIPTION_ID

    if not image_resource_group or not gallery_name_resolved or not image_subscription_id:
        update_deployment_status(deployment_id, "failed", error="Missing image configuration: image_resource_group, gallery_name, or image_subscription_id not set")
        return

    if not image_version or image_version.lower() == "latest":
        try:
            update_deployment_status(deployment_id, "resolving_image", "Determining latest image version")
            # Use the subscription that hosts the gallery (may differ from the deploy subscription)
            if image_subscription_id and image_subscription_id != subscription_id:
                img_compute_client = ComputeManagementClient(credentials, image_subscription_id)
            else:
                img_compute_client = compute_client
            versions_iter = img_compute_client.gallery_image_versions.list_by_gallery_image(
                image_resource_group, gallery_name_resolved, data["image_name"]
            )
            versions = list(versions_iter)
            if not versions:
                update_deployment_status(deployment_id, "failed", error="No image versions found")
                return
            sorted_versions = sorted(versions, key=lambda v: getattr(v, "name", ""), reverse=True)
            image_version = getattr(sorted_versions[0], "name", None)
            if not image_version:
                update_deployment_status(deployment_id, "failed", error="Could not resolve image version name")
                return
        except Exception as e:
            update_deployment_status(deployment_id, "failed", error=f"Could not determine image_version: {str(e)}")
            return

    image_info = next((i for i in AZURE_SHARED_IMAGES if i["name"] == data["image_name"]), None)
    if not image_info:
        update_deployment_status(deployment_id, "failed", error="Image definition not found")
        return

    # OS profile build
    try:
        admin_pass = (data.get("admin_password") or "").strip()
        if not admin_pass:
            update_deployment_status(deployment_id, "failed", error="admin_password is required and cannot be empty")
            return
        os_profile = OSProfile(
            computer_name=data["vm_name"],
            admin_username=data["admin_username"],
            admin_password=admin_pass,
        )
    except Exception as e:
        update_deployment_status(deployment_id, "failed", error=f"Failed to build OS profile: {str(e)}")
        return

    # VM create — use explicit SDK model objects so azure-mgmt-compute serialises
    # correctly regardless of SDK version (plain dicts broke in v29+ DPG style).
    try:
        update_deployment_status(deployment_id, "creating_vm", f"Creating virtual machine {data['vm_name']}")
        image_id = (
            f"/subscriptions/{image_subscription_id}/resourceGroups/{image_resource_group}"
            f"/providers/Microsoft.Compute/galleries/{gallery_name_resolved}"
            f"/images/{data['image_name']}/versions/{image_version}"
        )
        storage_profile = StorageProfile(
            image_reference=ImageReference(id=image_id)
        )

        # Tags
        azure_tags = {}
        tags_data = data.get("tags") or {}
        if isinstance(tags_data, str):
            try:
                tags_data = json.loads(tags_data)
            except Exception:
                tags_data = {}
        if isinstance(tags_data, dict):
            if 'AccountNumber' in tags_data:
                azure_tags['AccountNumber'] = str(tags_data['AccountNumber'])
            if 'Approvers' in tags_data:
                azure_tags['Approvers'] = str(tags_data['Approvers'])
            if 'PS' in tags_data:
                azure_tags['PS'] = str(tags_data['PS'])

        azure_tags['DeployedBy'] = 'MultiCloudPortal'
        azure_tags['DeploymentId'] = deployment_id

        vm_obj = VirtualMachine(
            location=data["location"],
            hardware_profile=HardwareProfile(vm_size=data["vm_size"]),
            storage_profile=storage_profile,
            os_profile=os_profile,
            network_profile=NetworkProfile(
                network_interfaces=[NetworkInterfaceReference(id=nic.id)]
            ),
            tags=azure_tags,
        )
        if data.get("availability_zone"):
            vm_obj.zones = [data["availability_zone"]]

        try:
            vm_create = compute_client.virtual_machines.begin_create_or_update(
                data["resource_group"], data["vm_name"], vm_obj
            )
            vm_result = vm_create.result()
        except HttpResponseError as create_err:
            err_obj = getattr(create_err, "error", None)
            err_code = str(getattr(err_obj, "code", "") or "").lower()
            err_text = str(getattr(err_obj, "message", "") or str(create_err))
            has_trusted_launch_error_text = (
                "trustedlaunch" in err_text.lower()
                and "security type" in err_text.lower()
            )
            # Some Azure errors omit code details; allow text-based fallback in that case.
            trusted_launch_required = has_trusted_launch_error_text and (
                not err_code or err_code == AZURE_BAD_REQUEST_CODE
            )
            if not trusted_launch_required:
                raise

            # Some Shared Gallery images (e.g., newer Azure Linux/RHEL generations)
            # can only be deployed with Trusted Launch enabled.
            vm_obj.security_profile = SecurityProfile(
                security_type="TrustedLaunch",
                uefi_settings=UefiSettings(
                    secure_boot_enabled=True,
                    v_tpm_enabled=True,
                ),
            )
            update_deployment_status(
                deployment_id,
                "creating_vm",
                f"Retrying VM creation for {data['vm_name']} with TrustedLaunch",
            )
            vm_create = compute_client.virtual_machines.begin_create_or_update(
                data["resource_group"], data["vm_name"], vm_obj
            )
            vm_result = vm_create.result()

        update_deployment_status(deployment_id, "completed", f"VM {data['vm_name']} deployed successfully", vm_id=vm_result.id)

        # Post-deployment: create svc_ecloudadmin service account on all Azure VMs.
        # The password must be set via the SVC_ECLOUDADMIN_PASSWORD app setting (never hard-coded).
        svc_pwd = SVC_ECLOUDADMIN_PASSWORD or (data.get("admin_password") or "").strip()
        if not SVC_ECLOUDADMIN_PASSWORD and svc_pwd:
            logger.warning(
                "[%s] SVC_ECLOUDADMIN_PASSWORD not set; using fallback credential for svc_ecloudadmin on %s",
                deployment_id,
                data["vm_name"],
            )
        if svc_pwd:
            vm_os_from_image = str(image_info.get("os_type", "") or "").strip().lower()
            vm_os_from_result = str(
                getattr(getattr(getattr(vm_result, "storage_profile", None), "os_disk", None), "os_type", "") or ""
            ).strip().lower()
            vm_image_name = str(data.get("image_name", "") or "").strip().lower()
            vm_os_profile = getattr(vm_result, "os_profile", None)
            has_windows_configuration = bool(getattr(vm_os_profile, "windows_configuration", None))
            vm_os_candidates = [vm_os_from_result, vm_os_from_image, vm_image_name]
            is_windows_vm = has_windows_configuration or any(
                os_name and "windows" in os_name for os_name in vm_os_candidates
            )
            if is_windows_vm:
                logger.info(
                    "[%s] Skipping svc_ecloudadmin creation on Windows VM %s",
                    deployment_id,
                    data["vm_name"],
                )
            else:
                try:
                    logger.info("[%s] Creating svc_ecloudadmin account on Linux VM %s", deployment_id, data["vm_name"])
                    safe_admin_username = re.sub(r"[^A-Za-z0-9_\-]", "", (data.get("admin_username") or ""))[:32]
                    if not re.match(r"^[A-Za-z_]", safe_admin_username):
                        safe_admin_username = ""
                    quoted_admin_username = shlex.quote(safe_admin_username)
                    # Script runs as root inside the VM. The password is supplied via
                    # RunCommandInputParameter and is available as $1 in the script.
                    svc_script = [
                        f"PORTAL_ADMIN={quoted_admin_username}",
                        "id svc_ecloudadmin &>/dev/null || useradd -m -s /bin/bash svc_ecloudadmin",
                        "printf 'svc_ecloudadmin:%s\\n' \"$1\" | chpasswd",
                        "usermod -aG sudo svc_ecloudadmin 2>/dev/null; usermod -aG wheel svc_ecloudadmin 2>/dev/null; true",
                        "mkdir -p /etc/sudoers.d",
                        "echo 'svc_ecloudadmin ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/svc_ecloudadmin",
                        "chmod 440 /etc/sudoers.d/svc_ecloudadmin",
                        "ensure_allow_user_in_file() { local f=\"$1\"; local u=\"$2\"; [ -n \"$u\" ] || return 0; [ -f \"$f\" ] || return 0; "
                        "grep -qiE '^[[:space:]]*AllowUsers[[:space:]]+' \"$f\" || return 0; "
                        "if ! awk -v user=\"$u\" 'BEGIN{IGNORECASE=1} /^[[:space:]]*AllowUsers[[:space:]]+/ {for(i=2;i<=NF;i++) if($i==user) found=1} END{exit found?0:1}' \"$f\"; then "
                        "sed -i -E \"0,/^[[:space:]]*AllowUsers[[:space:]]+/ s//&${u} /\" \"$f\"; fi; }",
                        "ensure_allow_user_in_file /etc/ssh/sshd_config \"$PORTAL_ADMIN\"",
                        "ensure_allow_user_in_file /etc/ssh/sshd_config svc_ecloudadmin",
                        "if [ -d /etc/ssh/sshd_config.d ]; then for f in /etc/ssh/sshd_config.d/*; do "
                        "[ -f \"$f\" ] || continue; "
                        "ensure_allow_user_in_file \"$f\" \"$PORTAL_ADMIN\"; "
                        "ensure_allow_user_in_file \"$f\" svc_ecloudadmin; "
                        "done; fi",
                        "systemctl restart sshd 2>/dev/null || service sshd restart 2>/dev/null || true",
                    ]
                    run_cmd = RunCommandInput(
                        command_id="RunShellScript",
                        script=svc_script,
                        parameters=[RunCommandInputParameter(name="password", value=svc_pwd)],
                    )
                    # Linux VM Agent readiness is often delayed right after provisioning.
                    # Six attempts with a 45-second step (capped at 120s) gives about a
                    # 8-minute bounded retry window to avoid missing svc_ecloudadmin setup.
                    max_run_command_retries = 6
                    retry_backoff_multiplier_seconds = 45
                    retry_backoff_cap_seconds = 120
                    last_run_command_error: Optional[Exception] = None
                    for attempt in range(1, max_run_command_retries + 1):
                        try:
                            run_poller = compute_client.virtual_machines.begin_run_command(
                                data["resource_group"], data["vm_name"], run_cmd
                            )
                            run_poller.result()
                            break
                        except Exception as run_err:
                            last_run_command_error = run_err
                            if attempt >= max_run_command_retries:
                                break
                            retry_sleep_seconds = min(
                                retry_backoff_multiplier_seconds * attempt,
                                retry_backoff_cap_seconds,
                            )
                            logger.warning(
                                "[%s] svc_ecloudadmin run command attempt %d/%d failed for %s; retrying in %ss: %s",
                                deployment_id,
                                attempt,
                                max_run_command_retries,
                                data["vm_name"],
                                retry_sleep_seconds,
                                run_err,
                            )
                            time.sleep(retry_sleep_seconds)
                    if last_run_command_error:
                        raise RuntimeError(
                            "svc_ecloudadmin run command failed "
                            f"for VM '{data['vm_name']}' in resource group '{data['resource_group']}' "
                            f"after {max_run_command_retries} attempts"
                        ) from last_run_command_error
                    logger.info("[%s] svc_ecloudadmin account configured successfully on %s", deployment_id, data["vm_name"])
                except Exception as svc_err:
                    logger.warning(
                        "[%s] Could not create svc_ecloudadmin on %s (non-blocking): %s",
                        deployment_id, data["vm_name"], svc_err,
                    )
        else:
            logger.warning(
                "[%s] SVC_ECLOUDADMIN_PASSWORD not set; skipping service account creation on %s",
                deployment_id, data["vm_name"],
            )
        # ✅ Provisioning Start Time (Azure = time_created)
        try:
            tc = getattr(vm_result, "time_created", None)
            if tc:
                if hasattr(tc, "tzinfo") and tc.tzinfo:
                    tc_utc = tc.astimezone(timezone.utc)
                else:
                    tc_utc = tc.replace(tzinfo=timezone.utc)
                azure_time_created_str = tc_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                azure_time_created_str = None
        except Exception:
            azure_time_created_str = None

        # ✅ Cherwell: ensure account display uses subscription_id (fix Unknown)
        try:
            vm_details = {
                "vm_name": data["vm_name"],
                "cloud": "azure",
                "subscription_id": subscription_id,
                "account_name_display": subscription_id,
                "resource_group": data["resource_group"],
                "location": data["location"],
                "vm_size": data["vm_size"],
                "vm_id": vm_result.id,
                "os_type": image_info.get("os_type", ""),
                "image_name": data.get("image_name", ""),
                "provisioning_start_time": azure_time_created_str,
                "data_protection": data.get("data_protection", ""),
            }
            if azure_tags:
                vm_details["tags"] = azure_tags
            if azure_time_created_str:
                vm_details["provisioning_start_time"] = azure_time_created_str

            create_post_deployment_tasks(data["vm_name"], "azure", vm_details, user_email=user_email)
        except Exception as cherwell_err:
            logger.exception(f"[{deployment_id}] Error creating Cherwell tasks (non-blocking): %s", cherwell_err)

    except Exception as e:
        update_deployment_status(deployment_id, "failed", error=f"VM creation failed: {str(e)}")

@app.get("/api/deployment-status/{deployment_id}")
async def get_deployment_status_endpoint(deployment_id: str):
    """Get the status of a deployment by its ID."""
    status = get_deployment_status(deployment_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Deployment {deployment_id} not found")
    return status

# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/aws/account-tags")
async def get_aws_account_tags(
    request: Request,
    account: str = Query(...),
):
    """Return the AWS account-level tags for the given account ID (e.g. AccountNumber tag).

    Tries six methods in order:
    1a. AWS Organizations API using portal credentials (management/admin account) — reads
        org-level account tags (set via the AWS Organizations console) directly.  This is
        the most reliable method for AccountNumber tags set through AWS Organizations.
    1b. AWS Account Management API (account:ListTagsForResource) — can be called from within
        the member account itself; requires no Organization-level permissions.
    2. AWS Organizations API via assumed role — requires the caller to be the management
       account or a delegated admin; falls back if methods 1a+1b fail.
    3. Resource Groups Tagging API (tag:GetTagValues) — searches all tagged resources in
       the account for the AccountNumber key.  Tried in us-east-1 then us-west-2.
    4. EC2 DescribeTags — searches EC2 resource tags for AccountNumber.  ec2:DescribeTags
       is almost always available in the assumed role and covers EC2 instances/volumes/etc.
       Tried in us-west-2 then us-east-1 (most resources are expected in us-west-2).
    5. DB admin-managed lookup table (portal.aws_account_tags) — administrator-provided
       mapping of AWS account IDs to billing account numbers.  Used for accounts where
       no resource carries the AccountNumber tag.  Run aws-account-tags-table.sql to
       create the table, then INSERT a row per account as needed.
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not is_account_allowed(request, account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    # Method 1a: AWS Organizations API using the portal's own credentials (management account).
    # Organization-level account tags (set via the AWS Organizations console) can ONLY be
    # read from the management/delegated-admin account — not from an assumed role in the
    # member account.  This is the most reliable method for reading org-level tags like
    # AccountNumber.
    try:
        org_client_direct = boto3.client("organizations", region_name="us-east-1")
        resp = org_client_direct.list_tags_for_resource(ResourceId=account)
        tags = {t["Key"]: t["Value"] for t in resp.get("Tags", [])}
        if tags:
            logger.info(
                "get_aws_account_tags method1a (org API via portal credentials) found tags for %s", account
            )
            return {"tags": tags}
    except Exception as e1a:
        logger.debug(
            "get_aws_account_tags method1a (org API via portal credentials) failed for %s: %s", account, e1a
        )

    session = assume_role(account)
    err1 = None
    # Method 1b: AWS Account Management API (works from within the member account).
    # The ResourceId for the Account Management API is the account ID itself (12-digit number).
    try:
        acct_client = session.client("account", region_name="us-east-1")
        resp = acct_client.list_tags_for_resource(ResourceId=account)
        tags = {t["Key"]: t["Value"] for t in resp.get("Tags", [])}
        if tags:
            return {"tags": tags}
    except Exception as e1:
        err1 = e1
        logger.debug("get_aws_account_tags method1b (account API) failed for %s: %s", account, e1)
    # Method 2: AWS Organizations API via assumed role (requires management account / delegated admin access)
    try:
        org_client = session.client("organizations", region_name="us-east-1")
        resp = org_client.list_tags_for_resource(ResourceId=account)
        tags = {t["Key"]: t["Value"] for t in resp.get("Tags", [])}
        return {"tags": tags}
    except Exception as e2:
        logger.warning(
            "get_aws_account_tags methods 1a+1b+2 failed for account %s — trying methods 3+4. "
            "Method1b: %s | Method2: %s", account, err1, e2
        )
    # Method 3: ResourceGroupsTagging API — searches tags on resources within the account.
    # This works when the assumed role has tagging:GetTagValues permission, which is
    # commonly available.  We try the two most-used regions for this organization.
    for _region in ("us-east-1", "us-west-2"):
        try:
            tagging_client = session.client("resourcegroupstaggingapi", region_name=_region)
            resp = tagging_client.get_tag_values(Key="AccountNumber")
            values = [v for v in resp.get("TagValues", []) if v]
            if values:
                logger.info(
                    "get_aws_account_tags method3 (resourcegroupstaggingapi/%s) found "
                    "AccountNumber for %s: %s", _region, account, values[0]
                )
                return {"tags": {"AccountNumber": values[0]}}
        except Exception as e3:
            logger.debug(
                "get_aws_account_tags method3 (resourcegroupstaggingapi/%s) failed for %s: %s",
                _region, account, e3,
            )
    # Method 4: EC2 DescribeTags — filter by tag key "AccountNumber" across all EC2 resources.
    # ec2:DescribeTags is one of the most commonly available permissions in assumed roles.
    for _region in ("us-west-2", "us-east-1"):
        try:
            ec2_client = session.client("ec2", region_name=_region)
            resp = ec2_client.describe_tags(
                Filters=[{"Name": "key", "Values": ["AccountNumber"]}],
                MaxResults=5,
            )
            tag_values = [t["Value"] for t in resp.get("Tags", []) if t.get("Value")]
            if tag_values:
                logger.info(
                    "get_aws_account_tags method4 (ec2 describe_tags/%s) found "
                    "AccountNumber for %s: %s", _region, account, tag_values[0]
                )
                return {"tags": {"AccountNumber": tag_values[0]}}
        except Exception as e4:
            logger.debug(
                "get_aws_account_tags method4 (ec2 describe_tags/%s) failed for %s: %s",
                _region, account, e4,
            )
    logger.warning(
        "get_aws_account_tags: all 5 AWS API methods exhausted for account %s — no AccountNumber tag found in AWS. "
        "Trying DB admin override table (Method 6)...", account
    )
    # Method 6: DB admin-managed lookup table (portal.aws_account_tags).
    # Admins populate this table for accounts where no AWS API method can find
    # the tag (e.g., account has no tagged resources, or all API calls are denied).
    # Run aws-account-tags-table.sql once against the Azure SQL database to create
    # the table, then INSERT a row per account.
    if DB_AVAILABLE and get_aws_account_number_from_db is not None:
        try:
            db_number = get_aws_account_number_from_db(account)
            if db_number:
                logger.info(
                    "get_aws_account_tags method6 (DB lookup) found AccountNumber for %s: %s",
                    account, db_number,
                )
                return {"tags": {"AccountNumber": db_number}}
        except Exception as e5:
            logger.warning("get_aws_account_tags method6 (DB lookup) failed for %s: %s", account, e5)
    logger.warning(
        "get_aws_account_tags: all 6 methods exhausted for account %s — no AccountNumber found. "
        "Add a row to portal.aws_account_tags to provide a manual override.",
        account,
    )
    return {"tags": {}}

# Existing VM management endpoints
# ─────────────────────────────────────────────────────────────────────────────

# ── AWS: list existing instances ──────────────────────────────────────────────
@app.get("/api/aws/instances")
async def list_aws_instances(
    request: Request,
    account: str = Query(...),
    regions: str = Query(...)
):
    """List existing EC2 instances in one or more comma-separated regions."""
    if not is_account_allowed(request, account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    region_list = [r.strip() for r in regions.split(",") if r.strip()]
    if not region_list:
        raise HTTPException(status_code=400, detail="At least one region is required")

    all_vms: List[Dict[str, Any]] = []
    for region in region_list:
        try:
            session = assume_role(account)
            ec2 = session.client("ec2", region_name=region)
            response = ec2.describe_instances()
            for reservation in response.get("Reservations", []):
                for inst in reservation.get("Instances", []):
                    tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
                    name = tags.get("Name", inst.get("InstanceId", ""))
                    all_vms.append({
                        "instance_id": inst.get("InstanceId"),
                        "name": name,
                        "state": inst.get("State", {}).get("Name", ""),
                        "instance_type": inst.get("InstanceType", ""),
                        "region": region,
                        "availability_zone": inst.get("Placement", {}).get("AvailabilityZone", ""),
                        "private_ip": inst.get("PrivateIpAddress", ""),
                        "public_ip": inst.get("PublicIpAddress", ""),
                        "launch_time": inst.get("LaunchTime").isoformat() if inst.get("LaunchTime") else "",
                        "ami_id": inst.get("ImageId", ""),
                        "vpc_id": inst.get("VpcId", ""),
                        "subnet_id": inst.get("SubnetId", ""),
                        "tags": tags,
                    })
        except ClientError as e:
            logger.warning("describe_instances failed for account %s region %s: %s", account, region, e)

    return {"instances": all_vms}


@app.get("/api/aws/instance/{instance_id}")
async def get_aws_instance(
    request: Request,
    instance_id: str,
    account: str = Query(...),
    region: str = Query(...)
):
    """Get details for a specific EC2 instance."""
    if not is_account_allowed(request, account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    try:
        session = assume_role(account)
        ec2 = session.client("ec2", region_name=region)
        response = ec2.describe_instances(InstanceIds=[instance_id])
        reservations = response.get("Reservations", [])
        if not reservations or not reservations[0].get("Instances"):
            raise HTTPException(status_code=404, detail="Instance not found")
        inst = reservations[0]["Instances"][0]
        tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
        placement = inst.get("Placement", {})
        cpu_opts = inst.get("CpuOptions", {})
        state_reason = inst.get("StateReason", {}).get("Message", "")
        iam_profile = inst.get("IamInstanceProfile", {})
        iam_arn = iam_profile.get("Arn", "") if iam_profile else ""
        # EBS block device mappings
        bdm = []
        for mapping in inst.get("BlockDeviceMappings", []):
            ebs = mapping.get("Ebs", {})
            bdm.append({
                "device_name": mapping.get("DeviceName", ""),
                "volume_id": ebs.get("VolumeId", ""),
                "status": ebs.get("Status", ""),
                "delete_on_termination": ebs.get("DeleteOnTermination", False),
                "attach_time": ebs.get("AttachTime").isoformat() if ebs.get("AttachTime") is not None else "",
            })
        # Network interfaces summary
        net_ifaces = []
        for ni in inst.get("NetworkInterfaces", []):
            net_ifaces.append({
                "network_interface_id": ni.get("NetworkInterfaceId", ""),
                "subnet_id": ni.get("SubnetId", ""),
                "private_ip": ni.get("PrivateIpAddress", ""),
                "mac_address": ni.get("MacAddress", ""),
                "status": ni.get("Status", ""),
            })
        return {
            "instance_id": inst.get("InstanceId"),
            "name": tags.get("Name", inst.get("InstanceId", "")),
            "state": inst.get("State", {}).get("Name", ""),
            "state_reason": state_reason,
            "instance_type": inst.get("InstanceType", ""),
            "region": region,
            "availability_zone": placement.get("AvailabilityZone", ""),
            "tenancy": placement.get("Tenancy", ""),
            "private_ip": inst.get("PrivateIpAddress", ""),
            "public_ip": inst.get("PublicIpAddress", ""),
            "private_dns_name": inst.get("PrivateDnsName", ""),
            "public_dns_name": inst.get("PublicDnsName", ""),
            "launch_time": inst.get("LaunchTime").isoformat() if inst.get("LaunchTime") else "",
            "ami_id": inst.get("ImageId", ""),
            "vpc_id": inst.get("VpcId", ""),
            "subnet_id": inst.get("SubnetId", ""),
            "key_name": inst.get("KeyName", ""),
            "security_groups": [{"id": sg["GroupId"], "name": sg["GroupName"]} for sg in inst.get("SecurityGroups", [])],
            "platform": inst.get("Platform", "linux"),
            "architecture": inst.get("Architecture", ""),
            "virtualization_type": inst.get("VirtualizationType", ""),
            "hypervisor": inst.get("Hypervisor", ""),
            "root_device_type": inst.get("RootDeviceType", ""),
            "root_device_name": inst.get("RootDeviceName", ""),
            "ebs_optimized": inst.get("EbsOptimized", False),
            "monitoring": inst.get("Monitoring", {}).get("State", ""),
            "source_dest_check": inst.get("SourceDestCheck", True),
            "iam_instance_profile": iam_arn,
            "cpu_core_count": cpu_opts.get("CoreCount"),
            "cpu_threads_per_core": cpu_opts.get("ThreadsPerCore"),
            "block_device_mappings": bdm,
            "network_interfaces": net_ifaces,
            "tags": tags,
        }
    except ClientError as e:
        logger.exception("get_aws_instance failed: %s", e)
        raise HTTPException(status_code=500, detail=f"AWS Error: {str(e)}")


@app.post("/api/aws/instance/{instance_id}/tags")
async def update_aws_instance_tags(
    request: Request,
    instance_id: str,
    account: str = Query(...),
    region: str = Query(...)
):
    """Add or update tags on an EC2 instance."""
    if not is_account_allowed(request, account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    body = await request.json()
    tags: Dict[str, str] = body.get("tags", {})
    if not isinstance(tags, dict):
        raise HTTPException(status_code=400, detail="tags must be a JSON object")
    try:
        session = assume_role(account)
        ec2 = session.client("ec2", region_name=region)
        aws_tags = [{"Key": k, "Value": v} for k, v in tags.items()]
        ec2.create_tags(Resources=[instance_id], Tags=aws_tags)
        return {"ok": True, "message": f"Tags updated on {instance_id}"}
    except ClientError as e:
        logger.exception("update_aws_instance_tags failed: %s", e)
        raise HTTPException(status_code=500, detail=f"AWS Error: {str(e)}")


@app.delete("/api/aws/instance/{instance_id}")
async def delete_aws_instance(
    request: Request,
    instance_id: str,
    account: str = Query(...),
    region: str = Query(...),
    delete_volumes: Optional[str] = Query(None, description="Comma-separated EBS volume IDs to delete after termination"),
    release_eips: Optional[str] = Query(None, description="Comma-separated Elastic IP allocation IDs to release after termination"),
):
    """Terminate an EC2 instance and optionally delete associated EBS volumes / release Elastic IPs."""
    if not is_account_allowed(request, account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    try:
        session = assume_role(account)
        ec2 = session.client("ec2", region_name=region)
        ec2.terminate_instances(InstanceIds=[instance_id])

        deleted_resources = []
        errors = []

        volume_ids = [v.strip() for v in (delete_volumes or "").split(",") if v.strip()]
        eip_ids = [e.strip() for e in (release_eips or "").split(",") if e.strip()]

        if volume_ids or eip_ids:
            # Wait for the instance to terminate before deleting volumes / releasing EIPs
            try:
                waiter = ec2.get_waiter("instance_terminated")
                waiter.wait(
                    InstanceIds=[instance_id],
                    WaiterConfig={"Delay": 10, "MaxAttempts": 36},  # up to 6 minutes
                )
            except Exception as wait_err:
                logger.warning("Waiter for instance termination failed (proceeding): %s", wait_err)

            for vol_id in volume_ids:
                try:
                    ec2.delete_volume(VolumeId=vol_id)
                    deleted_resources.append(f"Volume:{vol_id}")
                except ClientError as exc:
                    errors.append(f"Volume {vol_id}: {exc}")

            for alloc_id in eip_ids:
                try:
                    ec2.release_address(AllocationId=alloc_id)
                    deleted_resources.append(f"EIP:{alloc_id}")
                except ClientError as exc:
                    errors.append(f"EIP {alloc_id}: {exc}")

        msg = f"Termination initiated for {instance_id}"
        if deleted_resources:
            msg += f"; also deleted: {', '.join(deleted_resources)}"
        if errors:
            msg += f"; cleanup errors: {'; '.join(errors)}"
        _audit(
            request, "delete_vm", "aws",
            resource_name=instance_id, resource_id=instance_id,
            account_or_subscription=account, region_or_zone=region,
            detail=msg,
        )
        return {"ok": True, "message": msg}
    except ClientError as e:
        logger.exception("delete_aws_instance failed: %s", e)
        _audit(
            request, "delete_vm", "aws",
            resource_name=instance_id, resource_id=instance_id,
            account_or_subscription=account, region_or_zone=region,
            status="failed", error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=f"AWS Error: {str(e)}")


@app.post("/api/aws/instance/{instance_id}/restart")
async def restart_aws_instance(
    request: Request,
    instance_id: str,
    account: str = Query(...),
    region: str = Query(...)
):
    """Reboot an EC2 instance."""
    if not is_account_allowed(request, account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    try:
        session = assume_role(account)
        ec2 = session.client("ec2", region_name=region)
        ec2.reboot_instances(InstanceIds=[instance_id])
        return {"ok": True, "message": f"Reboot initiated for {instance_id}"}
    except ClientError as e:
        logger.exception("restart_aws_instance failed: %s", e)
        raise HTTPException(status_code=500, detail=f"AWS Error: {str(e)}")


@app.post("/api/aws/instance/{instance_id}/power")
async def power_aws_instance(
    request: Request,
    instance_id: str,
    account: str = Query(...),
    region: str = Query(...),
    action: str = Query(..., description="'start' or 'stop'")
):
    """Start or stop an EC2 instance."""
    if not is_account_allowed(request, account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    action = action.lower()
    if action not in ("start", "stop"):
        raise HTTPException(status_code=400, detail="action must be 'start' or 'stop'")
    try:
        session = assume_role(account)
        ec2 = session.client("ec2", region_name=region)
        if action == "start":
            ec2.start_instances(InstanceIds=[instance_id])
            msg = f"Start initiated for {instance_id}"
        else:
            ec2.stop_instances(InstanceIds=[instance_id])
            msg = f"Stop initiated for {instance_id}"
        return {"ok": True, "message": msg}
    except ClientError as e:
        logger.exception("power_aws_instance failed: %s", e)
        raise HTTPException(status_code=500, detail=f"AWS Error: {str(e)}")


@app.post("/api/aws/instance/{instance_id}/resize")
async def resize_aws_instance(
    request: Request,
    instance_id: str,
    account: str = Query(...),
    region: str = Query(...),
    new_type: str = Query(...)
):
    """Change the instance type of a stopped EC2 instance (stops it first if running)."""
    if not is_account_allowed(request, account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    try:
        session = assume_role(account)
        ec2 = session.client("ec2", region_name=region)
        resp = ec2.describe_instances(InstanceIds=[instance_id])
        state = resp["Reservations"][0]["Instances"][0]["State"]["Name"]
        was_running = state == "running"
        if was_running:
            ec2.stop_instances(InstanceIds=[instance_id])
            waiter = ec2.get_waiter("instance_stopped")
            waiter.wait(InstanceIds=[instance_id])
        ec2.modify_instance_attribute(InstanceId=instance_id, InstanceType={"Value": new_type})
        if was_running:
            ec2.start_instances(InstanceIds=[instance_id])
            return {"ok": True, "message": f"Instance {instance_id} resized to {new_type} and restarted"}
        return {"ok": True, "message": f"Instance {instance_id} resized to {new_type} (was already stopped; start it manually if needed)"}
    except ClientError as e:
        logger.exception("resize_aws_instance failed: %s", e)
        raise HTTPException(status_code=500, detail=f"AWS Error: {str(e)}")


class AttachDiskRequest(BaseModel):
    disk_name: str
    size_gb: int
    disk_type: str = "gp3"


@app.post("/api/aws/instance/{instance_id}/attach-disk")
async def attach_disk_aws(
    request: Request,
    instance_id: str,
    account: str = Query(...),
    region: str = Query(...),
    body: AttachDiskRequest = Body(...)
):
    """Create a new EBS volume and attach it to an EC2 instance."""
    if not is_account_allowed(request, account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    try:
        session = assume_role(account)
        ec2 = session.client("ec2", region_name=region)
        # Determine AZ from instance
        resp = ec2.describe_instances(InstanceIds=[instance_id])
        az = resp["Reservations"][0]["Instances"][0]["Placement"]["AvailabilityZone"]
        vol = ec2.create_volume(
            AvailabilityZone=az,
            Size=body.size_gb,
            VolumeType=body.disk_type,
            TagSpecifications=[{"ResourceType": "volume", "Tags": [{"Key": "Name", "Value": body.disk_name}]}],
        )
        volume_id = vol["VolumeId"]
        waiter = ec2.get_waiter("volume_available")
        waiter.wait(VolumeIds=[volume_id])
        # Determine next available device letter
        existing = resp["Reservations"][0]["Instances"][0].get("BlockDeviceMappings", [])
        used = {m["DeviceName"] for m in existing}
        device = next((f"/dev/sd{c}" for c in "fghijklmnop" if f"/dev/sd{c}" not in used), "/dev/sdf")
        ec2.attach_volume(VolumeId=volume_id, InstanceId=instance_id, Device=device)
        return {"ok": True, "message": f"Volume {volume_id} ({body.size_gb} GB) attached as {device}"}
    except ClientError as e:
        logger.exception("attach_disk_aws failed: %s", e)
        raise HTTPException(status_code=500, detail=f"AWS Error: {str(e)}")


class ResizeDiskRequest(BaseModel):
    new_size_gb: int


@app.post("/api/aws/volume/{volume_id}/resize")
async def resize_aws_volume(
    request: Request,
    volume_id: str,
    account: str = Query(...),
    region: str = Query(...),
    body: ResizeDiskRequest = Body(...)
):
    """Resize an EBS volume (increase only). The OS may need a file system extend after resize."""
    if not is_account_allowed(request, account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    try:
        session = assume_role(account)
        ec2 = session.client("ec2", region_name=region)
        ec2.modify_volume(VolumeId=volume_id, Size=body.new_size_gb)
        return {"ok": True, "message": f"Volume {volume_id} resize initiated to {body.new_size_gb} GB. The file system may need extending inside the OS."}
    except ClientError as e:
        logger.exception("resize_aws_volume failed: %s", e)
        raise HTTPException(status_code=500, detail=f"AWS Error: {str(e)}")


@app.delete("/api/aws/volume/{volume_id}")
async def delete_aws_volume(
    request: Request,
    volume_id: str,
    account: str = Query(...),
    region: str = Query(...),
    instance_id: str = Query(None)
):
    """Detach (if attached) and delete an EBS volume. Cannot delete root volumes while instance is running."""
    if not is_account_allowed(request, account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    try:
        session = assume_role(account)
        ec2 = session.client("ec2", region_name=region)
        # Describe volume to check state
        desc = ec2.describe_volumes(VolumeIds=[volume_id])
        vols = desc.get("Volumes", [])
        if not vols:
            raise HTTPException(status_code=404, detail="Volume not found")
        vol_state = vols[0].get("State", "")
        if vol_state == "in-use":
            # Detach first
            ec2.detach_volume(VolumeId=volume_id, Force=True)
            for _ in range(30):
                d = ec2.describe_volumes(VolumeIds=[volume_id])
                if d["Volumes"][0]["State"] == "available":
                    break
                time.sleep(3)
        ec2.delete_volume(VolumeId=volume_id)
        _audit(
            request, "delete_volume", "aws",
            resource_name=volume_id, resource_id=volume_id,
            account_or_subscription=account, region_or_zone=region,
            detail=f"Deleted volume {volume_id}" + (f" (was attached to {instance_id})" if instance_id else ""),
        )
        return {"ok": True, "message": f"Volume {volume_id} deleted successfully."}
    except ClientError as e:
        logger.exception("delete_aws_volume failed: %s", e)
        _audit(
            request, "delete_volume", "aws",
            resource_name=volume_id, resource_id=volume_id,
            account_or_subscription=account, region_or_zone=region,
            status="failed", error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=f"AWS Error: {str(e)}")


class SnapshotRequest(BaseModel):
    snapshot_name: str
    description: str = ""


@app.post("/api/aws/instance/{instance_id}/snapshot")
async def snapshot_aws_instance(
    request: Request,
    instance_id: str,
    account: str = Query(...),
    region: str = Query(...),
    body: SnapshotRequest = Body(...)
):
    """Create an EBS snapshot of the root (OS) volume attached to an EC2 instance."""
    if not is_account_allowed(request, account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    try:
        session = assume_role(account)
        ec2 = session.client("ec2", region_name=region)
        resp = ec2.describe_instances(InstanceIds=[instance_id])
        instance = resp["Reservations"][0]["Instances"][0]
        root_device_name = instance.get("RootDeviceName", "")
        bdm = instance.get("BlockDeviceMappings", [])
        # Only snapshot the root (OS) volume; fall back to first volume if no match
        root_mapping = next(
            (m for m in bdm if m.get("DeviceName") == root_device_name),
            bdm[0] if bdm else None
        )
        if not root_mapping:
            raise HTTPException(status_code=400, detail="No volumes found on instance")
        vol_id = root_mapping["Ebs"]["VolumeId"]
        snap = ec2.create_snapshot(
            VolumeId=vol_id,
            Description=body.description or f"Snapshot of {instance_id} volume {vol_id}",
            TagSpecifications=[{"ResourceType": "snapshot", "Tags": [{"Key": "Name", "Value": body.snapshot_name}]}],
        )
        _audit(
            request, "snapshot_vm", "aws",
            resource_name=body.snapshot_name, resource_id=snap["SnapshotId"],
            account_or_subscription=account, region_or_zone=region,
            detail=f"Snapshot of instance {instance_id} root volume {vol_id}",
        )
        return {"ok": True, "message": f"Snapshot created: {snap['SnapshotId']}"}
    except ClientError as e:
        logger.exception("snapshot_aws_instance failed: %s", e)
        _audit(
            request, "snapshot_vm", "aws",
            resource_name=body.snapshot_name, resource_id=instance_id,
            account_or_subscription=account, region_or_zone=region,
            status="failed", error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=f"AWS Error: {str(e)}")


@app.get("/api/aws/instance/{instance_id}/snapshots")
async def list_aws_snapshots(
    request: Request,
    instance_id: str,
    account: str = Query(...),
    region: str = Query(...),
):
    """List EBS snapshots associated with this instance's root volume."""
    if not is_account_allowed(request, account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    try:
        session = assume_role(account)
        ec2 = session.client("ec2", region_name=region)
        resp = ec2.describe_instances(InstanceIds=[instance_id])
        instance = resp["Reservations"][0]["Instances"][0]
        root_device = instance.get("RootDeviceName", "")
        bdm = instance.get("BlockDeviceMappings", [])
        root_mapping = next(
            (m for m in bdm if m.get("DeviceName") == root_device),
            bdm[0] if bdm else None,
        )
        if not root_mapping:
            return {"snapshots": []}
        vol_id = root_mapping["Ebs"]["VolumeId"]
        snaps = ec2.describe_snapshots(
            Filters=[{"Name": "volume-id", "Values": [vol_id]}],
            OwnerIds=["self"],
        )
        result = []
        for s in sorted(snaps["Snapshots"], key=lambda x: x["StartTime"], reverse=True):
            result.append({
                "id": s["SnapshotId"],
                "name": next((t["Value"] for t in s.get("Tags", []) if t["Key"] == "Name"), ""),
                "description": s.get("Description", ""),
                "state": s["State"],
                "start_time": s["StartTime"].isoformat(),
                "volume_size": s.get("VolumeSize"),
            })
        return {"snapshots": result}
    except ClientError as e:
        logger.exception("list_aws_snapshots failed: %s", e)
        raise HTTPException(status_code=500, detail=f"AWS Error: {str(e)}")


@app.delete("/api/aws/snapshot/{snapshot_id}")
async def delete_aws_snapshot(
    request: Request,
    snapshot_id: str,
    account: str = Query(...),
    region: str = Query(...),
):
    """Delete an EBS snapshot by ID."""
    if not is_account_allowed(request, account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    try:
        session = assume_role(account)
        ec2 = session.client("ec2", region_name=region)
        ec2.delete_snapshot(SnapshotId=snapshot_id)
        _audit(
            request, "delete_snapshot", "aws",
            resource_name=snapshot_id, resource_id=snapshot_id,
            account_or_subscription=account, region_or_zone=region,
        )
        return {"ok": True, "message": f"Snapshot {snapshot_id} deleted"}
    except ClientError as e:
        logger.exception("delete_aws_snapshot failed: %s", e)
        _audit(
            request, "delete_snapshot", "aws",
            resource_name=snapshot_id, resource_id=snapshot_id,
            account_or_subscription=account, region_or_zone=region,
            status="failed", error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=f"AWS Error: {str(e)}")


# ── Azure: list existing VMs ──────────────────────────────────────────────────
def _extract_azure_rg(vm_id: str) -> str:
    """Safely extract resource group name from an Azure VM ID."""
    try:
        if vm_id and "/resourceGroups/" in vm_id:
            return vm_id.split("/resourceGroups/")[1].split("/")[0]
    except Exception:
        pass
    return ""


@app.get("/api/azure/vms")
def list_azure_vms(
    request: Request,
    subscription_id: str = Query(...),
    resource_group: Optional[str] = Query(None)
):
    """List existing Azure VMs, optionally scoped to a resource group."""
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        creds = get_azure_credentials()
        compute_client = ComputeManagementClient(creds, subscription_id)
        if resource_group:
            vms_iter = compute_client.virtual_machines.list(resource_group)
        else:
            vms_iter = compute_client.virtual_machines.list_all()

        result = []
        for vm in vms_iter:
            tags = vm.tags or {}
            state = "unknown"
            rg = _extract_azure_rg(vm.id)
            try:
                instance_view = compute_client.virtual_machines.instance_view(rg, vm.name)
                statuses = getattr(instance_view, "statuses", []) or []
                for s in statuses:
                    code = getattr(s, "code", "") or ""
                    if code.startswith("PowerState/"):
                        state = code.split("/")[1]
                        break
            except Exception:
                pass

            location = getattr(vm, "location", "")
            vm_size = getattr(getattr(vm, "hardware_profile", None), "vm_size", "") or ""
            os_type = ""
            storage_profile = getattr(vm, "storage_profile", None)
            if storage_profile:
                os_disk = getattr(storage_profile, "os_disk", None)
                if os_disk:
                    os_type = str(getattr(os_disk, "os_type", "") or "")
            result.append({
                "vm_id": vm.id,
                "name": vm.name,
                "state": state,
                "vm_size": vm_size,
                "location": location,
                "resource_group": rg,
                "os_type": os_type,
                "tags": {k: v for k, v in tags.items()},
            })
        return {"vms": result}
    except HttpResponseError as e:
        logger.exception("list_azure_vms failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Azure Error: {str(e)}")


@app.get("/api/azure/sql-databases")
def list_azure_sql_databases(
    request: Request,
    subscription_id: str = Query(...),
    resource_group: Optional[str] = Query(None),
):
    """List Azure SQL databases for a subscription/resource group."""
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        creds = get_azure_credentials()
        resource_client = ResourceManagementClient(creds, subscription_id)
        filter_expr = "resourceType eq 'Microsoft.Sql/servers/databases'"
        if resource_group:
            resources_iter = resource_client.resources.list_by_resource_group(resource_group_name=resource_group, filter=filter_expr)
        else:
            resources_iter = resource_client.resources.list(filter=filter_expr)

        result = []
        for res in resources_iter:
            full_name = getattr(res, "name", "") or ""
            server_name = ""
            database_name = full_name
            if "/" in full_name:
                server_name, database_name = full_name.split("/", 1)
            # Azure SQL returns the system "master" database for each server; we hide it
            # in portal listings because user actions should target application databases.
            if database_name.lower() == "master":
                continue

            rg = _extract_azure_rg(getattr(res, "id", ""))
            state = "unknown"
            sku_name = ""
            try:
                details = resource_client.resources.get_by_id(res.id, api_version="2021-11-01")
                props = getattr(details, "properties", None) or {}
                state = props.get("status") or props.get("state") or state
                sku_obj = getattr(details, "sku", None)
                # Depending on SDK/serialization path, sku may be a dict or model object.
                if isinstance(sku_obj, dict):
                    sku_name = sku_obj.get("name", "") or ""
                elif sku_obj is not None:
                    sku_name = getattr(sku_obj, "name", "") or str(sku_obj)
            except Exception:
                pass

            result.append({
                "id": res.id,
                "name": database_name,
                "database_name": database_name,
                "server_name": server_name,
                "state": state,
                "sku": sku_name,
                "location": getattr(res, "location", "") or "",
                "resource_group": rg,
            })
        return {"sql_databases": result}
    except HttpResponseError as e:
        logger.exception("list_azure_sql_databases failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Azure Error: {str(e)}")


@app.get("/api/azure/sql-servers")
def list_azure_sql_servers(
    request: Request,
    subscription_id: str = Query(...),
    resource_group: str = Query(...),
):
    """List Azure SQL servers in a resource group."""
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        creds = get_azure_credentials()
        resource_client = ResourceManagementClient(creds, subscription_id)
        resources_iter = resource_client.resources.list_by_resource_group(
            resource_group_name=resource_group,
            filter="resourceType eq 'Microsoft.Sql/servers'",
        )
        servers = []
        for res in resources_iter:
            servers.append({
                "id": getattr(res, "id", ""),
                "name": getattr(res, "name", ""),
                "location": getattr(res, "location", ""),
            })
        servers.sort(key=lambda x: (x.get("name") or "").lower())
        return {"sql_servers": servers}
    except HttpResponseError as e:
        logger.exception("list_azure_sql_servers failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Azure Error: {str(e)}")


@app.get("/api/azure/user-assigned-identities")
def list_azure_user_assigned_identities(
    request: Request,
    subscription_id: str = Query(...),
):
    """List user-assigned managed identities in the given Azure subscription."""
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        creds = get_azure_credentials()
        resource_client = ResourceManagementClient(creds, subscription_id)
        resources = resource_client.resources.list(
            filter="resourceType eq 'Microsoft.ManagedIdentity/userAssignedIdentities'"
        )
        identities = []
        for item in resources:
            rid = getattr(item, "id", "") or ""
            rg = ""
            parts = rid.split("/")
            if len(parts) >= 5 and parts[3].lower() == "resourcegroups":
                rg = parts[4]
            identities.append({
                "id": rid,
                "name": getattr(item, "name", "") or "",
                "resource_group": rg,
                "subscription": subscription_id,
            })
        identities.sort(key=lambda x: (x.get("name") or "").lower())
        return identities
    except HttpResponseError as e:
        logger.exception("list_azure_user_assigned_identities failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Azure Error: {str(e)}")


@app.post("/api/azure/deploy-sql")
async def deploy_azure_sql_managed_instance(request: Request):
    """Deploy an Azure SQL Managed Instance."""
    data = await request.json()
    required_keys = ["subscription_id", "resource_group", "managed_instance_name", "subnet_id"]
    for key in required_keys:
        if not data.get(key):
            raise HTTPException(status_code=400, detail=f"Missing field: {key}")
    if not is_subscription_allowed(request, data["subscription_id"]):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")

    try:
        creds = get_azure_credentials()
        resource_client = ResourceManagementClient(creds, data["subscription_id"])
        network_client = NetworkManagementClient(get_azure_credentials_service_principal(), data["subscription_id"])
        location = (data.get("location") or "").strip()
        if not location:
            rg = resource_client.resource_groups.get(data["resource_group"])
            location = rg.location

        managed_instance_name = (data.get("managed_instance_name") or "").strip()
        if not managed_instance_name:
            raise HTTPException(status_code=400, detail="Missing field: managed_instance_name")
        if not re.match(r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$', managed_instance_name):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Managed instance name must be 1–63 characters, contain only lowercase letters "
                    "(a-z), numbers (0-9), and hyphens (-), and must not start or end with a hyphen."
                ),
            )
        _check_sql_managed_instance_name_available(creds, data["subscription_id"], managed_instance_name)
        subnet_id = (data.get("subnet_id") or "").strip()
        subnet_parts = _parse_azure_subnet_resource_id(subnet_id)
        if not subnet_parts:
            raise HTTPException(status_code=400, detail="subnet_id must be a valid Azure subnet resource ID")
        if subnet_parts["subscription_id"].lower() != data["subscription_id"].lower():
            raise HTTPException(status_code=400, detail="subnet_id must belong to the selected Azure subscription")
        try:
            vnet = network_client.virtual_networks.get(
                subnet_parts["resource_group"],
                subnet_parts["vnet_name"],
            )
        except HttpResponseError as vnet_err:
            raise HTTPException(status_code=400, detail=f"Unable to read selected virtual network: {vnet_err.message or str(vnet_err)}")
        vnet_location = (getattr(vnet, "location", None) or "").strip()
        if location and vnet_location and vnet_location.lower() != location.lower():
            raise HTTPException(
                status_code=400,
                detail=f"Selected subnet must be in the same Azure region as the managed instance (managed instance: {location}, subnet VNet: {vnet_location})",
            )
        try:
            subnet = network_client.subnets.get(
                subnet_parts["resource_group"],
                subnet_parts["vnet_name"],
                subnet_parts["subnet_name"],
            )
        except HttpResponseError as subnet_err:
            raise HTTPException(status_code=400, detail=f"Unable to read selected subnet: {subnet_err.message or str(subnet_err)}")
        subnet_validation_errors = _get_sql_mi_subnet_validation_errors(subnet)
        if subnet_validation_errors:
            raise HTTPException(
                status_code=400,
                detail="Selected subnet is not supported for Azure SQL Managed Instance: " + "; ".join(subnet_validation_errors),
            )
        auth_method = (data.get("authentication_method") or "").strip().lower()
        if not auth_method:
            raise HTTPException(status_code=400, detail="Missing field: authentication_method")
        if auth_method not in ("entra_only", "both", "sql_only"):
            raise HTTPException(status_code=400, detail="authentication_method must be one of: entra_only, both, sql_only")

        admin_user = (data.get("server_admin_username") or "").strip()
        admin_password = (data.get("server_admin_password") or "").strip()
        if not admin_user or not admin_password:
            raise HTTPException(status_code=400, detail="Managed instance admin username and password are required")

        entra_admin_login = (data.get("entra_admin_login") or "").strip()
        entra_admin_object_id = (data.get("entra_admin_object_id") or "").strip()
        require_entra_auth = auth_method in ("both", "entra_only")
        if require_entra_auth and (not entra_admin_login or not entra_admin_object_id):
            current_user = get_current_user(request) or {}
            entra_admin_login = entra_admin_login or (current_user.get("email") or "").strip()
            entra_admin_object_id = entra_admin_object_id or (current_user.get("oid") or "").strip()
            data["entra_admin_login"] = entra_admin_login
            data["entra_admin_object_id"] = entra_admin_object_id
        entra_admin_principal_type_input = (data.get("entra_admin_principal_type") or "").strip()
        entra_admin_principal_type = entra_admin_principal_type_input or ("User" if "@" in entra_admin_login else "Group")
        if entra_admin_principal_type not in ("User", "Group", "Application"):
            raise HTTPException(status_code=400, detail="entra_admin_principal_type must be one of: User, Group, Application")
        data["entra_admin_principal_type"] = entra_admin_principal_type
        if require_entra_auth and (not entra_admin_login or not entra_admin_object_id):
            raise HTTPException(status_code=400, detail="entra_admin_login and entra_admin_object_id are required for Microsoft Entra authentication")

        try:
            capacity = int(data.get("capacity") if data.get("capacity") not in (None, "") else 4)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="capacity must be a valid integer")
        if capacity <= 0:
            raise HTTPException(status_code=400, detail="capacity must be a positive integer")

        try:
            storage_size_gb = int(data.get("max_size_gb") if data.get("max_size_gb") not in (None, "") else 256)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="max_size_gb must be a valid integer")
        if storage_size_gb < 32:
            raise HTTPException(status_code=400, detail="max_size_gb must be at least 32")

        storage_iops = None
        if data.get("storage_iops") not in (None, ""):
            try:
                storage_iops = int(data["storage_iops"])
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail="storage_iops must be a valid integer")
            if storage_iops < 300:
                raise HTTPException(status_code=400, detail="storage_iops must be at least 300")

        license_type_map = {"payg": "LicenseIncluded", "ahb": "BasePrice"}
        license_type = license_type_map.get((data.get("license_type") or "").strip().lower(), "LicenseIncluded")
        sku_name = (data.get("sku_name") or "GP_Gen5").strip()
        sku_tier = (data.get("sku_tier") or "GeneralPurpose").strip()
        sku_family = (data.get("sku_family") or "").strip()
        if not sku_family:
            sku_parts = sku_name.split("_")
            if sku_parts and sku_parts[-1].lower().startswith("gen"):
                sku_family = sku_parts[-1]
            else:
                sku_family = "Gen5"
        proxy_override_input = (data.get("proxy_override") or "").strip().lower()
        proxy_override_map = {
            "redirect": "Redirect",
            "proxy": "Proxy",
            "default": "Default",
        }
        if proxy_override_input and proxy_override_input not in proxy_override_map:
            raise HTTPException(status_code=400, detail="proxy_override must be one of: redirect, proxy, default")

        mi_properties: Dict[str, Any] = {
            "administratorLogin": admin_user,
            "administratorLoginPassword": admin_password,
            "subnetId": subnet_id,
            "licenseType": license_type,
            "storageSizeInGB": storage_size_gb,
            "minimalTlsVersion": data.get("minimal_tls_version") or "1.2",
            "publicDataEndpointEnabled": bool(data.get("public_data_endpoint_enabled")),
        }
        if data.get("collation"):
            mi_properties["collation"] = data["collation"]
        if data.get("backup_storage_redundancy"):
            mi_properties["requestedBackupStorageRedundancy"] = data["backup_storage_redundancy"]
        if data.get("zone_redundant") is not None:
            mi_properties["zoneRedundant"] = bool(data.get("zone_redundant"))
        if storage_iops is not None:
            mi_properties["storageIOps"] = storage_iops
        if data.get("instance_pool_id"):
            mi_properties["instancePoolId"] = data["instance_pool_id"]
        if data.get("timezone_id"):
            mi_properties["timezoneId"] = data["timezone_id"]
        if proxy_override_input:
            mi_properties["proxyOverride"] = proxy_override_map[proxy_override_input]
        if require_entra_auth:
            mi_properties["administrators"] = {
                "administratorType": "ActiveDirectory",
                "login": entra_admin_login,
                "sid": entra_admin_object_id,
                "tenantId": TENANT_ID,
                "principalType": entra_admin_principal_type,
                "azureADOnlyAuthentication": auth_method == "entra_only",
            }

        sql_engine_update_policy = (data.get("sql_engine_update_policy") or "").strip()
        if sql_engine_update_policy and sql_engine_update_policy not in ("always_up_to_date", "sql_server_2022", "sql_server_2025"):
            raise HTTPException(status_code=400, detail="sql_engine_update_policy must be one of: always_up_to_date, sql_server_2022, sql_server_2025")
        maintenance_window = (data.get("maintenance_window") or "").strip()
        if maintenance_window and maintenance_window not in ("system_default", "weekdays_22_06", "weekends_22_06", "weekdays_09_17"):
            raise HTTPException(status_code=400, detail="maintenance_window must be one of: system_default, weekdays_22_06, weekends_22_06, weekdays_09_17")

        sku_obj: Dict[str, Any] = {
            "name": sku_name,
            "tier": sku_tier,
            "capacity": capacity,
        }
        sku_obj["family"] = sku_family

        params: Dict[str, Any] = {"location": location, "sku": sku_obj, "properties": mi_properties}
        tags = data.get("tags") if isinstance(data.get("tags"), dict) else {}
        # Always inject the mandatory SQL MI team tag regardless of UI input
        tags["Team"] = "mcd-das-sql"
        if sql_engine_update_policy and sql_engine_update_policy != "always_up_to_date":
            tags.setdefault("SqlEngineUpdatePolicy", sql_engine_update_policy)
        if maintenance_window and maintenance_window != "system_default":
            tags.setdefault("MaintenanceWindow", maintenance_window)
        if bool(data.get("geo_replication_enabled")):
            tags.setdefault("GeoReplication", "enabled")
        params["tags"] = tags

        # Build identity block for the managed instance
        identity_system_assigned = bool(data.get("identity_system_assigned"))
        identity_user_assigned_ids = data.get("identity_user_assigned")
        if not isinstance(identity_user_assigned_ids, list):
            identity_user_assigned_ids = []
        identity_user_assigned_ids = [str(uid).strip() for uid in identity_user_assigned_ids if str(uid).strip()]
        identity_primary = (data.get("identity_primary") or "").strip()
        if identity_primary and identity_primary not in identity_user_assigned_ids:
            raise HTTPException(status_code=400, detail="identity_primary must be one of the selected user-assigned managed identities")
        # Microsoft Entra authentication requires an instance identity with Microsoft Graph read
        # permissions. Prefer a selected pre-permissioned UMI; otherwise fall back to SMI.
        if require_entra_auth and not identity_primary:
            identity_system_assigned = True
        if identity_primary:
            mi_properties["primaryUserAssignedIdentityId"] = identity_primary
        if identity_system_assigned or identity_user_assigned_ids:
            if identity_system_assigned and identity_user_assigned_ids:
                identity_type = "SystemAssigned,UserAssigned"
            elif identity_system_assigned:
                identity_type = "SystemAssigned"
            else:
                identity_type = "UserAssigned"
            identity_block: Dict[str, Any] = {"type": identity_type}
            if identity_user_assigned_ids:
                identity_block["userAssignedIdentities"] = {uid: {} for uid in identity_user_assigned_ids}
            params["identity"] = identity_block

        resource_id = (
            f"/subscriptions/{data['subscription_id']}/resourceGroups/{data['resource_group']}"
            f"/providers/Microsoft.Sql/managedInstances/{managed_instance_name}"
        )
        deployment_id = f"{managed_instance_name}-{uuid.uuid4().hex[:12]}"
        update_deployment_status(
            deployment_id,
            "starting",
            f"Starting Azure SQL Managed Instance deployment for {managed_instance_name}.",
            vm_id=resource_id,
        )
        thread = threading.Thread(
            target=_deploy_sql_managed_instance_background,
            args=(
                deployment_id,
                data,
                location,
                managed_instance_name,
                params,
                require_entra_auth,
                auth_method,
                entra_admin_login,
                entra_admin_object_id,
                resource_id,
            ),
            daemon=False,
        )
        thread.start()

        _audit(
            request, "deploy_sql_managed_instance", "azure",
            resource_name=managed_instance_name, resource_id=resource_id,
            account_or_subscription=data["subscription_id"], region_or_zone=location,
        )
        return {
            "status": "started",
            "message": "Azure SQL Managed Instance deployment initiated.",
            "managed_instance_name": managed_instance_name,
            "deployment_id": deployment_id,
            "resource_id": resource_id,
        }
    except HttpResponseError as e:
        logger.exception("deploy_azure_sql_managed_instance failed: %s", e)
        # Azure SDK errors can append a large raw JSON payload after "Content:".
        # Keep only the leading message to avoid returning noisy response bodies to UI users.
        error_message = _clean_azure_error_message(str(e))
        _audit(
            request, "deploy_sql_managed_instance", "azure",
            resource_name=data.get("managed_instance_name"), account_or_subscription=data.get("subscription_id"),
            region_or_zone=data.get("location"), status="failed", error_message=error_message,
        )
        raise HTTPException(status_code=500, detail=f"Azure SQL Managed Instance deployment failed: {error_message}")


@app.delete("/api/azure/sql-database")
def delete_azure_sql_database(
    request: Request,
    subscription_id: str = Query(...),
    resource_group: str = Query(...),
    server_name: str = Query(...),
    database_name: str = Query(...),
):
    """Delete an Azure SQL database."""
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        creds = get_azure_credentials()
        resource_client = ResourceManagementClient(creds, subscription_id)
        poller = resource_client.resources.begin_delete(
            resource_group_name=resource_group,
            resource_provider_namespace="Microsoft.Sql",
            parent_resource_path=f"servers/{server_name}",
            resource_type="databases",
            resource_name=database_name,
            api_version="2021-11-01",
        )
        poller.result()
        _audit(
            request, "delete_sql", "azure",
            resource_name=database_name, account_or_subscription=subscription_id,
        )
        return {"ok": True, "message": f"Deletion initiated for SQL database {database_name}"}
    except HttpResponseError as e:
        logger.exception("delete_azure_sql_database failed: %s", e)
        _audit(
            request, "delete_sql", "azure",
            resource_name=database_name, account_or_subscription=subscription_id,
            status="failed", error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Azure SQL delete failed: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# Azure SQL Managed Instance – list / start / stop / new-db / reset-password / delete
# ─────────────────────────────────────────────────────────────────────────────

AZURE_SQL_MI_LIST_API_VERSION = "2021-11-01"


@app.get("/api/azure/sql-managed-instances")
def list_azure_sql_managed_instances(
    request: Request,
    subscription_id: str = Query(...),
    resource_group: Optional[str] = Query(None),
):
    """List Azure SQL Managed Instances for a subscription/resource group."""
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        creds = get_azure_credentials()
        resource_client = ResourceManagementClient(creds, subscription_id)
        filter_expr = "resourceType eq 'Microsoft.Sql/managedInstances'"
        if resource_group:
            resources_iter = resource_client.resources.list_by_resource_group(
                resource_group_name=resource_group, filter=filter_expr
            )
        else:
            resources_iter = resource_client.resources.list(filter=filter_expr)

        result = []
        for res in resources_iter:
            rid = getattr(res, "id", "") or ""
            rg = _extract_azure_rg(rid)
            state = "unknown"
            sku_name = ""
            fqdn = ""
            try:
                details = resource_client.resources.get_by_id(res.id, api_version=AZURE_SQL_MI_LIST_API_VERSION)
                props = getattr(details, "properties", None) or {}
                if isinstance(props, dict):
                    state = props.get("state") or props.get("provisioningState") or state
                    fqdn = props.get("fullyQualifiedDomainName") or ""
                else:
                    state = getattr(props, "state", None) or getattr(props, "provisioning_state", None) or state
                    fqdn = getattr(props, "fully_qualified_domain_name", None) or getattr(props, "fullyQualifiedDomainName", None) or ""
                sku_obj = getattr(details, "sku", None)
                if isinstance(sku_obj, dict):
                    sku_name = sku_obj.get("name", "") or ""
                elif sku_obj is not None:
                    sku_name = getattr(sku_obj, "name", "") or str(sku_obj)
            except Exception:
                pass
            result.append({
                "id": rid,
                "name": getattr(res, "name", "") or "",
                "state": state,
                "sku": sku_name,
                "location": getattr(res, "location", "") or "",
                "resource_group": rg,
                "subscription_id": subscription_id,
                "fqdn": fqdn,
            })
        result.sort(key=lambda x: (x.get("name") or "").lower())
        return {"sql_managed_instances": result}
    except HttpResponseError as e:
        logger.exception("list_azure_sql_managed_instances failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Azure Error: {str(e)}")


@app.get("/api/azure/sql-mi-details")
def get_azure_sql_managed_instance_details(
    request: Request,
    subscription_id: str = Query(...),
    resource_group: str = Query(...),
    managed_instance_name: str = Query(...),
):
    """Get details of a specific Azure SQL Managed Instance."""
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        creds = get_azure_credentials()
        resource_client = ResourceManagementClient(creds, subscription_id)
        resource_id = (
            f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
            f"/providers/Microsoft.Sql/managedInstances/{managed_instance_name}"
        )
        details = resource_client.resources.get_by_id(resource_id, api_version=AZURE_SQL_MI_LIST_API_VERSION)
        props = getattr(details, "properties", None) or {}

        def _prop(name: str, alt: Optional[str] = None, default: Any = "") -> Any:
            if isinstance(props, dict):
                if name in props:
                    return props.get(name)
                if alt and alt in props:
                    return props.get(alt)
                return default
            value = getattr(props, name, None)
            if value is None and alt:
                value = getattr(props, alt, None)
            return default if value is None else value

        subnet_id = _prop("subnetId", "subnet_id", "") or ""
        vnet_name = ""
        subnet_name = ""
        if "/virtualNetworks/" in subnet_id:
            try:
                vnet_name = subnet_id.split("/virtualNetworks/")[1].split("/")[0]
            except Exception:
                vnet_name = ""
        if "/subnets/" in subnet_id:
            try:
                subnet_name = subnet_id.split("/subnets/")[1].split("/")[0]
            except Exception:
                subnet_name = ""

        def _arm_id_name(value: Any) -> str:
            if isinstance(value, dict):
                value = value.get("id") or ""
            value = str(value or "").strip()
            return value.strip("/").split("/")[-1] if value else ""

        virtual_cluster_id = _prop("virtualClusterId", "virtual_cluster_id", "") or ""
        virtual_cluster = _arm_id_name(virtual_cluster_id)
        instance_pool_id = _prop("instancePoolId", "instance_pool_id", "") or ""
        instance_pool = _arm_id_name(instance_pool_id)

        sku_obj = getattr(details, "sku", None)
        sku_name = ""
        sku_tier = ""
        if isinstance(sku_obj, dict):
            sku_name = sku_obj.get("name", "") or ""
            sku_tier = sku_obj.get("tier", "") or ""
        elif sku_obj is not None:
            sku_name = getattr(sku_obj, "name", "") or ""
            sku_tier = getattr(sku_obj, "tier", "") or ""

        pricing_tier = " / ".join(x for x in [sku_tier, sku_name] if x)
        tags_obj = getattr(details, "tags", None) or {}
        if not isinstance(tags_obj, dict):
            tags_obj = {}
        # SQL MI responses use either camelCase or snake_case depending on the SDK payload shape.
        admin_username = _prop("administratorLogin", "administrator_login", "")
        entra_admin_login = ""

        try:
            aad_admin = resource_client.resources.get(
                resource_group_name=resource_group,
                resource_provider_namespace="Microsoft.Sql",
                parent_resource_path=f"managedInstances/{managed_instance_name}",
                resource_type="administrators",
                resource_name="ActiveDirectory",
                api_version=AZURE_SQL_MI_API_VERSION,
            )
            aad_props = getattr(aad_admin, "properties", None) or {}
            if isinstance(aad_props, dict):
                entra_admin_login = (
                    aad_props.get("login")
                    or aad_props.get("administratorLogin")
                )
            else:
                entra_admin_login = (
                    getattr(aad_props, "login", None)
                    or getattr(aad_props, "administrator_login", None)
                )
        except HttpResponseError as aad_err:
            aad_err_text = str(aad_err or "").strip().lower()
            aad_err_obj = getattr(aad_err, "error", None)
            aad_err_code = str(getattr(aad_err_obj, "code", "") or "").strip().lower()
            if "not found" not in aad_err_text and aad_err_code not in {"notfound", "resourcenotfound"}:
                logger.warning(
                    "sql-mi-details Entra admin lookup failed for %s/%s: %s",
                    resource_group,
                    managed_instance_name,
                    aad_err,
                )
        except Exception as aad_err:
            logger.warning("sql-mi-details Entra admin lookup error: %s", aad_err)

        if not entra_admin_login:
            administrators_obj = _prop("administrators", default=None)
            if isinstance(administrators_obj, dict):
                entra_admin_login = (
                    administrators_obj.get("login")
                    or administrators_obj.get("administratorLogin")
                )
            elif administrators_obj is not None:
                entra_admin_login = (
                    getattr(administrators_obj, "login", None)
                    or getattr(administrators_obj, "administrator_login", None)
                )

        databases: List[str] = []
        try:
            token = creds.get_token("https://management.azure.com/.default").token
            db_url = (
                f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
                f"/providers/Microsoft.Sql/managedInstances/{managed_instance_name}/databases"
                f"?api-version={AZURE_SQL_MI_LIST_API_VERSION}"
            )
            db_resp = requests.get(db_url, headers={"Authorization": "Bearer " + token}, timeout=30)
            if db_resp.status_code == 200:
                db_json = db_resp.json() if db_resp.content else {}
                for item in (db_json.get("value") or []):
                    db_name = (item or {}).get("name")
                    if db_name:
                        databases.append(str(db_name))
            else:
                logger.warning(
                    "sql-mi-details databases list failed for %s/%s: %s",
                    resource_group,
                    managed_instance_name,
                    db_resp.status_code,
                )
        except Exception as db_err:
            logger.warning("sql-mi-details databases list error: %s", db_err)

        return {
            "name": getattr(details, "name", managed_instance_name) or managed_instance_name,
            "managed_instance_name": getattr(details, "name", managed_instance_name) or managed_instance_name,
            "state": _prop("state", "provisioningState", "") or "",
            "host": _prop("fullyQualifiedDomainName", "fully_qualified_domain_name", "") or "",
            "location": getattr(details, "location", "") or "",
            "resource_group": resource_group,
            "subscription_id": subscription_id,
            "vnet": vnet_name,
            "subnet": subnet_name,
            "virtual_cluster": virtual_cluster,
            "existing_databases": sorted(databases, key=lambda x: x.lower()),
            "pricing_tier": pricing_tier,
            "instance_pool": instance_pool,
            "admin_username": admin_username,
            "entra_admin_login": entra_admin_login,
            "tags": {k: v for k, v in tags_obj.items()},
        }
    except HttpResponseError as e:
        logger.exception("get_azure_sql_managed_instance_details failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Azure Error: {str(e)}")


@app.post("/api/azure/sql-mi/tags")
async def update_azure_sql_mi_tags(request: Request):
    """Add or update tags on an Azure SQL Managed Instance."""
    body = await request.json()
    subscription_id = body.get("subscription_id")
    resource_group = body.get("resource_group")
    managed_instance_name = body.get("managed_instance_name")
    tags: Dict[str, str] = body.get("tags", {})

    if not subscription_id or not resource_group or not managed_instance_name:
        raise HTTPException(status_code=400, detail="subscription_id, resource_group, and managed_instance_name are required")
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        creds = get_azure_credentials()
        resource_client = ResourceManagementClient(creds, subscription_id)
        resource_id = (
            f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
            f"/providers/Microsoft.Sql/managedInstances/{managed_instance_name}"
        )
        mi = resource_client.resources.get_by_id(resource_id, api_version=AZURE_SQL_MI_LIST_API_VERSION)
        existing_tags = dict(getattr(mi, "tags", None) or {})
        existing_tags.update(tags or {})
        poller = resource_client.resources.begin_update(
            resource_group_name=resource_group,
            resource_provider_namespace="Microsoft.Sql",
            parent_resource_path="",
            resource_type="managedInstances",
            resource_name=managed_instance_name,
            api_version=AZURE_SQL_MI_LIST_API_VERSION,
            parameters={"tags": existing_tags},
        )
        poller.result()
        return {"ok": True, "message": f"Tags updated on SQL Managed Instance {managed_instance_name}"}
    except HttpResponseError as e:
        logger.exception("update_azure_sql_mi_tags failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Azure Error: {str(e)}")


@app.post("/api/azure/sql-mi/power")
async def power_azure_sql_mi(
    request: Request,
    subscription_id: str = Query(...),
    resource_group: str = Query(...),
    managed_instance_name: str = Query(...),
    action: str = Query(..., description="'start' or 'stop'"),
):
    """Start or stop an Azure SQL Managed Instance.

    SQL MI start/stop are action-type endpoints only available in the
    2023-05-01-preview API version (no stable GA equivalent exists yet).
    """
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    action = action.lower()
    if action not in ("start", "stop"):
        raise HTTPException(status_code=400, detail="action must be 'start' or 'stop'")
    # SQL MI start/stop use a POST-action pattern. We invoke them via a direct
    # ARM REST call because azure-mgmt-sql is not a declared dependency.
    # preview API is required – no stable version supports start/stop yet.
    _SQL_MI_POWER_API = "2023-05-01-preview"
    url = (
        f"https://management.azure.com/subscriptions/{subscription_id}"
        f"/resourceGroups/{resource_group}/providers/Microsoft.Sql"
        f"/managedInstances/{managed_instance_name}/{action}"
        f"?api-version={_SQL_MI_POWER_API}"
    )
    try:
        creds = get_azure_credentials()
        token = creds.get_token("https://management.azure.com/.default").token
        resp = requests.post(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        if resp.status_code not in (200, 202):
            raise HTTPException(status_code=resp.status_code, detail=resp.text or f"SQL MI {action} failed")
        msg = f"SQL Managed Instance {managed_instance_name} {action} initiated"
        _audit(request, f"sql_mi_{action}", "azure", resource_name=managed_instance_name, account_or_subscription=subscription_id)
        return {"ok": True, "message": msg}
    except HTTPException:
        raise
    except Exception as e:
        err_text = str(e)
        logger.exception("power_azure_sql_mi failed: %s", e)
        _audit(request, f"sql_mi_{action}", "azure", resource_name=managed_instance_name, account_or_subscription=subscription_id, status="failed", error_message=err_text)
        raise HTTPException(status_code=500, detail=f"Azure SQL MI {action} failed: {err_text}")


@app.post("/api/azure/sql-mi/new-database")
async def create_azure_sql_mi_database(
    request: Request,
):
    """Create a new database inside an Azure SQL Managed Instance."""
    data = await request.json()
    subscription_id = data.get("subscription_id", "")
    resource_group = data.get("resource_group", "")
    managed_instance_name = data.get("managed_instance_name", "")
    database_name = (data.get("database_name") or "").strip()
    if not all([subscription_id, resource_group, managed_instance_name, database_name]):
        raise HTTPException(status_code=400, detail="subscription_id, resource_group, managed_instance_name and database_name are required")
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        creds = get_azure_credentials()
        resource_client = ResourceManagementClient(creds, subscription_id)
        params: Dict[str, Any] = {
            "location": data.get("location", ""),
            "properties": {},
        }
        poller = resource_client.resources.begin_create_or_update(
            resource_group_name=resource_group,
            resource_provider_namespace="Microsoft.Sql",
            parent_resource_path=f"managedInstances/{managed_instance_name}",
            resource_type="databases",
            resource_name=database_name,
            api_version=AZURE_SQL_MI_LIST_API_VERSION,
            parameters=params,
        )
        poller.result()
        _audit(request, "sql_mi_new_database", "azure", resource_name=database_name, account_or_subscription=subscription_id)
        return {"ok": True, "message": f"Database {database_name} created in {managed_instance_name}"}
    except HttpResponseError as e:
        err_text = str(e)
        logger.exception("create_azure_sql_mi_database failed: %s", e)
        _audit(request, "sql_mi_new_database", "azure", resource_name=database_name, account_or_subscription=subscription_id, status="failed", error_message=err_text)
        raise HTTPException(status_code=500, detail=f"Azure SQL MI new database failed: {err_text}")


@app.post("/api/azure/sql-mi/reset-password")
async def reset_azure_sql_mi_password(
    request: Request,
):
    """Reset the SQL administrator password of an Azure SQL Managed Instance."""
    data = await request.json()
    subscription_id = data.get("subscription_id", "")
    resource_group = data.get("resource_group", "")
    managed_instance_name = data.get("managed_instance_name", "")
    new_password = data.get("new_password", "")
    if not all([subscription_id, resource_group, managed_instance_name, new_password]):
        raise HTTPException(status_code=400, detail="subscription_id, resource_group, managed_instance_name and new_password are required")
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        creds = get_azure_credentials()
        resource_client = ResourceManagementClient(creds, subscription_id)
        patch_params: Dict[str, Any] = {
            "properties": {
                "administratorLoginPassword": new_password,
            }
        }
        poller = resource_client.resources.begin_update(
            resource_group_name=resource_group,
            resource_provider_namespace="Microsoft.Sql",
            parent_resource_path="",
            resource_type="managedInstances",
            resource_name=managed_instance_name,
            api_version=AZURE_SQL_MI_LIST_API_VERSION,
            parameters=patch_params,
        )
        poller.result()
        _audit(request, "sql_mi_reset_password", "azure", resource_name=managed_instance_name, account_or_subscription=subscription_id)
        return {"ok": True, "message": f"Password reset for SQL Managed Instance {managed_instance_name}"}
    except HttpResponseError as e:
        err_text = str(e)
        logger.exception("reset_azure_sql_mi_password failed: %s", e)
        _audit(request, "sql_mi_reset_password", "azure", resource_name=managed_instance_name, account_or_subscription=subscription_id, status="failed", error_message=err_text)
        raise HTTPException(status_code=500, detail=f"Azure SQL MI password reset failed: {err_text}")


@app.delete("/api/azure/sql-mi")
def delete_azure_sql_managed_instance_resource(
    request: Request,
    subscription_id: str = Query(...),
    resource_group: str = Query(...),
    managed_instance_name: str = Query(...),
):
    """Delete an Azure SQL Managed Instance."""
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        creds = get_azure_credentials()
        resource_client = ResourceManagementClient(creds, subscription_id)
        poller = resource_client.resources.begin_delete(
            resource_group_name=resource_group,
            resource_provider_namespace="Microsoft.Sql",
            parent_resource_path="",
            resource_type="managedInstances",
            resource_name=managed_instance_name,
            api_version=AZURE_SQL_MI_LIST_API_VERSION,
        )
        poller.result()
        _audit(request, "delete_sql_mi", "azure", resource_name=managed_instance_name, account_or_subscription=subscription_id)
        return {
            "ok": True,
            "message": (
                f"SQL Managed Instance {managed_instance_name} deletion completed. "
                "Azure may keep showing it briefly, but it should disappear soon."
            ),
        }
    except HttpResponseError as e:
        err_text = str(e)
        raw_code = ""
        try:
            if getattr(e, "error", None) is not None:
                raw_code = str(getattr(e.error, "code", "") or "")
        except Exception as code_ex:
            logger.debug("delete_azure_sql_managed_instance_resource code extraction failed: %s", code_ex)
            raw_code = ""
        if not raw_code:
            raw_code = str(getattr(e, "error_code", "") or "")
        error_code_normalized = str(raw_code or "").strip().lower()
        normalized_error_message = str(err_text or "").strip().lower()
        not_found_or_already_deleted = (
            error_code_normalized in {"servernotinsubscription", "resourcenotfound", "resourcegroupnotfound", "notfound"}
            or ("managed instance" in normalized_error_message and "not found" in normalized_error_message)
            or ("server" in normalized_error_message and "not have the server" in normalized_error_message)
            or "already being deleted" in normalized_error_message
            or "deletion is in progress" in normalized_error_message
        )
        if not_found_or_already_deleted:
            _audit(
                request,
                "delete_sql_mi",
                "azure",
                resource_name=managed_instance_name,
                account_or_subscription=subscription_id,
                status="success",
                error_message=None,
            )
            return {
                "ok": True,
                "message": (
                    f"SQL Managed Instance {managed_instance_name} is already deleted or deletion is in progress. "
                    "Azure may keep showing it for a while, but it should disappear soon."
                ),
            }
        logger.exception("delete_azure_sql_managed_instance_resource failed: %s", e)
        _audit(request, "delete_sql_mi", "azure", resource_name=managed_instance_name, account_or_subscription=subscription_id, status="failed", error_message=err_text)
        raise HTTPException(status_code=500, detail=f"Azure SQL MI delete failed: {err_text}")


@app.get("/api/azure/vm-details")
def get_azure_vm_details(
    request: Request,
    subscription_id: str = Query(...),
    resource_group: str = Query(...),
    vm_name: str = Query(...)
):
    """Get details of a specific Azure VM."""
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        creds = get_azure_credentials()
        compute_client = ComputeManagementClient(creds, subscription_id)
        network_client = NetworkManagementClient(creds, subscription_id)
        vm = compute_client.virtual_machines.get(resource_group, vm_name, expand="instanceView")
        tags = vm.tags or {}
        state = "unknown"
        statuses = getattr(getattr(vm, "instance_view", None), "statuses", []) or []
        for s in statuses:
            code = getattr(s, "code", "") or ""
            if code.startswith("PowerState/"):
                state = code.split("/")[1]
                break

        hardware_profile = getattr(vm, "hardware_profile", None)
        vm_size = getattr(hardware_profile, "vm_size", "") or ""
        storage_profile = getattr(vm, "storage_profile", None)
        os_disk = getattr(storage_profile, "os_disk", None) if storage_profile else None
        os_type = str(getattr(os_disk, "os_type", "") or "")
        os_disk_size = getattr(os_disk, "disk_size_gb", None)
        os_disk_name = getattr(os_disk, "name", "") or ""
        os_disk_caching = str(getattr(os_disk, "caching", "") or "")
        managed_disk = getattr(os_disk, "managed_disk", None) if os_disk else None
        os_disk_type = ""
        if managed_disk:
            sku = getattr(managed_disk, "storage_account_type", None)
            os_disk_type = str(sku) if sku else ""

        # OS image reference
        img_ref = getattr(storage_profile, "image_reference", None) if storage_profile else None
        os_image = ""
        if img_ref:
            parts = [
                getattr(img_ref, "publisher", "") or "",
                getattr(img_ref, "offer", "") or "",
                getattr(img_ref, "sku", "") or "",
                getattr(img_ref, "version", "") or getattr(img_ref, "exact_version", "") or "",
            ]
            os_image = " / ".join(p for p in parts if p)

        # Data disks
        data_disks_info = []
        for dd in (getattr(storage_profile, "data_disks", []) or []):
            dd_managed = getattr(dd, "managed_disk", None)
            dd_sku = ""
            if dd_managed:
                dd_sku = str(getattr(dd_managed, "storage_account_type", "") or "")
            data_disks_info.append({
                "name": getattr(dd, "name", "") or "",
                "size_gb": getattr(dd, "disk_size_gb", None),
                "caching": str(getattr(dd, "caching", "") or ""),
                "lun": getattr(dd, "lun", None),
                "storage_type": dd_sku,
            })

        # OS profile info
        os_profile = getattr(vm, "os_profile", None)
        computer_name = getattr(os_profile, "computer_name", "") or "" if os_profile else ""
        admin_username = getattr(os_profile, "admin_username", "") or "" if os_profile else ""

        # Availability set / proximity placement group
        avail_set = getattr(vm, "availability_set", None)
        availability_set_name = ""
        if avail_set:
            av_id = getattr(avail_set, "id", "") or ""
            availability_set_name = av_id.split("/")[-1] if av_id else ""

        # License type
        license_type = getattr(vm, "license_type", "") or ""

        # Provisioning state
        provisioning_state = getattr(vm, "provisioning_state", "") or ""

        network_profile = getattr(vm, "network_profile", None)
        nics = getattr(network_profile, "network_interfaces", []) or []
        private_ips = []
        public_ips = []
        nic_names = []
        vnet_names = []
        subnet_names = []
        for nic_ref in nics:
            nic_id = getattr(nic_ref, "id", "") or ""
            if "/networkInterfaces/" in nic_id:
                nic_rg = nic_id.split("/resourceGroups/")[1].split("/")[0]
                nic_name = nic_id.split("/networkInterfaces/")[1].split("/")[0]
                nic_names.append(nic_name)
                try:
                    nic = network_client.network_interfaces.get(nic_rg, nic_name)
                    for ip_config in (getattr(nic, "ip_configurations", []) or []):
                        pip = getattr(ip_config, "private_ip_address", None)
                        if pip:
                            private_ips.append(pip)
                        pub_ref = getattr(ip_config, "public_ip_address", None)
                        if pub_ref:
                            pub_id = getattr(pub_ref, "id", "") or ""
                            if "/publicIPAddresses/" in pub_id:
                                pip_rg = pub_id.split("/resourceGroups/")[1].split("/")[0]
                                pip_name = pub_id.split("/publicIPAddresses/")[1].split("/")[0]
                                try:
                                    pub_ip_obj = network_client.public_ip_addresses.get(pip_rg, pip_name)
                                    addr = getattr(pub_ip_obj, "ip_address", None)
                                    if addr:
                                        public_ips.append(addr)
                                except Exception:
                                    pass
                        # Extract VNet and Subnet from the subnet reference on the ip_config
                        subnet_ref = getattr(ip_config, "subnet", None)
                        if subnet_ref:
                            subnet_id_str = getattr(subnet_ref, "id", "") or ""
                            if "/virtualNetworks/" in subnet_id_str and "/subnets/" in subnet_id_str:
                                vnet_name = subnet_id_str.split("/virtualNetworks/")[1].split("/")[0]
                                subnet_name = subnet_id_str.split("/subnets/")[1].split("/")[0]
                                if vnet_name and vnet_name not in vnet_names:
                                    vnet_names.append(vnet_name)
                                if subnet_name and subnet_name not in subnet_names:
                                    subnet_names.append(subnet_name)
                except Exception:
                    pass

        return {
            "vm_id": vm.id,
            "name": vm.name,
            "state": state,
            "provisioning_state": provisioning_state,
            "vm_size": vm_size,
            "location": getattr(vm, "location", ""),
            "resource_group": resource_group,
            "subscription_id": subscription_id,
            "computer_name": computer_name,
            "admin_username": admin_username,
            "os_type": os_type,
            "os_image": os_image,
            "os_disk_name": os_disk_name,
            "os_disk_size_gb": os_disk_size,
            "os_disk_caching": os_disk_caching,
            "os_disk_type": os_disk_type,
            "data_disks": data_disks_info,
            "private_ips": private_ips,
            "public_ips": public_ips,
            "nic_names": nic_names,
            "vnet_names": vnet_names,
            "subnet_names": subnet_names,
            "zones": getattr(vm, "zones", []) or [],
            "availability_set": availability_set_name,
            "license_type": license_type,
            "tags": {k: v for k, v in tags.items()},
        }
    except HttpResponseError as e:
        logger.exception("get_azure_vm_details failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Azure Error: {str(e)}")


@app.post("/api/azure/vm/tags")
async def update_azure_vm_tags(request: Request):
    """Add or update tags on an Azure VM."""
    body = await request.json()
    subscription_id = body.get("subscription_id")
    resource_group = body.get("resource_group")
    vm_name = body.get("vm_name")
    tags: Dict[str, str] = body.get("tags", {})

    if not subscription_id or not resource_group or not vm_name:
        raise HTTPException(status_code=400, detail="subscription_id, resource_group, and vm_name are required")
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        creds = get_azure_credentials()
        compute_client = ComputeManagementClient(creds, subscription_id)
        vm = compute_client.virtual_machines.get(resource_group, vm_name)
        existing_tags = dict(vm.tags or {})
        existing_tags.update(tags)
        poller = compute_client.virtual_machines.begin_update(
            resource_group, vm_name, {"tags": existing_tags}
        )
        poller.result()
        return {"ok": True, "message": f"Tags updated on {vm_name}"}
    except HttpResponseError as e:
        logger.exception("update_azure_vm_tags failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Azure Error: {str(e)}")


@app.delete("/api/azure/vm")
async def delete_azure_vm(
    request: Request,
    subscription_id: str = Query(...),
    resource_group: str = Query(...),
    vm_name: str = Query(...),
    delete_disks: Optional[str] = Query(None, description="Comma-separated disk names to delete"),
    delete_nics: Optional[str] = Query(None, description="Comma-separated NIC names to delete"),
    delete_public_ips: Optional[str] = Query(None, description="Comma-separated public IP resource names to delete"),
):
    """Delete an Azure VM and optionally its associated disks, NICs, and public IPs."""
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        creds = get_azure_credentials()
        compute_client = ComputeManagementClient(creds, subscription_id)
        network_client = NetworkManagementClient(creds, subscription_id)

        # Delete the VM first
        poller = compute_client.virtual_machines.begin_delete(resource_group, vm_name)
        poller.result()

        deleted_resources = []
        errors = []

        # Delete requested NICs (must happen before public IPs since NICs hold the PIP reference)
        if delete_nics:
            for nic_name in [n.strip() for n in delete_nics.split(",") if n.strip()]:
                try:
                    network_client.network_interfaces.begin_delete(resource_group, nic_name).result()
                    deleted_resources.append(f"NIC:{nic_name}")
                except Exception as exc:
                    errors.append(f"NIC {nic_name}: {exc}")

        # Delete requested public IPs
        if delete_public_ips:
            for pip_name in [p.strip() for p in delete_public_ips.split(",") if p.strip()]:
                try:
                    network_client.public_ip_addresses.begin_delete(resource_group, pip_name).result()
                    deleted_resources.append(f"PublicIP:{pip_name}")
                except Exception as exc:
                    errors.append(f"PublicIP {pip_name}: {exc}")

        # Delete requested managed disks
        if delete_disks:
            for disk_name in [d.strip() for d in delete_disks.split(",") if d.strip()]:
                try:
                    compute_client.disks.begin_delete(resource_group, disk_name).result()
                    deleted_resources.append(f"Disk:{disk_name}")
                except Exception as exc:
                    errors.append(f"Disk {disk_name}: {exc}")

        msg = f"VM {vm_name} deleted"
        if deleted_resources:
            msg += f"; also deleted: {', '.join(deleted_resources)}"
        if errors:
            msg += f"; errors cleaning up: {'; '.join(errors)}"
        _audit(
            request, "delete_vm", "azure",
            resource_name=vm_name,
            account_or_subscription=subscription_id,
            detail=f"resource_group={resource_group}; {msg}",
        )
        return {"ok": True, "message": msg}
    except HttpResponseError as e:
        logger.exception("delete_azure_vm failed: %s", e)
        _audit(
            request, "delete_vm", "azure",
            resource_name=vm_name,
            account_or_subscription=subscription_id,
            detail=f"resource_group={resource_group}",
            status="failed", error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Azure Error: {str(e)}")


@app.post("/api/azure/vm/restart")
async def restart_azure_vm(
    request: Request,
    subscription_id: str = Query(...),
    resource_group: str = Query(...),
    vm_name: str = Query(...)
):
    """Restart an Azure VM."""
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        creds = get_azure_credentials()
        compute_client = ComputeManagementClient(creds, subscription_id)
        poller = compute_client.virtual_machines.begin_restart(resource_group, vm_name)
        poller.result()
        return {"ok": True, "message": f"VM {vm_name} restarted"}
    except HttpResponseError as e:
        logger.exception("restart_azure_vm failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Azure Error: {str(e)}")


@app.post("/api/azure/vm/power")
async def power_azure_vm(
    request: Request,
    subscription_id: str = Query(...),
    resource_group: str = Query(...),
    vm_name: str = Query(...),
    action: str = Query(..., description="'start' or 'stop'")
):
    """Start or stop (deallocate) an Azure VM."""
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    action = action.lower()
    if action not in ("start", "stop"):
        raise HTTPException(status_code=400, detail="action must be 'start' or 'stop'")
    try:
        creds = get_azure_credentials()
        compute_client = ComputeManagementClient(creds, subscription_id)
        if action == "start":
            poller = compute_client.virtual_machines.begin_start(resource_group, vm_name)
            msg = f"VM {vm_name} start initiated"
        else:
            poller = compute_client.virtual_machines.begin_deallocate(resource_group, vm_name)
            msg = f"VM {vm_name} stop (deallocate) initiated"
        poller.result()
        return {"ok": True, "message": msg}
    except HttpResponseError as e:
        logger.exception("power_azure_vm failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Azure Error: {str(e)}")


@app.post("/api/azure/vm/resize")
async def resize_azure_vm(
    request: Request,
    subscription_id: str = Query(...),
    resource_group: str = Query(...),
    vm_name: str = Query(...),
    new_size: str = Query(...)
):
    """Resize an Azure VM to a new hardware profile size."""
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        creds = get_azure_credentials()
        compute_client = ComputeManagementClient(creds, subscription_id)
        # Check current power state
        vm_instance = compute_client.virtual_machines.get(resource_group, vm_name, expand="instanceView")
        power_state = next(
            (s.code for s in (vm_instance.instance_view.statuses or []) if s.code.startswith("PowerState/")),
            "PowerState/unknown",
        )
        was_running = power_state == "PowerState/running"
        # Deallocate first (required for most resize operations)
        if was_running:
            poller = compute_client.virtual_machines.begin_deallocate(resource_group, vm_name)
            poller.result()
        # Re-fetch after deallocate so the model is up to date
        vm = compute_client.virtual_machines.get(resource_group, vm_name)
        vm.hardware_profile.vm_size = new_size
        poller = compute_client.virtual_machines.begin_create_or_update(resource_group, vm_name, vm)
        poller.result()
        if was_running:
            poller = compute_client.virtual_machines.begin_start(resource_group, vm_name)
            poller.result()
            return {"ok": True, "message": f"VM {vm_name} resized to {new_size} and restarted"}
        return {"ok": True, "message": f"VM {vm_name} resized to {new_size} (was already stopped)"}
    except HttpResponseError as e:
        logger.exception("resize_azure_vm failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Azure Error: {str(e)}")


@app.post("/api/azure/vm/attach-disk")
async def attach_disk_azure(
    request: Request,
    subscription_id: str = Query(...),
    resource_group: str = Query(...),
    vm_name: str = Query(...),
    body: AttachDiskRequest = Body(...)
):
    """Create a new managed disk and attach it to an Azure VM."""
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        from azure.mgmt.compute.models import DiskCreateOption, ManagedDiskParameters, DataDisk
        creds = get_azure_credentials()
        compute_client = ComputeManagementClient(creds, subscription_id)
        vm = compute_client.virtual_machines.get(resource_group, vm_name)
        location = vm.location
        # Create the managed disk
        disk_params = Disk(
            location=location,
            sku=DiskSku(name=body.disk_type),
            creation_data=CreationData(create_option="Empty"),
            disk_size_gb=body.size_gb,
        )
        poller = compute_client.disks.begin_create_or_update(resource_group, body.disk_name, disk_params)
        disk = poller.result()
        # Attach to VM
        lun = max((d.lun for d in (vm.storage_profile.data_disks or [])), default=-1) + 1
        vm.storage_profile.data_disks.append(
            DataDisk(
                lun=lun,
                name=body.disk_name,
                create_option=DiskCreateOption.ATTACH,
                managed_disk=ManagedDiskParameters(id=disk.id),
            )
        )
        attach_poller = compute_client.virtual_machines.begin_create_or_update(resource_group, vm_name, vm)
        attach_poller.result()
        return {"ok": True, "message": f"Disk {body.disk_name} ({body.size_gb} GB) attached to {vm_name} as LUN {lun}"}
    except HttpResponseError as e:
        logger.exception("attach_disk_azure failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Azure Error: {str(e)}")


@app.post("/api/azure/disk/resize")
async def resize_azure_disk(
    request: Request,
    subscription_id: str = Query(...),
    resource_group: str = Query(...),
    disk_name: str = Query(...),
    body: ResizeDiskRequest = Body(...)
):
    """Resize an Azure managed disk (increase only). VM must be deallocated for OS disk resize."""
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        creds = get_azure_credentials()
        compute_client = ComputeManagementClient(creds, subscription_id)
        disk = compute_client.disks.get(resource_group, disk_name)
        if disk.disk_size_gb and body.new_size_gb <= disk.disk_size_gb:
            raise HTTPException(status_code=400, detail=f"New size ({body.new_size_gb} GB) must be larger than current size ({disk.disk_size_gb} GB).")
        update_params = DiskUpdate(disk_size_gb=body.new_size_gb)
        poller = compute_client.disks.begin_update(resource_group, disk_name, update_params)
        poller.result()
        return {"ok": True, "message": f"Disk {disk_name} resized to {body.new_size_gb} GB. Extend the file system inside the OS if needed."}
    except HttpResponseError as e:
        logger.exception("resize_azure_disk failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Azure Error: {str(e)}")


@app.delete("/api/azure/vm/disk")
async def delete_azure_disk(
    request: Request,
    subscription_id: str = Query(...),
    resource_group: str = Query(...),
    vm_name: str = Query(...),
    disk_name: str = Query(...)
):
    """Detach a data disk from an Azure VM and delete the managed disk resource."""
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        creds = get_azure_credentials()
        compute_client = ComputeManagementClient(creds, subscription_id)
        vm = compute_client.virtual_machines.get(resource_group, vm_name)
        original_count = len(vm.storage_profile.data_disks or [])
        vm.storage_profile.data_disks = [
            d for d in (vm.storage_profile.data_disks or []) if d.name != disk_name
        ]
        if len(vm.storage_profile.data_disks) == original_count:
            raise HTTPException(status_code=404, detail=f"Data disk '{disk_name}' not found on VM '{vm_name}'. Cannot delete OS disk.")
        poller = compute_client.virtual_machines.begin_create_or_update(resource_group, vm_name, vm)
        poller.result()
        # Delete the managed disk resource
        del_poller = compute_client.disks.begin_delete(resource_group, disk_name)
        del_poller.result()
        _audit(
            request, "delete_disk", "azure",
            resource_name=disk_name,
            account_or_subscription=subscription_id,
            detail=f"resource_group={resource_group}; detached and deleted disk {disk_name} from VM {vm_name}",
        )
        return {"ok": True, "message": f"Disk {disk_name} detached and deleted successfully."}
    except HttpResponseError as e:
        logger.exception("delete_azure_disk failed: %s", e)
        _audit(
            request, "delete_disk", "azure",
            resource_name=disk_name,
            account_or_subscription=subscription_id,
            detail=f"resource_group={resource_group}",
            status="failed", error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Azure Error: {str(e)}")


@app.post("/api/azure/vm/snapshot")
async def snapshot_azure_vm(
    request: Request,
    subscription_id: str = Query(...),
    resource_group: str = Query(...),
    vm_name: str = Query(...),
    body: SnapshotRequest = Body(...)
):
    """Create a snapshot of the Azure VM's OS disk."""
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        creds = get_azure_credentials()
        compute_client = ComputeManagementClient(creds, subscription_id)
        vm = compute_client.virtual_machines.get(resource_group, vm_name)
        os_disk_id = vm.storage_profile.os_disk.managed_disk.id
        snapshot_params = Snapshot(
            location=vm.location,
            creation_data=CreationData(
                create_option="Copy",
                source_resource_id=os_disk_id,
            ),
        )
        poller = compute_client.snapshots.begin_create_or_update(resource_group, body.snapshot_name, snapshot_params)
        snap = poller.result()
        _audit(
            request, "snapshot_vm", "azure",
            resource_name=snap.name,
            account_or_subscription=subscription_id, region_or_zone=getattr(vm, "location", None),
            detail=f"resource_group={resource_group}; snapshot of OS disk of VM {vm_name}",
        )
        return {"ok": True, "message": f"Snapshot {snap.name} created from OS disk of {vm_name}"}
    except HttpResponseError as e:
        logger.exception("snapshot_azure_vm failed: %s", e)
        _audit(
            request, "snapshot_vm", "azure",
            resource_name=body.snapshot_name,
            account_or_subscription=subscription_id,
            detail=f"resource_group={resource_group}",
            status="failed", error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Azure Error: {str(e)}")


@app.get("/api/azure/vm/snapshots")
async def list_azure_snapshots(
    request: Request,
    subscription_id: str = Query(...),
    resource_group: str = Query(...),
):
    """List all snapshots in an Azure resource group."""
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        creds = get_azure_credentials()
        compute_client = ComputeManagementClient(creds, subscription_id)
        snapshots = list(compute_client.snapshots.list_by_resource_group(resource_group))
        result = []
        for s in snapshots:
            result.append({
                "name": s.name,
                "disk_size_gb": s.disk_size_gb,
                "time_created": s.time_created.isoformat() if s.time_created else None,
                "location": s.location,
                "provisioning_state": s.provisioning_state,
            })
        result.sort(key=lambda x: x.get("time_created") or "", reverse=True)
        return {"snapshots": result}
    except HttpResponseError as e:
        logger.exception("list_azure_snapshots failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Azure Error: {str(e)}")


@app.delete("/api/azure/vm/snapshot")
async def delete_azure_snapshot(
    request: Request,
    subscription_id: str = Query(...),
    resource_group: str = Query(...),
    snapshot_name: str = Query(...),
):
    """Delete an Azure snapshot by name."""
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    try:
        creds = get_azure_credentials()
        compute_client = ComputeManagementClient(creds, subscription_id)
        poller = compute_client.snapshots.begin_delete(resource_group, snapshot_name)
        poller.result()
        _audit(
            request, "delete_snapshot", "azure",
            resource_name=snapshot_name,
            account_or_subscription=subscription_id,
            detail=f"resource_group={resource_group}",
        )
        return {"ok": True, "message": f"Snapshot {snapshot_name} deleted"}
    except HttpResponseError as e:
        logger.exception("delete_azure_snapshot failed: %s", e)
        _audit(
            request, "delete_snapshot", "azure",
            resource_name=snapshot_name,
            account_or_subscription=subscription_id,
            detail=f"resource_group={resource_group}",
            status="failed", error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Azure Error: {str(e)}")


# ── Clone VM endpoints ───────────────────────────────────────────────────────

@app.post("/api/aws/instance/{instance_id}/clone")
async def clone_aws_instance(
    request: Request,
    instance_id: str,
    account: str = Query(...),
    region: str = Query(...)
):
    """Clone an existing EC2 instance — root volume and all additional EBS volumes are copied."""
    if not is_account_allowed(request, account):
        raise HTTPException(status_code=403, detail="Not allowed to access this AWS account")
    body = await request.json()
    new_name = (body.get("new_name") or "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="new_name is required")
    try:
        session = assume_role(account)
        ec2 = session.client("ec2", region_name=region)
        # Fetch source instance details
        resp = ec2.describe_instances(InstanceIds=[instance_id])
        reservations = resp.get("Reservations", [])
        if not reservations or not reservations[0].get("Instances"):
            raise HTTPException(status_code=404, detail="Source instance not found")
        src = reservations[0]["Instances"][0]
        ami_id = src.get("ImageId", "")
        instance_type = src.get("InstanceType", "")
        subnet_id = src.get("SubnetId", "")
        sg_ids = [sg["GroupId"] for sg in src.get("SecurityGroups", [])]
        key_name = src.get("KeyName") or None
        src_tags = {t["Key"]: t["Value"] for t in src.get("Tags", [])}
        root_device_name = src.get("RootDeviceName", "")
        availability_zone = (src.get("Placement") or {}).get("AvailabilityZone", "")

        # Identify root and additional (non-root) EBS volumes
        root_volume_id = None
        extra_volumes = []
        for bdm in src.get("BlockDeviceMappings", []):
            device_name = bdm.get("DeviceName", "")
            ebs = bdm.get("Ebs") or {}
            vol_id = ebs.get("VolumeId")
            if not device_name or not vol_id:
                continue
            if device_name == root_device_name:
                root_volume_id = vol_id
            else:
                extra_volumes.append({"vol_id": vol_id, "device_name": device_name})

        root_volume_info: Dict[str, Any] = {
            "size": None,
            "type": None,
            "iops": None,
            "throughput": None,
            "delete_on_termination": True,
        }
        root_snapshot_id = None
        if root_volume_id:
            root_vol_resp = ec2.describe_volumes(VolumeIds=[root_volume_id])
            root_volumes = root_vol_resp.get("Volumes", [])
            if root_volumes:
                root_vol = root_volumes[0]
                root_volume_info = {
                    "size": root_vol.get("Size"),
                    "type": root_vol.get("VolumeType", "gp2"),
                    "iops": root_vol.get("Iops"),
                    "throughput": root_vol.get("Throughput"),
                    "delete_on_termination": True,
                }
                for bdm in src.get("BlockDeviceMappings", []):
                    if bdm.get("DeviceName") == root_device_name:
                        root_volume_info["delete_on_termination"] = (bdm.get("Ebs") or {}).get("DeleteOnTermination", True)
                        break
                root_snap_resp = ec2.create_snapshot(
                    VolumeId=root_volume_id,
                    Description=f"Clone root snapshot of {instance_id} for {new_name}",
                )
                root_snapshot_id = root_snap_resp["SnapshotId"]
                ec2.get_waiter("snapshot_completed").wait(SnapshotIds=[root_snapshot_id])

        # Gather volume details and start snapshots in parallel before launching the instance
        snapshot_map: Dict[str, str] = {}   # device_name → snapshot_id
        vol_detail_map: Dict[str, dict] = {}  # vol_id → details
        if extra_volumes:
            vol_ids = [ev["vol_id"] for ev in extra_volumes]
            vols_resp = ec2.describe_volumes(VolumeIds=vol_ids)
            for vol in vols_resp.get("Volumes", []):
                vol_detail_map[vol["VolumeId"]] = {
                    "size": vol.get("Size"),
                    "type": vol.get("VolumeType", "gp2"),
                    "iops": vol.get("Iops"),
                    "throughput": vol.get("Throughput"),
                    "encrypted": vol.get("Encrypted", False),
                    "kms_key_id": vol.get("KmsKeyId") or None,
                }
            for ev in extra_volumes:
                snap_resp = ec2.create_snapshot(
                    VolumeId=ev["vol_id"],
                    Description=f"Clone of {ev['vol_id']} for {new_name}",
                )
                snapshot_map[ev["device_name"]] = snap_resp["SnapshotId"]

        # Build tags for new instance
        new_tags = {k: v for k, v in src_tags.items() if k != "Name"}
        new_tags["Name"] = new_name
        tag_specs = [{"ResourceType": "instance", "Tags": [{"Key": k, "Value": v} for k, v in new_tags.items()]}]
        run_kwargs: dict = {
            "ImageId": ami_id,
            "InstanceType": instance_type,
            "MinCount": 1,
            "MaxCount": 1,
            "TagSpecifications": tag_specs,
        }
        if root_snapshot_id and root_device_name:
            root_ebs: Dict[str, Any] = {
                "SnapshotId": root_snapshot_id,
                "DeleteOnTermination": bool(root_volume_info.get("delete_on_termination", True)),
            }
            if root_volume_info.get("size"):
                root_ebs["VolumeSize"] = root_volume_info["size"]
            if root_volume_info.get("type"):
                root_ebs["VolumeType"] = root_volume_info["type"]
            if root_volume_info.get("iops") and root_volume_info.get("type") in ("io1", "io2", "gp3"):
                root_ebs["Iops"] = root_volume_info["iops"]
            if root_volume_info.get("throughput") and root_volume_info.get("type") == "gp3":
                root_ebs["Throughput"] = root_volume_info["throughput"]
            run_kwargs["BlockDeviceMappings"] = [{"DeviceName": root_device_name, "Ebs": root_ebs}]
        if subnet_id:
            run_kwargs["SubnetId"] = subnet_id
        if sg_ids:
            run_kwargs["SecurityGroupIds"] = sg_ids
        if key_name:
            run_kwargs["KeyName"] = key_name
        new_resp = ec2.run_instances(**run_kwargs)
        new_inst = new_resp["Instances"][0]
        new_instance_id = new_inst["InstanceId"]

        if extra_volumes and snapshot_map:
            # Wait for the new instance to enter the running state
            ec2.get_waiter("instance_running").wait(InstanceIds=[new_instance_id])
            # Wait for all snapshots to complete
            ec2.get_waiter("snapshot_completed").wait(SnapshotIds=list(snapshot_map.values()))
            # Create new volumes from snapshots and attach them
            for ev in extra_volumes:
                device_name = ev["device_name"]
                snap_id = snapshot_map.get(device_name)
                if not snap_id:
                    continue
                vol_info = vol_detail_map.get(ev["vol_id"], {})
                create_vol_kwargs: dict = {
                    "SnapshotId": snap_id,
                    "AvailabilityZone": availability_zone,
                    "VolumeType": vol_info.get("type", "gp2"),
                    "Encrypted": vol_info.get("encrypted", False),
                    "TagSpecifications": [
                        {"ResourceType": "volume", "Tags": [{"Key": "Name", "Value": f"{new_name}-{device_name.lstrip('/')}"}]}
                    ],
                }
                if vol_info.get("kms_key_id"):
                    create_vol_kwargs["KmsKeyId"] = vol_info["kms_key_id"]
                if vol_info.get("iops") and vol_info.get("type") in ("io1", "io2", "gp3"):
                    create_vol_kwargs["Iops"] = vol_info["iops"]
                if vol_info.get("throughput") and vol_info.get("type") == "gp3":
                    create_vol_kwargs["Throughput"] = vol_info["throughput"]
                new_vol = ec2.create_volume(**create_vol_kwargs)
                ec2.get_waiter("volume_available").wait(VolumeIds=[new_vol["VolumeId"]])
                ec2.attach_volume(
                    VolumeId=new_vol["VolumeId"],
                    InstanceId=new_instance_id,
                    Device=device_name,
                )

        extra_msg = f" with {len(extra_volumes)} additional volume(s)" if extra_volumes else ""
        _audit(
            request, "clone_vm", "aws",
            resource_name=new_name, resource_id=new_instance_id,
            account_or_subscription=account, region_or_zone=region,
            detail=f"Cloned from {instance_id}{extra_msg}",
        )
        return {
            "ok": True,
            "new_instance_id": new_instance_id,
            "message": f"Cloned instance {instance_id} → {new_instance_id} (name: {new_name}){extra_msg}",
        }
    except ClientError as e:
        logger.exception("clone_aws_instance failed: %s", e)
        _audit(
            request, "clone_vm", "aws",
            resource_name=new_name, resource_id=instance_id,
            account_or_subscription=account, region_or_zone=region,
            status="failed", error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=f"AWS Error: {str(e)}")


@app.post("/api/azure/vm/clone")
async def clone_azure_vm(
    request: Request,
    subscription_id: str = Query(...),
    resource_group: str = Query(...),
    vm_name: str = Query(...)
):
    """Clone an Azure VM by copying its managed OS/data disks and recreating NICs in the same RG."""
    if not is_subscription_allowed(request, subscription_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this Azure subscription")
    body = await request.json()
    new_name = (body.get("new_name") or "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="new_name is required")
    try:
        def _parse_resource_id(resource_id: str) -> Dict[str, str]:
            parts = [part for part in (resource_id or "").split("/") if part]
            return {
                parts[idx]: parts[idx + 1]
                for idx in range(len(parts) - 1)
                if parts[idx] in {"subscriptions", "resourceGroups", "providers", "networkInterfaces"}
            }

        def _copy_managed_disk(source_disk_id: str, disk_name: str, storage_account_type: Optional[str]) -> Any:
            disk_kwargs: Dict[str, Any] = {
                "location": location,
                "creation_data": CreationData(
                    create_option="Copy",
                    source_resource_id=source_disk_id,
                ),
            }
            if storage_account_type:
                disk_kwargs["sku"] = DiskSku(name=storage_account_type)
            disk_params = Disk(**disk_kwargs)
            if getattr(src_vm, "zones", None):
                disk_params.zones = list(src_vm.zones)
            return compute_client.disks.begin_create_or_update(resource_group, disk_name, disk_params).result()

        def _delete_resource_if_exists(delete_fn: Any, *args: Any) -> None:
            """Silently delete a resource; ignore 404 (not found) errors."""
            try:
                delete_fn(*args).result()
            except HttpResponseError as _del_err:
                if getattr(_del_err, "status_code", None) != 404:
                    logger.warning("clone_azure_vm pre-flight cleanup failed for %s: %s", args, _del_err)

        creds = get_azure_credentials()
        compute_client = ComputeManagementClient(creds, subscription_id)
        network_client = NetworkManagementClient(creds, subscription_id)

        # Pre-flight check: abort if the target VM already exists (a previous clone succeeded).
        try:
            compute_client.virtual_machines.get(resource_group, new_name)
            raise HTTPException(
                status_code=409,
                detail=(
                    f"A VM named '{new_name}' already exists in resource group '{resource_group}'. "
                    "Choose a different clone name or delete the existing VM first."
                ),
            )
        except HttpResponseError as _pre_check_err:
            if _pre_check_err.status_code != 404:
                raise  # real error — propagate
            # 404 means the target VM does not exist; proceed with clone

        src_vm = compute_client.virtual_machines.get(resource_group, vm_name)
        location = src_vm.location
        hw = getattr(src_vm, "hardware_profile", None)
        vm_size = getattr(hw, "vm_size", "Standard_B2s") if hw else "Standard_B2s"
        storage = getattr(src_vm, "storage_profile", None)
        os_disk = getattr(storage, "os_disk", None) if storage else None
        if not os_disk:
            raise HTTPException(status_code=400, detail="Source VM OS disk could not be determined")
        src_os_managed_disk = getattr(os_disk, "managed_disk", None)
        src_os_disk_id = getattr(src_os_managed_disk, "id", None) if src_os_managed_disk else None
        if not src_os_disk_id:
            raise HTTPException(status_code=400, detail="Source VM must use a managed OS disk to be cloned")
        raw_os_type = getattr(os_disk, "os_type", None)
        raw_os_type_value = getattr(raw_os_type, "value", raw_os_type)
        raw_os_type_name = getattr(raw_os_type, "name", None)
        os_type_lookup = {
            "WINDOWS": "Windows",
            "LINUX": "Linux",
            "OPERATINGSYSTEMTYPES.WINDOWS": "Windows",
            "OPERATINGSYSTEMTYPES.LINUX": "Linux",
        }
        os_type_text = str(raw_os_type_name or raw_os_type_value or "").strip().upper()
        os_type = os_type_lookup.get(os_type_text)
        if not os_type:
            logger.warning("clone_azure_vm encountered unsupported normalized source os_type '%s' (raw=%s)", os_type_text, raw_os_type)
            raise HTTPException(status_code=400, detail=f"Unsupported source VM os_type for clone: {os_type_text or raw_os_type}")

        # Clean up any leftover artifacts from a previous failed clone attempt so
        # that begin_create_or_update for disks / NICs doesn't fail with Conflict.
        # This is safe because the pre-flight check above confirmed the target VM
        # does not yet exist, so any resource with the clone name is an orphan.
        src_data_disks_for_cleanup = getattr(storage, "data_disks", []) or []
        for _d in src_data_disks_for_cleanup:
            _lun = getattr(_d, "lun", None)
            if _lun is not None:
                _delete_resource_if_exists(
                    compute_client.disks.begin_delete, resource_group, f"{new_name}-datadisk-{_lun}"
                )
        _delete_resource_if_exists(
            compute_client.disks.begin_delete, resource_group, f"{new_name}-osdisk"
        )
        src_nic_refs_for_cleanup = getattr(getattr(src_vm, "network_profile", None), "network_interfaces", []) or []
        for _ni, _ in enumerate(src_nic_refs_for_cleanup, start=1):
            _nic_cleanup_name = f"{new_name}-nic" if len(src_nic_refs_for_cleanup) == 1 else f"{new_name}-nic-{_ni}"
            _delete_resource_if_exists(
                network_client.network_interfaces.begin_delete, resource_group, _nic_cleanup_name
            )

        new_os_disk = _copy_managed_disk(
            src_os_disk_id,
            f"{new_name}-osdisk",
            getattr(src_os_managed_disk, "storage_account_type", None),
        )

        data_disk_models: List[DataDisk] = []
        used_luns: Set[int] = set()
        for idx, src_data_disk in enumerate(getattr(storage, "data_disks", []) or [], start=1):
            src_data_managed_disk = getattr(src_data_disk, "managed_disk", None)
            src_data_disk_id = getattr(src_data_managed_disk, "id", None) if src_data_managed_disk else None
            if not src_data_disk_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Attached data disk '{getattr(src_data_disk, 'name', idx)}' is not a managed disk",
                )
            cloned_data_disk = _copy_managed_disk(
                src_data_disk_id,
                f"{new_name}-datadisk-{getattr(src_data_disk, 'lun', idx)}",
                getattr(src_data_managed_disk, "storage_account_type", None),
            )
            lun = getattr(src_data_disk, "lun", None)
            if lun is None or lun in used_luns:
                lun = 0
                while lun in used_luns:
                    lun += 1
            used_luns.add(lun)
            data_disk_models.append(
                DataDisk(
                    lun=lun,
                    name=cloned_data_disk.name,
                    create_option="Attach",
                    caching=getattr(src_data_disk, "caching", None),
                    managed_disk=ManagedDiskParameters(id=cloned_data_disk.id),
                    delete_option=getattr(src_data_disk, "delete_option", None),
                    write_accelerator_enabled=getattr(src_data_disk, "write_accelerator_enabled", None),
                )
            )

        # Recreate NICs against the same subnets and preserve safe NIC-level settings.
        nics = getattr(src_vm, "network_profile", None)
        nic_refs = getattr(nics, "network_interfaces", []) if nics else []
        if not nic_refs:
            raise HTTPException(status_code=400, detail="Source VM has no network interfaces to clone")

        new_nic_refs: List[NetworkInterfaceReference] = []
        source_has_primary_nic = any(bool(getattr(nic_ref, "primary", False)) for nic_ref in nic_refs)
        for idx, nic_ref in enumerate(nic_refs, start=1):
            src_nic_id = getattr(nic_ref, "id", "")
            src_nic_ref_parts = _parse_resource_id(src_nic_id)
            src_nic_name = src_nic_ref_parts.get("networkInterfaces", "")
            src_nic_rg = src_nic_ref_parts.get("resourceGroups", resource_group)
            if not src_nic_name:
                raise HTTPException(status_code=400, detail="Could not determine a source NIC name")

            src_nic = network_client.network_interfaces.get(src_nic_rg, src_nic_name)
            ip_cfgs = getattr(src_nic, "ip_configurations", []) or []
            if not ip_cfgs:
                raise HTTPException(status_code=400, detail=f"Source NIC '{src_nic_name}' has no IP configuration")

            # Build ipConfigurations using a camelCase dict body so the REST request
            # is serialised correctly regardless of azure-mgmt-network SDK version.
            cloned_ip_cfgs_body: List[Dict[str, Any]] = []
            for cfg_idx, ip_cfg in enumerate(ip_cfgs, start=1):
                subnet = getattr(ip_cfg, "subnet", None)
                subnet_id = getattr(subnet, "id", None) if subnet else None
                if not subnet_id:
                    raise HTTPException(status_code=400, detail=f"Could not determine subnet for NIC '{src_nic_name}'")
                _raw_alloc = getattr(ip_cfg, "private_ip_allocation_method", None)
                # On Python 3.11+, str() on an Azure SDK str-enum returns "IPAllocationMethod.DYNAMIC"
                # rather than the plain value "Dynamic". Prefer .value when available; fall back to
                # direct use when the SDK already returns a plain string.
                if _raw_alloc is None:
                    allocation_method = "Dynamic"
                elif hasattr(_raw_alloc, "value"):
                    allocation_method = _raw_alloc.value or "Dynamic"
                else:
                    allocation_method = str(_raw_alloc) or "Dynamic"
                # Reusing a static private IP on the clone would immediately conflict with the source NIC,
                # so the clone keeps the subnet but falls back to a fresh dynamic address when needed.
                cfg_body: Dict[str, Any] = {
                    "name": getattr(ip_cfg, "name", None) or f"ipconfig{cfg_idx}",
                    "properties": {
                        "subnet": {"id": subnet_id},
                        "privateIPAllocationMethod": "Dynamic" if allocation_method.lower() == "static" else allocation_method,
                    },
                }
                if getattr(ip_cfg, "primary", None) is not None:
                    cfg_body["properties"]["primary"] = bool(ip_cfg.primary)
                cloned_ip_cfgs_body.append(cfg_body)

            new_nic_name = f"{new_name}-nic" if len(nic_refs) == 1 else f"{new_name}-nic-{idx}"
            nic_body: Dict[str, Any] = {
                "location": location,
                "properties": {
                    "ipConfigurations": cloned_ip_cfgs_body,
                },
            }
            if getattr(src_nic, "enable_accelerated_networking", None) is not None:
                nic_body["properties"]["enableAcceleratedNetworking"] = bool(src_nic.enable_accelerated_networking)
            if getattr(src_nic, "enable_ip_forwarding", None) is not None:
                nic_body["properties"]["enableIPForwarding"] = bool(src_nic.enable_ip_forwarding)
            src_nic_nsg = getattr(src_nic, "network_security_group", None)
            src_nic_nsg_id = getattr(src_nic_nsg, "id", None) if src_nic_nsg else None
            if src_nic_nsg_id:
                nic_body["properties"]["networkSecurityGroup"] = {"id": src_nic_nsg_id}
            if getattr(src_nic, "tags", None):
                nic_body["tags"] = dict(src_nic.tags)

            new_nic = network_client.network_interfaces.begin_create_or_update(
                resource_group,
                new_nic_name,
                nic_body,
            ).result()
            is_primary_nic = bool(getattr(nic_ref, "primary", False))
            if not is_primary_nic and idx == 1 and not source_has_primary_nic:
                is_primary_nic = True
            new_nic_refs.append(
                NetworkInterfaceReference(
                    id=new_nic.id,
                    # Some GET responses omit the primary flag on single-NIC VMs; default the first NIC to
                    # primary in that case so the clone still has a valid primary interface.
                    primary=is_primary_nic,
                )
            )

        def build_clone_vm_params(include_optional: bool) -> VirtualMachine:
            vm_params = VirtualMachine(
                location=location,
                hardware_profile=HardwareProfile(vm_size=vm_size),
                storage_profile=StorageProfile(
                    disk_controller_type=getattr(storage, "disk_controller_type", None),
                    os_disk=OSDisk(
                        name=new_os_disk.name,
                        os_type=os_type,
                        caching=getattr(os_disk, "caching", None),
                        create_option="Attach",
                        managed_disk=ManagedDiskParameters(id=new_os_disk.id),
                        delete_option=getattr(os_disk, "delete_option", None),
                    ),
                    data_disks=data_disk_models or None,
                ),
                network_profile=NetworkProfile(network_interfaces=new_nic_refs),
                tags=dict(src_vm.tags or {}),
            )
            if getattr(src_vm, "zones", None):
                vm_params.zones = list(src_vm.zones)
            if getattr(src_vm, "plan", None):
                vm_params.plan = src_vm.plan
            if getattr(src_vm, "availability_set", None):
                vm_params.availability_set = src_vm.availability_set
            if getattr(src_vm, "security_profile", None):
                vm_params.security_profile = src_vm.security_profile
            if include_optional:
                # Preserve only VM settings that are generally safe to carry to a same-RG clone.
                # Several optional profile-like fields are intentionally excluded because they are
                # source-environment-specific and may fail create_or_update validation on clone.
                # Placement/capacity/host bindings are intentionally excluded because they can be
                # environment-specific and fail clone creation when copied blindly.
                for vm_field in (
                    "identity",
                    "license_type",
                    "priority",
                    "eviction_policy",
                    "user_data",
                ):
                    vm_value = getattr(src_vm, vm_field, None)
                    if vm_value is not None:
                        setattr(vm_params, vm_field, vm_value)
            return vm_params

        vm_params = build_clone_vm_params(include_optional=True)
        try:
            poller = compute_client.virtual_machines.begin_create_or_update(resource_group, new_name, vm_params)
            result = poller.result()
        except HttpResponseError as create_vm_err:
            logger.warning(
                "clone_azure_vm optional VM settings (identity/license_type/priority/eviction_policy/user_data) "
                "failed for '%s'; retrying with minimal profile: %s",
                vm_name,
                create_vm_err,
            )
            fallback_vm_params = build_clone_vm_params(include_optional=False)
            poller = compute_client.virtual_machines.begin_create_or_update(resource_group, new_name, fallback_vm_params)
            result = poller.result()
        total_data_disks = len(data_disk_models)
        disk_suffix = f" and {total_data_disks} data disk(s)" if total_data_disks else ""
        _audit(
            request, "clone_vm", "azure",
            resource_name=new_name, resource_id=result.id,
            account_or_subscription=subscription_id, region_or_zone=location,
            detail=f"resource_group={resource_group}; cloned from VM '{vm_name}'{disk_suffix}",
        )
        return {
            "ok": True,
            "new_vm_id": result.id,
            "message": f"Cloned VM '{vm_name}' → '{new_name}' successfully with OS disk{disk_suffix}",
        }
    except HttpResponseError as e:
        logger.exception("clone_azure_vm failed: %s", e)
        _audit(
            request, "clone_vm", "azure",
            resource_name=new_name,
            account_or_subscription=subscription_id,
            detail=f"resource_group={resource_group}",
            status="failed", error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Azure Error: {str(e)}")
    except HTTPException:
        raise  # let FastAPI handle 4xx/5xx raised inside the try block (e.g. 409 duplicate VM)
    except Exception as e:
        logger.exception("clone_azure_vm unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=f"Clone VM failed: {str(e)}")


@app.get("/healthz")
def healthz():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}

@app.get("/debug/sp_subs")
def debug_sp_subs():
    try:
        subs = get_azure_subscriptions_sp_cached()
        return {"count": len(subs), "subs": subs}
    except Exception as e:
        logger.exception("debug_sp_subs failed: %s", e)
        return {"error": str(e)}

@app.post("/debug/clear_caches")
def debug_clear_caches():
    try:
        sp_subs_cache.clear()
        user_subs_cache.clear()
        subs_rg_cache.clear()
        user_groups_cache.clear()
        logger.info("Cleared internal caches via /debug/clear_caches")
        return {"cleared": True}
    except Exception as e:
        logger.exception("Failed to clear caches: %s", e)
        return {"cleared": False, "error": str(e)}

# ── In-browser SSH terminal ──────────────────────────────────────────────────
# Short-lived token store: token → {host, username, password, port, created_at}
_ssh_token_store: dict = {}
_ssh_token_lock = threading.Lock()
_SSH_TOKEN_TTL_SECONDS = 300  # 5 minutes

# In-memory host-key store for TOFU (Trust-On-First-Use) verification.
# Maps hostname → hex fingerprint seen on first connect.  A mismatch on a
# subsequent connect raises an error, preventing silent MITM acceptance.
_ssh_known_hosts: dict = {}
_ssh_known_hosts_lock = threading.Lock()


class _TofuHostKeyPolicy:
    """
    Trust-On-First-Use SSH host-key policy.

    First connection to a host: the key is accepted and its fingerprint is
    stored in _ssh_known_hosts.  All future connections to the same host must
    present the same key; a different key raises paramiko.SSHException.

    This is significantly safer than AutoAddPolicy, which silently accepts any
    key on every connection (no MITM protection at all).
    """

    def missing_host_key(self, client, hostname, key):  # noqa: ARG002
        fp = key.get_fingerprint().hex()
        with _ssh_known_hosts_lock:
            known = _ssh_known_hosts.get(hostname)
            if known is None:
                logger.info("SSH TOFU: trusting host key for %s (fp=…%s)", hostname, fp[-16:])
                _ssh_known_hosts[hostname] = fp
            elif known != fp:
                raise paramiko.SSHException(
                    f"Host key mismatch for {hostname}: "
                    f"expected …{known[-16:]} but got …{fp[-16:]}. "
                    "Connection refused to prevent a potential MITM attack."
                )
            # else: key matches stored fingerprint — proceed normally


def _purge_stale_ssh_tokens():
    cutoff = time.time() - _SSH_TOKEN_TTL_SECONDS
    with _ssh_token_lock:
        stale = [t for t, v in _ssh_token_store.items() if v.get("created_at", 0) < cutoff]
        for t in stale:
            _ssh_token_store.pop(t, None)

@app.post("/api/ssh/session")
async def create_ssh_session(request: Request):
    """
    Exchange SSH credentials for a short-lived token used by the WebSocket endpoint.
    Credentials are never placed in the WebSocket URL (which would appear in server logs).
    """
    data = await request.json()
    host = (data.get("host") or "").strip()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    port = int(data.get("port") or 22)

    if not host or not username:
        raise HTTPException(status_code=400, detail="host and username are required")
    # Validate host: allow IPv4, IPv6, and simple hostnames; block anything suspicious
    if not re.match(r'^[A-Za-z0-9._:\[\]-]+$', host):
        raise HTTPException(status_code=400, detail="Invalid host value")
    if port < 1 or port > 65535:
        raise HTTPException(status_code=400, detail="Invalid port")

    _purge_stale_ssh_tokens()
    token = uuid.uuid4().hex
    with _ssh_token_lock:
        _ssh_token_store[token] = {
            "host": host, "username": username, "password": password,
            "port": port, "created_at": time.time()
        }
    return {"token": token}


@app.websocket("/ws/ssh/{token}")
async def ssh_terminal_ws(websocket: WebSocket, token: str):
    """
    WebSocket endpoint that proxies an interactive SSH shell.
    The client connects with xterm.js; input/output are streamed bi-directionally.
    JSON messages from the client:
      {"type": "data",   "data": "<chars>"}          — keystrokes
      {"type": "resize", "cols": N, "rows": N}        — terminal resize
    Binary frames from the server contain raw SSH stdout bytes.
    """
    import asyncio

    # Consume the one-time token immediately
    with _ssh_token_lock:
        session = _ssh_token_store.pop(token, None)

    await websocket.accept()

    if not session:
        await websocket.send_text("\r\n\x1b[31mSSH session token is invalid or has expired. "
                                  "Please try again.\x1b[0m\r\n")
        await websocket.close(1008)
        return

    # Lazy-import paramiko so the app still starts even if not installed
    try:
        import paramiko  # noqa: F401 – checked here to give a clear error
    except ImportError:
        await websocket.send_text(
            "\r\n\x1b[31mServer error: paramiko is not installed. "
            "Ask the administrator to add 'paramiko' to requirements.txt.\x1b[0m\r\n"
        )
        await websocket.close(1011)
        return

    host = session["host"]
    username = session["username"]
    password = session["password"]
    port = session["port"]

    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(_TofuHostKeyPolicy())
    loop = asyncio.get_running_loop()

    try:
        await websocket.send_text(
            f"\x1b[33mConnecting to {username}@{host}:{port} …\x1b[0m\r\n"
        )

        # Connect in a thread pool to avoid blocking the event loop
        await loop.run_in_executor(
            None,
            lambda: ssh_client.connect(
                host, port=port, username=username, password=password,
                timeout=15, allow_agent=False, look_for_keys=False,
                banner_timeout=20,
            )
        )

        channel = ssh_client.invoke_shell(term="xterm-256color", width=220, height=50)
        channel.settimeout(0.05)  # non-blocking recv with short poll interval

        stop_event = threading.Event()

        def ssh_reader():
            """Read SSH stdout in a background thread and post to the WebSocket."""
            while not stop_event.is_set():
                try:
                    data = channel.recv(4096)
                    if data:
                        asyncio.run_coroutine_threadsafe(
                            websocket.send_bytes(data), loop
                        )
                    elif channel.exit_status_ready():
                        stop_event.set()
                        break
                except paramiko.buffered_pipe.PipeTimeout:
                    pass  # normal: no data available right now
                except Exception:
                    stop_event.set()
                    break

        reader_thread = threading.Thread(target=ssh_reader, daemon=True)
        reader_thread.start()

        # Forward WebSocket → SSH
        try:
            while not stop_event.is_set():
                try:
                    msg = await asyncio.wait_for(websocket.receive(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                if msg["type"] == "websocket.disconnect":
                    break
                if msg["type"] == "websocket.receive":
                    text = msg.get("text") or ""
                    raw = msg.get("bytes") or b""
                    if raw:
                        channel.sendall(raw)
                    elif text:
                        try:
                            parsed = json.loads(text)
                            if parsed.get("type") == "resize":
                                cols = int(parsed.get("cols", 220))
                                rows = int(parsed.get("rows", 50))
                                channel.resize_pty(width=cols, height=rows)
                            elif parsed.get("type") == "data":
                                channel.sendall(parsed.get("data", "").encode("utf-8", errors="replace"))
                        except (json.JSONDecodeError, ValueError):
                            channel.sendall(text.encode("utf-8", errors="replace"))
        except WebSocketDisconnect:
            pass

        stop_event.set()
        reader_thread.join(timeout=3)

    except paramiko.AuthenticationException:
        await websocket.send_text(
            "\r\n\x1b[31mAuthentication failed. "
            "Check the username and password.\x1b[0m\r\n"
        )
    except (OSError, paramiko.ssh_exception.NoValidConnectionsError, TimeoutError) as e:
        await websocket.send_text(
            f"\r\n\x1b[31mCould not reach {host}:{port} — {e}\x1b[0m\r\n"
            "\x1b[33mMake sure the VM has a public IP, port 22 is open in its firewall/NSG, "
            "and the backend server can reach the VM.\x1b[0m\r\n"
        )
    except Exception as e:
        logger.exception("SSH WebSocket error for %s@%s: %s", username, host, e)
        await websocket.send_text(f"\r\n\x1b[31mUnexpected error: {e}\x1b[0m\r\n")
    finally:
        try:
            ssh_client.close()
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("unified_main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
