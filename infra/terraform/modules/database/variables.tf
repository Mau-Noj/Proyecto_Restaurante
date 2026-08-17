variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Al menos 2 subredes privadas en distintas AZ"
}

variable "app_security_group_id" {
  type        = string
  description = "Security group de la app; único origen permitido hacia el puerto 5432"
}

variable "instance_class" {
  type    = string
  default = "db.t3.micro"
}

variable "allocated_storage" {
  type    = number
  default = 20
}

variable "engine_version" {
  type    = string
  default = "16.4"
}

variable "db_name" {
  type    = string
  default = "restaurante"
}

variable "db_username" {
  type    = string
  default = "restaurante_app"
}

variable "multi_az" {
  type        = bool
  default     = false
  description = "Alta disponibilidad (duplica el costo). false para MVP/dev"
}

variable "skip_final_snapshot" {
  type    = bool
  default = true
}
