# Zenith Healthcare AI Platform - Architecture Documentation

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     ZENITH HEALTHCARE AI PLATFORM                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │                    DATA INGESTION LAYER                       │       │
│  │                                                                │       │
│  │  ┌─────────────┐        ┌──────────────────────────┐         │       │
│  │  │  Flask Web   │───────▶│  Azure Blob Storage       │         │       │
│  │  │  Application │        │  (patient-intake-forms)   │         │       │
│  │  │  (Upload     │        │  LRS Hot Tier             │         │       │
│  │  │   Portal)    │        │  Encrypted at rest        │         │       │
│  │  └─────────────┘        └───────────┬──────────────┘         │       │
│  └──────────────────────────────────────┼───────────────────────┘       │
│                                          │                               │
│  ┌──────────────────────────────────────┼───────────────────────┐       │
│  │                AI PROCESSING LAYER    │                       │       │
│  │                                       ▼                       │       │
│  │  ┌────────────────────────────────────────────────┐           │       │
│  │  │  Azure AI Document Intelligence (Free F0)       │           │       │
│  │  │  - Prebuilt document model                      │           │       │
│  │  │  - Key-value pair extraction                    │           │       │
│  │  │  - Clinical field mapping                       │           │       │
│  │  │  - Confidence scoring                           │           │       │
│  │  └────────────────────┬───────────────────────────┘           │       │
│  └───────────────────────┼───────────────────────────────────────┘       │
│                           │                                               │
│  ┌───────────────────────┼───────────────────────────────────────┐       │
│  │              DATA STORAGE LAYER                                │       │
│  │                       ▼                                        │       │
│  │  ┌────────────────────────────────────────────────┐           │       │
│  │  │  Azure MySQL Flexible Server (Burstable B1ms Free)  │           │       │
│  │  │  - patient_records table                        │           │       │
│  │  │  - Structured clinical data                     │           │       │
│  │  │  - Confidence scores (JSON)                     │           │       │
│  │  │  - Urgency classification                       │           │       │
│  │  │  - SSL/TLS encrypted connections                │           │       │
│  │  └────────────────────┬───────────────────────────┘           │       │
│  └───────────────────────┼───────────────────────────────────────┘       │
│                           │                                               │
│  ┌───────────────────────┼───────────────────────────────────────┐       │
│  │              KNOWLEDGE LAYER                                   │       │
│  │                       ▼                                        │       │
│  │  ┌────────────────────────────────────────────────┐           │       │
│  │  │  Azure AI Search (Basic)                        │           │       │
│  │  │  - patient-intake-index                         │           │       │
│  │  │  - Full-text search                             │           │       │
│  │  │  - Filterable by urgency, symptoms, conditions  │           │       │
│  │  │  - Sortable by date, patient name               │           │       │
│  │  └────────────────────┬───────────────────────────┘           │       │
│  └───────────────────────┼───────────────────────────────────────┘       │
│                           │                                               │
│  ┌───────────────────────┼───────────────────────────────────────┐       │
│  │              GENERATIVE AI LAYER (RAG)                         │       │
│  │                       ▼                                        │       │
│  │  ┌────────────────────────────────────────────────┐           │       │
│  │  │  Azure OpenAI (GPT-4o)                          │           │       │
│  │  │  - RAG: Search → Augment → Generate             │           │       │
│  │  │  - Clinical system prompt with guardrails       │           │       │
│  │  │  - Content filtering enabled                    │           │       │
│  │  │  - Temperature 0.3 (focused, factual)           │           │       │
│  │  │  - Multi-turn conversation support              │           │       │
│  │  └────────────────────────────────────────────────┘           │       │
│  └───────────────────────────────────────────────────────────────┘       │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │              IDENTITY & SECURITY                              │       │
│  │  - Azure Managed Identity (DefaultAzureCredential)           │       │
│  │  - Azure Key Vault (SQL password, RBAC-based access)         │       │
│  │  - No API keys hardcoded in source code (keys via .env)      │       │
│  │  - RBAC role assignments for each Azure service              │       │
│  │  - HTTPS endpoints with TLS encryption                       │       │
│  │  - Python logging (structured, no PII)                       │       │
│  │  - Azure App Service diagnostics                             │       │
│  │  - Content safety filtering (Azure OpenAI built-in)          │       │
│  │  - Responsible AI disclaimers on all AI outputs              │       │
│  └──────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Sequences

### 1. Patient Intake Upload Flow
```
User → Flask App → Azure Blob Storage → Document Intelligence → Azure MySQL → Azure AI Search
```

### 2. Search Query Flow
```
User → Flask App → Azure AI Search → Results displayed
```

### 3. AI Triage Assistant Flow (RAG)
```
User Question → Azure AI Search (retrieve context) → Augmented Prompt → Azure OpenAI → Response
```

## Security Measures

| Measure | Implementation |
|---------|---------------|
| Encryption at rest | Azure Storage SSE, MySQL server-side encryption |
| Encryption in transit | TLS 1.2 for all connections |
| Authentication | Azure Managed Identity (DefaultAzureCredential) |
| Access control | RBAC role assignments, Key Vault for secrets, MySQL firewall rules |
| Input validation | File type checking, size limits (16 MB) |
| AI guardrails | System prompt constraints, content filtering |
| Logging | Structured Python logging, no PII in logs |

## Responsible AI Principles

1. **Transparency**: System clearly states it provides informational assistance only
2. **Fairness**: Urgency classification uses documented clinical criteria
3. **Privacy**: Patient data encrypted, access controlled, minimal PII in logs
4. **Accountability**: All AI outputs include disclaimers and cite source records
5. **Safety**: Content filtering enabled, guardrails prevent diagnostic claims
