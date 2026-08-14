terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Provider uses OAuth token from environment variable GOOGLE_OAUTH_ACCESS_TOKEN
# This is set by the backend when running Terraform
# The token is validated before Terraform execution
provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}

resource "google_compute_instance" "vm" {
  for_each = var.vms
  
  name         = each.value.vm_name
  machine_type = each.value.machine_type
  zone         = each.value.zone
  project      = each.value.project

  boot_disk {
    initialize_params {
      image = each.value.image
      size  = each.value.disk_size
      type  = lookup(each.value, "disk_type", "pd-balanced")
    }
  }

  network_interface {
    # Use subnetwork only (preferred in GCP)
    # Subnetwork reference includes the network implicitly
    subnetwork = each.value.subnetwork
    
    # Conditional external IP assignment based on user preference
    # The dynamic block creates an access_config block only if external_ip is true
    # Using [1] as a single-item list to iterate once when condition is met
    dynamic "access_config" {
      for_each = lookup(each.value, "external_ip", true) ? [1] : []
      content {
        # Ephemeral public IP - no configuration needed
        # GCP automatically assigns an ephemeral IP when access_config block exists
      }
    }
  }

  metadata = {
    "DeployedBy" = "MultiCloudPortal"
  }
  
  labels = merge(
    {
      "deployedby" = "multicloudportal"
    },
    each.value.labels
  )
}
