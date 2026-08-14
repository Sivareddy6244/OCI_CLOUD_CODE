#!/usr/bin/env python3
"""
Configuration Validation Script for Multi-Cloud Portal

This script validates the environment configuration for the multi-cloud portal,
checking Azure AD settings, GCP WIF configuration, OCI configuration, and providing guidance.
"""

import os
import sys
from typing import Dict, List, Tuple

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    """Print a section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")

def check_required_env(var_name: str, description: str) -> Tuple[bool, str]:
    """Check if a required environment variable is set"""
    value = os.getenv(var_name)
    if value:
        return True, value
    return False, ""

def check_optional_env(var_name: str, description: str) -> Tuple[bool, str]:
    """Check if an optional environment variable is set"""
    value = os.getenv(var_name)
    if value:
        return True, value
    return False, ""

def validate_azure_ad_config() -> Dict[str, bool]:
    """Validate Azure AD configuration"""
    print_header("Azure AD Configuration")
    
    results = {}
    
    # Required Azure AD settings
    tenant_ok, tenant_id = check_required_env("AZURE_TENANT_ID", "Azure AD Tenant ID")
    if tenant_ok:
        print_success(f"AZURE_TENANT_ID: {tenant_id}")
        results['tenant'] = True
    else:
        print_error("AZURE_TENANT_ID: Not set (REQUIRED)")
        results['tenant'] = False
    
    client_ok, client_id = check_required_env("AZURE_CLIENT_ID", "Azure AD Client ID")
    if client_ok:
        print_success(f"AZURE_CLIENT_ID: {client_id}")
        results['client'] = True
    else:
        print_error("AZURE_CLIENT_ID: Not set (REQUIRED)")
        results['client'] = False
    
    secret_ok, _ = check_required_env("AZURE_CLIENT_SECRET", "Azure AD Client Secret")
    if secret_ok:
        print_success("AZURE_CLIENT_SECRET: Set (value hidden)")
        results['secret'] = True
    else:
        print_error("AZURE_CLIENT_SECRET: Not set (REQUIRED)")
        results['secret'] = False
    
    redirect_ok, redirect_uri = check_optional_env("AZURE_REDIRECT_URI", "Azure AD Redirect URI")
    if redirect_ok:
        print_success(f"AZURE_REDIRECT_URI: {redirect_uri}")
        results['redirect'] = True
    else:
        print_warning("AZURE_REDIRECT_URI: Not set (using default: http://localhost:8000/auth/callback)")
        results['redirect'] = False
    
    return results

def validate_gcp_wif_config() -> Dict[str, bool]:
    """Validate GCP Workload Identity Federation configuration"""
    print_header("GCP Workload Identity Federation Configuration")
    
    results = {}
    
    # Check GCP WIF settings
    project_ok, project_num = check_optional_env("GCP_PROJECT_NUMBER", "GCP Project Number")
    if project_ok:
        print_success(f"GCP_PROJECT_NUMBER: {project_num}")
        results['project'] = True
    else:
        print_warning("GCP_PROJECT_NUMBER: Not set")
        results['project'] = False
    
    pool_ok, pool_id = check_optional_env("GCP_WIF_POOL_ID", "GCP WIF Pool ID")
    if pool_ok:
        print_success(f"GCP_WIF_POOL_ID: {pool_id}")
        results['pool'] = True
    else:
        print_warning("GCP_WIF_POOL_ID: Not set (using default: azure-ad-pool)")
        results['pool'] = False
    
    provider_ok, provider_id = check_optional_env("GCP_WIF_PROVIDER_ID", "GCP WIF Provider ID")
    if provider_ok:
        print_success(f"GCP_WIF_PROVIDER_ID: {provider_id}")
        results['provider'] = True
    else:
        print_warning("GCP_WIF_PROVIDER_ID: Not set (using default: azure-ad-provider)")
        results['provider'] = False
    
    sa_ok, sa_email = check_optional_env("GCP_SERVICE_ACCOUNT_EMAIL", "GCP Service Account Email")
    if sa_ok:
        print_success(f"GCP_SERVICE_ACCOUNT_EMAIL: {sa_email}")
        results['sa'] = True
    else:
        print_warning("GCP_SERVICE_ACCOUNT_EMAIL: Not set (optional - for service account impersonation)")
        results['sa'] = False
    
    return results

def validate_google_oauth_config() -> Dict[str, bool]:
    """Validate Google OAuth configuration (fallback for GCP)"""
    print_header("Google OAuth Configuration (GCP Fallback)")
    
    results = {}
    
    client_ok, client_id = check_optional_env("GOOGLE_CLIENT_ID", "Google OAuth Client ID")
    if client_ok:
        print_success(f"GOOGLE_CLIENT_ID: {client_id}")
        results['client'] = True
    else:
        print_warning("GOOGLE_CLIENT_ID: Not set")
        results['client'] = False
    
    secret_ok, _ = check_optional_env("GOOGLE_CLIENT_SECRET", "Google OAuth Client Secret")
    if secret_ok:
        print_success("GOOGLE_CLIENT_SECRET: Set (value hidden)")
        results['secret'] = True
    else:
        print_warning("GOOGLE_CLIENT_SECRET: Not set")
        results['secret'] = False
    
    redirect_ok, redirect_uri = check_optional_env("GOOGLE_REDIRECT_URI", "Google OAuth Redirect URI")
    if redirect_ok:
        print_success(f"GOOGLE_REDIRECT_URI: {redirect_uri}")
        results['redirect'] = True
    else:
        print_warning("GOOGLE_REDIRECT_URI: Not set (using default: http://localhost:8000/api/gcp/oauth2callback)")
        results['redirect'] = False
    
    return results

def validate_oci_config() -> Dict[str, bool]:
    """Validate OCI configuration"""
    print_header("OCI Configuration")

    results = {}
    enabled_ok, enabled_val = check_optional_env("OCI_ENABLED", "OCI feature flag")
    oci_enabled = enabled_ok and enabled_val.lower() in ("1", "true", "yes", "on")
    if oci_enabled:
        print_success("OCI_ENABLED: true")
    else:
        print_warning("OCI_ENABLED: Not enabled")
    results["enabled"] = oci_enabled

    tenancy_keys_ok, tenancy_keys = check_optional_env("OCI_TENANCY_KEYS", "OCI tenancy keys")
    parsed_keys = [item.strip() for item in tenancy_keys.split(",") if item.strip()] if tenancy_keys_ok else []
    if parsed_keys:
        print_success(f"OCI_TENANCY_KEYS: {', '.join(parsed_keys)}")
        results["tenancy_keys"] = True
    else:
        print_warning("OCI_TENANCY_KEYS: Not set")
        results["tenancy_keys"] = False

    valid_tenancies = 0
    for raw_key in parsed_keys:
        prefix = f"OCI_{raw_key.upper().replace('-', '_')}"
        print_info(f"Checking tenancy config for {raw_key}")
        required_suffixes = [
            "TENANCY_OCID",
            "USER_OCID",
            "FINGERPRINT",
            "REGION",
        ]
        required_ok = True
        for suffix in required_suffixes:
            ok, value = check_optional_env(f"{prefix}_{suffix}", f"{raw_key} {suffix}")
            if ok:
                print_success(f"{prefix}_{suffix}: {value}")
            else:
                print_warning(f"{prefix}_{suffix}: Not set")
                required_ok = False

        private_key_ok, _ = check_optional_env(f"{prefix}_PRIVATE_KEY", f"{raw_key} private key")
        private_key_b64_ok, _ = check_optional_env(f"{prefix}_PRIVATE_KEY_B64", f"{raw_key} base64 private key")
        if private_key_ok or private_key_b64_ok:
            print_success(f"{prefix}_PRIVATE_KEY / PRIVATE_KEY_B64: Set")
        else:
            print_warning(f"{prefix}_PRIVATE_KEY / PRIVATE_KEY_B64: Not set")
            required_ok = False

        image_comp_ok, image_comp = check_optional_env(f"{prefix}_IMAGE_COMPARTMENT_OCID", f"{raw_key} image compartment")
        if image_comp_ok:
            print_success(f"{prefix}_IMAGE_COMPARTMENT_OCID: {image_comp}")
        else:
            print_warning(f"{prefix}_IMAGE_COMPARTMENT_OCID: Not set (will fall back to the tenancy root compartment)")

        if required_ok:
            valid_tenancies += 1

    results["valid_tenancies"] = valid_tenancies > 0
    return results

def print_recommendations(azure_results: Dict, gcp_wif_results: Dict, google_oauth_results: Dict, oci_results: Dict):
    """Print recommendations based on configuration"""
    print_header("Configuration Summary & Recommendations")
    
    # Check Azure AD
    azure_complete = all(azure_results.get(k, False) for k in ['tenant', 'client', 'secret'])
    
    if azure_complete:
        print_success("Azure AD configuration is complete")
        print_info("Users can login with Azure AD and access Azure resources")
    else:
        print_error("Azure AD configuration is incomplete")
        print_info("Required environment variables: AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET")
        print_info("Users will not be able to login")
    
    print()
    
    # Check GCP WIF
    gcp_wif_complete = all([
        gcp_wif_results.get('project', False),
        gcp_wif_results.get('pool', False),
        gcp_wif_results.get('provider', False)
    ])
    
    if gcp_wif_complete:
        print_success("GCP Workload Identity Federation is configured")
        print_info("Users with Azure AD can access GCP via WIF (single sign-on)")
        print_warning("Note: GCP WIF must be configured in GCP Console to accept Azure AD tokens")
        print_info("See SSO_CROSS_CLOUD_SETUP.md for GCP configuration steps")
    else:
        print_warning("GCP Workload Identity Federation is not configured")
        print_info("Users will need to use Google OAuth for GCP access (separate login)")
    
    print()
    
    # Check Google OAuth
    google_oauth_complete = all([
        google_oauth_results.get('client', False),
        google_oauth_results.get('secret', False)
    ])
    
    if google_oauth_complete:
        print_success("Google OAuth is configured")
        print_info("Users can login with Google for GCP access (fallback option)")
    elif not gcp_wif_complete:
        print_warning("Neither GCP WIF nor Google OAuth is fully configured")
        print_error("Users will not be able to access GCP resources")
        print_info("Configure one of the following:")
        print_info("  1. GCP Workload Identity Federation (recommended for SSO)")
        print_info("  2. Google OAuth (quick setup, requires separate login)")

    print()

    if oci_results.get("enabled"):
        if oci_results.get("tenancy_keys") and oci_results.get("valid_tenancies"):
            print_success("OCI is enabled and at least one root tenancy is configured")
            print_info("Users can select OCI, choose a configured root tenancy, then deploy to available subcompartments.")
        else:
            print_warning("OCI is enabled but the tenancy configuration is incomplete")
            print_info("Set OCI_TENANCY_KEYS and the per-tenancy OCI_* environment variables before enabling production OCI access.")
    else:
        print_info("OCI is currently disabled")

    print()
    
    # Overall recommendation
    print_header("Next Steps")
    
    if azure_complete:
        if gcp_wif_complete:
            print_info("Configuration: Azure AD + GCP WIF (True SSO)")
            print_info("✓ Complete GCP WIF setup in GCP Console (see SSO_CROSS_CLOUD_SETUP.md)")
            print_info("✓ Start the application: docker-compose up --build")
        elif google_oauth_complete:
            print_info("Configuration: Azure AD + Google OAuth (Separate logins)")
            print_info("✓ Start the application: docker-compose up --build")
            print_info("✓ Users will login with Azure AD for Azure, Google for GCP")
        else:
            print_warning("GCP access not configured")
            print_info("Choose one:")
            print_info("  Option 1: Configure GCP WIF (see SSO_CROSS_CLOUD_SETUP.md)")
            print_info("  Option 2: Configure Google OAuth (see OAUTH_SETUP_GUIDE.md)")
    else:
        print_error("Azure AD configuration incomplete - application will not work")
        print_info("1. Set required Azure AD environment variables")
        print_info("2. Re-run this script to validate")
        print_info("3. See SETUP_GUIDE.md for detailed instructions")

def main():
    """Main validation function"""
    print(f"\n{Colors.BOLD}Multi-Cloud Portal Configuration Validator{Colors.END}")
    print("This script checks your environment configuration\n")
    
    # Validate configurations
    azure_results = validate_azure_ad_config()
    gcp_wif_results = validate_gcp_wif_config()
    google_oauth_results = validate_google_oauth_config()
    oci_results = validate_oci_config()
    
    # Print recommendations
    print_recommendations(azure_results, gcp_wif_results, google_oauth_results, oci_results)
    
    # Exit code based on essential configuration
    azure_complete = all(azure_results.get(k, False) for k in ['tenant', 'client', 'secret'])
    
    if not azure_complete:
        print(f"\n{Colors.RED}Configuration validation FAILED{Colors.END}")
        print("Azure AD configuration is required for the application to work\n")
        sys.exit(1)
    
    print(f"\n{Colors.GREEN}Configuration validation PASSED{Colors.END}")
    print("Essential configuration is present. See recommendations above for optional features.\n")
    sys.exit(0)

if __name__ == "__main__":
    main()
