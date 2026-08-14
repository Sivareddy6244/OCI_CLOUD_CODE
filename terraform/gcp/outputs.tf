output "instances" {
  value = {
    for k, v in google_compute_instance.vm : k => {
      name        = v.name
      self_link   = v.self_link
      network_ip  = v.network_interface[0].network_ip
      external_ip = length(v.network_interface[0].access_config) > 0 ? v.network_interface[0].access_config[0].nat_ip : "None"
      zone        = v.zone
      tags        = v.tags
    }
  }
  description = "Map of created instances with their details"
}
