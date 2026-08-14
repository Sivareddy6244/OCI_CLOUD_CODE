from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from azure.identity import ClientSecretCredential
from azure.mgmt.subscription import SubscriptionClient
try:
    from azure.mgmt.resource import ResourceManagementClient
except ImportError:
    from azure.mgmt.resource.resources import ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.compute import ComputeManagementClient
import os
import logging

app = FastAPI()

app.mount("/static", StaticFiles(directory=".", html=True), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    try:
        with open("index_azure.html", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logging.error(f"Error serving UI file: {e}")
        raise HTTPException(status_code=500, detail="UI file not found or cannot be read.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")

if not (TENANT_ID and CLIENT_ID and CLIENT_SECRET):
    raise RuntimeError("Azure credentials not set in environment variables.")

def get_credentials():
    return ClientSecretCredential(TENANT_ID, CLIENT_ID, CLIENT_SECRET)

SHARED_IMAGE_SUBSCRIPTION_ID = "ef41a7a7-df63-46b8-83ec-a397b194a107"
SHARED_IMAGE_RESOURCE_GROUP = "ISD-eCloud"
SHARED_IMAGE_GALLERY = "eCloud_Images"
SHARED_IMAGES = [
    {"name": "linux_rhel86", "label": "Linux RHEL 8.6", "os_type": "Linux"},
    {"name": "Win2K19-Wholesale", "label": "Windows Server 2019", "os_type": "Windows"},
    {"name": "Win2K22-Wholesale", "label": "Windows Server 2022", "os_type": "Windows"},
]

@app.get("/api/azure/subscriptions")
def list_subscriptions():
    client = SubscriptionClient(get_credentials())
    return [{"id": s.subscription_id, "name": s.display_name} for s in client.subscriptions.list()]

@app.get("/api/azure/resource-groups")
def list_resource_groups(subscription_id: str = Query(...)):
    client = ResourceManagementClient(get_credentials(), subscription_id)
    groups = client.resource_groups.list()
    return [{"id": g.id, "name": g.name, "location": g.location} for g in groups]

@app.get("/api/azure/vnets")
def list_vnets(subscription_id: str = Query(...)):
    client = NetworkManagementClient(get_credentials(), subscription_id)
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
    client = NetworkManagementClient(get_credentials(), subscription_id)
    nsgs = client.network_security_groups.list(resource_group)
    return [{"id": nsg.id, "name": nsg.name} for nsg in nsgs]

@app.get("/api/azure/subnets")
def list_subnets(subscription_id: str, resource_group: str, vnet_name: str):
    client = NetworkManagementClient(get_credentials(), subscription_id)
    subnets = client.subnets.list(resource_group, vnet_name)
    return [{"id": s.id, "name": s.name, "address_prefix": s.address_prefix} for s in subnets]

@app.get("/api/azure/vm-sizes")
def list_vm_sizes(subscription_id: str, location: str):
    compute_client = ComputeManagementClient(get_credentials(), subscription_id)
    sizes = compute_client.virtual_machine_sizes.list(location)
    return [{"name": s.name, "numberOfCores": s.number_of_cores, "memoryInMB": s.memory_in_mb} for s in sizes]

@app.get("/api/azure/image-definitions")
def list_image_definitions():
    return [
        {
            "name": img["name"],
            "label": img["label"],
            "gallery": SHARED_IMAGE_GALLERY,
            "subscription_id": SHARED_IMAGE_SUBSCRIPTION_ID,
            "resource_group": SHARED_IMAGE_RESOURCE_GROUP,
            "os_type": img["os_type"]
        } for img in SHARED_IMAGES
    ]

@app.get("/api/azure/image-versions")
def list_image_versions(
    subscription_id: str = Query(...),
    resource_group: str = Query(...),
    gallery_name: str = Query(...),
    image_definition_name: str = Query(...),
):
    try:
        credentials = get_credentials()
        compute_client = ComputeManagementClient(credentials, subscription_id)
        versions = compute_client.gallery_image_versions.list_by_gallery_image(
            resource_group, gallery_name, image_definition_name
        )
        return [{"name": v.name, "location": v.location} for v in versions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not list image versions: {e}")

@app.post("/api/azure/deploy-vm")
async def deploy_vm(request: Request):
    data = await request.json()
    required_keys = ["subscription_id", "resource_group", "vnet_name", "subnet_id",
                     "gallery_name", "image_name", "vm_size", "location", "vm_name", "admin_username"]

    for key in required_keys:
        if not data.get(key):
            raise HTTPException(status_code=400, detail=f"Missing field: {key}")

    subscription_id = data["subscription_id"]
    credentials = get_credentials()
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

    # Get image version (use latest if not supplied)
    image_version = data.get("image_version")
    if not image_version:
        versions = compute_client.gallery_image_versions.list(
            data["image_resource_group"], data["gallery_name"], data["image_name"]
        )
        sorted_versions = sorted(versions, key=lambda v: v.name, reverse=True)
        if not sorted_versions:
            raise HTTPException(status_code=404, detail="No image versions found.")
        image_version = sorted_versions[0].name

    # Determine OS type (Linux or Windows)
    image_info = next((i for i in SHARED_IMAGES if i["name"] == data["image_name"]), None)
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
                    "key_data": data["ssh_public_key"]
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
