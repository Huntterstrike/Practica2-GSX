environment_name = "dev"
app_message      = "Hello from Terraform dev"
nginx_node_port  = 31080
app_pv_host_path = "/data/gsx-app-dev"

nginx_image      = "nginx-gsx:latest"
simple_app_image = "simple-app-gsx:latest"
