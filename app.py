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
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
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


def is_authenticated() -> bool:
    return bool(session.get("user"))


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            # For API routes return JSON 401
            if request.path.startswith("/api/"):
                return jsonify({"error": "Unauthorized"}), 401
            # For web pages redirect to login
            return redirect(url_for("login", next=request.path))
        return func(*args, **kwargs)
    return wrapper


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            flash("Please log in.", "error")
            return redirect(url_for("login", next=request.path))
        if session.get("role") != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("index"))
        return func(*args, **kwargs)
    return wrapper


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


@app.route("/login", methods=["GET", "POST"])
def login():
    """Simple username/password login using users table in MySQL."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = db_service.get_user_by_username(username)
        if not user:
            flash("Invalid username or password.", "error")
            return redirect(url_for("login"))
        if not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.", "error")
            return redirect(url_for("login"))
        session["user"] = user["username"]
        session["role"] = user.get("role", "user")
        flash("Logged in successfully.", "success")
        next_url = request.args.get("next") or url_for("patients")
        return redirect(next_url)
    
    # Check if any users exist; if not, show bootstrap message
    try:
        conn = db_service._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        user_count = result[0] if result else 0
    except:
        user_count = 0
    
    return render_template("login.html", user_count=user_count)


@app.route("/setup/first-user", methods=["GET", "POST"])
def setup_first_user():
    """Allow creating the first admin user without authentication."""
    # Check if users already exist
    try:
        conn = db_service._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        user_count = result[0] if result else 0
    except:
        user_count = 0
    
    if user_count > 0:
        flash("Users already exist. Use /admin/users to manage them.", "info")
        return redirect(url_for("login"))
    
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        if not username or not password:
            flash("Username and password required.", "error")
            return redirect(url_for("setup_first_user"))
        
        try:
            pw_hash = generate_password_hash(password)
            db_service.create_user(username, pw_hash, role="admin")
            flash(f"Admin user '{username}' created! Please log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"Error: {str(e)}", "error")
            return redirect(url_for("setup_first_user"))
    
    return render_template("setup_first_user.html")



@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("index"))


@app.route("/admin/users", methods=["GET", "POST", "DELETE"])
@admin_required
def admin_users():
    """Admin panel to manage users."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "user")
        
        if not username or not password:
            flash("Username and password required.", "error")
            return redirect(url_for("admin_users"))
        
        existing = db_service.get_user_by_username(username)
        if existing:
            flash(f"User '{username}' already exists.", "error")
            return redirect(url_for("admin_users"))
        
        try:
            pw_hash = generate_password_hash(password)
            user_id = db_service.create_user(username, pw_hash, role=role)
            flash(f"Created user '{username}' with role '{role}'.", "success")
        except Exception as e:
            flash(f"Error creating user: {str(e)}", "error")
        
        return redirect(url_for("admin_users"))
    
    # GET: Show users list + create form
    try:
        conn = db_service._get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, role, created_at FROM users ORDER BY created_at")
        users = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        users = []
        flash(f"Error loading users: {str(e)}", "error")
    
    return render_template("admin_users.html", users=users)


@app.route("/admin/users/<int:user_id>", methods=["DELETE", "POST"])
@admin_required
def delete_user_admin(user_id: int):
    """Delete a user (admin only)."""
    try:
        conn = db_service._get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            flash("User not found.", "error")
            return redirect(url_for("admin_users"))
        
        # Prevent deleting yourself
        if user["username"] == session.get("user"):
            flash("Cannot delete your own account.", "error")
            return redirect(url_for("admin_users"))
        
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash(f"Deleted user '{user['username']}'.", "success")
    except Exception as e:
        flash(f"Error deleting user: {str(e)}", "error")
    
    return redirect(url_for("admin_users"))


@app.route("/patients")
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
def assistant():
    """AI Triage Assistant chat interface."""
    return render_template("assistant.html")


@app.route("/api/assistant", methods=["POST"])
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
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

    # Create default admin user if provided in env and not present
    try:
        admin_user = os.environ.get("ADMIN_USERNAME")
        admin_pass = os.environ.get("ADMIN_PASSWORD")
        if admin_user and admin_pass:
            existing = db_service.get_user_by_username(admin_user)
            if not existing:
                pw_hash = generate_password_hash(admin_pass)
                db_service.create_user(admin_user, pw_hash, role="admin")
                logger.info("Created default admin user: %s", admin_user)
            else:
                logger.info("Admin user already exists: %s", admin_user)
    except Exception as e:
        logger.warning("Failed to ensure admin user: %s", e)

    # Ensure search index exists
    try:
        search_service.create_index()
        logger.info("Search index initialised.")
    except Exception as e:
        logger.warning("Could not initialise search index: %s", e)

    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
