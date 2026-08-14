import requests

url = "http://127.0.0.1:8000/deploy"
data = {
    "cloud": "aws",
    "vm_name": "fastapi-vm-001",
    "cpu": 1,
    "memory": 1
}

response = requests.post(url, data=data)
print(response.json())