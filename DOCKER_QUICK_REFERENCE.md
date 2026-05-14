# Docker & ACR Deployment Quick Reference

## 📋 Files Created

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage production build (Python 3.11 slim) |
| `docker-compose.yml` | Local testing with docker-compose |
| `.dockerignore` | Exclude unnecessary files from image |
| `.env.example` | Environment variable documentation |
| `DOCKER_DEPLOYMENT_GUIDE.md` | Complete Azure deployment walkthrough |
| `build-and-push.sh` | Quick script to build & push to ACR |
| `requirements.txt` | Updated with `gunicorn==23.0.0` for production |

## 🚀 Quick Start: Local Testing

### 1. Build Locally
```bash
docker build -t aicare:latest .
```

### 2. Run with Docker Compose
```bash
# Copy .env.example to .env and fill in your Azure credentials
cp .env.example .env

# Start container
docker-compose up -d

# View logs
docker-compose logs -f aicare-app

# Stop
docker-compose down
```

### 3. Test
```bash
curl http://localhost:5000/health
# Expected: {"status":"ok"}

# Access app
open http://localhost:5000/login
```

## 🔧 Deploy to Azure App Service

### 1. Build & Push to ACR
```bash
# Using provided script
chmod +x build-and-push.sh
./build-and-push.sh aicareprod latest

# OR manually
docker build -t aicare:latest .
docker tag aicare:latest aicareprod.azurecr.io/aicare:latest
az acr login --name aicareprod
docker push aicareprod.azurecr.io/aicare:latest
```

### 2. Update App Service
```bash
# Configure to use new image
az webapp config container set \
  --name aicare-prod \
  --resource-group aicare-rg \
  --docker-custom-image-name aicareprod.azurecr.io/aicare:latest
```

### 3. Check Deployment
```bash
# View logs
az webapp log tail --name aicare-prod --resource-group aicare-rg

# Test health
curl https://aicare-prod.azurewebsites.net/health
```

## 🔑 Environment Variables (Must Configure in Azure)

**Critical for containerized app:**
- `FLASK_SECRET_KEY` - Generate: `python -c "import os; print(os.urandom(24).hex())"`
- `FLASK_ENV` - Set to `production`
- `AZURE_MYSQL_HOST`, `AZURE_MYSQL_USERNAME`, `AZURE_MYSQL_PASSWORD`
- `AZURE_STORAGE_CONNECTION_STRING`
- `DOCUMENT_INTELLIGENCE_ENDPOINT`, `DOCUMENT_INTELLIGENCE_KEY`
- `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_KEY`
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`

Set all in Azure Portal: **App Service → Configuration → Application settings**

## 📊 Image Stats

```bash
docker images aicare:latest
# Shows image size, creation time

docker run --rm aicare:latest gunicorn --version
# Verify gunicorn installation
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| `Module not found` | Check requirements.txt is complete |
| `Connection refused` | Verify MySQL host/credentials in env vars |
| `Health check fails` | Check `/health` endpoint responds (port 5000) |
| `Upload fails` | Verify AZURE_STORAGE_CONNECTION_STRING |
| `Auth fails` | Ensure FLASK_SECRET_KEY is set |

## 📈 Next Phase Checklist

- [ ] Build and test Docker image locally
- [ ] Push image to ACR
- [ ] Create App Service Plan (B2 or higher)
- [ ] Create Web App from ACR image
- [ ] Configure all environment variables
- [ ] Test `/health`, `/login`, `/` (upload) endpoints
- [ ] Set up custom domain (optional)
- [ ] Enable HTTPS (auto-managed by Azure)
- [ ] Configure auto-scaling rules (optional)
- [ ] Set up monitoring/Application Insights (optional)

## 💡 Best Practices

✅ **DO:**
- Use production image (gunicorn, not Flask dev server)
- Set `FLASK_ENV=production`
- Generate strong `FLASK_SECRET_KEY`
- Use secrets management (Azure Key Vault) for sensitive data
- Monitor logs regularly
- Set up health checks/auto-restart

❌ **DON'T:**
- Commit `.env` file to Git
- Use `FLASK_DEBUG=true` in production
- Store secrets in code
- Use Flask development server in containers
- Hard-code Azure credentials

## 📚 Learn More

- [Dockerfile best practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Azure Container Registry documentation](https://learn.microsoft.com/en-us/azure/container-registry/)
- [Azure App Service deployment](https://learn.microsoft.com/en-us/azure/app-service/deploy-container-github-action)
- [Gunicorn configuration](https://gunicorn.org/source/stable/source/gunicorn/)
