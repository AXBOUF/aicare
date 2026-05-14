"""
Azure MySQL Flexible Server Database Service
Manages structured storage of patient intake records.
"""

import logging
import json
from datetime import datetime, timezone
import mysql.connector
from config import Config

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# SQL Schema (MySQL)
# ------------------------------------------------------------------
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS patient_records (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    patient_name        VARCHAR(255),
    date_of_birth       VARCHAR(50),
    symptoms            TEXT,
    existing_conditions TEXT,
    medications         TEXT,
    allergies           TEXT,
    referral_reason     TEXT,
    full_text           TEXT,
    confidence_scores   TEXT,
    blob_name           VARCHAR(500),
    original_filename   VARCHAR(500),
    upload_date         DATETIME DEFAULT (UTC_TIMESTAMP()),
    urgency_level       VARCHAR(50) DEFAULT 'Normal'
);
"""

INSERT_SQL = """
INSERT INTO patient_records
    (patient_name, date_of_birth, symptoms, existing_conditions,
     medications, allergies, referral_reason, full_text,
     confidence_scores, blob_name, original_filename, urgency_level)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
"""

SELECT_ALL_SQL = "SELECT * FROM patient_records ORDER BY upload_date DESC;"
SELECT_BY_ID_SQL = "SELECT * FROM patient_records WHERE id = %s;"
SEARCH_SQL = """
SELECT * FROM patient_records
WHERE patient_name LIKE %s OR symptoms LIKE %s
      OR existing_conditions LIKE %s OR referral_reason LIKE %s
ORDER BY upload_date DESC;
"""


class DatabaseService:
    """Manages CRUD operations on Azure MySQL Flexible Server patient records."""

    def __init__(self):
        self.conn_config = Config.get_mysql_connection_config()

    def _get_connection(self):
        return mysql.connector.connect(**self.conn_config)

    def create_tables(self):
        """Create the patient_records table if it doesn't exist."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(CREATE_TABLE_SQL)
            conn.commit()
            cursor.close()
        finally:
            conn.close()
        logger.info("Database tables ensured.")

    def save_patient_record(self, patient_data: dict, blob_info: dict) -> int:
        """
        Persist extracted patient data to MySQL.
        Returns the new record ID.
        """
        confidence_scores = {
            k: patient_data[k]["confidence"]
            for k in [
                "patient_name", "date_of_birth", "symptoms",
                "existing_conditions", "medications", "allergies",
                "referral_reason",
            ]
            if isinstance(patient_data.get(k), dict)
        }

        urgency = self._assess_urgency(
            patient_data.get("symptoms", {}).get("value", "")
        )

        params = (
            patient_data.get("patient_name", {}).get("value", ""),
            patient_data.get("date_of_birth", {}).get("value", ""),
            patient_data.get("symptoms", {}).get("value", ""),
            patient_data.get("existing_conditions", {}).get("value", ""),
            patient_data.get("medications", {}).get("value", ""),
            patient_data.get("allergies", {}).get("value", ""),
            patient_data.get("referral_reason", {}).get("value", ""),
            patient_data.get("full_text", ""),
            json.dumps(confidence_scores),
            blob_info.get("blob_name", ""),
            blob_info.get("original_filename", ""),
            urgency,
        )

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(INSERT_SQL, params)
            record_id = cursor.lastrowid
            conn.commit()
            cursor.close()
        finally:
            conn.close()

        logger.info("Saved patient record ID=%d", record_id)
        return record_id

    def get_all_patients(self) -> list:
        """Return all patient records."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(SELECT_ALL_SQL)
            rows = cursor.fetchall()
            cursor.close()
        finally:
            conn.close()
        return rows

    def get_patient_by_id(self, record_id: int) -> dict | None:
        """Return a single patient record by ID."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(SELECT_BY_ID_SQL, (record_id,))
            row = cursor.fetchone()
            cursor.close()
        finally:
            conn.close()
        return row

    def search_patients(self, query: str) -> list:
        """Basic SQL search across patient fields."""
        like = f"%{query}%"
        conn = self._get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(SEARCH_SQL, (like, like, like, like))
            rows = cursor.fetchall()
            cursor.close()
        finally:
            conn.close()
        return rows

    @staticmethod
    def _assess_urgency(symptoms_text: str) -> str:
        """Simple keyword-based urgency classification."""
        high_keywords = ["chest pain", "breathing difficulty", "unconscious",
                         "severe bleeding", "stroke", "heart attack", "seizure"]
        medium_keywords = ["fever", "vomiting", "pain", "dizziness",
                           "shortness of breath", "infection"]

        text_lower = symptoms_text.lower()
        if any(kw in text_lower for kw in high_keywords):
            return "High"
        if any(kw in text_lower for kw in medium_keywords):
            return "Medium"
        return "Normal"
