# Azure App Service Deployment Guide

This guide walks through deploying the Zenith Healthcare Flask app to Azure App Service using Azure Container Registry (ACR).

## Prerequisites

- Azure subscription
- Azure CLI installed and authenticated (`az login`)
- Docker installed locally
- The Flask application code with Dockerfile

## Step 1: Create Azure Container Registry (ACR)

```bash
# Set variables
RESOURCE_GROUP="aicare-rg"
ACR_NAME="aicareprod"  # Must be unique globally
REGION="eastus"

# Create resource group (if not exists)
az group create --name $RESOURCE_GROUP --location $REGION

# Create Azure Container Registry
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Standard
```

## Step 2: Build Docker Image Locally

```bash
# Navigate to project directory
cd /path/to/aicare

# Build image
docker build -t aicare:latest .

# Tag for ACR
docker tag aicare:latest $ACR_NAME.azurecr.io/aicare:latest
```

## Step 3: Push Image to ACR

```bash
# Login to ACR
az acr login --name $ACR_NAME

# Push image
docker push $ACR_NAME.azurecr.io/aicare:latest

# Verify (list repositories in ACR)
az acr repository list --name $ACR_NAME
```

## Step 4: Create App Service Plan

```bash
# Create App Service Plan (Linux, B2 for Flask production workloads)
az appservice plan create \
  --name aicare-plan \
  --resource-group $RESOURCE_GROUP \
  --sku B2 \
  --is-linux
```

## Step 5: Create Web App

```bash
# Create Web App connected to ACR
az webapp create \
  --resource-group $RESOURCE_GROUP \
  --plan aicare-plan \
  --name aicare-prod \
  --deployment-container-image-name $ACR_NAME.azurecr.io/aicare:latest
```

## Step 6: Configure Docker Container Settings

```bash
# Configure app to pull from ACR
az webapp config container set \
  --name aicare-prod \
  --resource-group $RESOURCE_GROUP \
  --docker-custom-image-name $ACR_NAME.azurecr.io/aicare:latest \
  --docker-registry-server-url https://$ACR_NAME.azurecr.io \
  --docker-registry-server-user <username-for-acr> \
  --docker-registry-server-password <password-for-acr>
```

Get ACR credentials:
```bash
az acr credential show --name $ACR_NAME
```

## Step 7: Configure Environment Variables

### Via Azure Portal:
1. Navigate to **App Service** → **Configuration**
2. Add application settings (environment variables):

**Required Variables:**
```
FLASK_ENV = production
FLASK_SECRET_KEY = (generate with: python -c "import os; print(os.urandom(24).hex())")
AZURE_MYSQL_HOST = your-server.mysql.database.azure.com
AZURE_MYSQL_USERNAME = dbadmin@your-server
AZURE_MYSQL_PASSWORD = your-password
AZURE_MYSQL_DATABASE = zenith_healthcare
AZURE_STORAGE_CONNECTION_STRING = DefaultEndpointsProtocol=https;...
DOCUMENT_INTELLIGENCE_ENDPOINT = https://your-region.api.cognitive.microsoft.com/
DOCUMENT_INTELLIGENCE_KEY = your-key
AZURE_SEARCH_ENDPOINT = https://your-service.search.windows.net/
AZURE_SEARCH_KEY = your-key
AZURE_OPENAI_ENDPOINT = https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY = your-key
AZURE_OPENAI_DEPLOYMENT = gpt-4o
```

### Via CLI:
```bash
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name aicare-prod \
  --settings \
    FLASK_ENV=production \
    FLASK_SECRET_KEY=your-secret-key \
    AZURE_MYSQL_HOST=your-host.mysql.database.azure.com \
    AZURE_MYSQL_USERNAME=your-user \
    AZURE_MYSQL_PASSWORD=your-password \
    AZURE_MYSQL_DATABASE=zenith_healthcare \
    AZURE_STORAGE_CONNECTION_STRING='DefaultEndpointsProtocol=https;...' \
    DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-region.api.cognitive.microsoft.com/ \
    DOCUMENT_INTELLIGENCE_KEY=your-key \
    AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net/ \
    AZURE_SEARCH_KEY=your-key \
    AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/ \
    AZURE_OPENAI_KEY=your-key \
    AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

## Step 8: Enable Continuous Deployment (Optional)

Enable automatic redeployment when you push new images to ACR:

```bash
az webapp deployment container config \
  --name aicare-prod \
  --resource-group $RESOURCE_GROUP \
  --enable-cd true
```

Get the webhook URL:
```bash
az webapp deployment container show-cd-url \
  --name aicare-prod \
  --resource-group $RESOURCE_GROUP
```

Configure webhook in ACR:
```bash
az acr webhook create \
  --registry $ACR_NAME \
  --name aicareprodwebhook \
  --actions push \
  --uri <webhook-url-from-previous-command>
```

## Step 9: Verify Deployment

```bash
# Get app URL
az webapp show --resource-group $RESOURCE_GROUP --name aicare-prod --query defaultHostName

# Check logs
az webapp log tail --name aicare-prod --resource-group $RESOURCE_GROUP

# Test health endpoint
curl https://aicare-prod.azurewebsites.net/health
```

## Step 10: Configure SSL/HTTPS

Azure App Service provides automatic SSL certificates via App Service Managed Certificate.

1. Go to **Azure Portal** → **App Service** → **TLS/SSL settings**
2. Click **Create App Service Managed Certificate**
3. Select your custom domain or use `*.azurewebsites.net`
4. Create HTTPS binding automatically

## Step 11: Monitor and Logs

### View logs:
```bash
az webapp log tail --name aicare-prod --resource-group $RESOURCE_GROUP
```

### Enable Application Insights:
```bash
# Create Application Insights
az monitor app-insights component create \
  --app aicare-insights \
  --location $REGION \
  --resource-group $RESOURCE_GROUP

# Connect to App Service
az webapp config appsettings set \
  --name aicare-prod \
  --resource-group $RESOURCE_GROUP \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY=<key-from-portal>
```

## Troubleshooting

### Container won't start
```bash
# Check logs
az webapp log tail --name aicare-prod --resource-group $RESOURCE_GROUP

# Verify image exists in ACR
az acr repository show --name $ACR_NAME --image aicare:latest
```

### Connection errors to Azure MySQL
- Verify firewall rules allow App Service IP
- Check MySQL credentials in environment variables
- Ensure database exists: `AZURE_MYSQL_DATABASE=zenith_healthcare`

### Health check failures
- Container logs should show startup errors
- Verify all required environment variables are set
- Test `/health` endpoint responds with 200 OK

## Scaling

```bash
# Scale App Service Plan
az appservice plan update \
  --name aicare-plan \
  --resource-group $RESOURCE_GROUP \
  --sku P1V2  # For higher traffic
```

## Cost Optimization

- Use **B2** tier for development/testing
- Use **D1** tier for development only (shared infrastructure)
- Use **P1V2** for production workloads
- Set auto-scaling rules based on CPU/memory metrics

```bash
# Enable auto-scaling
az monitor autoscale create \
  --resource-group $RESOURCE_GROUP \
  --resource aicare-plan \
  --resource-type "Microsoft.Web/serverfarms" \
  --name aicare-autoscale \
  --min-count 1 \
  --max-count 5 \
  --count 1
```

## Next Steps

1. Set up custom domain (`aicare.yourdomain.com`)
2. Configure Azure Front Door for CDN/global routing
3. Set up backup/disaster recovery
4. Monitor with Application Insights and set up alerts
5. Implement CI/CD with GitHub Actions
