"""
Zenith Healthcare AI Platform - Flask Application
Main entry point for the web application.

Serves both:
1. React SPA frontend (built to /Pixel Perfect/dist/)
2. JSON API endpoints for React components
"""

import os
import json
import logging
from pathlib import Path
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, jsonify, session, send_from_directory,
)
from flask_cors import CORS
from config import Config
from services.blob_storage import BlobStorageService
from services.document_intelligence import DocumentIntelligenceService
from services.database import DatabaseService
from services.search_service import SearchService
from services.openai_service import OpenAIService

# ──────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Flask App
# ──────────────────────────────────────────────────────────────
# Determine if we're using React SPA (production) or Jinja2 templates (legacy)
REACT_BUILD_PATH = Path(__file__).parent / "Pixel Perfect" / "dist"
USING_REACT = REACT_BUILD_PATH.exists()

if USING_REACT:
    app = Flask(__name__, static_folder=str(REACT_BUILD_PATH), static_url_path="")
else:
    app = Flask(__name__)

app.secret_key = Config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB upload limit

# Enable CORS for API endpoints
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Register custom Jinja2 filters
app.jinja_env.filters['fromjson'] = json.loads

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "tiff"}

# ──────────────────────────────────────────────────────────────
# Service Instances
# ──────────────────────────────────────────────────────────────
blob_service = BlobStorageService()
doc_intel_service = DocumentIntelligenceService()
db_service = DatabaseService()
search_service = SearchService()
openai_service = OpenAIService()


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ──────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Home / Upload page."""
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_document():
    """
    Handle patient intake form upload:
    1. Upload PDF to Azure Blob Storage
    2. Extract data via Document Intelligence
    3. Save structured data to Azure MySQL
    4. Index record in Azure AI Search
    """
    if "file" not in request.files:
        flash("No file selected.", "error")
        return redirect(url_for("index"))

    file = request.files["file"]
    if file.filename == "" or not allowed_file(file.filename):
        flash("Please upload a valid PDF or image file.", "error")
        return redirect(url_for("index"))

    try:
        # 1. Upload to Blob Storage
        logger.info("Uploading file: %s", file.filename)
        blob_info = blob_service.upload_document(file.stream, file.filename)

        # 2. Extract clinical data
        logger.info("Extracting data from document...")
        file.stream.seek(0)
        patient_data = doc_intel_service.extract_from_pdf(file.stream.read())

        # 3. Save to database
        logger.info("Saving patient record...")
        record_id = db_service.save_patient_record(patient_data, blob_info)

        # 4. Index in search
        logger.info("Indexing patient record...")
        record = db_service.get_patient_by_id(record_id)
        if record:
            search_service.index_patient_record(record)

        flash(f"Successfully processed intake form for: "
              f"{patient_data.get('patient_name', {}).get('value', 'Unknown')}", "success")
        return redirect(url_for("patient_detail", patient_id=record_id))

    except Exception as e:
        logger.exception("Error processing upload")
        flash(f"Error processing document: {str(e)}", "error")
        return redirect(url_for("index"))


@app.route("/patients")
def patients():
    """List all patient records."""
    try:
        records = db_service.get_all_patients()
        return render_template("patients.html", patients=records)
    except Exception as e:
        logger.exception("Error fetching patients")
        flash(f"Error loading patient records: {str(e)}", "error")
        return render_template("patients.html", patients=[])


@app.route("/patients/<int:patient_id>")
def patient_detail(patient_id: int):
    """View individual patient record with AI summary."""
    try:
        record = db_service.get_patient_by_id(patient_id)
        if not record:
            flash("Patient record not found.", "error")
            return redirect(url_for("patients"))
        return render_template("patient_detail.html", patient=record)
    except Exception as e:
        logger.exception("Error fetching patient %d", patient_id)
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for("patients"))


@app.route("/patients/<int:patient_id>/summary")
def patient_summary(patient_id: int):
    """Generate an AI summary for a patient."""
    try:
        record = db_service.get_patient_by_id(patient_id)
        if not record:
            return jsonify({"error": "Patient not found"}), 404
        summary = openai_service.summarise_patient(record)
        return jsonify({"summary": summary})
    except Exception as e:
        logger.exception("Error generating summary for patient %d", patient_id)
        return jsonify({"error": str(e)}), 500


@app.route("/search")
def search():
    """Search patient records via Azure AI Search."""
    query = request.args.get("q", "").strip()
    urgency = request.args.get("urgency", "").strip()
    results = []

    if query or urgency:
        try:
            filters = f"urgency_level eq '{urgency}'" if urgency else None
            results = search_service.search(query=query or "*", filters=filters)
        except Exception as e:
            logger.exception("Search error")
            flash(f"Search error: {str(e)}", "error")

    return render_template("search.html", results=results, query=query, urgency=urgency)


@app.route("/assistant")
def assistant():
    """AI Triage Assistant chat interface."""
    return render_template("assistant.html")


@app.route("/api/assistant", methods=["POST"])
def api_assistant():
    """API endpoint for AI Triage Assistant queries."""
    data = request.get_json()
    if not data or not data.get("question"):
        return jsonify({"error": "No question provided"}), 400

    question = data["question"]
    conversation_history = data.get("history", [])

    try:
        answer = openai_service.ask_triage_assistant(question, conversation_history)
        return jsonify({"answer": answer})
    except Exception as e:
        logger.exception("Assistant error")
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────────────────────
# JSON API Endpoints (for React SPA)
# ──────────────────────────────────────────────────────────────
@app.route("/api/upload", methods=["POST"])
def api_upload_document():
    """
    API endpoint for file upload (React SPA).
    Returns submission ID and status tracking endpoint.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed. Use PDF, PNG, JPG, or TIFF."}), 400

    try:
        logger.info("API: Uploading file: %s", file.filename)
        blob_info = blob_service.upload_document(file.stream, file.filename)

        file.stream.seek(0)
        patient_data = doc_intel_service.extract_from_pdf(file.stream.read())

        record_id = db_service.save_patient_record(patient_data, blob_info)

        record = db_service.get_patient_by_id(record_id)
        if record:
            search_service.index_patient_record(record)

        return jsonify({
            "success": True,
            "submissionId": f"SUB-{record_id}",
            "recordId": record_id,
            "patientName": patient_data.get("patient_name", {}).get("value", "Unknown"),
        })

    except Exception as e:
        logger.exception("API: Error processing upload")
        return jsonify({"error": str(e)}), 500


@app.route("/api/patients", methods=["GET"])
def api_get_patients():
    """API endpoint: Get all patient records."""
    try:
        records = db_service.get_all_patients()
        return jsonify({
            "success": True,
            "patients": [dict(r) if not isinstance(r, dict) else r for r in records]
        })
    except Exception as e:
        logger.exception("API: Error fetching patients")
        return jsonify({"error": str(e)}), 500


@app.route("/api/patients/<int:patient_id>", methods=["GET"])
def api_get_patient(patient_id: int):
    """API endpoint: Get single patient record."""
    try:
        record = db_service.get_patient_by_id(patient_id)
        if not record:
            return jsonify({"error": "Patient not found"}), 404
        return jsonify({
            "success": True,
            "patient": dict(record) if not isinstance(record, dict) else record
        })
    except Exception as e:
        logger.exception("API: Error fetching patient %d", patient_id)
        return jsonify({"error": str(e)}), 500


@app.route("/api/patients/<int:patient_id>/summary", methods=["GET"])
def api_get_patient_summary(patient_id: int):
    """API endpoint: Get AI-generated summary for patient."""
    try:
        record = db_service.get_patient_by_id(patient_id)
        if not record:
            return jsonify({"error": "Patient not found"}), 404
        summary = openai_service.summarise_patient(record)
        return jsonify({"success": True, "summary": summary})
    except Exception as e:
        logger.exception("API: Error generating summary for patient %d", patient_id)
        return jsonify({"error": str(e)}), 500


@app.route("/api/search", methods=["GET"])
def api_search():
    """API endpoint: Search patient records."""
    query = request.args.get("q", "").strip()
    urgency = request.args.get("urgency", "").strip()
    results = []

    if query or urgency:
        try:
            filters = f"urgency_level eq '{urgency}'" if urgency else None
            results = search_service.search(query=query or "*", filters=filters)
        except Exception as e:
            logger.exception("API: Search error")
            return jsonify({"error": str(e)}), 500

    return jsonify({"success": True, "results": results})


# ──────────────────────────────────────────────────────────────
# React SPA Fallback Routing
# ──────────────────────────────────────────────────────────────
@app.route("/api/config", methods=["GET"])
def api_config():
    """API endpoint: Get frontend configuration."""
    return jsonify({
        "apiBase": os.environ.get("API_BASE", "/api"),
        "environment": os.environ.get("ENVIRONMENT", "development"),
    })


if USING_REACT:
    @app.route("/<path:path>")
    def react_catch_all(path):
        """
        Serve React app for non-API routes.
        This allows React Router to handle all SPA routing.
        """
        file_path = REACT_BUILD_PATH / path
        if file_path.exists() and file_path.is_file():
            return send_from_directory(REACT_BUILD_PATH, path)
        return send_from_directory(REACT_BUILD_PATH, "index.html")


# ──────────────────────────────────────────────────────────────
# Health Check
# ──────────────────────────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "healthy", "service": "Zenith Healthcare AI Platform"})


# ──────────────────────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Ensure DB tables exist on startup
    try:
        db_service.create_tables()
        logger.info("Database tables initialised.")
    except Exception as e:
        logger.warning("Could not initialise database: %s", e)

    # Ensure search index exists
    try:
        search_service.create_index()
        logger.info("Search index initialised.")
    except Exception as e:
        logger.warning("Could not initialise search index: %s", e)

    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
