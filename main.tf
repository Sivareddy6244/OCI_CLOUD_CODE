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
  ami                    = var.ami_id
  instance_type          = var.instance_type
  subnet_id              = var.subnet_id
  vpc_security_group_ids = var.security_group_ids
  key_name               = var.key_pair_name

  # ✅ CRITICAL FIX: Merge default tags with custom tags
  tags = merge(
    {
      Name       = var.vm_name
      DeployedBy = "MultiCloudPortal"
      Account    = var.account
    },
    var.custom_tags  # ✅ This adds AccountNumber, Approvers, PS tags
  )
}

output "instance_id" {
  value = aws_instance.vm.id
}

output "instance_tags" {
  value = aws_instance.vm.tags
}
