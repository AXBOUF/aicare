# Zenith Healthcare AI Platform

**Capstone Project — AI-Powered Patient Intake Processing System**

A secure, Azure-based platform that automates patient intake form processing, extracts structured clinical data using AI, enables intelligent search, and provides a RAG-based AI triage assistant.

---

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────────┐     ┌──────────────────┐
│   Upload Portal  │────▶│  Azure Blob Storage   │────▶│  Document        │
│   (Flask App)    │     │  (Patient PDFs)        │     │  Intelligence    │
└─────────────────┘     └──────────────────────┘     └────────┬─────────┘
                                                               │
                                                               ▼
┌─────────────────┐     ┌──────────────────────┐     ┌──────────────────┐
│  AI Triage       │◀───│  Azure AI Search      │◀───│  Azure MySQL     │
│  Assistant       │     │  (Knowledge Index)     │     │  Database        │
│  (Azure OpenAI)  │     └──────────────────────┘     └──────────────────┘
└─────────────────┘
```

### Data Flow
1. **Upload** — Patient intake form (PDF/image) uploaded via web portal
2. **Store** — File stored securely in Azure Blob Storage (LRS Hot)
3. **Extract** — Azure AI Document Intelligence extracts structured clinical fields
4. **Persist** — Extracted data saved to Azure MySQL Flexible Server with confidence scores
5. **Index** — Record indexed in Azure AI Search for knowledge mining
6. **Query** — RAG-based AI assistant retrieves context and generates responses

---

## How a File Upload Works — Step by Step

> **For students:** This section traces exactly what happens in the code from the moment you click "Upload" to the moment you see the patient detail page. Each step maps to a specific file in the project.

```
Browser  →  Flask (app.py)  →  Blob Storage  →  Document Intelligence  →  OpenAI (fallback)  →  MySQL  →  AI Search
```

### Step 1 — You click Upload (Browser → Flask)

The browser sends the file as a `multipart/form-data` POST request to the `/upload` endpoint.

**Code:** `app.py` → `upload_document()` function (`@app.route("/upload", methods=["POST"])`)

Flask first validates the request:
- Is a file present in the request?
- Is the file extension allowed? (`pdf`, `png`, `jpg`, `jpeg`, `tiff`)
- If either check fails → flash an error and redirect back to the home page. **No Azure calls happen.**

---

### Step 2 — File stored in Azure Blob Storage

**Code:** `services/blob_storage.py` → `BlobStorageService.upload_document()`

- A **random UUID filename** is generated (e.g. `3f7a1b2c-uuid.pdf`) so two uploads of the same original filename never overwrite each other.
- `ensure_container()` checks that the blob container exists and creates it if not.
- The file bytes are streamed directly to **Azure Blob Storage**.
- Returns a dict `{ blob_name, blob_url, original_filename }` that is passed through all later steps.

> Authentication uses **Managed Identity / DefaultAzureCredential** — no storage account key or secret is ever stored in code.

---

### Step 3 — Clinical data extracted by Azure AI Document Intelligence

**Code:** `services/document_intelligence.py` → `DocumentIntelligenceService.extract_from_pdf()`

- The file stream is re-wound (`seek(0)`) and the raw bytes are sent to **Azure AI Document Intelligence** using the `prebuilt-layout` model.
- The model reads the form and returns two things:
  - **Key-value pairs** — e.g. `"Patient Name" → "Rajesh Sharma"` with a confidence score
  - **Full page text** — every line on every page concatenated
- `_parse_result()` maps raw detected keys to the clinical schema:

  | Schema field | Detected keys searched |
  |---|---|
  | `patient_name` | "patient name", "name", "full name", "patient" |
  | `date_of_birth` | "date of birth", "dob", "d.o.b", "birth date" |
  | `symptoms` | "symptoms", "presenting symptoms", "chief complaint" |
  | `existing_conditions` | "existing conditions", "medical history", "conditions" |
  | `medications` | "medications", "current medications", "drugs" |
  | `allergies` | "allergies", "known allergies", "allergy" |
  | `referral_reason` | "referral reason", "reason for referral", "referral" |

  Each field comes back as `{ "value": "...", "confidence": 0.94 }` — the confidence score is provided directly by Document Intelligence.

---

### Step 4 — OpenAI fallback (only if Document Intelligence missed fields)

**Code:** `services/document_intelligence.py` → `_parse_result()` (bottom section)  
**Code:** `services/openai_service.py` → `OpenAIService.enhance_extraction()`

If Document Intelligence returned **no patient name** (e.g. a scanned image with an unusual layout), the full raw page text is sent to **Azure OpenAI** (GPT) with a prompt asking it to extract all fields and return structured JSON:

```
"Extract patient_name, date_of_birth, symptoms, existing_conditions,
 medications, allergies, referral_reason from this text. Return JSON only."
```

GPT's response backfills any empty fields. This is a **safety net** — for clean, well-structured PDFs it usually does **not** trigger.

---

### Step 5 — Record saved to Azure MySQL

**Code:** `services/database.py` → `DatabaseService.save_patient_record()`

- Pulls the `.value` string out of each field dict.
- Calls `_assess_urgency()` — scans the symptoms text for keywords to decide priority:
  - `"chest pain"`, `"severe"`, `"emergency"`, `"acute"` → **High**
  - `"persistent"`, `"recurring"`, `"worsening"` → **Medium**
  - Everything else → **Normal**
- Inserts one row into the `patient_records` MySQL table with: all clinical fields, confidence scores (stored as a JSON string), blob name, original filename, and urgency level.
- Returns the new **record ID** (auto-increment primary key).

---

### Step 6 — Record indexed in Azure AI Search

**Code:** `services/search_service.py` → `SearchService.index_patient_record()`

The fresh record is re-fetched from MySQL then pushed into the **Azure AI Search index**:
- All text fields (`symptoms`, `existing_conditions`, `referral_reason`, `full_text`) become **full-text searchable**.
- `urgency_level` and `upload_date` are **filterable and sortable**.
- This index is what powers both the `/search` page and the RAG assistant — both query it to find relevant patients.

---

### Step 7 — You see the Patient Detail page

`app.py` redirects to `/patients/<record_id>`. That route fetches the row from MySQL and renders `patient_detail.html` showing all extracted fields alongside their confidence scores.

---

### Full Pipeline at a Glance

```
You upload a file
        │
        ▼
[app.py] upload_document()
        │
        ├─ Step 2 ──▶ [blob_storage.py] upload_document()
        │                  Saves file to Azure Blob Storage
        │                  Returns: blob_name, blob_url
        │
        ├─ Step 3 ──▶ [document_intelligence.py] extract_from_pdf()
        │                  Sends bytes to Azure DI (prebuilt-layout model)
        │                  Parses key-value pairs → clinical fields + confidence scores
        │                       │
        │                       └─(Step 4: only if DI found no patient name)
        │                            ▶ [openai_service.py] enhance_extraction()
        │                                GPT reads raw page text → returns JSON fields
        │
        ├─ Step 5 ──▶ [database.py] save_patient_record()
        │                  Keyword-based urgency assessment
        │                  Inserts row into Azure MySQL
        │                  Returns: record_id
        │
        └─ Step 6 ──▶ [search_service.py] index_patient_record()
                           Pushes record into Azure AI Search index
                           Makes it searchable + available to the RAG assistant

        ▼
Step 7: Redirect → /patients/<record_id>
        Patient detail page rendered with all extracted fields and confidence scores
```

---

## How Reading a Patient Record Works — Step by Step

> **For students:** Once a document has been uploaded and processed, there are **three separate user actions** that each trigger a different read path. None of them re-run Document Intelligence — the extraction already happened at upload time. This section explains what actually gets called for each action.

---

### Action A — Viewing the Patient List (`/patients`)

**Code:** `app.py` → `patients()` route → `DatabaseService.get_all_patients()`

```
Browser  →  Flask (app.py)  →  MySQL  →  patients.html
```

1. You navigate to `/patients`.
2. Flask calls `db_service.get_all_patients()` in `services/database.py`.
3. That runs a single SQL query: `SELECT * FROM patient_records ORDER BY upload_date DESC`.
4. MySQL returns every row as a list of dicts.
5. Flask passes the list to `patients.html` which renders one card per patient.

> **No Document Intelligence. No OpenAI. No Azure AI Search.** Just a straight SQL SELECT.

---

### Action B — Opening a Patient Detail Page (`/patients/<id>`)

**Code:** `app.py` → `patient_detail()` route → `DatabaseService.get_patient_by_id()`

```
Browser  →  Flask (app.py)  →  MySQL  →  patient_detail.html
```

1. You click on a patient name (or navigate to `/patients/5`).
2. Flask calls `db_service.get_patient_by_id(patient_id)` in `services/database.py`.
3. That runs: `SELECT * FROM patient_records WHERE id = 5`.
4. MySQL returns the single row — all the fields that were extracted and saved at upload time.
5. Flask renders `patient_detail.html` with that data.

The template reads the `confidence_scores` column (stored as a JSON string) and uses the custom `fromjson` Jinja2 filter to parse it into a Python dict so it can display a coloured confidence bar for each field.

> **No Document Intelligence. No OpenAI. No Azure AI Search.** The extracted data was already saved to MySQL during upload — reading it back is just a SQL lookup.

---

### Action C — Clicking "Generate AI Summary" (on the detail page)

This is where **OpenAI is called for the first time during reading**. It is triggered on demand by a button click, not automatically on page load.

```
Browser  →  JavaScript fetch()  →  Flask /patients/<id>/summary  →  MySQL  →  Azure OpenAI  →  JSON response  →  Browser
```

**Step-by-step:**

1. **Button click** — `patient_detail.html` has a "Generate AI Summary" button. Clicking it calls the `generateSummary(patientId)` JavaScript function.

2. **JavaScript fetches the API** — The browser sends a `GET` request to `/patients/<id>/summary` (no page reload — it's an AJAX call).

3. **Flask fetches from MySQL** — `app.py` → `patient_summary()` calls `db_service.get_patient_by_id(patient_id)` again. This re-reads the already-saved data from MySQL.  
   **Why re-read?** The route needs the full record to pass to OpenAI. It does not re-run Document Intelligence.

4. **OpenAI generates the summary** — Flask calls `openai_service.summarise_patient(record)` in `services/openai_service.py`.  
   - The patient record (all fields except `full_text`) is serialised to JSON.
   - That JSON is sent to **Azure OpenAI** (GPT) as a user message.
   - The system prompt instructs the model to produce a concise clinical summary with urgency assessment and recommended next steps.
   - GPT returns the summary text.
   - `max_completion_tokens=800` caps the response length.

5. **JSON response → Browser** — Flask returns `{ "summary": "..." }` as JSON. The JavaScript inserts it into the page.

> **No Document Intelligence. No Azure AI Search.** Just MySQL + OpenAI.

---

### Action D — Using the Search Page (`/search?q=chest pain`)

**Code:** `app.py` → `search()` route → `SearchService.search()`

```
Browser  →  Flask (app.py)  →  Azure AI Search  →  search.html
```

1. You type a query and submit it.
2. Flask calls `search_service.search(query="chest pain", filters=None)` in `services/search_service.py`.
3. Azure AI Search performs **full-text search** across `symptoms`, `existing_conditions`, `referral_reason`, `full_text`, and `patient_name` fields in the index.
4. Results are returned ranked by relevance. An optional OData filter like `urgency_level eq 'High'` can narrow results further.
5. Flask passes the results list to `search.html` for rendering.

> **No Document Intelligence. No OpenAI. No MySQL.** The search index was built at upload time — querying it skips the database entirely.

---

### Action E — Asking the AI Triage Assistant (`/assistant`)

This is the full **RAG (Retrieval-Augmented Generation)** pattern in action.

```
Browser  →  Flask /api/assistant  →  Azure AI Search (retrieve)  →  Azure OpenAI (generate)  →  JSON response  →  Browser
```

**Code:** `app.py` → `api_assistant()` → `openai_service.ask_triage_assistant()`  
**Code:** `services/openai_service.py` → `ask_triage_assistant()`

**Step-by-step:**

1. **You type a question** — e.g. `"Which patients have chest pain?"` The JavaScript POSTs it to `/api/assistant` along with the conversation history.

2. **Step R — Retrieve** — `search_service.search(query=user_question, top=5)` queries **Azure AI Search** for the 5 most relevant patient records. This returns real data from the index.

3. **Format context** — The retrieved records are formatted into a block of text:
   ```
   --- Record 1 ---
   Patient: Sarah Johnson
   Symptoms: Persistent chest pain radiating to left arm...
   Urgency: High
   ...
   ```

4. **Step G — Generate** — The formatted context is combined with your question into a prompt and sent to **Azure OpenAI**:
   - The system prompt (from `prompts/system_messages.py`) sets the AI's persona as a clinical triage assistant with guardrails.
   - The conversation history is included for multi-turn awareness.
   - GPT generates a grounded answer based only on the retrieved records.
   - `max_completion_tokens=1024` caps the response.

5. **Response returned** — Flask returns `{ "answer": "..." }` as JSON. The JavaScript appends it to the chat.

> **No Document Intelligence. No MySQL.** RAG uses Azure AI Search to retrieve context, then OpenAI to generate the response.

---

### Summary: Which Services Are Called for Each Action?

| User Action | MySQL | Azure AI Search | Azure OpenAI | Doc Intelligence |
|---|:---:|:---:|:---:|:---:|
| View patient list (`/patients`) | ✅ | — | — | — |
| View patient detail (`/patients/<id>`) | ✅ | — | — | — |
| Generate AI Summary (button on detail page) | ✅ | — | ✅ | — |
| Search (`/search?q=...`) | — | ✅ | — | — |
| Ask AI Assistant (`/assistant`) | — | ✅ | ✅ | — |
| **Upload a new document** | ✅ | ✅ | ✅ (fallback only) | ✅ |

> **Key insight for students:** Document Intelligence only runs **once** — at upload time. Everything after that reads from the data that was already extracted and stored. The AI assistant never looks at the original PDF again.

---

## Technology Stack

| Layer | Azure Service | Tier |
|-------|--------------|------|
| Web App | Flask (local / Azure App Service) | Local dev / B1 |
| File Storage | Azure Blob Storage | LRS Hot |
| AI Extraction | Azure AI Document Intelligence | Free (F0) |
| Database | Azure MySQL Flexible Server | Burstable B1ms (Free) |
| Search | Azure AI Search | Basic |
| AI Assistant | Azure OpenAI (GPT-4o) | Standard (low token) |
| Auth (starter) | API Keys via `.env` | — |
| Auth (advanced) | Azure Managed Identity + Key Vault | Standard |

---

## Project Structure

```
├── app.py                        # Flask application (main entry point)
├── config.py                     # Configuration — reads .env; supports apikey + managed modes
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variable template (copy to .env)
│
├── services/                     # Azure service integrations
│   ├── blob_storage.py           # Azure Blob Storage
│   ├── document_intelligence.py  # Azure AI Document Intelligence
│   ├── database.py               # Azure MySQL Flexible Server
│   ├── search_service.py         # Azure AI Search
│   └── openai_service.py         # Azure OpenAI (RAG)
│
├── prompts/
│   └── system_messages.py        # AI model system messages & guardrails
│
├── templates/                    # HTML templates (Jinja2)
│   ├── base.html                 # Base layout
│   ├── index.html                # Upload portal
│   ├── patients.html             # Patient records list
│   ├── patient_detail.html       # Individual patient view
│   ├── search.html               # Intelligent search
│   └── assistant.html            # AI Triage Assistant chat
│
├── static/
│   ├── css/style.css             # Custom styles
│   └── js/app.js                 # Frontend JavaScript
│
├── scripts/
│   ├── student/                  # ← STUDENTS: run these in order
│   │   ├── README.md             # Step-by-step instructions
│   │   ├── 1_create_database.py          # Step 1 — create MySQL table
│   │   ├── 2_create_search_index.py      # Step 2 — create AI Search index
│   │   ├── 3_generate_test_documents.py  # Step 3 — generate sample PDFs/images
│   │   └── 4_load_sample_data.py         # Step 4 — load sample patient records
│
└── sample_data/
    ├── sample_intake_records.json # Sample patient data
    └── test_documents/           # Generated by 3_generate_test_documents.py
```

---

## Quick Start — Student Setup Guide

Follow these steps in order. Each step tells you exactly where to go in the Azure Portal and what to copy into your `.env` file.

---

### Prerequisites
- Python 3.10+
- An Azure subscription (use your student account or the free trial)
- A modern browser

---

### Step 1 — Get the code running locally

```bash
# Create a virtual environment and install dependencies
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Then copy the environment template:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` in a text editor — you will fill it in as you create each Azure resource below.

---

### Step 2 — Create Azure Resources in the Portal

Log in to the [Azure Portal](https://portal.azure.com) and create the following five resources. Use the same **Resource Group** and **Region** for all of them (e.g. `rg-zenith-capstone` in `Australia East`).

---

#### 2a — Azure Blob Storage

1. Search for **Storage accounts** → **Create**
2. Settings to use:
   - Redundancy: **Locally-redundant storage (LRS)**
   - Access tier: **Hot**
3. After creation, go to the resource → **Security + networking** → **Access keys**
4. Click **Show** next to Key 1 → copy the **Connection string**
5. Paste it into `.env`:
   ```
   AZURE_STORAGE_CONNECTION_STRING=<paste here>
   ```

---

#### 2b — Azure AI Document Intelligence

1. Search for **Document Intelligence** (under AI + Machine Learning) → **Create**
2. Pricing tier: **Free (F0)** — enough for this project
3. After creation, go to the resource → **Keys and Endpoint**
4. Copy **Endpoint** and **Key 1**, paste into `.env`:
   ```
   DOCUMENT_INTELLIGENCE_ENDPOINT=https://YOUR_RESOURCE.cognitiveservices.azure.com/
   DOCUMENT_INTELLIGENCE_KEY=<paste key here>
   ```

---

#### 2c — Azure MySQL Flexible Server

1. Search for **Azure Database for MySQL flexible servers** → **Create** → **Flexible server**
2. Settings:
   - Admin username: choose a username (e.g. `zenith_admin`)
   - Admin password: choose a strong password (save it — you will need it)
   - MySQL version: **8.0**
   - Compute tier: **Burstable**, size **B1ms** (free tier eligible)
3. On the **Networking** tab: enable **Allow public access from Azure services** and add your current IP address
4. After creation, go to the resource → **Overview** → copy the **Server name** (ends in `.mysql.database.azure.com`)
5. SSL certificate:
   - The file `DigiCertGlobalRootCA.crt.pem` is **already included** in the project root — no download needed.
   - If the file is missing, download it from [DigiCertGlobalRootCA.crt.pem](https://dl.cacerts.digicert.com/DigiCertGlobalRootCA.crt.pem) and save it in the **root of this project folder**
6. Paste into `.env`:
   ```
   AZURE_MYSQL_HOST=YOUR_SERVER.mysql.database.azure.com
   AZURE_MYSQL_USERNAME=YOUR_ADMIN_USERNAME
   AZURE_MYSQL_PASSWORD=YOUR_ADMIN_PASSWORD
   AZURE_MYSQL_SSL_CA=DigiCertGlobalRootCA.crt.pem
   ```

---

#### 2d — Azure AI Search

1. Search for **AI Search** (formerly Cognitive Search) → **Create**
2. Pricing tier: **Basic** (lowest tier that supports indexing)
3. After creation, go to the resource → **Overview** → copy the **URL**
4. Go to **Keys** → copy the **Primary admin key**
5. Paste into `.env`:
   ```
   AZURE_SEARCH_ENDPOINT=https://YOUR_SERVICE.search.windows.net
   AZURE_SEARCH_KEY=<paste primary admin key>
   ```

---

#### 2e — Azure OpenAI

1. Search for **Azure OpenAI** → **Create**
   > If you don't see Azure OpenAI, your subscription may need to be approved. Ask your lecturer.
2. After creation, go to the resource → **Keys and Endpoint**
3. Copy **Endpoint** and **Key 1**, paste into `.env`:
   ```
   AZURE_OPENAI_ENDPOINT=https://YOUR_RESOURCE.openai.azure.com/
   AZURE_OPENAI_KEY=<paste key here>
   ```
4. Now deploy a model: go to **Model deployments** → **Manage deployments** → **Deploy model** → choose **gpt-4o**
5. Give the deployment a name (e.g. `gpt-4o`), then paste that name into `.env`:
   ```
   AZURE_OPENAI_DEPLOYMENT=gpt-4o
   ```

---

### Step 3 — Initialise the Database

With all `.env` values filled in, create the MySQL database table:

```bash
python scripts/student/1_create_database.py
```

You should see: `Database tables created successfully!`

> **Note:** This script is safe to re-run. If the table already exists, it will skip creation gracefully.

---

### Step 4 — Create the Search Index

```bash
python scripts/student/2_create_search_index.py
```

You should see: `Search index 'patient-intake-index' created/updated.`

> **Note:** This script is safe to re-run. If the index already exists, it will update the schema rather than fail.

---

### Step 5 — Generate Test Documents and Load Sample Data (Optional but recommended)

Generate sample intake form files you can upload:

```bash
python scripts/student/3_generate_test_documents.py
```

Then load pre-built patient records into the database and search index:

```bash
python scripts/student/4_load_sample_data.py
```

---

### Step 6 — Run the Application

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

---

### Advanced Option — Managed Identity (AUTH_MODE=auto or AUTH_MODE=managed)

If your organisation disables API key access on Azure resources (common in universities and enterprises), or you want to follow production best practices, use Managed Identity instead of API keys.

There are two modes that use Managed Identity:

| Mode | When to use |
|------|-------------|
| `auto` | Org disables key auth on **some** resources (e.g. Storage only). The app uses your `.env` keys for services that accept them and falls back to Managed Identity for any that reject key auth. |
| `managed` | Org disables key auth on **all** resources, or you want full production-grade auth. Every service uses Managed Identity. MySQL password comes from Key Vault. |

**Step 1 — Run `az login`**

```bash
az login
```

This lets `DefaultAzureCredential` use your Azure account locally. You must be logged in before starting the app.

---

**Step 2 — Update `.env`**

For `auto` mode (recommended when only some services block key auth):
```
AUTH_MODE=auto
AZURE_STORAGE_ACCOUNT_NAME=<your storage account name>
```

For `managed` mode (all services use Managed Identity):
```
AUTH_MODE=managed
AZURE_STORAGE_ACCOUNT_NAME=<your storage account name>
AZURE_KEY_VAULT_URL=https://YOUR_KEYVAULT.vault.azure.net/
```

> In `managed` mode, create a **Key Vault**, add a secret named `mysql-admin-password` with your MySQL password, and assign yourself the **Key Vault Secrets User** role on the vault.

---

**Step 3 — Assign RBAC roles in the Azure Portal**

This is the most important step. Each Azure service needs a specific role assigned to your user account before Managed Identity will work.

**How to assign any role (same steps for all services below):**
1. Go to [portal.azure.com](https://portal.azure.com) and open the resource
2. In the left menu → **Access Control (IAM)**
3. Click **+ Add** → **Add role assignment**
4. Search for and select the role name listed below
5. Click **Next** → **Members** tab → **+ Select members**
6. Search for your user account email → select it → **Select**
7. Click **Review + assign**

> **RBAC changes take 2–5 minutes to propagate.** If you still get a 403 error immediately after assigning, wait a few minutes and retry.

---

#### Required roles — full reference

| Azure Resource | Role to assign | What it allows |
|----------------|---------------|----------------|
| **Storage account** | `Storage Blob Data Contributor` | Upload and download patient document files |
| **Document Intelligence** | `Cognitive Services User` | Send PDFs for AI extraction |
| **Azure OpenAI** | `Cognitive Services User` | Call GPT-4o for summaries and the triage assistant |
| **AI Search** | `Search Index Data Contributor` | Index and query patient records |
| **AI Search** | `Search Service Contributor` | Create and manage the search index schema |
| **Key Vault** *(managed mode only)* | `Key Vault Secrets User` | Read the `mysql-admin-password` secret at startup |

---

#### Detailed role assignment steps per resource

**Storage account** (your account name)
- Role: **Storage Blob Data Contributor**
- Portal path: Storage account → Access Control (IAM)

**Document Intelligence** (your resource name)
- Role: **Cognitive Services User**
- Portal path: Document Intelligence resource → Access Control (IAM)

**Azure OpenAI** (your resource name)
- Role: **Cognitive Services User**
- Portal path: Azure OpenAI resource → Access Control (IAM)

**Azure AI Search** (your resource name)
- Role 1: **Search Index Data Contributor**
- Role 2: **Search Service Contributor**
- Portal path: AI Search resource → Access Control (IAM)
- *(Assign both roles — two separate "Add role assignment" operations)*

> ⚠️ **Extra step required for AI Search — enable RBAC on the resource itself**
>
> Azure AI Search defaults to API key authentication only. Even after assigning the roles above, requests will still return **403 Forbidden** unless you explicitly allow token-based (RBAC) access on the resource.
>
> **Steps:**
> 1. Go to your AI Search resource in the Azure Portal
> 2. Left menu → **Settings** → **Keys**
> 3. Under **API Access Control**, change the setting from **"API keys"** to **"Both"**
> 4. Click **Save**
>
> The **"Both"** option allows the resource to accept either API keys **or** RBAC tokens — this is what is needed when running with `AUTH_MODE=auto` or `AUTH_MODE=managed`. Without this change, RBAC role assignments alone are not sufficient.

**Key Vault** *(managed mode only)*
- Role: **Key Vault Secrets User**
- Portal path: Key Vault resource → Access Control (IAM)

---

## Features

### 1. Patient Intake Upload
- Upload PDF or scanned intake forms
- Automatic extraction via Azure AI Document Intelligence
- Extracted fields: Patient Name, DOB, Symptoms, Conditions, Medications, Allergies, Referral Reason
- Confidence scores for each extracted field

### 2. Patient Records
- Structured storage in Azure MySQL Flexible Server
- Automatic urgency classification (High / Medium / Normal)
- Detailed patient view with extraction confidence visualisation

### 3. Intelligent Search (Knowledge Mining)
- Full-text search powered by Azure AI Search
- Filter by urgency level
- Search across symptoms, conditions, medications, referral reasons

### 4. AI Triage Assistant (RAG)
- Conversational AI interface powered by Azure OpenAI GPT-4o
- Retrieval-Augmented Generation using indexed patient records
- Example queries:
  - "Show patients with chest pain in last 7 days"
  - "Summarise this patient's intake"
  - "What specialist referral is recommended?"
- AI-generated clinical summaries per patient
- Responsible AI guardrails — always states: *"This system provides informational assistance and does not replace clinical judgement."*

---

## Responsible AI & Healthcare Governance

| Principle | Implementation |
|-----------|---------------|
| **Patient Data Privacy** | MySQL encryption at rest, HTTPS in transit, no PII in logs |
| **Access Control** | API keys via .env (starter) or Managed Identity + Key Vault (advanced) |
| **Ethical AI Use** | System prompt guardrails, disclaimer on all AI outputs |
| **Bias Mitigation** | Keyword-based + AI urgency classification, transparent reasoning |
| **Model Transparency** | Confidence scores displayed, AI explains its reasoning |
| **Logging & Monitoring** | Python logging, Azure App Service diagnostics |
| **Content Filtering** | Azure OpenAI built-in content safety filters |

---

## Learning Outcome Alignment

| Learning Outcome | Implementation |
|-----------------|----------------|
| LO1 — Infrastructure | Secure Azure pipeline (Blob → DocIntel → MySQL → Search → OpenAI) |
| LO2 — AI Algorithms | OCR extraction, NLP search, keyword urgency classification, GenAI |
| LO3 — Autonomous Agents | RAG-based AI triage assistant with guardrails |
| LO4 — End-to-End Workflow | Intake → Extraction → Index → RAG → Clinical Output |

---

## Budget Estimate

| Service | Tier | Est. Monthly Cost (AUD) |
|---------|------|------------------------|
| Azure Storage | LRS Hot | ~$1 |
| Document Intelligence | Free (F0) | $0 |
| Azure AI Search | Basic | ~$15 |
| Azure OpenAI | Standard (low usage) | ~$5–15 |
| Azure MySQL Flexible | Burstable B1ms Free | $0 |
| **Total** | | **~$21–31** |

> Tip: Delete or stop resources when not in use to minimise costs.

---

## Troubleshooting

This section covers the most common errors students encounter when running the application locally, along with their root causes and fixes. Most problems fall into two categories: **missing RBAC role assignments** and **network access being disabled**.

---

### Quick Checklist

Before diving into specific errors, verify these fundamentals:

- [ ] You have run `az login` in the terminal (required for `AUTH_MODE=managed`)
- [ ] All Azure resources are in the **same resource group and region**
- [ ] The MySQL Flexible Server is **Running** (not Stopped — Azure pauses burstable servers after periods of inactivity)
- [ ] The `DigiCertGlobalRootCA.crt.pem` file is in the **project root folder**

---

### RBAC Role Requirements

When `AUTH_MODE=managed`, the application uses `DefaultAzureCredential` (your Azure CLI identity locally, or a Managed Identity in production). That identity must have the correct role assigned on each Azure resource. Missing roles cause `AuthorizationFailure` or `Forbidden` errors with no other explanation.

Use the following table to verify your role assignments. In the Azure Portal, open each resource → **Access control (IAM)** → **View my access**.

| Azure Resource | Required Role | Who needs it |
|---|---|---|
| **Azure Blob Storage** | `Storage Blob Data Contributor` | Your user account (local dev) |
| **Azure Key Vault** | `Key Vault Secrets User` | Your user account (local dev) |
| **Azure AI Search** | `Search Index Data Contributor` | Your user account (local dev) |
| **Azure AI Search** | `Search Service Contributor` | Your user account (local dev) if creating/updating indexes |
| **Azure AI Document Intelligence** | `Cognitive Services User` | Your user account (local dev) |
| **Azure OpenAI** | `Cognitive Services OpenAI User` | Your user account (local dev) |

> **Note for `AUTH_MODE=apikey`:** Role assignments are not required — API keys bypass RBAC. However, the network access rules below still apply.

#### How to assign a missing role

1. Open the resource in the Azure Portal (e.g. your Storage Account)
2. Click **Access control (IAM)** in the left menu
3. Click **+ Add** → **Add role assignment**
4. Search for the role name from the table above, click **Next**
5. Under **Members**, click **+ Select members** → search for your account email → select it
6. Click **Review + assign**

Role propagation can take **1–5 minutes**. Wait before retrying.

---

### Network Access Requirements

Azure resources created with default-secure settings often have **public network access disabled**, which blocks all traffic from your local machine — even if your RBAC roles are correct. This produces errors like:

- `ForbiddenByConnection` — Key Vault
- `AuthorizationFailure` — Blob Storage / AI Search
- `Public network access is disabled` — any resource

Each resource needs public network access **enabled** for local development.

#### Azure Key Vault

**Error:** `(Forbidden) Public network access is disabled and request is not from a trusted service`

**Fix:**
```bash
az keyvault update --name <your-keyvault-name> --public-network-access Enabled
```

Or in the Portal: Key Vault → **Networking** → **Firewalls and virtual networks** → set **Public network access** to **Enabled from all networks** (or **Enabled from specific virtual networks and IP addresses** and add your IP).

---

#### Azure Blob Storage

**Error:** `AuthorizationFailure — This request is not authorized to perform this operation`

**Fix:**
```bash
az storage account update \
  --name <your-storage-account-name> \
  --resource-group <your-resource-group> \
  --public-network-access Enabled
```

Or in the Portal: Storage Account → **Networking** → **Firewalls and virtual networks** → set to **Enabled from all networks**.

> **Important:** `allowSharedKeyAccess` must also be `true` if using connection strings (`AUTH_MODE=apikey`). In the Portal: Storage Account → **Configuration** → **Allow storage account key access** → **Enabled**.

---

#### Azure AI Search

**Error:** `403 Forbidden` when indexing or searching

**Fix:**
```bash
az search service update \
  --name <your-search-service-name> \
  --resource-group <your-resource-group> \
  --public-network-access enabled
```

Or in the Portal: AI Search → **Networking** → set **Public network access** to **Enabled**.

---

#### Azure AI Document Intelligence

**Error:** `Access denied` or `403` when analysing a document

**Fix in Portal:** Document Intelligence resource → **Networking** → set **Allow access from** to **All networks**.

---

#### Azure OpenAI

**Error:** `403` or `PermissionDenied` when calling the completions endpoint

**Fix in Portal:** Azure OpenAI resource → **Networking** → set to **All networks** (or add your IP under **Selected networks and private endpoints**).

---

### Troubleshooting — Authentication Errors

#### `KeyBasedAuthenticationNotPermitted`

```
Error processing document: Key based authentication is not permitted on this storage account.
```

**Cause:** The storage account has "Allow storage account key access" disabled by org policy.  
**Fix:** Set `AUTH_MODE=auto` in `.env`, ensure `AZURE_STORAGE_ACCOUNT_NAME` is set, run `az login`, and assign **Storage Blob Data Contributor** as above.

---

#### `AuthorizationPermissionMismatch` or `403 Forbidden`

```
Error processing document: This request is not authorized to perform this operation using this permission.
```

**Cause:** Managed Identity auth succeeded, but your account lacks the RBAC role for that service.  
**Fix:** Assign the missing role from the table above. Wait 2–5 minutes for propagation, then retry.

---

#### `401 Access denied due to invalid subscription key`

```
Error processing document: Access denied due to invalid subscription key or wrong API endpoint.
```

**Cause:** Running in `apikey` mode but the API key in `.env` is missing, incorrect, or the org has disabled key auth on that service (Document Intelligence or OpenAI).  
**Fix:** Switch to `AUTH_MODE=auto` and assign **Cognitive Services User** on the affected resource.

---

#### Quick reference — which `AUTH_MODE` should I use?

| Situation | Recommended `AUTH_MODE` |
|-----------|------------------------|
| Just starting out, no org restrictions | `apikey` |
| Org disables key auth on some resources | `auto` |
| Org disables key auth on all resources | `managed` |
| Production / deployed to Azure | `managed` |

---

### Common Error Reference

| Error Message | Most Likely Cause | Fix |
|---|---|---|
| `Public network access is disabled ... ForbiddenByConnection` | Key Vault public access disabled | `az keyvault update --public-network-access Enabled` |
| `AuthorizationFailure` on blob upload/download | Storage public access disabled **or** missing `Storage Blob Data Contributor` role | Enable public access + check RBAC |
| `Lost connection to MySQL server at 'reading initial communication packet'` | MySQL Flexible Server is **Stopped** | `az mysql flexible-server start --resource-group <rg> --name <server>` |
| `SSL connection error` / MySQL SSL failure | `DigiCertGlobalRootCA.crt.pem` missing from project root | Download cert — see Step 2c above |
| `Key Vault secret not found` | Secret name mismatch or missing `Key Vault Secrets User` role | Verify secret is named `mysql-admin-password`; check IAM |
| `Search index not found` | Index not yet created | Run `python scripts/student/2_create_search_index.py` |
| `No module named ...` | Virtual environment not activated | Run `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (macOS/Linux) |
| `AZURE_MYSQL_PASSWORD is not set` | Running `AUTH_MODE=apikey` without a password in `.env` | Add `AZURE_MYSQL_PASSWORD=<your password>` to `.env` |
| `DefaultAzureCredential failed` | Not logged in to Azure CLI | Run `az login` then retry |

---

### Checking Resource States via Azure CLI

Use these commands to quickly check the state of each resource from your terminal:

```bash
# Check MySQL server state (should be "Ready")
az mysql flexible-server show \
  --resource-group <rg> --name <server> \
  --query "{state:state}" -o table

# Check Key Vault public network access
az keyvault show --name <vault> \
  --query "properties.publicNetworkAccess" -o tsv

# Check Storage Account public network access
az storage account show \
  --name <account> --resource-group <rg> \
  --query "{publicNetworkAccess:publicNetworkAccess, allowSharedKey:allowSharedKeyAccess}" -o table

# List your RBAC assignments on a storage account
az role assignment list \
  --scope "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.Storage/storageAccounts/<account>" \
  --assignee <your-email> \
  --query "[].{role:roleDefinitionName}" -o table

# List your RBAC assignments on a Key Vault
az role assignment list \
  --scope "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.KeyVault/vaults/<vault>" \
  --assignee <your-email> \
  --query "[].{role:roleDefinitionName}" -o table
```

