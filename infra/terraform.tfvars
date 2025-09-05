app_name     = "hello-world"
image_uri    = "128121109380.dkr.ecr.us-east-1.amazonaws.com/hello-world:1757106532"
aws_region   = "us-east-1"
container_port = 5000
desired_count  = 1
extra_env = {
  GUNICORN_CMD_ARGS = "--access-logfile - --log-level info"
}