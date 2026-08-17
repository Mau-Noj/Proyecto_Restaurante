# Infraestructura (AWS)

Terraform aprovisiona los recursos de AWS; Ansible configura el software dentro
del servidor de la app. Arquitectura acorde a lo definido en
`Toma De Requerimientos/Arquitecturas_Candidatas_Restaurante.docx`: **monolito
modular** (Django + PostgreSQL + Redis), pensado para arrancar barato (MVP,
1-3 sucursales) con camino claro para escalar después.

## Qué crea Terraform

- VPC con subredes públicas (app) y privadas (datos), sin NAT Gateway (ahorro de costo).
- 1 instancia EC2 (Ubuntu 22.04) para la app, con Elastic IP.
- RDS PostgreSQL (privado, solo alcanzable desde la app).
- ElastiCache Redis (privado, solo alcanzable desde la app).
- Bucket S3 privado para media/static.
- Credenciales de la DB generadas y guardadas en Secrets Manager (nunca en el `.tfstate` en texto plano expuesto, ni en el repo).

## Qué hace Ansible

- Hardening básico del EC2 (ufw, paquetes base).
- Instala Docker + Docker Compose.
- Genera `.env` y `docker-compose.yml` en el servidor y levanta los contenedores
  (`web` = app Django/gunicorn, `nginx` = reverse proxy + estáticos).
- Lee la password de la DB directamente de Secrets Manager en el momento del deploy.

## Orden de ejecución (primera vez)

```bash
# 1. Bootstrap del backend remoto de Terraform (una sola vez por cuenta AWS)
cd infra/terraform/bootstrap
terraform init
terraform apply
terraform output   # anota state_bucket y lock_table

# 2. Ambiente dev
cd ../environments/dev
cp backend.hcl.example backend.hcl        # completar con el output anterior
cp terraform.tfvars.example terraform.tfvars  # completar key_name y tu IP
terraform init -backend-config=backend.hcl
terraform plan
terraform apply

# 3. Sincronizar el inventario de Ansible con los outputs de Terraform
cd ../../../..
python3 infra/scripts/sync-terraform-outputs.py dev

# 4. Configurar y desplegar la app
cd infra/ansible
pip install -r requirements.txt
ansible-galaxy collection install -r requirements.yml
ansible-playbook playbooks/site.yml -i inventories/dev/hosts.ini
```

Repetir para `prod` cambiando `dev` por `prod` en los pasos 2-4.

## CI/CD del propio Terraform (`.github/workflows/terraform.yml`)

Corre `terraform plan` en cada PR que toque `infra/terraform/**` y `terraform apply`
al hacer push a `main`, usando el rol de OIDC creado en `bootstrap/github_oidc.tf`
(sin access keys guardadas en GitHub). Secrets a configurar una vez en
GitHub → Settings → Secrets and variables → Actions:

| Secret | De dónde sale |
|---|---|
| `AWS_TERRAFORM_ROLE_ARN` | Output `github_actions_role_arn` de `bootstrap` |
| `TF_STATE_BUCKET` | Output `state_bucket` de `bootstrap` |
| `TF_STATE_LOCK_TABLE` | Output `lock_table` de `bootstrap` |
| `TF_EC2_KEY_NAME` | Nombre del Key Pair EC2 que crees en la consola AWS |
| `TF_ALLOWED_SSH_CIDR` | Tu IP pública en formato CIDR |

El job `apply` corre contra el environment de GitHub `production` (para prod) o
`development` (para dev) — protégelos con reviewers requeridos en Settings →
Environments si quieres aprobar manualmente antes de aplicar contra AWS real.

## Imagen Docker de la app (`.github/workflows/cd.yml`)

Al hacer push a `main` o `develop` se construye y publica la imagen en GHCR
(`ghcr.io/mau-noj/proyecto_restaurante:latest` / `:develop`), referenciada por
`docker_image` en `infra/ansible/inventories/*/group_vars/all.yml`.

**Pendiente antes del primer deploy real:** las imágenes publicadas con
`GITHUB_TOKEN` quedan **privadas** en GHCR por defecto. El EC2 necesita poder
hacer `docker pull` de esa imagen — hay que decidir entre (a) marcar el
paquete como público en GitHub → tu perfil → Packages → proyecto_restaurante →
Package settings, o (b) agregar una tarea `docker login ghcr.io` al rol
`infra/ansible/roles/docker` usando un token con permiso `read:packages`
guardado en Secrets Manager. Ninguna de las dos está hecha todavía.

## Qué necesito para poder aplicar esto en tu cuenta de AWS

Ver la sección de credenciales en el mensaje del asistente — en resumen: un
usuario/rol de AWS con la política de `bootstrap/terraform-deployer-policy.json`,
configurado en tu máquina (`aws configure`) para que Terraform y Ansible lo usen.
Nunca se pega el access key/secret key directamente en el chat.
