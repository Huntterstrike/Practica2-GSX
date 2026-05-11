environment_name = "prod"
app_message      = "Hello from Terraform prod"
nginx_node_port  = 31082
app_pv_host_path = "/data/gsx-app-prod"

nginx_image      = "nginx-gsx:latest"
simple_app_image = "simple-app-gsx:latest"
