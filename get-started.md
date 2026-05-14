# Get Started — Zenith Healthcare AI Platform

A concise step-by-step guide to get the template running locally and prepare Azure resources for development and testing.

## Purpose

This document summarizes the minimal steps to run the project locally, initialize Azure resources (via the provided student scripts), and verify the app is working.

## Prerequisites

- Python 3.10+
- An Azure subscription (for full pipeline features)
- A modern browser
- Access to the project root in a terminal

## Quick setup (local)

1. Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

2. Copy the environment template and fill values from the Azure Portal:

```bash
cp .env.example .env
# Edit .env and replace every YOUR_... placeholder
```

- Recommended `AUTH_MODE=apikey` for students.
- Place the SSL CA file `DigiCertGlobalRootCA.crt.pem` in the project root if using Azure MySQL.

3. Run the student setup scripts in order (they read `.env` automatically):

```bash
python scripts/student/1_create_database.py
python scripts/student/2_create_search_index.py
python scripts/student/3_generate_test_documents.py
python scripts/student/4_load_sample_data.py
```

4. Start the Flask application:

```bash
export FLASK_DEBUG=true   # optional for development
python app.py
```

5. Open the app in your browser: `http://localhost:5000`

## Verify basic functionality

- Visit `/patients` to see loaded sample records.
- Upload a sample PDF from the home page to exercise upload → extract → store → index.
- Use `/assistant` to test the RAG triage assistant (requires Azure OpenAI + Search).

## Environment variables (high level)

Fill Section A in `.env` (apikey mode):

- `FLASK_SECRET_KEY`
- `AZURE_STORAGE_CONNECTION_STRING`, `AZURE_STORAGE_CONTAINER`
- `DOCUMENT_INTELLIGENCE_ENDPOINT`, `DOCUMENT_INTELLIGENCE_KEY`
- `AZURE_MYSQL_HOST`, `AZURE_MYSQL_DATABASE`, `AZURE_MYSQL_USERNAME`, `AZURE_MYSQL_PASSWORD`, `AZURE_MYSQL_SSL_CA`
- `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_KEY`, `AZURE_SEARCH_INDEX`
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`

See `.env.example` for full variable names and comments.

## Optional: local-only development

If you don't have Azure resources available, you can:

- Stub or modify the service implementations in `services/` to use local mocks (filesystem + SQLite) — this requires code changes.
- Or run the app and use the UI for non-upload pages; uploads will fail without real Azure credentials.

## Troubleshooting

- `Can't connect to MySQL server`: add your IP under your Azure MySQL Networking settings.
- `ResourceNotFoundError` for Search: run `2_create_search_index.py` first.
- `AuthenticationError`: check endpoints and keys in `.env` against the Azure Portal.

## Key files to review

- `app.py` — Flask entry point and routes
- `config.py` — reads `.env` and configures services
- `services/blob_storage.py`, `services/document_intelligence.py`, `services/database.py`, `services/search_service.py`, `services/openai_service.py` — Azure integrations
- `scripts/student/` — setup helper scripts (run these in order)

## Next steps

- Want me to create a `local-dev` branch that stubs Azure services with SQLite and local files? (I can scaffold it.)
- Or shall I attempt to run the student scripts here and report any errors?

---

Created from project template to help you get started quickly.
