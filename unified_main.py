from fastapi import FastAPI, HTTPException, Form, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import json
import os
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
from azure.identity import ClientSecretCredential
from azure.mgmt.resource import SubscriptionClient, ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.compute import ComputeManagementClient
import logging

AMI_MAP = {
    "RHEL8.10-AWS-ISD": "ami-0f6931f6e7509df92",
    "RHEL9.6-AWS-ISD": "ami-082e2c722b8c50965",
    "ISD-Win2k19-Image": "ami-068a39310845aa93e",
    "ISD-Win2K22-Image": "ami-03bc70cc76785d5dc"
}

AZURE_SHARED_IMAGE_SUBSCRIPTION_ID = "ef41a7a7-df63-46b8-83ec-a397b194a107"
AZURE_SHARED_IMAGE_RESOURCE_GROUP = "ISD-eCloud"
AZURE_SHARED_IMAGE_GALLERY = "eCloud_Images"
AZURE_SHARED_IMAGES = [
    {"name": "linux_rhel86", "label": "Linux RHEL 8.6", "os_type": "Linux"},
    {"name": "Win2K19-Wholesale", "label": "Windows Server 2019", "os_type": "Windows"},
    {"name": "Win2K22-Wholesale", "label": "Windows Server 2022", "os_type": "Windows"},
]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_index():
    return FileResponse("../frontend/static/unified_index.html")

# ---------- AWS Endpoints ----------
class DeployRequest(BaseModel):
    cloud: str
    account: str
    vpc_id: str
    subnet_id: str
    security_group: str
    vm_name: str
    ami_name: str
    instance_type: str
    key_pair_name: str
    os_type: str

@app.get("/accounts/aws")
async def get_aws_accounts():
    return {
        "accounts": [
            {"account_id": "600198011871"},
            {"account_id": "932757390505"},
            {"account_id": "792294445508"},
            {"account_id": "919672611458"},
            {"account_id": "443914036196"},
            {"account_id": "332070355516"},
            {"account_id": "761763126862"},
            {"account_id": "280928810037"},
            {"account_id": "533267447517"},
            {"account_id": "011528284338"},
            {"account_id": "017820666232"},
            {"account_id": "017820666235"},
            {"account_id": "058264242063"},
            {"account_id": "533266964199"},
            {"account_id": "339713154018"},
            {"account_id": "476553995083"}
        ]
    }

def assume_role(account_id: str):
    if account_id == "600198011871":
        return boto3.Session()
    role_arn = f"arn:aws:iam::{account_id}:role/MultiCloudAccessRole"
    sts_client = boto3.client("sts")
    try:
        response = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName="multicloud-session"
        )
        creds = response['Credentials']
        return boto3.Session(
            aws_access_key_id=creds['AccessKeyId'],
            aws_secret_access_key=creds['SecretAccessKey'],
            aws_session_token=creds['SessionToken']
        )
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"STS AssumeRole failed: {str(e)}")

@app.get("/vpcs/aws")
async def get_aws_vpcs(account: str):
    session = assume_role(account)
    ec2 = session.client("ec2")
    try:
        vpcs = ec2.describe_vpcs()["Vpcs"]
        return {"vpcs": [{"vpc_id": v["VpcId"], "cidr_block": v.get("CidrBlock", "")} for v in vpcs]}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"AWS Error: {str(e)}")

@app.get("/subnets/aws")
async def get_aws_subnets(vpc_id: str, account: str):
    session = assume_role(account)
    ec2 = session.client("ec2")
    try:
        subnets = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])["Subnets"]
        return {"subnets": [{"subnet_id": sn["SubnetId"], "cidr_block": sn["CidrBlock"]} for sn in subnets]}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"AWS Error: {str(e)}")

@app.get("/security-groups/aws")
async def get_aws_security_groups(vpc_id: str, account: str):
    session = assume_role(account)
    ec2 = session.client("ec2")
    try:
        groups = ec2.describe_security_groups(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])["SecurityGroups"]
        return {"security_groups": [{"group_id": sg["GroupId"], "group_name": sg["GroupName"]} for sg in groups]}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"AWS Error: {str(e)}")

@app.get("/amis/aws")
async def get_shared_amis(account: str):
    session = assume_role(account)
    ec2 = session.client("ec2")
    try:
        images = ec2.describe_images(Owners=["476553995083"])["Images"]
        sorted_images = sorted(images, key=lambda x: x.get("CreationDate", ""), reverse=True)
        return {
            "amis": [
                {
                    "ami_id": img["ImageId"],
                    "name": img.get("Name", img["ImageId"])
                }
                for img in sorted_images
            ]
        }
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"AMI fetch error: {str(e)}")

@app.get("/instance-types/aws")
async def get_aws_instance_types(account: str):
    session = assume_role(account)
    ec2 = session.client("ec2")
    try:
        paginator = ec2.get_paginator('describe_instance_types')
        instance_types = []
        for page in paginator.paginate():
            instance_types.extend(page['InstanceTypes'])
        types = sorted([it['InstanceType'] for it in instance_types])
        return {"instance_types": types}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"AWS Error fetching instance types: {str(e)}")

@app.post("/create-keypair/aws")
async def create_key_pair(account: str = Query(...)):
    session = assume_role(account)
    ec2 = session.client("ec2")
    key_name = f"auto-key-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    try:
        key_pair = ec2.create_key_pair(KeyName=key_name)
        return {
            "key_pair_name": key_name,
            "message": "Key pair created.",
            "private_key": key_pair['KeyMaterial']
        }
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Key pair error: {str(e)}")

@app.post("/deploy")
async def deploy_vm_form(
    cloud: str = Form(...),
    account: str = Form(...),
    vpc_id: str = Form(...),
    subnet_id: str = Form(...),
    security_group: str = Form(...),
    vm_name: str = Form(...),
    ami_name: str = Form(...),
    os_type: str = Form(...),
    instance_type: str = Form(...),
    key_pair_name: str = Form(...),
):
    unique_vm_name = f"{vm_name}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    return run_terraform(cloud, account, vpc_id, subnet_id, security_group, unique_vm_name, ami_name, os_type, instance_type, key_pair_name)

@app.post("/api/deploy")
async def deploy_vm_json(req: DeployRequest):
    unique_vm_name = f"{req.vm_name}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    return run_terraform(req.cloud, req.account, req.vpc_id, req.subnet_id, req.security_group, unique_vm_name, req.ami_name, req.os_type, req.instance_type, req.key_pair_name)

def run_terraform(cloud, account, vpc_id, subnet_id, security_group, vm_name, ami_name, os_type, instance_type, key_pair_name):
    module_path = f"../terraform/{cloud.lower()}"
    if not os.path.isdir(module_path):
        raise HTTPException(status_code=400, detail=f"No module found for cloud: {cloud}")

    env = os.environ.copy()

    if account != "600198011871":
        session = assume_role(account)
        creds = session.get_credentials().get_frozen_credentials()
        env["AWS_ACCESS_KEY_ID"] = creds.access_key
        env["AWS_SECRET_ACCESS_KEY"] = creds.secret_key
        env["AWS_SESSION_TOKEN"] = creds.token

    ami_id = AMI_MAP.get(ami_name)
    if not ami_id:
        raise HTTPException(status_code=400, detail=f"Invalid AMI name: {ami_name}")

    env["TF_VAR_account"] = account
    env["TF_VAR_vpc_id"] = vpc_id
    env["TF_VAR_subnet_id"] = subnet_id
    env["TF_VAR_vm_name"] = vm_name
    env["TF_VAR_ami_id"] = ami_id
    env["TF_VAR_os_type"] = os_type
    env["TF_VAR_instance_type"] = instance_type
    env["TF_VAR_key_pair_name"] = key_pair_name
    env["TF_VAR_security_group_ids"] = json.dumps([security_group])
    env["TF_VAR_region"] = "us-west-2"

    try:
        subprocess.run(
            ["terraform", "init"],
            cwd=module_path,
            check=True,
            env=env,
            capture_output=True,
            text=True
        )
        subprocess.run(
            ["terraform", "apply", "-auto-approve"],
            cwd=module_path,
            check=True,
            env=env,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        raise HTTPException(status_code=500, detail=f"Terraform error: {error_msg}")

    return {
        "status": "success",
        "cloud": cloud,
        "vm_name": vm_name,
        "account": account,
        "vpc_id": vpc_id,
        "subnet_id": subnet_id,
        "security_group": security_group,
        "os_type": os_type,
        "instance_type": instance_type,
        "key_pair_name": key_pair_name,
    }

# ---------- Azure Endpoints ----------
TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")

def get_azure_credentials():
    if not (TENANT_ID and CLIENT_ID and CLIENT_SECRET):
        raise RuntimeError("Azure credentials not set in environment variables.")
    return ClientSecretCredential(TENANT_ID, CLIENT_ID, CLIENT_SECRET)

@app.get("/api/azure/subscriptions")
def list_subscriptions():
    client = SubscriptionClient(get_azure_credentials())
    return [{"id": s.subscription_id, "name": s.display_name} for s in client.subscriptions.list()]

@app.get("/api/azure/resource-groups")
def list_resource_groups(subscription_id: str = Query(...)):
    client = ResourceManagementClient(get_azure_credentials(), subscription_id)
    groups = client.resource_groups.list()
    return [{"id": g.id, "name": g.name, "location": g.location} for g in groups]

@app.get("/api/azure/vnets")
def list_vnets(subscription_id: str = Query(...)):
    client = NetworkManagementClient(get_azure_credentials(), subscription_id)
    vnets = client.virtual_networks.list_all()
    return [
        {
            "id": vnet.id,
            "name": vnet.name,
            "resource_group": vnet.id.split("/")[4],
            "location": vnet.location,
        }
        for vnet in vnets
    ]

@app.get("/api/azure/nsgs")
def list_nsgs(subscription_id: str, resource_group: str):
    client = NetworkManagementClient(get_azure_credentials(), subscription_id)
    nsgs = client.network_security_groups.list(resource_group)
    return [{"id": nsg.id, "name": nsg.name} for nsg in nsgs]

@app.get("/api/azure/subnets")
def list_subnets(subscription_id: str, resource_group: str, vnet_name: str):
    client = NetworkManagementClient(get_azure_credentials(), subscription_id)
    subnets = client.subnets.list(resource_group, vnet_name)
    return [{"id": s.id, "name": s.name, "address_prefix": s.address_prefix} for s in subnets]

@app.get("/api/azure/vm-sizes")
def list_vm_sizes(subscription_id: str, location: str):
    compute_client = ComputeManagementClient(get_azure_credentials(), subscription_id)
    sizes = compute_client.virtual_machine_sizes.list(location)
    return [{"name": s.name, "numberOfCores": s.number_of_cores, "memoryInMB": s.memory_in_mb} for s in sizes]

@app.get("/api/azure/image-definitions")
def list_image_definitions():
    return [
        {
            "name": img["name"],
            "label": img["label"],
            "gallery": AZURE_SHARED_IMAGE_GALLERY,
            "subscription_id": AZURE_SHARED_IMAGE_SUBSCRIPTION_ID,
            "resource_group": AZURE_SHARED_IMAGE_RESOURCE_GROUP,
            "os_type": img["os_type"]
        } for img in AZURE_SHARED_IMAGES
    ]

@app.get("/api/azure/image-versions")
def list_image_versions(
    subscription_id: str = Query(...),
    resource_group: str = Query(...),
    gallery_name: str = Query(...),
    image_definition_name: str = Query(...),
):
    try:
        credentials = get_azure_credentials()
        compute_client = ComputeManagementClient(credentials, subscription_id)
        versions = compute_client.gallery_image_versions.list_by_gallery_image(
            resource_group, gallery_name, image_definition_name
        )
        return [{"name": v.name, "location": v.location} for v in versions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not list image versions: {e}")

@app.post("/api/azure/deploy-vm")
async def deploy_vm_azure(request: Request):
    data = await request.json()
    required_keys = ["subscription_id", "resource_group", "vnet_name", "subnet_id",
                     "gallery_name", "image_name", "vm_size", "location", "vm_name", "admin_username"]

    for key in required_keys:
        if not data.get(key):
            raise HTTPException(status_code=400, detail=f"Missing field: {key}")

    subscription_id = data["subscription_id"]
    credentials = get_azure_credentials()
    compute_client = ComputeManagementClient(credentials, subscription_id)
    network_client = NetworkManagementClient(credentials, subscription_id)

    nic_name = f"{data['vm_name']}-nic"
    ip_config = {
        "name": "ipconfig1",
        "subnet": {"id": data["subnet_id"]},
    }
    # NSG must be set on the NIC itself (top-level), not inside ip_configurations.
    # Azure ARM silently ignores "network_security_group" inside an ip_configuration entry.
    nic_params = {
        "location": data["location"],
        "ip_configurations": [ip_config],
        "enable_accelerated_networking": data.get("accelerated_networking", False)
    }
    if data.get("nsg_id"):
        nic_params["network_security_group"] = {"id": data["nsg_id"]}

    try:
        nic = network_client.network_interfaces.begin_create_or_update(
            data["resource_group"], nic_name, nic_params).result()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NIC creation failed: {e}")

    image_version = data.get("image_version")
    if not image_version:
        versions = compute_client.gallery_image_versions.list(
            data["image_resource_group"], data["gallery_name"], data["image_name"]
        )
        sorted_versions = sorted(versions, key=lambda v: v.name, reverse=True)
        if not sorted_versions:
            raise HTTPException(status_code=404, detail="No image versions found.")
        image_version = sorted_versions[0].name

    image_info = next((i for i in AZURE_SHARED_IMAGES if i["name"] == data["image_name"]), None)
    if not image_info:
        raise HTTPException(status_code=404, detail="Image definition not found.")

    os_profile = {
        "computer_name": data["vm_name"],
        "admin_username": data["admin_username"],
    }

    if image_info["os_type"] == "Linux":
        os_profile["linux_configuration"] = {
            "disable_password_authentication": True,
            "ssh": {
                "public_keys": [{
                    "path": f"/home/{data['admin_username']}/.ssh/authorized_keys",
                    "key_data": data.get("ssh_public_key", "")
                }]
            }
        }
    else:
        os_profile["admin_password"] = data["admin_password"]

    vm_params = {
        "location": data["location"],
        "zones": [data["availability_zone"]] if data.get("availability_zone") else None,
        "hardware_profile": {"vm_size": data["vm_size"]},
        "storage_profile": {
            "image_reference": {
                "id": f"/subscriptions/{data['image_subscription_id']}/resourceGroups/{data['image_resource_group']}/providers/Microsoft.Compute/galleries/{data['gallery_name']}/images/{data['image_name']}/versions/{image_version}"
            }
        },
        "os_profile": os_profile,
        "network_profile": {
            "network_interfaces": [{"id": nic.id}]
        }
    }

    try:
        vm_create = compute_client.virtual_machines.begin_create_or_update(
            data["resource_group"], data["vm_name"], vm_params)
        vm_result = vm_create.result()
        return {"status": "success", "vm_id": vm_result.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VM creation failed: {e}")
