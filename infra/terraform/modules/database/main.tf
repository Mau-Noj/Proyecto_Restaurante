locals {
  name = "${var.project_name}-${var.environment}"
}

resource "random_password" "db" {
  length  = 24
  special = false # evita caracteres que compliquen la DATABASE_URL
}

resource "aws_db_subnet_group" "this" {
  name       = "${local.name}-db-subnets"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name = "${local.name}-db-subnets"
  }
}

resource "aws_security_group" "db" {
  name        = "${local.name}-db-sg"
  description = "Postgres accesible solo desde el security group de la app"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Postgres desde la app"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.app_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name}-db-sg"
  }
}

resource "aws_db_instance" "this" {
  identifier     = "${local.name}-postgres"
  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class

  allocated_storage = var.allocated_storage
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  multi_az               = var.multi_az

  backup_retention_period = 7
  skip_final_snapshot     = var.skip_final_snapshot
  deletion_protection     = !var.skip_final_snapshot

  tags = {
    Name        = "${local.name}-postgres"
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# Credenciales en Secrets Manager: Ansible/la app las leen desde aquí,
# nunca quedan en texto plano en el estado de Terraform expuesto a CI logs.
resource "aws_secretsmanager_secret" "db" {
  name = "${local.name}/database"
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id = aws_secretsmanager_secret.db.id
  secret_string = jsonencode({
    engine   = "postgres"
    host     = aws_db_instance.this.address
    port     = 5432
    dbname   = var.db_name
    username = var.db_username
    password = random_password.db.result
  })
}
