from fastapi import APIRouter, Request
from user_access import E_CLOUD_ADMINS

import requests  # For Azure API calls
import boto3     # For AWS API calls

router = APIRouter()

def get_email_from_request(request: Request):
    user = request.session.get("user")
    return user.get("email") if user else None

# ======================== AZURE ========================
def get_all_azure_subscriptions():
    # Use a privileged service principal/token to list all
    # Replace below with your actual method
    token = "ADMIN_AZURE_TOKEN"
    url = "https://management.azure.com/subscriptions?api-version=2020-01-01"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)
    return resp.json()

def get_user_azure_subscriptions(user_token):
    url = "https://management.azure.com/subscriptions?api-version=2020-01-01"
    headers = {"Authorization": f"Bearer {user_token}"}
    resp = requests.get(url, headers=headers)
    return resp.json()

@router.get("/subscriptions/azure")
async def azure_subscriptions(request: Request):
    email = get_email_from_request(request)
    if email in E_CLOUD_ADMINS:
        return get_all_azure_subscriptions()
    # You must have user's Azure OAuth token in session
    user_token = request.session.get("azure_token")
    if not user_token:
        return {"subscriptions": []}
    return get_user_azure_subscriptions(user_token)

# ======================== AWS ========================
def get_all_aws_accounts():
    # Use privileged admin credentials (IAM role)
    org_client = boto3.client('organizations')
    accounts = org_client.list_accounts()['Accounts']
    return {"accounts": [{"account_id": a["Id"], "name": a["Name"]} for a in accounts]}

def get_user_aws_accounts(aws_access_key, aws_secret_key, aws_session_token=None):
    # Use user's AWS credentials (from SSO or federated login)
    session = boto3.Session(
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key,
        aws_session_token=aws_session_token
    )
    org_client = session.client('organizations')
    try:
        accounts = org_client.list_accounts()['Accounts']
        return {"accounts": [{"account_id": a["Id"], "name": a["Name"]} for a in accounts]}
    except Exception:
        # If user cannot access org, fallback to their STS identity
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        return {"accounts": [{"account_id": identity["Account"], "name": "Your AWS Account"}]}

@router.get("/accounts/aws")
async def aws_accounts(request: Request):
    email = get_email_from_request(request)
    if email in E_CLOUD_ADMINS:
        return get_all_aws_accounts()
    aws_access_key = request.session.get("aws_access_key")
    aws_secret_key = request.session.get("aws_secret_key")
    aws_session_token = request.session.get("aws_session_token")
    if not aws_access_key or not aws_secret_key:
        return {"accounts": []}
    return get_user_aws_accounts(aws_access_key, aws_secret_key, aws_session_token)

# ======================= GCP (Sample) =======================
def get_user_gcp_projects(gcp_token):
    url = "https://cloudresourcemanager.googleapis.com/v1/projects"
    headers = {"Authorization": f"Bearer {gcp_token}"}
    resp = requests.get(url, headers=headers)
    return resp.json()

@router.get("/projects/gcp")
async def gcp_projects(request: Request):
    email = get_email_from_request(request)
    if email in E_CLOUD_ADMINS:
        # TODO: Implement admin GCP listing if needed
        return {"projects": []}
    gcp_token = request.session.get("gcp_token")
    if not gcp_token:
        return {"projects": []}
    return get_user_gcp_projects(gcp_token)
