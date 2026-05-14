# Integration Guide: React Frontend + Flask Backend

## Overview

The Zenith Healthcare platform now integrates:
- **Frontend**: React SPA (`Pixel Perfect/`) with Radix UI components
- **Backend**: Flask API server serving both JSON endpoints and static files
- **Database**: Azure MySQL with AI-powered document processing
- **Services**: Azure Blob, Document Intelligence, AI Search, OpenAI

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Browser (User)                       │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP/HTTPS
                     ▼
┌─────────────────────────────────────────────────────────┐
│         Flask Application (app.py - Port 5000)          │
├─────────────────────────────────────────────────────────┤
│ Static File Serving:                                    │
│  • React build (Pixel Perfect/dist/)                    │
│  • CSS, JS, Images                                      │
├─────────────────────────────────────────────────────────┤
│ JSON API Endpoints:                                     │
│  • POST /api/upload                                     │
│  • GET  /api/patients                                   │
│  • GET  /api/patients/<id>                              │
│  • GET  /api/patients/<id>/summary                      │
│  • GET  /api/search                                     │
│  • POST /api/assistant                                  │
├─────────────────────────────────────────────────────────┤
│ Service Layer (services/):                              │
│  • database.py (MySQL operations)                       │
│  • blob_storage.py (Azure Blob)                         │
│  • document_intelligence.py (OCR/Extraction)            │
│  • search_service.py (Azure AI Search)                  │
│  • openai_service.py (AI/LLM calls)                     │
└────────────┬─────────────────────────────────────┬──────┘
             │                                     │
             ▼                                     ▼
   ┌──────────────────────┐          ┌─────────────────────┐
   │  Azure MySQL         │          │  Azure Services:    │
   │  Database            │          │  • Blob Storage     │
   │  zenith_healthcare   │          │  • AI Search        │
   └──────────────────────┘          │  • Form Recognizer  │
                                     │  • OpenAI API       │
                                     └─────────────────────┘
```

## Deployment Modes

### 1. Development (Local)

**Run Frontend + Backend Separately:**

```bash
# Terminal 1: React dev server (auto-reload)
cd "Pixel Perfect"
bun run dev        # Runs on localhost:5173

# Terminal 2: Flask backend
source .venv/bin/activate
FLASK_DEBUG=true python app.py  # Runs on localhost:5000
```

**Frontend** queries backend at `http://localhost:5000/api/*`

### 2. Production (Azure VM or App Service)

**Single Server:**

```bash
# Build React
cd "Pixel Perfect" && bun run build && cd ..

# Run Flask (serves both frontend + API)
python app.py  # Localhost:5000 serves everything
```

Flask automatically:
- ✅ Serves React static files from `Pixel Perfect/dist/`
- ✅ Handles `/api/*` routes as JSON endpoints
- ✅ Falls back to `index.html` for React routing

---

## Data Flow Examples

### Example 1: Document Upload

**User Action**: Uploads PDF from upload page

```
1. React Component (index.tsx)
   │
   ├─> Validate file (type, size)
   ├─> Create FormData with file
   │
   └─> POST /api/upload
       │
       └──> Flask Handler: api_upload_document()
            │
            ├─> BlobStorageService.upload_document()
            │   └─> Uploads to Azure Blob Storage
            │
            ├─> DocumentIntelligenceService.extract_from_pdf()
            │   └─> Sends to Azure Document Intelligence (OCR)
            │
            ├─> DatabaseService.save_patient_record()
            │   └─> Inserts into MySQL database
            │
            ├─> SearchService.index_patient_record()
            │   └─> Indexes in Azure AI Search
            │
            └─> Return JSON
                {
                  "success": true,
                  "submissionId": "SUB-123456",
                  "recordId": 123456,
                  "patientName": "John Doe"
                }

2. React Component (upload.status.$submissionId.tsx)
   │
   └─> Displays processing status with animation
```

### Example 2: View Patient List

**User Action**: Navigates to `/patients`

```
1. React Component (patients.tsx)
   │
   ├─> Component mounts
   │
   └─> GET /api/patients
       │
       └──> Flask Handler: api_get_patients()
            │
            ├─> DatabaseService.get_all_patients()
            │   └─> SELECT * FROM patient_records
            │
            └─> Return JSON
                {
                  "success": true,
                  "patients": [
                    {
                      "id": 1,
                      "patient_name": "John Doe",
                      "urgency_level": "high",
                      ...
                    }
                  ]
                }

2. React renders patient list
   └─> Each patient clickable to view detail page
```

### Example 3: Search Records

**User Action**: Searches for "respiratory"

```
1. React Component (search.tsx)
   │
   ├─> User types query
   └─> GET /api/search?q=respiratory&urgency=high
       │
       └──> Flask Handler: api_search()
            │
            ├─> SearchService.search(query, filters)
            │   └─> Queries Azure AI Search index
            │
            └─> Return JSON
                {
                  "success": true,
                  "results": [...]
                }

2. React renders search results
```

---

## API Response Format

All JSON responses follow this format:

**Success Response:**
```json
{
  "success": true,
  "data": {...}        // or specific key like "patients", "patient", "summary"
}
```

**Error Response:**
```json
{
  "error": "Description of what went wrong"
}
```

---

## File Organization

```
.
├── app.py                          # Main Flask app (UPDATED)
│   ├── Serves React static files
│   ├── REST API endpoints (/api/*)
│   └── Health check (/health)
│
├── Pixel Perfect/                  # React frontend project
│   ├── src/
│   │   ├── routes/                 # Page components (React Router)
│   │   ├── components/             # UI components (Radix UI)
│   │   └── styles.css              # Tailwind CSS
│   ├── dist/                       # Built static files (after `bun run build`)
│   └── package.json
│
├── services/                       # Backend service layer
│   ├── database.py                 # MySQL operations
│   ├── blob_storage.py            # Azure Blob Storage
│   ├── document_intelligence.py   # OCR/Document parsing
│   ├── search_service.py          # Azure AI Search
│   └── openai_service.py          # OpenAI API calls
│
├── static/                        # (Legacy) Web assets
│   ├── css/
│   └── js/
│
├── templates/                     # (Legacy) Jinja2 templates
│
├── scripts/
│   ├── deploy-azure-vm.sh        # Deploy to Azure VM (NEW)
│   ├── quick-start.sh            # Local quick start (NEW)
│   └── student/
│       ├── 1_create_database.py
│       ├── 2_create_search_index.py
│       ├── 3_generate_test_documents.py
│       └── 4_load_sample_data.py
│
├── config.py                       # Configuration
├── requirements.txt                # Python dependencies (UPDATED +flask-cors)
├── AZURE_VM_DEPLOYMENT.md          # Azure VM deployment guide (NEW)
└── .env                           # Environment variables (Git ignored)
```

---

## Configuration Changes

### app.py (UPDATED)

**Added:**
- ✅ CORS headers for API endpoints
- ✅ React static file serving from `Pixel Perfect/dist/`
- ✅ Fallback routing for React SPA (`.react_catch_all()`)
- ✅ JSON API endpoints for all operations
- ✅ Auto-detection of React build

**Code Logic:**
```python
# Determines if React build exists
REACT_BUILD_PATH = Path(__file__).parent / "Pixel Perfect" / "dist"
USING_REACT = REACT_BUILD_PATH.exists()

if USING_REACT:
    # Serve React static files
    app = Flask(__name__, static_folder=str(REACT_BUILD_PATH), static_url_path="")
else:
    # Fallback to Jinja2 templates
    app = Flask(__name__)
```

### requirements.txt (UPDATED)

**Added:**
- ✅ `Flask-CORS==4.0.0` - Enable CORS headers for API

---

## How to Build & Deploy

### Step 1: Build React Frontend

```bash
cd "Pixel Perfect"
bun install              # Install dependencies
bun run build           # Build to dist/
cd ..
```

Output: `Pixel Perfect/dist/` (contains index.html, js/ chunks, css/)

### Step 2: Verify Flask Can Find React Build

```bash
ls "Pixel Perfect/dist/index.html"  # Should exist
```

### Step 3: Run Flask

```bash
source .venv/bin/activate
python app.py
```

Flask will:
1. Detect `Pixel Perfect/dist/` exists
2. Serve React static files at root (`/`)
3. Handle API calls at `/api/*`
4. Serve static assets (JS, CSS)

### Step 4: Test

```bash
# Frontend loads at:
curl http://localhost:5000

# API works at:
curl http://localhost:5000/api/patients
curl http://localhost:5000/health
```

---

## Automated Deployment

### Quick Start Script (Local)

```bash
bash scripts/quick-start.sh
# ✅ Builds React
# ✅ Sets up Python venv
# ✅ Shows ready message
```

### Azure VM Deployment Script

```bash
bash scripts/deploy-azure-vm.sh
# ✅ Installs system dependencies
# ✅ Builds React
# ✅ Sets up Python
# ✅ Initializes database
# ✅ Shows deployment summary
```

See `AZURE_VM_DEPLOYMENT.md` for full Azure VM setup.

---

## Troubleshooting

### React Not Loading

**Symptom**: Blank page or 404

**Solution:**
```bash
# Verify React was built
ls "Pixel Perfect/dist/"

# Rebuild if missing
cd "Pixel Perfect" && bun run build && cd ..

# Restart Flask
python app.py
```

### API Returning 404

**Symptom**: `POST /api/upload` returns 404

**Solution:**
```bash
# Check Flask is running
curl http://localhost:5000/health

# Verify Python venv is activated
which python       # Should show .venv/bin/python

# Check .env variables are set
cat .env | grep AZURE_MYSQL_HOST
```

### CORS Errors in Browser Console

**Symptom**: "Access to XMLHttpRequest has been blocked by CORS policy"

**Solution:**
```python
# Verify CORS is enabled in app.py
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Should see this in Flask logs:
# "WARNING in flask_cors.core: ... CORS have been"
```

### Database Connection Failed

**Symptom**: "Errno 110: Connection timed out"

**Solution:**
```bash
# Test MySQL connection
python3 -c "
from config import Config
import mysql.connector
try:
    conn = mysql.connector.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        ssl_ca=Config.SSL_CA_PATH,
    )
    print('✅ Connected')
    conn.close()
except Exception as e:
    print(f'❌ {e}')
"
```

---

## Next: Wire Up React Components

The React components in `Pixel Perfect/src/routes/` need to be updated to call the Flask `/api/*` endpoints:

**Example: Update `index.tsx` upload handler**

```typescript
async function handleSubmit() {
  const formData = new FormData();
  files.forEach(f => formData.append('file', f));

  const response = await fetch('/api/upload', {
    method: 'POST',
    body: formData
  });

  const data = await response.json();
  if (data.success) {
    navigate({ 
      to: '/upload/status/$submissionId', 
      params: { submissionId: data.submissionId } 
    });
  }
}
```

Similar updates needed in other route files to consume the Flask APIs.

