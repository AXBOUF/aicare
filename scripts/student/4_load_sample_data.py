"""
STEP 4 — Load Sample Patient Data (Optional)
Inserts pre-built patient records into Azure MySQL and the AI Search index
so you can explore the app without uploading real documents.

Prerequisites:
    - Steps 1 and 2 completed (database table and search index exist)
    - .env file filled in

Usage:
    python scripts/student/4_load_sample_data.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.database import DatabaseService
from services.search_service import SearchService

# ──────────────────────────────────────────────────────────────
# Sample Patient Records
# ──────────────────────────────────────────────────────────────
SAMPLE_PATIENTS = [
    {
        "patient_name": {"value": "Sarah Johnson", "confidence": 0.95},
        "date_of_birth": {"value": "15/03/1985", "confidence": 0.92},
        "symptoms": {"value": "Persistent chest pain radiating to left arm, shortness of breath, dizziness", "confidence": 0.88},
        "existing_conditions": {"value": "Hypertension, Type 2 Diabetes", "confidence": 0.90},
        "medications": {"value": "Metformin 500mg, Lisinopril 10mg", "confidence": 0.85},
        "allergies": {"value": "Penicillin", "confidence": 0.93},
        "referral_reason": {"value": "Urgent cardiology assessment - suspected acute coronary syndrome", "confidence": 0.87},
        "full_text": "Patient presents with persistent chest pain radiating to left arm for the past 2 hours. History of hypertension and Type 2 Diabetes. Currently on Metformin and Lisinopril. Known allergy to Penicillin. GP referral for urgent cardiology assessment.",
    },
    {
        "patient_name": {"value": "Michael Chen", "confidence": 0.97},
        "date_of_birth": {"value": "22/07/1972", "confidence": 0.94},
        "symptoms": {"value": "Recurring headaches, blurred vision, neck stiffness", "confidence": 0.91},
        "existing_conditions": {"value": "Migraine history, Cervical spondylosis", "confidence": 0.86},
        "medications": {"value": "Sumatriptan 50mg as needed, Ibuprofen 400mg", "confidence": 0.89},
        "allergies": {"value": "None known", "confidence": 0.96},
        "referral_reason": {"value": "Neurology referral - increasing frequency of migraines with new visual disturbances", "confidence": 0.88},
        "full_text": "Patient Michael Chen reports worsening headaches over the past 3 months with new onset blurred vision. Has a history of migraines and cervical spondylosis. Using Sumatriptan for acute attacks. No known allergies. Referred for neurology assessment due to changing pattern of headaches.",
    },
    {
        "patient_name": {"value": "Emily Williams", "confidence": 0.93},
        "date_of_birth": {"value": "08/11/1998", "confidence": 0.95},
        "symptoms": {"value": "Persistent cough for 3 weeks, low-grade fever, fatigue, weight loss", "confidence": 0.87},
        "existing_conditions": {"value": "Asthma (childhood)", "confidence": 0.82},
        "medications": {"value": "Ventolin inhaler as needed", "confidence": 0.90},
        "allergies": {"value": "Sulfa drugs", "confidence": 0.94},
        "referral_reason": {"value": "Respiratory medicine referral - persistent cough with constitutional symptoms requiring investigation", "confidence": 0.85},
        "full_text": "Young woman presenting with a 3-week history of productive cough, low-grade fever, fatigue, and unintentional weight loss of 3kg. Childhood history of asthma. Uses Ventolin inhaler occasionally. Allergic to sulfa drugs. GP requests respiratory medicine review for further investigation.",
    },
    {
        "patient_name": {"value": "Robert Thompson", "confidence": 0.96},
        "date_of_birth": {"value": "30/01/1960", "confidence": 0.91},
        "symptoms": {"value": "Severe lower back pain, numbness in right leg, difficulty walking", "confidence": 0.89},
        "existing_conditions": {"value": "Osteoarthritis, Previous lumbar disc herniation (2018)", "confidence": 0.84},
        "medications": {"value": "Paracetamol 1g QID, Naproxen 500mg BD", "confidence": 0.88},
        "allergies": {"value": "Codeine (causes nausea)", "confidence": 0.92},
        "referral_reason": {"value": "Orthopaedic/Neurosurgery referral - recurrent disc herniation with neurological deficit", "confidence": 0.86},
        "full_text": "65-year-old male with severe lower back pain and new right leg numbness and weakness developing over 2 weeks. History of lumbar disc herniation in 2018 treated conservatively. Also has osteoarthritis. On regular Paracetamol and Naproxen. Codeine intolerant. Urgent orthopaedic review requested.",
    },
    {
        "patient_name": {"value": "Priya Patel", "confidence": 0.94},
        "date_of_birth": {"value": "14/06/1990", "confidence": 0.93},
        "symptoms": {"value": "Anxiety, insomnia, heart palpitations, tremor", "confidence": 0.86},
        "existing_conditions": {"value": "Generalised anxiety disorder, Iron deficiency anaemia", "confidence": 0.88},
        "medications": {"value": "Ferrous fumarate 210mg, Escitalopram 10mg", "confidence": 0.91},
        "allergies": {"value": "Latex", "confidence": 0.95},
        "referral_reason": {"value": "Endocrinology referral - rule out thyroid dysfunction as cause of worsening anxiety and palpitations", "confidence": 0.83},
        "full_text": "35-year-old woman with worsening anxiety symptoms, insomnia, palpitations, and new onset tremor despite being on Escitalopram. Existing GAD and iron deficiency anaemia on treatment. Latex allergy noted. GP suspects possible thyroid disorder and refers for endocrinology assessment and thyroid function testing.",
    },
]


def main():
    print("=" * 50)
    print("Zenith Healthcare - Sample Data Generator")
    print("=" * 50)

    db = DatabaseService()
    search = SearchService()

    # Ensure tables and index exist
    print("\nEnsuring database tables exist...")
    db.create_tables()

    print("Ensuring search index exists...")
    search.create_index()

    print(f"\nInserting {len(SAMPLE_PATIENTS)} sample patient records...")

    for i, patient in enumerate(SAMPLE_PATIENTS, 1):
        blob_info = {
            "blob_name": f"sample-{i}.pdf",
            "original_filename": f"sample_intake_{i}.pdf",
        }

        # Save to database
        record_id = db.save_patient_record(patient, blob_info)
        print(f"  [{i}] {patient['patient_name']['value']} -> Record ID {record_id}")

        # Index in search
        record = db.get_patient_by_id(record_id)
        if record:
            search.index_patient_record(record)
            print(f"      Indexed in Azure AI Search")

    print(f"\nDone! {len(SAMPLE_PATIENTS)} sample patient records created.")
    print("\nYou can now:")
    print("  - View them at http://localhost:5000/patients")
    print("  - Search at http://localhost:5000/search")
    print("  - Ask the AI assistant at http://localhost:5000/assistant")


if __name__ == "__main__":
    main()
