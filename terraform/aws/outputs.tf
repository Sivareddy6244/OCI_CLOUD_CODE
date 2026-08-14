output "instance_public_ips" {
  description = "Public IPs of all instances"
  value = { for k, vm in aws_instance.vm : k => vm.public_ip }
}