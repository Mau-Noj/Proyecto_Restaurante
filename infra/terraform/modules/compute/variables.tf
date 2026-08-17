variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "public_subnet_id" {
  type        = string
  description = "Subred pública donde vive la instancia de la app"
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "key_name" {
  type        = string
  description = "Nombre del Key Pair de EC2 ya existente en AWS (para acceso SSH)"
}

variable "allowed_ssh_cidr" {
  type        = string
  description = "CIDR permitido para conectarse por SSH (ej. tu IP pública /32). Nunca dejar 0.0.0.0/0"
}
