variable "kubeconfig_path" {
  description = "Path to the kubeconfig file used for the local Minikube deployment."
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "Kubernetes context name used by Terraform."
  type        = string
  default     = "minikube"
}

variable "environment_name" {
  description = "Environment identifier used for names, namespaces, and labels."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.environment_name))
    error_message = "environment_name must contain only lowercase letters, digits, and hyphens."
  }
}

variable "app_message" {
  description = "Message returned by the backend root endpoint."
  type        = string
}

variable "nginx_node_port" {
  description = "NodePort used to expose nginx from Minikube."
  type        = number

  validation {
    condition     = var.nginx_node_port >= 30000 && var.nginx_node_port <= 32767
    error_message = "nginx_node_port must be within the Kubernetes NodePort range."
  }
}

variable "nginx_image" {
  description = "Image reference for the nginx frontend."
  type        = string
  default     = "nginx-gsx:latest"
}

variable "simple_app_image" {
  description = "Image reference for the simple backend application."
  type        = string
  default     = "simple-app-gsx:latest"
}

variable "redis_image" {
  description = "Image reference for Redis."
  type        = string
  default     = "redis:7-alpine"
}

variable "image_pull_policy" {
  description = "Kubernetes image pull policy for locally loaded or registry-hosted images."
  type        = string
  default     = "IfNotPresent"
}

variable "nginx_replicas" {
  description = "Replica count for nginx."
  type        = number
  default     = 1
}

variable "simple_app_replicas" {
  description = "Replica count for the backend deployment."
  type        = number
  default     = 1
}

variable "redis_replicas" {
  description = "Replica count for the Redis StatefulSet."
  type        = number
  default     = 1
}

variable "app_storage_class" {
  description = "Storage class used by the backend persistent volume and claim."
  type        = string
  default     = "manual"
}

variable "app_storage_size" {
  description = "Persistent storage size for the backend shared data volume."
  type        = string
  default     = "1Gi"
}

variable "app_pv_host_path" {
  description = "Minikube hostPath used by the backend persistent volume."
  type        = string
}

variable "redis_storage_size" {
  description = "Persistent storage size for the Redis StatefulSet."
  type        = string
  default     = "1Gi"
}
