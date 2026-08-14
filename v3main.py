from fastapi import FastAPI, HTTPException, Form, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import subprocess
import json
import os
import boto3
from botocore.exceptions import ClientError
from datetime import datetime

AMI_MAP = {
    "RHEL8.10-AWS-ISD": "ami-0f6931f6e7509df92",
    "RHEL9.6-AWS-ISD": "ami-082e2c722b8c50965",
    "ISD-Win2k19-Image": "ami-068a39310845aa93e",
    "ISD-Win2K22-Image": "ami-03bc70cc76785d5dc"
}

app = FastAPI()
app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("../frontend/index.html")

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
        # Returning private key material for download (do NOT save on disk for security)
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

    # If assuming role, update env with credentials
    if account != "600198011871":
        session = assume_role(account)
        creds = session.get_credentials().get_frozen_credentials()
        env["AWS_ACCESS_KEY_ID"] = creds.access_key
        env["AWS_SECRET_ACCESS_KEY"] = creds.secret_key
        env["AWS_SESSION_TOKEN"] = creds.token

    # Lookup AMI ID from map
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
    env["TF_VAR_region"] = "us-west-2"  # Consider making configurable

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
