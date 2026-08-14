from fastapi import FastAPI, HTTPException, Form
from pydantic import BaseModel
import subprocess
import os
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Serve frontend files statically
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

@app.get("/", response_class=FileResponse)
async def serve_index():
    return FileResponse("../frontend/index.html")

class DeployRequest(BaseModel):
    cloud: str
    vm_name: str
    cpu: int
    memory: int

@app.post("/deploy")
async def deploy_vm_form(
    cloud: str = Form(...),
    vm_name: str = Form(...),
    cpu: int = Form(...),
    memory: int = Form(...)
):
    return run_terraform(cloud, vm_name, cpu, memory)

@app.post("/api/deploy")
async def deploy_vm_json(req: DeployRequest):
    return run_terraform(req.cloud, req.vm_name, req.cpu, req.memory)

def run_terraform(cloud, vm_name, cpu, memory):
    module_path = f"../terraform/{cloud.lower()}"
    if not os.path.isdir(module_path):
        raise HTTPException(status_code=400, detail=f"No module found for cloud: {cloud}")

    env = os.environ.copy()
    env["TF_VAR_vm_name"] = vm_name
    env["TF_VAR_cpu"] = str(cpu)
    env["TF_VAR_memory"] = str(memory)

    try:
        subprocess.run(["terraform", "init"], cwd=module_path, check=True, env=env)
        subprocess.run(["terraform", "apply", "-auto-approve"], cwd=module_path, check=True, env=env)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Terraform error: {e.stderr or str(e)}")

    return {
        "status": "success",
        "cloud": cloud,
        "vm_name": vm_name
    }
