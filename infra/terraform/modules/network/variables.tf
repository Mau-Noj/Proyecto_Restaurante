variable "project_name" {
  type        = string
  description = "Nombre del proyecto, usado como prefijo en los tags/nombres de recursos"
}

variable "environment" {
  type        = string
  description = "Nombre del ambiente (dev, staging, prod)"
}

variable "vpc_cidr" {
  type        = string
  description = "Bloque CIDR de la VPC"
  default     = "10.0.0.0/16"
}

variable "azs" {
  type        = list(string)
  description = "Availability Zones a usar (mínimo 2, RDS/ElastiCache lo requieren para el subnet group)"
}

variable "public_subnet_cidrs" {
  type        = list(string)
  description = "CIDRs de las subredes públicas (una por AZ)"
}

variable "private_subnet_cidrs" {
  type        = list(string)
  description = "CIDRs de las subredes privadas (una por AZ), para RDS y ElastiCache"
}
