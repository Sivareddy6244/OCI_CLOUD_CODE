#!/bin/bash
# Cleanup script for GCP deployment issues

echo "================================================"
echo "GCP VM Deployment - Cleanup and Fresh Start"
echo "================================================"
echo ""

echo "This script will:"
echo "1. Stop running Docker containers"
echo "2. Remove old VM state files"
echo "3. Clean Terraform state"
echo "4. Rebuild Docker images from scratch"
echo "5. Start the application"
echo ""

read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "Step 1: Stopping Docker containers..."
docker-compose down

echo ""
echo "Step 2: Removing old VM state files..."
if [ -f "backend/gcp_vms.json" ]; then
    echo "  - Backing up gcp_vms.json to gcp_vms.json.bak"
    mv backend/gcp_vms.json backend/gcp_vms.json.bak
fi

if [ -f "backend/aws_vms.json" ]; then
    echo "  - Backing up aws_vms.json to aws_vms.json.bak"
    mv backend/aws_vms.json backend/aws_vms.json.bak
fi

echo ""
echo "Step 3: Cleaning Terraform state..."
if [ -d "terraform/gcp/.terraform" ]; then
    echo "  - Removing .terraform directory"
    rm -rf terraform/gcp/.terraform
fi

if [ -f "terraform/gcp/terraform.tfstate" ]; then
    echo "  - Backing up terraform.tfstate to terraform.tfstate.bak"
    mv terraform/gcp/terraform.tfstate terraform/gcp/terraform.tfstate.bak
fi

if [ -f "terraform/gcp/terraform.tfstate.backup" ]; then
    echo "  - Removing terraform.tfstate.backup"
    rm terraform/gcp/terraform.tfstate.backup
fi

if [ -f "terraform/gcp/.terraform.lock.hcl" ]; then
    echo "  - Removing .terraform.lock.hcl"
    rm terraform/gcp/.terraform.lock.hcl
fi

echo ""
echo "Step 4: Rebuilding Docker images (no cache)..."
docker-compose build --no-cache

echo ""
echo "Step 5: Starting the application..."
docker-compose up -d

echo ""
echo "================================================"
echo "Cleanup Complete!"
echo "================================================"
echo ""
echo "✅ The application is now running with fresh state"
echo "✅ Old state files backed up with .bak extension"
echo ""
echo "Access the application at: http://localhost:8000"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f app"
echo ""
echo "To stop:"
echo "  docker-compose down"
echo ""
