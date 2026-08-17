# Flujo de trabajo (Git Flow)

Este proyecto usa **Git Flow clásico**. Stack: Python / Django / PostgreSQL / Redis.

## Ramas

| Rama         | Propósito                                              | Nace de   | Se fusiona en     |
|--------------|----------------------------------------------------------|-----------|--------------------|
| `main`       | Código en producción, siempre estable y desplegable    | —         | —                   |
| `develop`    | Rama de integración, último código listo para próxima release | `main`    | —                   |
| `feature/*`  | Nueva funcionalidad                                     | `develop` | `develop`           |
| `release/*`  | Preparación de una versión (ajustes finales, changelog) | `develop` | `main` y `develop`  |
| `hotfix/*`   | Corrección urgente en producción                        | `main`    | `main` y `develop`  |

## Convención de nombres

- `feature/nombre-corto-descriptivo` (ej. `feature/gestion-mesas`)
- `release/vX.Y.Z` (ej. `release/v1.0.0`)
- `hotfix/nombre-corto-descriptivo` (ej. `hotfix/fix-login-token`)

## Flujo típico

### Feature
```bash
git checkout develop
git pull
git checkout -b feature/mi-funcionalidad
# ... trabajar, commits ...
git push -u origin feature/mi-funcionalidad
# Abrir PR: feature/mi-funcionalidad -> develop
```

### Release
```bash
git checkout develop
git pull
git checkout -b release/v1.0.0
# ... version bump, últimos ajustes ...
git push -u origin release/v1.0.0
# PR: release/v1.0.0 -> main
# Luego fusionar también release/v1.0.0 -> develop
# Etiquetar en main: git tag v1.0.0
```

### Hotfix
```bash
git checkout main
git pull
git checkout -b hotfix/fix-critico
# ... fix ...
git push -u origin hotfix/fix-critico
# PR: hotfix/fix-critico -> main (y luego mergear también a develop)
```

## Pull Requests
- Todo cambio entra por PR, nunca push directo a `main` o `develop`.
- El PR debe pasar el pipeline de CI (lint + tests) antes de poder fusionarse.
- Usa la plantilla de PR que se completa automáticamente.

## CI/CD (GitHub Actions)
- **`ci.yml`**: corre en cada push/PR a `main`, `develop`, `feature/**`, `release/**`, `hotfix/**`.
  - Lint con `ruff`.
  - Tests con `pytest` (usa servicios de PostgreSQL y Redis en el runner).
- **`cd.yml`**: corre al llegar a `main` (releases/hotfixes fusionados). Actualmente hace build/checks;
  el job `deploy` es un placeholder pendiente de definir el proveedor de hosting.

## Reglas de protección de rama recomendadas (configurar en GitHub → Settings → Branches)
Como no hay `gh` CLI autenticado en este entorno, configúralas manualmente:

- **`main`**: requiere PR con al menos 1 revisión aprobada, requiere que pasen los checks de CI (`lint`, `test`),
  prohíbe push directo y force-push, requiere rama actualizada antes de fusionar.
- **`develop`**: mismas reglas que `main` (revisión + CI obligatorio), sin necesidad de proteger contra force-push
  con la misma rigurosidad, pero se recomienda igual.
