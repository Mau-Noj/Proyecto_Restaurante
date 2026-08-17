#!/usr/bin/env python3
"""Sincroniza los outputs de Terraform hacia el inventario de Ansible.

Uso:
    python3 infra/scripts/sync-terraform-outputs.py dev
    python3 infra/scripts/sync-terraform-outputs.py prod

Requiere haber corrido `terraform apply` en infra/terraform/environments/<env>
previamente. Sobrescribe hosts.ini y group_vars/all.yml de ese ambiente con
los valores reales (IP pública, endpoint de RDS, endpoint de Redis, bucket S3).
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("dev", "prod"):
        print("Uso: sync-terraform-outputs.py <dev|prod>")
        sys.exit(1)

    env = sys.argv[1]
    tf_dir = ROOT / "infra" / "terraform" / "environments" / env
    ansible_dir = ROOT / "infra" / "ansible" / "inventories" / env

    result = subprocess.run(
        ["terraform", "output", "-json"],
        cwd=tf_dir,
        capture_output=True,
        text=True,
        check=True,
    )
    outputs = {k: v["value"] for k, v in json.loads(result.stdout).items()}

    hosts_path = ansible_dir / "hosts.ini"
    hosts = hosts_path.read_text(encoding="utf-8")
    hosts = re.sub(
        r"ansible_host=\S+",
        f"ansible_host={outputs['app_public_ip']}",
        hosts,
    )
    hosts_path.write_text(hosts, encoding="utf-8")

    vars_path = ansible_dir / "group_vars" / "all.yml"
    vars_text = vars_path.read_text(encoding="utf-8")
    replacements = {
        "db_host": outputs["db_endpoint"],
        "db_secret_arn": outputs["db_secret_arn"],
        "redis_host": outputs["redis_endpoint"],
        "media_bucket": outputs["media_bucket"],
    }
    for key, value in replacements.items():
        vars_text = re.sub(
            rf'^{key}:.*$',
            f'{key}: "{value}"',
            vars_text,
            flags=re.MULTILINE,
        )
    vars_path.write_text(vars_text, encoding="utf-8")

    print(f"Inventario de '{env}' actualizado con los outputs de Terraform.")


if __name__ == "__main__":
    main()
