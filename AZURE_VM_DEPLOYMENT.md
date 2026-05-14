# Azure VM Deployment Guide

## Quick Start for Azure VM

This guide explains how to deploy the Zenith Healthcare platform to an Azure VM.

### Prerequisites

- **Azure VM** (Ubuntu 20.04 or 22.04) running on Azure
- **SSH access** to the VM
- **.env file** with all Azure credentials (see `.env.example`)

### 1. Create Azure VM

```bash
# Example using Azure CLI
az vm create \
  --resource-group myResourceGroup \
  --name zenith-healthcare-vm \
  --image UbuntuLTS \
  --size Standard_B2s \
  --admin-username azureuser \
  --generate-ssh-keys \
  --public-ip-sku Standard
```

### 2. Connect to VM

```bash
ssh azureuser@<your-vm-public-ip>
```

### 3. Clone Repository

```bash
git clone <your-repo-url> zenith-healthcare
cd zenith-healthcare
```

### 4. Set Up Environment Variables

```bash
# Copy template and fill with your Azure credentials
cp .env.example .env
nano .env

# Required variables:
# AZURE_MYSQL_HOST=your-mysql.mysql.database.azure.com
# AZURE_MYSQL_USER=admin@your-mysql
# AZURE_MYSQL_PASSWORD=your-password
# AZURE_STORAGE_CONNECTION_STRING=...
# AZURE_SEARCH_ENDPOINT=...
# AZURE_SEARCH_KEY=...
# AZURE_OPENAI_KEY=...
# DOCUMENT_INTELLIGENCE_ENDPOINT=...
# DOCUMENT_INTELLIGENCE_KEY=...
```

### 5. Run Deployment Script

```bash
bash scripts/deploy-azure-vm.sh
```

This will:
- ✅ Install system dependencies (Python, Node.js tools)
- ✅ Build React frontend to static files
- ✅ Set up Python virtual environment
- ✅ Install all Python packages
- ✅ Initialize database
- ✅ Show deployment summary

### 6. Start Application

```bash
source .venv/bin/activate
python app.py
```

Output should show:
```
Running on http://0.0.0.0:5000
```

### 7. Access the Application

Visit: `http://<your-vm-public-ip>:5000`

---

## Architecture

### Frontend (React/TanStack)
- **Location**: `Pixel Perfect/dist/` (built static files)
- **Framework**: React 18 + TanStack Router
- **Styling**: Tailwind CSS + Radix UI components
- **Build process**: `bun run build`

### Backend (Flask API)
- **Location**: `app.py`
- **Framework**: Flask 3.1 with Python 3.11
- **Static serving**: Serves React build + REST API endpoints
- **CORS**: Enabled for frontend requests

### Database
- **Azure MySQL Flexible Server**
- **Auto-initialized** by deployment script
- **SSL connections** via DigiCert certificate

---

## API Endpoints

All endpoints return JSON. The React frontend calls these automatically.

### Upload (Public)
```
POST /api/upload
Content-Type: multipart/form-data

Request:
{
  "file": <binary file data>
}

Response:
{
  "success": true,
  "submissionId": "SUB-123456",
  "recordId": 123456,
  "patientName": "John Doe"
}
```

### Patients (Admin - TODO: Add auth)
```
GET /api/patients

Response:
{
  "success": true,
  "patients": [
    {
      "id": 1,
      "patient_name": "John Doe",
      "urgency_level": "high",
      "created_at": "2024-01-15T10:30:00"
    }
  ]
}
```

### Patient Detail (Admin)
```
GET /api/patients/<id>

Response:
{
  "success": true,
  "patient": {
    "id": 1,
    "patient_name": "John Doe",
    "age": 45,
    "urgency_level": "high",
    "chief_complaint": "...",
    "extracted_fields": {...}
  }
}
```

### Patient Summary (Admin)
```
GET /api/patients/<id>/summary

Response:
{
  "success": true,
  "summary": "AI-generated clinical summary..."
}
```

### Search (Admin)
```
GET /api/search?q=<query>&urgency=<level>

Response:
{
  "success": true,
  "results": [...]
}
```

### Assistant Chat (Admin)
```
POST /api/assistant
Content-Type: application/json

Request:
{
  "question": "What is...",
  "history": [...]
}

Response:
{
  "answer": "..."
}
```

### Health Check
```
GET /health

Response:
{
  "status": "healthy",
  "service": "Zenith Healthcare AI Platform"
}
```

---

## Running in Production on Azure VM

### Option 1: Use Systemd Service (Recommended)

Create `/etc/systemd/system/zenith.service`:

```ini
[Unit]
Description=Zenith Healthcare AI Platform
After=network.target

[Service]
Type=simple
User=azureuser
WorkingDirectory=/home/azureuser/zenith-healthcare
Environment="PATH=/home/azureuser/zenith-healthcare/.venv/bin"
ExecStart=/home/azureuser/zenith-healthcare/.venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable zenith
sudo systemctl start zenith
sudo systemctl status zenith
```

### Option 2: Use PM2 (Node-based process manager)

```bash
# Install PM2 globally
npm install -g pm2

# Create PM2 app config (ecosystem.config.js)
pm2 start app.py --name zenith-healthcare --interpreter python

# Make it restart on reboot
pm2 startup
pm2 save
```

### Option 3: Docker (If Docker installed)

```bash
# Build Docker image
docker build -t zenith-healthcare .

# Run container
docker run -p 5000:5000 \
  --env-file .env \
  zenith-healthcare
```

---

## Monitoring

### Check App Status
```bash
# If using systemd
sudo systemctl status zenith

# Check logs
sudo journalctl -u zenith -f
```

### Monitor Performance
```bash
# Install monitoring tools
sudo apt-get install htop iotop

# Check system resources
htop
```

### Database Connection
```bash
# Test MySQL connection from VM
python3 -c "
import mysql.connector
from config import Config
try:
    conn = mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        ssl_ca=Config.SSL_CA_PATH,
    )
    print('✅ MySQL Connection OK')
    conn.close()
except Exception as e:
    print(f'❌ MySQL Error: {e}')
"
```

---

## Troubleshooting

### "Connection timed out" to MySQL
1. Verify VM security group allows outbound on port 3306
2. Check Azure MySQL firewall rules include VM IP
3. Test: `telnet <mysql-host> 3306`

### "Permission denied" running script
```bash
chmod +x scripts/deploy-azure-vm.sh
```

### React frontend not loading
```bash
# Check if React build exists
ls Pixel\ Perfect/dist/

# Rebuild if needed
cd Pixel\ Perfect && bun run build && cd ..
```

### Port 5000 already in use
```bash
# Find process using port 5000
sudo lsof -i :5000

# Kill it
sudo kill -9 <PID>
```

---

## Next Steps

1. **Set up HTTPS**: Use Azure Application Gateway or Let's Encrypt
2. **Add Authentication**: Integrate with Azure AD or Auth0
3. **Use App Service**: Migrate from VM to Azure App Service for auto-scaling
4. **Set up CI/CD**: GitHub Actions to auto-deploy on push

