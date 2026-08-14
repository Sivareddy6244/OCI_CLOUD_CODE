variable "ami_id" {
  description = "The AMI ID to use for the instance"
  type        = string
}

variable "instance_type" {
  description = "Instance type"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID"
  type        = string
}

variable "security_group_ids" {
  description = "List of security group IDs"
  type        = list(string)
}

variable "key_pair_name" {
  description = "Name of the key pair"
  type        = string
}

variable "vm_name" {
  description = "Name tag for the VM"
  type        = string
}

variable "account" {
  description = "Account ID"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

# ✅ ADD THIS: Custom tags variable
variable "custom_tags" {
  description = "Custom tags to apply to the VM (AccountNumber, Approvers, PS)"
  type        = map(string)
  default     = {}
}
