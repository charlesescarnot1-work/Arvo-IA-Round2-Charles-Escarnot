variable "aws_region" {
  type = string
}

variable "app_name" {
  type = string
}

variable "image_uri" {
  type = string
}

variable "container_port" {
  type        = number
  description = "Container port to expose"
  default     = 8080
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "extra_env" {
  type        = map(string)
  default     = {}
  description = "Extra env vars for the container (key=value)"
}

