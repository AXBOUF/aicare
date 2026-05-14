"""
STEP 1 — Database Setup
Creates the patient_records table in Azure MySQL Flexible Server.

Prerequisites:
    - .env file filled in with your Azure MySQL details
    - MySQL Flexible Server is running and your IP is whitelisted

Usage:
    python scripts/student/1_create_database.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.database import DatabaseService


def main():
    print("=" * 50)
    print("Zenith Healthcare - Database Setup")
    print("=" * 50)

    db = DatabaseService()

    print("\nCreating patient_records table...")
    db.create_tables()
    print("Database tables created successfully!")

    # Verify
    patients = db.get_all_patients()
    print(f"Current record count: {len(patients)}")
    print("\nDone!")


if __name__ == "__main__":
    main()
