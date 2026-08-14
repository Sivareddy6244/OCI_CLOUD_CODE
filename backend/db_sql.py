import os
import json
import uuid
import re
import logging
from pathlib import Path
from functools import lru_cache
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pyodbc

logger = logging.getLogger(__name__)


def _get_conn() -> pyodbc.Connection:
    """
    Uses SQL_CONNECTION_STRING from App Service configuration.
    Recommended to store an ODBC-style connection string.
    """
    cs = os.getenv("SQL_CONNECTION_STRING")
    if not cs:
        raise RuntimeError("SQL_CONNECTION_STRING is not set in environment variables.")
    return pyodbc.connect(cs)


def insert_portal_request_all(row: Dict[str, Any]) -> str:
    """
    Insert one row into portal.portal_request_all and return request_id.
    Expect at least: cloud_provider
    """
    request_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    cloud_provider = row.get("cloud_provider")
    if not cloud_provider:
        raise ValueError("cloud_provider is required (aws|azure|gcp|oci)")

    payload_json = row.get("payload_json")
    if payload_json is not None and not isinstance(payload_json, str):
        payload_json = json.dumps(payload_json)

    # Keep firewall_rules_json as string
    gcp_fw = row.get("gcp_firewall_rules_json")
    if gcp_fw is not None and not isinstance(gcp_fw, str):
        gcp_fw = json.dumps(gcp_fw)

    sql = """
    INSERT INTO portal.portal_request_all (
        request_id, created_at_utc, updated_at_utc,
        user_email, user_oid,
        cloud_provider,
        vm_name_requested, vm_name_final,
        tag_account_number, tag_approvers, tag_ps,
        status, error_message, payload_json,

        aws_account_id, aws_region, aws_vpc_id, aws_subnet_id, aws_ami_id, aws_os_type,
        aws_instance_type, aws_security_group_id, aws_create_new_sg, aws_key_pair_name,

        azure_subscription_id, azure_resource_group, azure_virtual_network, azure_subnet_id,
        azure_image_definition, azure_vm_size, azure_os_disk_type, azure_location, azure_availability_zone,
        azure_nsg_id, azure_create_new_nsg, azure_admin_username, azure_admin_password_provided,
        azure_use_managed_disks, azure_accelerated_networking,

        gcp_project_id, gcp_region, gcp_network, gcp_subnetwork, gcp_machine_type,
        gcp_image_project, gcp_image_family, gcp_disk_type, gcp_disk_size_gb, gcp_firewall_rules_json
    )
    VALUES (
        ?, ?, ?,
        ?, ?,
        ?,
        ?, ?,
        ?, ?, ?,
        ?, ?, ?,

        ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?,

        ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?,

        ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?
    )
    """

    params = [
        request_id, now, now,
        row.get("user_email"), row.get("user_oid"),
        cloud_provider,
        row.get("vm_name_requested"), row.get("vm_name_final"),
        row.get("tag_account_number"), row.get("tag_approvers"), row.get("tag_ps"),
        row.get("status", "received"), row.get("error_message"), payload_json,

        row.get("aws_account_id"), row.get("aws_region"), row.get("aws_vpc_id"), row.get("aws_subnet_id"),
        row.get("aws_ami_id"), row.get("aws_os_type"),
        row.get("aws_instance_type"), row.get("aws_security_group_id"),
        row.get("aws_create_new_sg"), row.get("aws_key_pair_name"),

        row.get("azure_subscription_id"), row.get("azure_resource_group"),
        row.get("azure_virtual_network"), row.get("azure_subnet_id"),
        row.get("azure_image_definition"), row.get("azure_vm_size"),
        row.get("azure_os_disk_type"), row.get("azure_location"),
        row.get("azure_availability_zone"),
        row.get("azure_nsg_id"), row.get("azure_create_new_nsg"),
        row.get("azure_admin_username"), row.get("azure_admin_password_provided"),
        row.get("azure_use_managed_disks"), row.get("azure_accelerated_networking"),

        row.get("gcp_project_id"), row.get("gcp_region"), row.get("gcp_network"),
        row.get("gcp_subnetwork"), row.get("gcp_machine_type"),
        row.get("gcp_image_project"), row.get("gcp_image_family"),
        row.get("gcp_disk_type"), row.get("gcp_disk_size_gb"),
        gcp_fw,
    ]

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
    finally:
        conn.close()

    return request_id

def update_portal_request_status(request_id: str, status: str, error_message: str = None) -> None:
    """
    Update status/error_message for an existing request row.
    """
    sql = """
    UPDATE portal.portal_request_all
    SET
        status = ?,
        error_message = ?,
        updated_at_utc = SYSUTCDATETIME()
    WHERE request_id = ?
    """

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, [status, error_message, request_id])
        conn.commit()
    finally:
        conn.close()

def update_latest_portal_request_vm_outcome(
    cloud_provider: str,
    vm_name_final: str,
    vm_status: str,
    vm_error_log: str = None,
) -> None:
    """
    Update VM outcome fields for the latest matching portal_request_all row.
    Falls back to legacy status/error_message only if the new columns do not exist yet.
    """
    sql_with_new_columns = """
    ;WITH latest_row AS (
        SELECT TOP 1 request_id
        FROM portal.portal_request_all
        WHERE cloud_provider = ?
          AND vm_name_final = ?
        ORDER BY created_at_utc DESC
    )
    UPDATE p
    SET
        status = ?,
        error_message = ?,
        vm_deployment_status = ?,
        vm_error_logs = ?,
        updated_at_utc = SYSUTCDATETIME()
    FROM portal.portal_request_all p
    INNER JOIN latest_row l
        ON p.request_id = l.request_id
    """

    sql_legacy_only = """
    ;WITH latest_row AS (
        SELECT TOP 1 request_id
        FROM portal.portal_request_all
        WHERE cloud_provider = ?
          AND vm_name_final = ?
        ORDER BY created_at_utc DESC
    )
    UPDATE p
    SET
        status = ?,
        error_message = ?,
        updated_at_utc = SYSUTCDATETIME()
    FROM portal.portal_request_all p
    INNER JOIN latest_row l
        ON p.request_id = l.request_id
    """

    conn = _get_conn()
    try:
        cur = conn.cursor()
        try:
            cur.execute(
                sql_with_new_columns,
                [cloud_provider, vm_name_final, vm_status, vm_error_log, vm_status, vm_error_log],
            )
            conn.commit()
            return
        except pyodbc.Error as primary_err:
            err_text = str(primary_err or "").lower()
            if "invalid column name" not in err_text:
                raise
            logger.debug(
                "update_latest_portal_request_vm_outcome: VM outcome columns not yet present, falling back to legacy status/error_message update: %s",
                primary_err,
            )
            cur.execute(
                sql_legacy_only,
                [cloud_provider, vm_name_final, vm_status, vm_error_log],
            )
            conn.commit()
    finally:
        conn.close()

def _normalize_billing_account(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"[^0-9A-Za-z]", "", s).upper().strip()

def get_billing_approver_emails_csv(billing_account: str) -> Optional[str]:
    """
    Return approver email(s) for a billing account.
    If multiple approvers exist, returns a single string: "a@x.com; b@y.com"
    Returns None if not found.
    """
    acct = _normalize_billing_account(billing_account)
    if not acct:
        return None

    sql = """
    SELECT approver_email
    FROM portal.portal_billing_approvers
    WHERE billing_account = ?
      AND is_active = 1
    ORDER BY approver_email
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, [acct])
        rows = cur.fetchall()
        emails = [r[0] for r in rows if r and r[0]]
        if not emails:
            return None
        return ",".join([e.strip() for e in emails if e and e.strip()])
    finally:
        conn.close()


@lru_cache(maxsize=1)
def _load_sql_seed_fallbacks() -> tuple[Dict[str, str], List[tuple]]:
    """
    Load static fallback data directly from the SQL seed files.
    This keeps AWS account-number and Azure VM-size fallback behavior working
    even when DB connectivity/table setup is temporarily unavailable.
    """
    logger = logging.getLogger(__name__)
    aws_map: Dict[str, str] = {}
    azure_sizes: List[tuple] = []
    repo_root = Path(__file__).resolve().parents[1]

    aws_sql = repo_root / "aws-account-tags-table.sql"
    azure_sql = repo_root / "azure-vm-sizes-table.sql"

    try:
        aws_text = aws_sql.read_text(encoding="utf-8")
        aws_pattern = re.compile(
            r"INSERT INTO portal\.aws_account_tags\s*\(account_id,\s*account_number,\s*account_name\)\s*"
            r"SELECT\s*'([^']+)'\s*,\s*'([^']+)'\s*,",
            re.IGNORECASE,
        )
        for account_id, account_number in aws_pattern.findall(aws_text):
            aws_map[account_id.strip()] = account_number.strip()
    except Exception as e:
        logger.debug("Failed loading AWS SQL seed fallback map: %s", e)

    try:
        azure_text = azure_sql.read_text(encoding="utf-8")
        azure_pattern = re.compile(
            r"INSERT INTO portal\.azure_vm_sizes\s*\(name,\s*vcpus,\s*memory_mb,\s*sort_order\)\s*"
            r"SELECT\s*'([^']+)'\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)",
            re.IGNORECASE,
        )
        parsed = []
        for name, vcpus, memory_mb, sort_order in azure_pattern.findall(azure_text):
            parsed.append((name, int(vcpus), int(memory_mb), int(sort_order)))
        parsed.sort(key=lambda x: (x[3], x[0]))
        azure_sizes = [(name, vcpus, memory_mb) for name, vcpus, memory_mb, _ in parsed]
    except Exception as e:
        logger.debug("Failed loading Azure SQL seed fallback sizes: %s", e)

    return aws_map, azure_sizes


def _lookup_aws_seed_account_number(candidates: List[str]) -> Optional[str]:
    aws_fallback_map = _load_sql_seed_fallbacks()[0]
    for candidate in candidates:
        if candidate in aws_fallback_map:
            return aws_fallback_map[candidate]
    return None


def get_resources_by_department(department: str, cloud: str = None) -> List[Dict[str, Any]]:
    """
    Return all portal_department_resources rows for the given department
    (case-insensitive). Optionally filter by cloud provider ('azure' or 'aws').
    Only Active records are returned.

    This table is pre-loaded by administrators and maps Azure subscriptions /
    AWS accounts to a department name derived from the user's email domain.
    E.g. 'ADahbashi@dhs.lacounty.gov' -> department 'dhs'.
    """
    if cloud:
        sql = """
        SELECT id, subscription_name, subscription_id, status, department, cloud,
               sample_mail, created_at_utc, updated_at_utc
        FROM portal.portal_department_resources
        WHERE LOWER(department) = LOWER(?)
          AND LOWER(cloud)      = LOWER(?)
          AND LOWER(status)     = 'active'
        ORDER BY subscription_name
        """
        params = [department, cloud]
    else:
        sql = """
        SELECT id, subscription_name, subscription_id, status, department, cloud,
               sample_mail, created_at_utc, updated_at_utc
        FROM portal.portal_department_resources
        WHERE LOWER(department) = LOWER(?)
          AND LOWER(status)     = 'active'
        ORDER BY subscription_name
        """
        params = [department]

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()


def is_admin_by_email(email: str) -> bool:
    """
    Return True if the given email address is in the portal.portal_admins table
    with status = 'Active'.  The comparison is case-insensitive.

    This is the DB-backed counterpart to the hardcoded ADMIN_EMAILS list in
    unified_main.py.  When the DB is available this check runs first; the
    hardcoded list serves as a fallback when the DB is unreachable.
    """
    if not email:
        return False
    sql = """
    SELECT TOP 1 1
    FROM   portal.portal_admins
    WHERE  LOWER(email)  = LOWER(?)
      AND  LOWER(status) = 'active'
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, [email])
        return cur.fetchone() is not None
    finally:
        conn.close()


def upsert_deployment_status(
    deployment_id: str,
    status: str,
    message: str = "",
    vm_id: str = None,
    error: str = None,
) -> None:
    """
    Insert or update a deployment status row in portal.deployment_status.
    Silently does nothing if the table does not yet exist.
    """
    sql = """
    MERGE portal.deployment_status AS target
    USING (SELECT ? AS deployment_id) AS source
        ON target.deployment_id = source.deployment_id
    WHEN MATCHED THEN
        UPDATE SET
            status         = ?,
            message        = ?,
            vm_id          = ?,
            error          = ?,
            updated_at_utc = SYSUTCDATETIME()
    WHEN NOT MATCHED THEN
        INSERT (deployment_id, status, message, vm_id, error, updated_at_utc)
        VALUES (?, ?, ?, ?, ?, SYSUTCDATETIME());
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        try:
            cur.execute(
                sql,
                [deployment_id, status, message, vm_id, error,
                 deployment_id, status, message, vm_id, error],
            )
            conn.commit()
        except Exception:
            # Table may not exist yet; caller is responsible for swallowing the error.
            raise
    finally:
        conn.close()


def get_deployment_status_db(deployment_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a deployment status row from portal.deployment_status.
    Returns None if the row does not exist or the table is missing.
    """
    sql = """
    SELECT status, message, vm_id, error, updated_at_utc
    FROM   portal.deployment_status
    WHERE  deployment_id = ?
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        try:
            cur.execute(sql, [deployment_id])
        except Exception:
            # Table may not exist yet.
            return None
        row = cur.fetchone()
        if not row:
            return None
        return {
            "status":     row[0] or "",
            "message":    row[1] or "",
            "vm_id":      row[2],
            "error":      row[3],
            "updated_at": row[4].isoformat() if row[4] else None,
        }
    finally:
        conn.close()


def get_azure_vm_sizes() -> List[tuple]:
    """
    Return a list of (name, vcpus, memory_mb) tuples for all active Azure VM sizes
    stored in portal.azure_vm_sizes, ordered by sort_order then name.

    If the table does not exist / is empty / is unreachable, this function falls back
    to parsing azure-vm-sizes-table.sql from the repo. If that also fails, it returns
    an empty list and the caller can still use the hardcoded app fallback list.
    """
    sql = """
    SELECT name, vcpus, memory_mb
    FROM   portal.azure_vm_sizes
    WHERE  is_active = 1
    ORDER BY sort_order, name
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        try:
            cur.execute(sql)
        except Exception:
            # Table does not exist yet or DB unavailable.
            return _load_sql_seed_fallbacks()[1]
        rows = cur.fetchall()
        db_rows = [(r[0], r[1], r[2]) for r in rows if r]
        if db_rows:
            return db_rows
        return _load_sql_seed_fallbacks()[1]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Compiled patterns used by the ISD subscription helpers.
# ---------------------------------------------------------------------------

_AZURE_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_AWS_ID_RE = re.compile(r"^\d{12}$")


def _is_azure_id(value: str) -> bool:
    """Return True if *value* looks like an Azure subscription GUID."""
    return bool(_AZURE_ID_RE.match(value.strip())) if value else False


def _is_aws_id(value: str) -> bool:
    """Return True if *value* looks like an AWS account ID (exactly 12 digits)."""
    return bool(_AWS_ID_RE.match(value.strip())) if value else False


def get_isd_subscriptions_for_email(
    email: str,
    cloud: str = "azure",
) -> Optional[List[str]]:
    """
    Return the cloud account / subscription IDs that an ISD user may see.

    Parameters
    ----------
    email : str
        The user's login email address.
    cloud : str
        Either ``"azure"`` (default) or ``"aws"``.  IDs are filtered so that
        only those matching the cloud's expected format are returned:

        * Azure – UUID format ``xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx``
        * AWS   – exactly 12-digit numeric string (e.g. ``123456789012``)

    The function checks two tables in priority order:

      1. portal.isd_non_support_teams
           If the user's email is found here, return only the IDs on the
           user's own row(s) that match the requested cloud format.

      2. portal.isd_linux_windows_team  (type-based access)
           Each row has a ``type`` column (e.g. ``wps``, ``lps``).
           If the user's email is found here, determine the user's type
           from their row(s), then return **all** IDs in the table that
           share that type and match the requested cloud format.
           Rows whose ``type`` column is NULL fall back to the original
           "return the user's own rows" behaviour for backward compat.

    Returns
    -------
    list[str] | None
        A list of IDs when the email was matched in at least one table
        (may be empty if the match produced no cloud-appropriate IDs).
        ``None`` when the email was not found in either table — the caller
        should then fall through to the generic department lookup.

    Raises
    ------
    pyodbc.Error
        Any database error that is **not** a "table/column does not exist"
        error is re-raised so the caller can log and handle it.
    """
    if not email:
        return None

    cloud = cloud.lower()
    email_lower = email.lower()

    def _filter_by_cloud(ids: List[str]) -> List[str]:
        if cloud == "aws":
            return [s for s in ids if _is_aws_id(s)]
        return [s for s in ids if _is_azure_id(s)]

    conn = _get_conn()
    try:
        cur = conn.cursor()

        # --- Step 1: isd_non_support_teams ---
        try:
            cur.execute(
                "SELECT subscription_id FROM portal.isd_non_support_teams "
                "WHERE LOWER(email) = ? AND is_active = 1",
                [email_lower],
            )
            rows = cur.fetchall()
            nst_subs = _filter_by_cloud([r[0] for r in rows if r and r[0]])
        except pyodbc.Error as e:
            if "invalid object name" in str(e).lower():
                nst_subs = []
            else:
                raise

        if nst_subs:
            return nst_subs

        # --- Step 2: isd_linux_windows_team (type-based) ---
        # First check whether the user has any rows at all (and read their type).
        try:
            cur.execute(
                "SELECT subscription_id, type FROM portal.isd_linux_windows_team "
                "WHERE LOWER(email) = ? AND is_active = 1",
                [email_lower],
            )
            user_lwt_rows = cur.fetchall()
        except pyodbc.Error as e:
            err_lower = str(e).lower()
            if "invalid object name" in err_lower or "invalid column name" in err_lower:
                # Table or 'type' column doesn't exist yet — skip gracefully.
                return None
            raise

        if not user_lwt_rows:
            # Email not found in either ISD table.
            return None

        # Determine the user's type(s) from their row(s).
        user_types = list({r[1] for r in user_lwt_rows if r[1] is not None})

        if user_types:
            # Type-based access: return ALL IDs in the table that share the
            # user's type(s), filtered to the requested cloud format.
            placeholders = ", ".join(["?"] * len(user_types))
            cur.execute(
                f"SELECT DISTINCT subscription_id "
                f"FROM portal.isd_linux_windows_team "
                f"WHERE type IN ({placeholders}) "
                f"  AND is_active = 1 "
                f"  AND subscription_id IS NOT NULL",
                user_types,
            )
            type_subs = [r[0] for r in cur.fetchall() if r and r[0]]
            lwt_subs = _filter_by_cloud(type_subs)
        else:
            # Legacy rows with no type value — return the user's own rows
            # (backward compatible behaviour).
            lwt_subs = _filter_by_cloud([r[0] for r in user_lwt_rows if r[0]])

        return lwt_subs if lwt_subs else []
    finally:
        conn.close()


def log_vm_action(
    action_type: str,
    cloud_provider: str,
    resource_name: str = None,
    resource_id: str = None,
    account_or_subscription: str = None,
    region_or_zone: str = None,
    detail: str = None,
    performed_by_email: str = None,
    performed_by_oid: str = None,
    status: str = "success",
    error_message: str = None,
) -> None:
    """
    Insert one audit row into portal.vm_action_audit.

    This function is intentionally fire-and-forget: if the table does not
    exist yet (e.g. vm_action_audit.sql has not been run) or if any other
    database error occurs, the error is logged at WARNING level and swallowed
    so that the actual portal action is never blocked by audit-logging failure.

    Parameters
    ----------
    action_type : str
        Short label for the action, e.g. ``delete_vm``, ``clone_vm``,
        ``snapshot_vm``, ``delete_disk``, ``delete_snapshot``,
        ``delete_volume``.
    cloud_provider : str
        ``azure``, ``aws``, or ``gcp``.
    resource_name : str, optional
        Human-readable name of the primary resource.
    resource_id : str, optional
        Cloud-native resource identifier (EC2 instance_id, Azure VM ID, etc.).
    account_or_subscription : str, optional
        Azure subscription ID, AWS account ID, or GCP project ID.
    region_or_zone : str, optional
        AWS region, Azure location, or GCP zone.
    detail : str, optional
        Additional context (e.g. list of also-deleted NICs, resource group).
    performed_by_email : str, optional
        Email of the logged-in user who triggered the action.
    performed_by_oid : str, optional
        Azure AD OID of the user (if available).
    status : str
        ``"success"`` (default) or ``"failed"``.
    error_message : str, optional
        Error detail when ``status = "failed"``.
    """
    sql = """
    INSERT INTO portal.vm_action_audit (
        action_type, cloud_provider,
        resource_name, resource_id,
        account_or_subscription, region_or_zone, detail,
        performed_by_email, performed_by_oid,
        status, error_message, performed_at_utc
    ) VALUES (
        ?, ?,
        ?, ?,
        ?, ?, ?,
        ?, ?,
        ?, ?, SYSUTCDATETIME()
    )
    """
    conn = None
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(sql, [
            action_type, cloud_provider,
            resource_name, resource_id,
            account_or_subscription, region_or_zone, detail,
            performed_by_email, performed_by_oid,
            status, error_message,
        ])
        conn.commit()
    except Exception as exc:
        logger.warning(
            "log_vm_action: failed to write audit row "
            "(action=%s cloud=%s resource=%s user=%s): %s",
            action_type, cloud_provider, resource_name, performed_by_email, exc,
        )
    finally:
        if conn is not None:
            conn.close()


def get_aws_account_number_from_db(account_id: str) -> Optional[str]:
    """
    Return the billing AccountNumber for the given AWS account ID from the
    admin-managed portal.aws_account_tags table.

    This is the final fallback (Method 5) used by get_aws_account_tags when all
    four automatic AWS API methods are unable to find the AccountNumber tag —
    either because the account has no tagged resources or the assumed role lacks
    the necessary permissions.

    Administrators populate this table by running aws-account-tags-table.sql and
    inserting a row for each account:
        INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
        VALUES ('792294445508', 'P1355422005', 'My Account');

    Returns None if no active row exists for the given account_id, or if the
    table does not yet exist.
    """
    if not account_id:
        return None
    normalized = re.sub(r"\D", "", account_id.strip())
    candidates: List[str] = []
    for candidate in [account_id.strip(), normalized, normalized.zfill(12) if normalized else None]:
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    sql = """
    SELECT TOP 1 account_number
    FROM   portal.aws_account_tags
    WHERE  account_id = ?
      AND  is_active  = 1
    """
    conn = _get_conn()
    try:
        cur = conn.cursor()
        try:
            row = None
            for candidate in candidates:
                cur.execute(sql, [candidate])
                row = cur.fetchone()
                if row and row[0]:
                    return row[0]
        except Exception as _table_err:
            # Treat any DB-level error (table not found, permission denied, etc.)
            # as a miss so we don't crash the request.  The full error is logged
            # at DEBUG so it is visible when needed without polluting normal logs.
            logging.getLogger(__name__).debug(
                "get_aws_account_number_from_db: DB query failed for account %s: %s",
                account_id, _table_err,
            )
            return _lookup_aws_seed_account_number(candidates)
        return _lookup_aws_seed_account_number(candidates)
    finally:
        conn.close()
