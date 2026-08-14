variable "gcp_project" {
  description = "GCP project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP region"
  type        = string
  default     = "us-west1"
}

variable "vms" {
  description = "Map of VM configs"
  type = map(object({
    vm_name      = string
    machine_type = string
    zone         = string
    project      = string
    image        = string
    subnetwork   = string
    disk_size    = number
    disk_type    = optional(string)
    external_ip  = optional(bool)
    labels       = optional(map(string), {})
  }))
}
