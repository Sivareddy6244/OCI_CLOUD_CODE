#!/usr/bin/env python3
"""
GCP Workload Identity Federation Module
Handles token exchange from Azure AD JWT to GCP access tokens.
Implements the federation workflow for accessing GCP resources using Azure AD credentials.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import logging
import httpx
from datetime import datetime, timezone, timedelta
import json

logger = logging.getLogger(__name__)

# GCP Workload Identity Federation Configuration
GCP_PROJECT_NUMBER = os.getenv("GCP_PROJECT_NUMBER")
GCP_WIF_POOL_ID = os.getenv("GCP_WIF_POOL_ID", "azure-ad-pool")
GCP_WIF_PROVIDER_ID = os.getenv("GCP_WIF_PROVIDER_ID", "azure-ad-provider")
GCP_SERVICE_ACCOUNT_EMAIL = os.getenv("GCP_SERVICE_ACCOUNT_EMAIL")

# GCP Token Exchange Endpoint
GCP_STS_TOKEN_ENDPOINT = "https://sts.googleapis.com/v1/token"
GCP_IAM_CREDENTIALS_ENDPOINT = "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts"

# Token cache
wif_token_cache: Dict[str, Dict[str, Any]] = {}

router = APIRouter()


class WIFTokenRequest(BaseModel):
    """Request model for WIF token exchange"""
    azure_ad_token: str
    scope: Optional[str] = "https://www.googleapis.com/auth/cloud-platform"


class WIFTokenResponse(BaseModel):
    """Response model for WIF token exchange"""
    access_token: str
    token_type: str
    expires_in: int
    issued_token_type: str


def build_workload_identity_pool_name() -> str:
    """Build the full resource name for the Workload Identity Pool."""
    if not GCP_PROJECT_NUMBER or not GCP_WIF_POOL_ID or not GCP_WIF_PROVIDER_ID:
        raise ValueError(
            "GCP Workload Identity Federation not configured. "
            "Please set GCP_PROJECT_NUMBER, GCP_WIF_POOL_ID, and GCP_WIF_PROVIDER_ID."
        )
    
    return (
        f"projects/{GCP_PROJECT_NUMBER}/locations/global/"
        f"workloadIdentityPools/{GCP_WIF_POOL_ID}/"
        f"providers/{GCP_WIF_PROVIDER_ID}"
    )


def exchange_azure_token_for_gcp_token(azure_ad_token: str, scope: str) -> Dict[str, Any]:
    """Exchange Azure AD token for GCP access token using Workload Identity Federation.
    
    Args:
        azure_ad_token: Azure AD JWT token (id_token)
        scope: GCP OAuth scope (default: cloud-platform)
    
    Returns:
        Dictionary with GCP access token and metadata
    
    Raises:
        HTTPException: If token exchange fails
    """
    try:
        # Build the workload identity pool provider resource name
        audience = f"//iam.googleapis.com/{build_workload_identity_pool_name()}"
        
        # Prepare token exchange request according to RFC 8693
        token_exchange_payload = {
            "audience": audience,
            "grantType": "urn:ietf:params:oauth:grant-type:token-exchange",
            "requestedTokenType": "urn:ietf:params:oauth:token-type:access_token",
            "scope": scope,
            "subjectTokenType": "urn:ietf:params:oauth:token-type:jwt",
            "subjectToken": azure_ad_token
        }
        
        logger.info(f"Exchanging Azure AD token for GCP token via WIF")
        
        # Make token exchange request to GCP STS
        response = httpx.post(
            GCP_STS_TOKEN_ENDPOINT,
            json=token_exchange_payload,
            headers={"Content-Type": "application/json"}
        )
        
        response.raise_for_status()
        sts_response = response.json()
        
        # The response contains a federated token that can be used with GCP APIs
        federated_token = sts_response.get("access_token")
        expires_in = sts_response.get("expires_in", 3600)
        
        logger.info(f"Successfully exchanged Azure AD token for GCP federated token")
        
        # If we need to impersonate a service account for additional permissions
        if GCP_SERVICE_ACCOUNT_EMAIL:
            return impersonate_service_account(federated_token, scope, expires_in)
        
        # Calculate expiry time
        expires_at = datetime.now(timezone.utc).timestamp() + expires_in
        
        return {
            "access_token": federated_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "expires_at": expires_at,
            "scope": scope,
            "issued_token_type": sts_response.get("issued_token_type")
        }
        
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        logger.error(f"GCP token exchange failed: {error_detail}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Failed to exchange Azure AD token for GCP token: {error_detail}"
        )
    except ValueError as e:
        logger.error(f"WIF configuration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during token exchange")
        raise HTTPException(
            status_code=500,
            detail=f"Token exchange failed: {str(e)}"
        )


def impersonate_service_account(
    federated_token: str,
    scope: str,
    lifetime_seconds: int = 3600
) -> Dict[str, Any]:
    """Impersonate a service account to get a GCP access token.
    
    This is used when the federated identity needs to assume a service account
    for additional permissions.
    
    Args:
        federated_token: Federated access token from STS
        scope: OAuth scope for the service account token
        lifetime_seconds: Token lifetime (max 43200 seconds / 12 hours)
    
    Returns:
        Dictionary with service account access token and metadata
    """
    try:
        # Build the service account impersonation endpoint
        sa_endpoint = (
            f"{GCP_IAM_CREDENTIALS_ENDPOINT}/{GCP_SERVICE_ACCOUNT_EMAIL}"
            ":generateAccessToken"
        )
        
        # Prepare impersonation request
        impersonation_payload = {
            "scope": [scope],
            "lifetime": f"{lifetime_seconds}s"
        }
        
        logger.info(f"Impersonating service account: {GCP_SERVICE_ACCOUNT_EMAIL}")
        
        # Make impersonation request
        response = httpx.post(
            sa_endpoint,
            json=impersonation_payload,
            headers={
                "Authorization": f"Bearer {federated_token}",
                "Content-Type": "application/json"
            }
        )
        
        response.raise_for_status()
        sa_response = response.json()
        
        # Parse expiration time
        expire_time_str = sa_response.get("expireTime")
        # Convert ISO 8601 to timestamp
        expire_time = datetime.fromisoformat(expire_time_str.replace('Z', '+00:00'))
        expires_at = expire_time.timestamp()
        expires_in = int(expires_at - datetime.now(timezone.utc).timestamp())
        
        logger.info(f"Successfully impersonated service account")
        
        return {
            "access_token": sa_response.get("accessToken"),
            "token_type": "Bearer",
            "expires_in": expires_in,
            "expires_at": expires_at,
            "scope": scope,
            "issued_token_type": "urn:ietf:params:oauth:token-type:access_token",
            "service_account": GCP_SERVICE_ACCOUNT_EMAIL
        }
        
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        logger.error(f"Service account impersonation failed: {error_detail}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Failed to impersonate service account: {error_detail}"
        )
    except Exception as e:
        logger.exception("Unexpected error during service account impersonation")
        raise HTTPException(
            status_code=500,
            detail=f"Service account impersonation failed: {str(e)}"
        )


def get_cached_gcp_token(session_id: str) -> Optional[Dict[str, Any]]:
    """Get cached GCP token for a session if it exists and is not expired.
    
    Args:
        session_id: Session identifier
    
    Returns:
        Cached token data or None if not found or expired
    """
    if session_id not in wif_token_cache:
        return None
    
    cached_token = wif_token_cache[session_id]
    expires_at = cached_token.get("expires_at", 0)
    
    # Check if token is still valid (with 5 minute buffer)
    if datetime.now(timezone.utc).timestamp() + 300 >= expires_at:
        logger.info(f"Cached GCP token expired for session {session_id}")
        del wif_token_cache[session_id]
        return None
    
    logger.info(f"Using cached GCP token for session {session_id}")
    return cached_token


def cache_gcp_token(session_id: str, token_data: Dict[str, Any]):
    """Cache GCP token for a session.
    
    Args:
        session_id: Session identifier
        token_data: Token data to cache
    """
    wif_token_cache[session_id] = token_data
    logger.info(f"Cached GCP token for session {session_id}")


def get_gcp_token_from_azure_session(request: Request) -> Optional[Dict[str, Any]]:
    """Get GCP access token by exchanging Azure AD token from session.
    
    This function:
    1. Retrieves Azure AD token from session
    2. Checks for cached GCP token
    3. If no valid cache, uses Azure AD ID token for GCP WIF exchange
    4. Exchanges Azure AD token for GCP token
    5. Caches the new GCP token
    
    Note: GCP Workload Identity Federation must be configured to accept Azure AD tokens.
    See SSO_CROSS_CLOUD_SETUP.md for configuration instructions.
    
    Args:
        request: FastAPI request object
    
    Returns:
        GCP token data or None if Azure AD session not found or exchange fails
    """
    from azure_ad_auth import get_azure_ad_token_from_session
    
    # Check if GCP WIF environment variables are configured
    if not GCP_PROJECT_NUMBER:
        logger.error(
            "GCP_PROJECT_NUMBER not set. Cannot use Azure AD SSO for GCP. "
            "Please set GCP_PROJECT_NUMBER in .env file and configure GCP WIF. "
            "See SSO_CROSS_CLOUD_SETUP.md for setup instructions."
        )
        return None
    
    if not GCP_WIF_POOL_ID or not GCP_WIF_PROVIDER_ID:
        logger.error(
            f"GCP WIF configuration incomplete. Set: GCP_WIF_POOL_ID={GCP_WIF_POOL_ID or 'NOT SET'}, "
            f"GCP_WIF_PROVIDER_ID={GCP_WIF_PROVIDER_ID or 'NOT SET'}. "
            "See SSO_CROSS_CLOUD_SETUP.md for setup instructions."
        )
        return None
    
    # Get Azure AD token from session
    azure_token_data = get_azure_ad_token_from_session(request)
    if not azure_token_data:
        logger.debug("No Azure AD token data found in session")
        return None
    
    session_id = request.session.get("azure_ad_session_id")
    if not session_id:
        logger.debug("No Azure AD session ID found")
        return None
    
    # Check cache first
    cached_token = get_cached_gcp_token(session_id)
    if cached_token:
        return cached_token
    
    # Exchange Azure AD ID token for GCP token
    try:
        # Use ID token from Azure AD
        # This token has audience = Azure AD client ID by default
        # GCP WIF must be configured to accept this audience (see SSO_CROSS_CLOUD_SETUP.md)
        id_token = azure_token_data.get("id_token")
        if not id_token:
            logger.error("No id_token found in Azure AD token data")
            return None
        
        logger.info("Attempting to exchange Azure AD ID token for GCP access token")
        logger.info(f"Using GCP WIF: projects/{GCP_PROJECT_NUMBER}/locations/global/workloadIdentityPools/{GCP_WIF_POOL_ID}/providers/{GCP_WIF_PROVIDER_ID}")
        
        gcp_token = exchange_azure_token_for_gcp_token(
            azure_ad_token=id_token,
            scope="https://www.googleapis.com/auth/cloud-platform"
        )
        
        # Cache the token
        cache_gcp_token(session_id, gcp_token)
        
        logger.info("Successfully obtained and cached GCP access token")
        return gcp_token
        
    except HTTPException as e:
        # Log the specific error for debugging
        logger.error(f"Failed to get GCP token from Azure session: {e.status_code}: {e.detail}")
        
        # Provide helpful guidance based on the error
        error_detail = str(e.detail).lower()
        if "invalid_target" in error_detail or "doesn't exist" in error_detail:
            logger.error(
                "GCP WIF Pool/Provider does NOT exist in GCP or is disabled. "
                f"The pool 'projects/{GCP_PROJECT_NUMBER}/locations/global/workloadIdentityPools/{GCP_WIF_POOL_ID}/providers/{GCP_WIF_PROVIDER_ID}' "
                "must be created in GCP Console. "
                "Follow the step-by-step guide in SSO_CROSS_CLOUD_SETUP.md (steps 1-4) to create it."
            )
        elif "audience" in error_detail:
            logger.error(
                "GCP WIF is configured but not set to accept Azure AD tokens. "
                "Update your GCP WIF provider to set --allowed-audiences to your Azure AD Client ID. "
                "See SSO_CROSS_CLOUD_SETUP.md for the exact command."
            )
        else:
            logger.error(
                "GCP WIF token exchange failed. See SSO_CROSS_CLOUD_SETUP.md for troubleshooting. "
                f"Error: {e.detail}"
            )
        return None
    except ValueError as e:
        # This catches the error from build_workload_identity_pool_name
        logger.error(f"GCP WIF configuration error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting GCP token from Azure session: {e}")
        return None


@router.post("/gcp/wif/exchange-token")
async def exchange_token(request: Request, token_request: WIFTokenRequest):
    """Endpoint to manually exchange Azure AD token for GCP token.
    
    This is primarily for testing and debugging. Normal operation uses
    get_gcp_token_from_azure_session() automatically.
    """
    try:
        gcp_token = exchange_azure_token_for_gcp_token(
            azure_ad_token=token_request.azure_ad_token,
            scope=token_request.scope
        )
        
        return WIFTokenResponse(
            access_token=gcp_token["access_token"],
            token_type=gcp_token["token_type"],
            expires_in=gcp_token["expires_in"],
            issued_token_type=gcp_token["issued_token_type"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Token exchange endpoint failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gcp/wif/status")
async def wif_status(request: Request):
    """Check GCP WIF configuration and token status."""
    try:
        pool_name = build_workload_identity_pool_name()
        configured = True
    except ValueError as e:
        pool_name = None
        configured = False
    
    session_id = request.session.get("azure_ad_session_id")
    has_cached_token = session_id and session_id in wif_token_cache
    
    return {
        "configured": configured,
        "workload_identity_pool": pool_name,
        "project_number": GCP_PROJECT_NUMBER,
        "pool_id": GCP_WIF_POOL_ID,
        "provider_id": GCP_WIF_PROVIDER_ID,
        "service_account": GCP_SERVICE_ACCOUNT_EMAIL,
        "has_cached_token": has_cached_token
    }
