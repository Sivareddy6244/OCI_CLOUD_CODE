variable "vms" {
  description = "Map of VM configs"
  type = map(object({
    ami_id               = string
    instance_type        = string
    subnet_id            = string
    security_group_ids   = list(string)
    key_pair_name        = optional(string, "")
    vm_name              = string
    account              = string
    tags                 = optional(map(string), {})
    user_data_base64     = optional(string, "")
  }))
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}