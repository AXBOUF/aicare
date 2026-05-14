# Student Scripts

Run these scripts **in order** after filling in your `.env` file.
Each script corresponds to one setup step. They all read your Azure credentials from `.env` — no
command-line arguments needed.

> Make sure your virtual environment is active and you are in the **project root** before running
> any script.

---

## Workflow

| # | Script | What it does | Needs app running? |
|---|--------|-------------|:-----------------:|
| 1 | `1_create_database.py` | Creates the `patient_records` table in your MySQL Flexible Server | No |
| 2 | `2_create_search_index.py` | Creates the `patient-intake-index` in your Azure AI Search service | No |
| 3 | `3_generate_test_documents.py` | Generates sample PDF / PNG / JPG intake forms in `sample_data/test_documents/` | No |
| 4 | `4_load_sample_data.py` | Loads 5 pre-built patient records into MySQL and the Search index | No |

---

## How to run

```bash
# From the project root (with venv active):

python scripts/student/1_create_database.py
python scripts/student/2_create_search_index.py
python scripts/student/3_generate_test_documents.py
python scripts/student/4_load_sample_data.py
```

---

## Troubleshooting

| Error | Likely cause | Fix |
|-------|-------------|-----|
| `AZURE_MYSQL_PASSWORD is not set` | Missing value in `.env` | Open `.env` and fill in the MySQL password |
| `Can't connect to MySQL server` | Firewall / IP issue | Azure Portal → MySQL server → Networking → add your IP |
| `Connection refused (localhost:5000)` | App not running | Run `python app.py` in a separate terminal first |
| `ResourceNotFoundError` (Search) | Index doesn't exist yet | Run step 2 first |
| `AuthenticationError` | Wrong API key or endpoint | Check the `.env` values against the Azure Portal |
