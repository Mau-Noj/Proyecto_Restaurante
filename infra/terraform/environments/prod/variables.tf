variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "proyecto-restaurante"
}

variable "environment" {
  type    = string
  default = "prod"
}

variable "vpc_cidr" {
  type    = string
  default = "10.1.0.0/16"
}

variable "azs" {
  type    = list(string)
  default = ["us-east-1a", "us-east-1b"]
}

variable "public_subnet_cidrs" {
  type    = list(string)
  default = ["10.1.1.0/24", "10.1.2.0/24"]
}

variable "private_subnet_cidrs" {
  type    = list(string)
  default = ["10.1.11.0/24", "10.1.12.0/24"]
}

variable "instance_type" {
  type    = string
  default = "t3.small"
}

variable "key_name" {
  type        = string
  description = "Key Pair de EC2 ya creado en la cuenta de AWS"
}

variable "allowed_ssh_cidr" {
  type        = string
  description = "Tu IP pública en formato CIDR. Nunca 0.0.0.0/0"
}

variable "db_name" {
  type    = string
  default = "restaurante"
}

variable "db_username" {
  type    = string
  default = "restaurante_app"
}

variable "db_multi_az" {
  type        = bool
  default     = true
  description = "Alta disponibilidad para producción (duplica el costo de RDS)"
}
