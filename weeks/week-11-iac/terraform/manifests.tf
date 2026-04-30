locals {
  namespace_manifest = yamlencode({
    apiVersion = "v1"
    kind       = "Namespace"
    metadata = {
      name   = local.namespace
      labels = local.common_labels
    }
  })

  app_pv_manifest = "${yamlencode({
    apiVersion = "v1"
    kind       = "PersistentVolume"
    metadata = {
      name   = local.app_pv_name
      labels = local.common_labels
    }
    spec = {
      capacity = {
        storage = var.app_storage_size
      }
      accessModes                   = ["ReadWriteOnce"]
      storageClassName              = var.app_storage_class
      persistentVolumeReclaimPolicy = "Retain"
      hostPath = {
        path = var.app_pv_host_path
      }
    }
  })}\n"

  app_pvc_manifest = "${yamlencode({
    apiVersion = "v1"
    kind       = "PersistentVolumeClaim"
    metadata = {
      name      = "app-data-pvc"
      namespace = local.namespace
      labels    = local.simple_app_labels
    }
    spec = {
      accessModes      = ["ReadWriteOnce"]
      storageClassName = var.app_storage_class
      volumeName       = local.app_pv_name
      resources = {
        requests = {
          storage = var.app_storage_size
        }
      }
    }
  })}\n"

  redis_manifest_bundle = "${join("\n---\n", [
    yamlencode({
      apiVersion = "v1"
      kind       = "Service"
      metadata = {
        name      = "redis-headless"
        namespace = local.namespace
        labels    = local.redis_labels
      }
      spec = {
        clusterIP = "None"
        selector  = local.redis_labels
        ports = [{
          name       = "redis"
          port       = 6379
          targetPort = 6379
        }]
      }
    }),
    yamlencode({
      apiVersion = "v1"
      kind       = "Service"
      metadata = {
        name      = "redis"
        namespace = local.namespace
        labels    = local.redis_labels
      }
      spec = {
        type     = "ClusterIP"
        selector = local.redis_labels
        ports = [{
          name       = "redis"
          port       = 6379
          targetPort = 6379
        }]
      }
    }),
    yamlencode({
      apiVersion = "apps/v1"
      kind       = "StatefulSet"
      metadata = {
        name      = "redis"
        namespace = local.namespace
        labels    = local.redis_labels
      }
      spec = {
        serviceName = "redis-headless"
        replicas    = var.redis_replicas
        selector = {
          matchLabels = local.redis_labels
        }
        template = {
          metadata = {
            labels = local.redis_labels
          }
          spec = {
            containers = [{
              name            = "redis"
              image           = var.redis_image
              imagePullPolicy = var.image_pull_policy
              args            = ["redis-server", "--appendonly", "yes"]
              ports = [{
                name          = "redis"
                containerPort = 6379
              }]
              readinessProbe = local.redis_readiness_probe
              livenessProbe  = local.redis_liveness_probe
              resources      = local.redis_resources
              volumeMounts = [{
                name      = "redis-data"
                mountPath = "/data"
              }]
            }]
          }
        }
        volumeClaimTemplates = [{
          metadata = {
            name   = "redis-data"
            labels = local.redis_labels
          }
          spec = {
            accessModes = ["ReadWriteOnce"]
            resources = {
              requests = {
                storage = var.redis_storage_size
              }
            }
          }
        }]
      }
    }),
  ])}\n"

  simple_app_manifest_bundle = "${join("\n---\n", [
    yamlencode({
      apiVersion = "v1"
      kind       = "ConfigMap"
      metadata = {
        name      = "simple-app-config"
        namespace = local.namespace
        labels    = local.simple_app_labels
      }
      data = {
        PORT        = "5000"
        APP_MESSAGE = var.app_message
        REDIS_HOST  = "redis"
        REDIS_PORT  = "6379"
      }
    }),
    yamlencode({
      apiVersion = "v1"
      kind       = "Service"
      metadata = {
        name      = "simple-app"
        namespace = local.namespace
        labels    = local.simple_app_labels
      }
      spec = {
        type     = "ClusterIP"
        selector = local.simple_app_labels
        ports = [{
          name       = "http"
          port       = 5000
          targetPort = 5000
        }]
      }
    }),
    yamlencode({
      apiVersion = "apps/v1"
      kind       = "Deployment"
      metadata = {
        name      = "simple-app"
        namespace = local.namespace
        labels    = local.simple_app_labels
      }
      spec = {
        replicas = var.simple_app_replicas
        selector = {
          matchLabels = local.simple_app_labels
        }
        template = {
          metadata = {
            labels = local.simple_app_labels
          }
          spec = {
            initContainers = [{
              name            = "fix-app-data-permissions"
              image           = var.simple_app_image
              imagePullPolicy = var.image_pull_policy
              command = [
                "sh",
                "-c",
                "APP_UID=$(id -u app) && APP_GID=$(id -g app) && chown -R $${APP_UID}:$${APP_GID} /data && chmod 775 /data",
              ]
              securityContext = {
                runAsUser = 0
              }
              volumeMounts = [{
                name      = "app-data"
                mountPath = "/data"
              }]
            }]
            containers = [{
              name            = "simple-app"
              image           = var.simple_app_image
              imagePullPolicy = var.image_pull_policy
              ports = [{
                name          = "http"
                containerPort = 5000
              }]
              envFrom = [{
                configMapRef = {
                  name = "simple-app-config"
                }
              }]
              readinessProbe = local.simple_app_readiness_probe
              livenessProbe  = local.simple_app_liveness_probe
              resources      = local.simple_app_resources
              volumeMounts = [{
                name      = "app-data"
                mountPath = "/data"
              }]
            }]
            volumes = [{
              name = "app-data"
              persistentVolumeClaim = {
                claimName = "app-data-pvc"
              }
            }]
          }
        }
      }
    }),
  ])}\n"

  nginx_manifest_bundle = "${join("\n---\n", [
    yamlencode({
      apiVersion = "v1"
      kind       = "ConfigMap"
      metadata = {
        name      = "nginx-config"
        namespace = local.namespace
        labels    = local.nginx_labels
      }
      data = {
        "default.conf" = local.nginx_config
      }
    }),
    yamlencode({
      apiVersion = "v1"
      kind       = "Service"
      metadata = {
        name      = "nginx"
        namespace = local.namespace
        labels    = local.nginx_labels
      }
      spec = {
        type     = "NodePort"
        selector = local.nginx_labels
        ports = [{
          name       = "http"
          port       = 80
          targetPort = 80
          nodePort   = var.nginx_node_port
        }]
      }
    }),
    yamlencode({
      apiVersion = "apps/v1"
      kind       = "Deployment"
      metadata = {
        name      = "nginx"
        namespace = local.namespace
        labels    = local.nginx_labels
      }
      spec = {
        replicas = var.nginx_replicas
        selector = {
          matchLabels = local.nginx_labels
        }
        template = {
          metadata = {
            labels = local.nginx_labels
          }
          spec = {
            containers = [{
              name            = "nginx"
              image           = var.nginx_image
              imagePullPolicy = var.image_pull_policy
              ports = [{
                name          = "http"
                containerPort = 80
              }]
              readinessProbe = local.nginx_readiness_probe
              livenessProbe  = local.nginx_liveness_probe
              resources      = local.nginx_resources
              volumeMounts = [{
                name      = "nginx-config-volume"
                mountPath = "/etc/nginx/conf.d/default.conf"
                subPath   = "default.conf"
              }]
            }]
            volumes = [{
              name = "nginx-config-volume"
              configMap = {
                name = "nginx-config"
              }
            }]
          }
        }
      }
    }),
  ])}\n"
}
