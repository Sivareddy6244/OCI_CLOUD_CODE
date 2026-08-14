terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.3"
    }
  }
}

provider "aws" {
  region = var.region
}

resource "aws_instance" "vm" {
  for_each = var.vms
  ami                    = each.value.ami_id
  instance_type          = each.value.instance_type
  subnet_id              = each.value.subnet_id
  vpc_security_group_ids = each.value.security_group_ids
  key_name               = each.value.key_pair_name != "" ? each.value.key_pair_name : null
  user_data_base64       = each.value.user_data_base64 != "" ? each.value.user_data_base64 : null

  tags = merge(
    {
      Name       = each.value.vm_name
      DeployedBy = "MultiCloudPortal"
      Account    = each.value.account
    },
    each.value.tags
  )
}