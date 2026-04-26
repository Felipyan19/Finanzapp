# Guía de configuración de GitHub Actions y Registry

## 1. Variables de Entorno Necesarias

Agrega estas variables secretas en **Settings → Secrets and variables → Actions**:

### Para publicar en GHCR (GitHub Container Registry):
- No necesita configuración manual, usa `GITHUB_TOKEN` automáticamente

### Para notificaciones a Slack (opcional):
```
SLACK_WEBHOOK: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Para otros registries:
```
# Docker Hub
DOCKER_USERNAME: your_username
DOCKER_PASSWORD: your_token

# Amazon ECR
AWS_ACCOUNT_ID: your_account_id
AWS_ACCESS_KEY_ID: your_access_key
AWS_SECRET_ACCESS_KEY: your_secret_key
AWS_REGION: us-east-1

# Azure Container Registry
AZURE_REGISTRY_LOGIN_SERVER: your_registry.azurecr.io
AZURE_REGISTRY_USERNAME: your_username
AZURE_REGISTRY_PASSWORD: your_password
```

## 2. Workflows Incluidos

### docker-build-push.yml
- Construye en: push a `main`, `develop` o tags semver
- Pushea a GHCR automáticamente (excepto en PRs)
- Cachea capas en GitHub Actions para builds más rápidos
- Genera tags: `branch`, `semver`, `sha`, `latest`

### dev-test.yml
- Se ejecuta en PRs a `develop`
- Ejecuta pytest + cobertura
- Ejecuta migraciones de BD
- Escanea vulnerabilidades con Trivy
- Carga resultados a GitHub Security tab

### deploy-production.yml
- Se ejecuta solo en tags semver (`v*.*.*`)
- Escanea vulnerabilidades en ambas imágenes
- Crea GitHub Release con reports de Trivy
- Envía notificación a Slack (si está configurado)

## 3. Uso

### Build y Push automático:
```bash
git push origin main
# Automáticamente construye y pushea a ghcr.io/tu-usuario/finanzapp-api:latest
```

### Deploy a producción:
```bash
git tag v1.0.0
git push origin v1.0.0
# Automáticamente construye v1.0.0 de ambas imágenes y escanea vulnerabilidades
```

### PRs en develop:
```bash
git checkout develop
git checkout -b feature/my-feature
# ... cambios ...
git push origin feature/my-feature
# Automáticamente corre tests y construye (no pushea)
```

## 4. Customización

### Cambiar registry (Docker Hub):
En `docker-build-push.yml`, reemplaza:
```yaml
registry: docker.io
username: ${{ secrets.DOCKER_USERNAME }}
password: ${{ secrets.DOCKER_PASSWORD }}
```

### Cambiar registry (AWS ECR):
```yaml
registry: ${{ env.AWS_ACCOUNT_ID }}.dkr.ecr.${{ env.AWS_REGION }}.amazonaws.com
username: AWS
password: ${{ steps.login-ecr.outputs.docker_password }}
```

### Agregar ambiente de staging:
1. Crea `deploy-staging.yml` similar a `deploy-production.yml`
2. Cambia `on: push: tags:` a `on: push: branches: [develop]`
3. Agrega paso de deploy a tu servidor staging

## 5. Images generadas

Después del push a main:
```
ghcr.io/usuario/finanzapp-api:latest
ghcr.io/usuario/finanzapp-api:main
ghcr.io/usuario/finanzapp-api:sha-abcd1234

ghcr.io/usuario/finanzapp-frontend:latest
ghcr.io/usuario/finanzapp-frontend:main
ghcr.io/usuario/finanzapp-frontend:sha-abcd1234
```

Después del tag `v1.0.0`:
```
ghcr.io/usuario/finanzapp-api:v1.0.0
ghcr.io/usuario/finanzapp-api:1.0
ghcr.io/usuario/finanzapp-api:latest

ghcr.io/usuario/finanzapp-frontend:v1.0.0
ghcr.io/usuario/finanzapp-frontend:1.0
ghcr.io/usuario/finanzapp-frontend:latest
```

## 6. Próximos pasos

1. Push a main para triggerear el primer build
2. Configura variable `SLACK_WEBHOOK` si quieres notificaciones
3. Agrega más tests en `pytest` si existen
4. Considera agregar paso de deploy automático (kubectl, docker-compose, etc.)
5. Configura GitHub Branch Protection para requerir PR checks exitosos
