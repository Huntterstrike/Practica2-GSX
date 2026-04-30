environment_name = "staging"
app_message      = "Hello from Terraform staging"
nginx_node_port  = 31081
app_pv_host_path = "/data/gsx-app-staging"

nginx_image      = "nginx-gsx:latest"
simple_app_image = "simple-app-gsx:latest"
