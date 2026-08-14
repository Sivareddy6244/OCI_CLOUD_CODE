#!/usr/bin/env python3
"""
Azure AD OIDC Authentication Module
Handles Azure Entra ID (formerly Azure AD) authentication using OIDC.
Provides JWT tokens that can be used for federation with AWS and GCP.
"""

from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import logging
import jwt
from datetime import datetime, timezone, timedelta
from authlib.integrations.starlette_client import OAuth
from authlib.oauth2.rfc7523 import JWTBearerToken
import httpx

logger = logging.getLogger(__name__)

# Azure AD OIDC Configuration
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
AZURE_REDIRECT_URI = os.getenv("AZURE_REDIRECT_URI", "http://localhost:8000/auth/callback")

# GCP Workload Identity Federation Configuration (for audience claim)
GCP_PROJECT_NUMBER = os.getenv("GCP_PROJECT_NUMBER")
GCP_WIF_POOL_ID = os.getenv("GCP_WIF_POOL_ID", "azure-ad-pool")
GCP_WIF_PROVIDER_ID = os.getenv("GCP_WIF_PROVIDER_ID", "azure-ad-provider")

# OIDC endpoints
AZURE_AUTHORITY = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}"
AZURE_TOKEN_ENDPOINT = f"{AZURE_AUTHORITY}/oauth2/v2.0/token"
AZURE_AUTHORIZATION_ENDPOINT = f"{AZURE_AUTHORITY}/oauth2/v2.0/authorize"
AZURE_JWKS_URI = f"{AZURE_AUTHORITY}/discovery/v2.0/keys"

# Build GCP WIF audience if configured
GCP_WIF_AUDIENCE = None
if GCP_PROJECT_NUMBER and GCP_WIF_POOL_ID and GCP_WIF_PROVIDER_ID:
    GCP_WIF_AUDIENCE = f"//iam.googleapis.com/projects/{GCP_PROJECT_NUMBER}/locations/global/workloadIdentityPools/{GCP_WIF_POOL_ID}/providers/{GCP_WIF_PROVIDER_ID}"

# Scopes for Azure AD
# Note: Cannot use .default scope with resource-specific scopes
AZURE_SCOPES = [
    "openid",
    "profile",
    "email",
    "offline_access",  # For refresh token
    "https://management.azure.com/user_impersonation",  # Azure access
]

router = APIRouter()

# In-memory token storage (use Redis/database in production)
azure_ad_sessions: Dict[str, Dict[str, Any]] = {}


class AzureADConfig(BaseModel):
    """Azure AD configuration model"""
    tenant_id: str
    client_id: str
    client_secret: str
    redirect_uri: str


def get_azure_ad_token_from_session(request: Request) -> Optional[Dict[str, Any]]:
    """Extract Azure AD token information from session."""
    session_id = request.session.get("azure_ad_session_id")
    if not session_id or session_id not in azure_ad_sessions:
        return None
    
    session_data = azure_ad_sessions[session_id]
    token_data = session_data.get("token_data")
    
    if not token_data:
        return None
    
    # Check if token is expired
    expires_at = token_data.get("expires_at")
    if expires_at and datetime.now(timezone.utc).timestamp() >= expires_at:
        # Try to refresh the token
        refresh_token = token_data.get("refresh_token")
        if refresh_token:
            try:
                new_token_data = refresh_azure_ad_token(refresh_token)
                if new_token_data:
                    azure_ad_sessions[session_id]["token_data"] = new_token_data
                    return new_token_data
            except Exception as e:
                logger.error(f"Failed to refresh Azure AD token: {e}")
                return None
        return None
    
    return token_data


def refresh_azure_ad_token(refresh_token: str) -> Optional[Dict[str, Any]]:
    """Refresh Azure AD token using refresh token."""
    try:
        data = {
            "client_id": AZURE_CLIENT_ID,
            "client_secret": AZURE_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": " ".join(AZURE_SCOPES)
        }
        
        response = httpx.post(AZURE_TOKEN_ENDPOINT, data=data)
        response.raise_for_status()
        
        token_response = response.json()
        
        # Calculate expiry time
        expires_in = token_response.get("expires_in", 3600)
        expires_at = datetime.now(timezone.utc).timestamp() + expires_in
        
        return {
            "access_token": token_response.get("access_token"),
            "id_token": token_response.get("id_token"),
            "refresh_token": token_response.get("refresh_token", refresh_token),
            "token_type": token_response.get("token_type", "Bearer"),
            "expires_at": expires_at,
            "scope": token_response.get("scope")
        }
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        return None


def decode_jwt_token(token: str, verify: bool = False) -> Optional[Dict[str, Any]]:
    """Decode JWT token without verification for inspection.
    
    **Security Note**: This function decodes tokens WITHOUT signature verification.
    It is used ONLY for extracting user claims from ID tokens that have already been
    obtained through a secure OAuth2 flow with Azure AD. The tokens are verified
    during the OAuth2 exchange process itself.
    
    For production use cases requiring full JWT verification:
    1. Fetch JWKS from Azure AD: {AZURE_JWKS_URI}
    2. Verify signature using public keys from JWKS
    3. Validate issuer, audience, expiration claims
    4. Consider using libraries like python-jose or authlib for full verification
    
    Args:
        token: JWT token string
        verify: Whether to verify signature (requires JWKS) - not implemented
    
    Returns:
        Decoded token claims or None if invalid
    """
    try:
        if verify:
            # TODO: Implement full verification with signature check
            # This requires fetching JWKS from Azure AD and validating the signature
            logger.warning("JWT signature verification not yet implemented")
            pass
        
        # Decode without verification - safe here because token obtained via OAuth2 flow
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded
    except Exception as e:
        logger.error(f"Failed to decode JWT: {e}")
        return None


@router.get("/auth/sign_in")
async def azure_ad_sign_in(request: Request):
    """Initiate Azure AD OIDC login flow."""
    if not AZURE_TENANT_ID or not AZURE_CLIENT_ID or not AZURE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Azure AD not configured. Please set AZURE_TENANT_ID, AZURE_CLIENT_ID, and AZURE_CLIENT_SECRET."
        )
    
    # Build authorization URL
    params = {
        "client_id": AZURE_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": AZURE_REDIRECT_URI,
        "scope": " ".join(AZURE_SCOPES),
        "response_mode": "query",
        "state": f"state_{datetime.now(timezone.utc).timestamp()}"
    }
    
    # Store state in session for CSRF protection
    request.session["azure_ad_oauth_state"] = params["state"]
    
    # Build authorization URL
    auth_url = AZURE_AUTHORIZATION_ENDPOINT + "?" + "&".join([f"{k}={v}" for k, v in params.items()])
    
    return RedirectResponse(url=auth_url)


@router.get("/auth/callback")
async def azure_ad_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...)
):
    """Handle OAuth2 callback from Azure AD."""
    # Verify state for CSRF protection
    stored_state = request.session.get("azure_ad_oauth_state")
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid state parameter - possible CSRF attack")
    
    try:
        # Exchange authorization code for tokens
        token_data = {
            "client_id": AZURE_CLIENT_ID,
            "client_secret": AZURE_CLIENT_SECRET,
            "code": code,
            "redirect_uri": AZURE_REDIRECT_URI,
            "grant_type": "authorization_code",
            "scope": " ".join(AZURE_SCOPES)
        }
        
        response = httpx.post(AZURE_TOKEN_ENDPOINT, data=token_data)
        response.raise_for_status()
        
        token_response = response.json()
        
        # Decode ID token to get user information
        id_token = token_response.get("id_token")
        user_claims = decode_jwt_token(id_token)
        
        if not user_claims:
            raise HTTPException(status_code=500, detail="Failed to decode user claims from ID token")
        
        # Calculate expiry time
        expires_in = token_response.get("expires_in", 3600)
        expires_at = datetime.now(timezone.utc).timestamp() + expires_in
        
        # Store tokens in session
        session_id = f"azure_ad_{user_claims.get('oid')}_{datetime.now(timezone.utc).timestamp()}"
        azure_ad_sessions[session_id] = {
            "token_data": {
                "access_token": token_response.get("access_token"),
                "id_token": id_token,
                "refresh_token": token_response.get("refresh_token"),
                "token_type": token_response.get("token_type", "Bearer"),
                "expires_at": expires_at,
                "scope": token_response.get("scope")
            },
            "user_info": {
                "email": user_claims.get("email") or user_claims.get("preferred_username"),
                "name": user_claims.get("name"),
                "oid": user_claims.get("oid"),
                "tid": user_claims.get("tid")
            }
        }
        
        request.session["azure_ad_session_id"] = session_id
        request.session["user_email"] = user_claims.get("email") or user_claims.get("preferred_username")
        request.session["user"] = azure_ad_sessions[session_id]["user_info"]
        
        logger.info(f"User authenticated: {user_claims.get('email')}")
        
        # Redirect back to main page
        return RedirectResponse(url="/")
        
    except httpx.HTTPStatusError as e:
        logger.error(f"Token exchange failed: {e.response.text}")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {e.response.text}")
    except Exception as e:
        logger.exception("Azure AD callback failed")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@router.get("/auth/status")
async def auth_status(request: Request):
    """Check Azure AD authentication status."""
    token_data = get_azure_ad_token_from_session(request)
    
    if token_data:
        user_info = request.session.get("user", {})
        return {
            "authenticated": True,
            "user": user_info,
            "token_type": token_data.get("token_type"),
            "expires_at": token_data.get("expires_at")
        }
    
    return {"authenticated": False}


@router.post("/auth/sign_out")
async def azure_ad_sign_out(request: Request):
    """Sign out from Azure AD and clear session."""
    session_id = request.session.get("azure_ad_session_id")
    
    if session_id and session_id in azure_ad_sessions:
        del azure_ad_sessions[session_id]
    
    # Clear session
    request.session.clear()
    
    return {"status": "success", "message": "Signed out successfully"}


def require_azure_ad_auth(request: Request) -> Dict[str, Any]:
    """Dependency to require Azure AD authentication."""
    token_data = get_azure_ad_token_from_session(request)
    
    if not token_data:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated with Azure AD. Please sign in first."
        )
    
    return token_data
