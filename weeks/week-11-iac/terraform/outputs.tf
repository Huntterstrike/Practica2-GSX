output "namespace" {
  description = "Namespace created for the selected environment."
  value       = local.namespace
}

output "nginx_node_port" {
  description = "NodePort used to expose nginx."
  value       = var.nginx_node_port
}

output "app_persistent_volume_name" {
  description = "Cluster-scoped persistent volume used by the backend."
  value       = local.app_pv_name
}

output "simple_app_image" {
  description = "Resolved backend image reference."
  value       = var.simple_app_image
}

output "nginx_image" {
  description = "Resolved nginx image reference."
  value       = var.nginx_image
}
