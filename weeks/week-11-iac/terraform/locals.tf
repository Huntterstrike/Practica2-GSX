locals {
  namespace   = "green-dev-${var.environment_name}"
  app_pv_name = "green-dev-${var.environment_name}-app-data-pv"

  common_labels = {
    project     = "green-devcorp"
    managed-by  = "terraform"
    environment = var.environment_name
    week        = "11"
  }

  nginx_labels = merge(local.common_labels, {
    app = "nginx"
  })

  simple_app_labels = merge(local.common_labels, {
    app = "simple-app"
  })

  redis_labels = merge(local.common_labels, {
    app = "redis"
  })

  nginx_config = <<-EOT
    server {
        listen 80;
        server_name localhost;

        location / {
            root /usr/share/nginx/html;
            index index.html index.htm;
        }

        location /api/ {
            proxy_pass http://simple-app:5000/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        error_page 500 502 503 504 /50x.html;
        location = /50x.html {
            root /usr/share/nginx/html;
        }
    }
  EOT

  nginx_readiness_probe = {
    httpGet = {
      path = "/"
      port = 80
    }
    initialDelaySeconds = 5
    periodSeconds       = 10
    timeoutSeconds      = 3
    failureThreshold    = 5
  }

  nginx_liveness_probe = {
    httpGet = {
      path = "/"
      port = 80
    }
    initialDelaySeconds = 10
    periodSeconds       = 15
    timeoutSeconds      = 3
    failureThreshold    = 5
  }

  simple_app_readiness_probe = {
    httpGet = {
      path = "/health"
      port = 5000
    }
    initialDelaySeconds = 5
    periodSeconds       = 10
    timeoutSeconds      = 3
    failureThreshold    = 5
  }

  simple_app_liveness_probe = {
    httpGet = {
      path = "/health"
      port = 5000
    }
    initialDelaySeconds = 10
    periodSeconds       = 15
    timeoutSeconds      = 3
    failureThreshold    = 5
  }

  redis_readiness_probe = {
    exec = {
      command = ["redis-cli", "ping"]
    }
    initialDelaySeconds = 5
    periodSeconds       = 10
    timeoutSeconds      = 3
    failureThreshold    = 5
  }

  redis_liveness_probe = {
    exec = {
      command = ["redis-cli", "ping"]
    }
    initialDelaySeconds = 10
    periodSeconds       = 15
    timeoutSeconds      = 3
    failureThreshold    = 5
  }

  nginx_resources = {
    requests = {
      cpu    = "100m"
      memory = "64Mi"
    }
    limits = {
      cpu    = "250m"
      memory = "128Mi"
    }
  }

  simple_app_resources = {
    requests = {
      cpu    = "200m"
      memory = "128Mi"
    }
    limits = {
      cpu    = "500m"
      memory = "256Mi"
    }
  }

  redis_resources = {
    requests = {
      cpu    = "100m"
      memory = "64Mi"
    }
    limits = {
      cpu    = "250m"
      memory = "128Mi"
    }
  }
}
