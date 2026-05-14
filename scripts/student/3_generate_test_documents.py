"""
STEP 3 — Generate Test Documents
Generates sample patient intake form files (PDF, PNG, JPG) that you can
upload via the app to test the full pipeline.

Output: sample_data/test_documents/  (created automatically)

Usage:
    python scripts/student/3_generate_test_documents.py

This does NOT require Azure credentials — it only creates local files.
"""

import os
import sys
import textwrap
import datetime
from pathlib import Path

# ── patient records ────────────────────────────────────────────────────────────
PATIENTS = [
    {
        "name": "Sarah Johnson",
        "dob": "15/03/1985",
        "symptoms": "Persistent chest pain radiating to left arm, shortness of breath, dizziness",
        "conditions": "Hypertension, Type 2 Diabetes",
        "medications": "Metformin 500mg, Lisinopril 10mg",
        "allergies": "Penicillin",
        "reason": "Urgent cardiology assessment - suspected acute coronary syndrome",
        "urgency": "HIGH",
    },
    {
        "name": "Michael Chen",
        "dob": "22/07/1972",
        "symptoms": "Recurring headaches, blurred vision, neck stiffness",
        "conditions": "Migraine history, Cervical spondylosis",
        "medications": "Sumatriptan 50mg as needed, Ibuprofen 400mg",
        "allergies": "None known",
        "reason": "Neurology referral – increasing frequency of migraines with new visual disturbances",
        "urgency": "MEDIUM",
    },
    {
        "name": "Emily Williams",
        "dob": "08/11/1998",
        "symptoms": "Persistent cough for 3 weeks, low-grade fever, fatigue, weight loss",
        "conditions": "Asthma (childhood)",
        "medications": "Ventolin inhaler as needed",
        "allergies": "Sulfa drugs",
        "reason": "Respiratory medicine referral - persistent cough with constitutional symptoms",
        "urgency": "MEDIUM",
    },
    {
        "name": "Robert Thompson",
        "dob": "30/01/1960",
        "symptoms": "Severe lower back pain, numbness in right leg, difficulty walking",
        "conditions": "Osteoarthritis, Previous lumbar disc herniation (2018)",
        "medications": "Paracetamol 1g QID, Naproxen 500mg BD",
        "allergies": "Codeine (causes nausea)",
        "reason": "Orthopaedic/Neurosurgery referral - recurrent disc herniation with neurological deficit",
        "urgency": "HIGH",
    },
    {
        "name": "Priya Patel",
        "dob": "14/06/1990",
        "symptoms": "Anxiety, insomnia, heart palpitations, tremor",
        "conditions": "Generalised anxiety disorder, Iron deficiency anaemia",
        "medications": "Ferrous fumarate 210mg, Escitalopram 10mg",
        "allergies": "Latex",
        "reason": "Endocrinology referral - rule out thyroid dysfunction",
        "urgency": "LOW",
    },
    {
        "name": "James O'Brien",
        "dob": "03/09/2001",
        "symptoms": "Sudden onset rash over trunk, fever 38.5 °C, joint pain",
        "conditions": "No known chronic conditions",
        "medications": "Nil regular medications",
        "allergies": "Amoxicillin (rash)",
        "reason": "Immunology referral - possible autoimmune or viral aetiology",
        "urgency": "HIGH",
    },
    {
        "name": "Linda Martinez",
        "dob": "27/04/1955",
        "symptoms": "Progressive memory loss, confusion, difficulty with daily tasks",
        "conditions": "Type 2 Diabetes, Hyperlipidaemia",
        "medications": "Metformin 1g BD, Atorvastatin 40mg",
        "allergies": "None known",
        "reason": "Geriatric neurology referral - early-onset dementia workup",
        "urgency": "MEDIUM",
    },
    {
        "name": "David Kim",
        "dob": "11/12/1988",
        "symptoms": "Sharp abdominal pain (right lower quadrant), nausea, vomiting",
        "conditions": "Nil significant past history",
        "medications": "Nil",
        "allergies": "None known",
        "reason": "General surgery assessment - rule out acute appendicitis",
        "urgency": "HIGH",
    },
    {
        "name": "Fatima Al-Hassan",
        "dob": "19/02/1978",
        "symptoms": "Chronic fatigue, cold intolerance, weight gain, dry skin",
        "conditions": "Iron deficiency anaemia",
        "medications": "Ferrous sulphate 325mg",
        "allergies": "Aspirin (GI upset)",
        "reason": "Endocrinology referral - suspected hypothyroidism",
        "urgency": "LOW",
    },
]

OUT_DIR = Path(__file__).resolve().parent.parent.parent / "sample_data" / "test_documents"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════
# PDF generation (reportlab)
# ═══════════════════════════════════════════════════════════════
def generate_pdf(patient: dict, out_path: Path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    )

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title2",
        parent=styles["Title"],
        fontSize=18,
        textColor=colors.HexColor("#1a4f8a"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#555555"),
        spaceAfter=12,
    )
    section_style = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontSize=11,
        textColor=colors.HexColor("#1a4f8a"),
        spaceBefore=10,
        spaceAfter=4,
        borderPad=2,
    )
    label_style = ParagraphStyle(
        "Label",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#777777"),
    )
    value_style = ParagraphStyle(
        "Value",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.black,
        spaceAfter=6,
    )

    urgency_colors = {
        "HIGH": colors.HexColor("#c0392b"),
        "MEDIUM": colors.HexColor("#e67e22"),
        "LOW": colors.HexColor("#27ae60"),
    }
    urgency = patient["urgency"]
    u_color = urgency_colors.get(urgency, colors.grey)

    story = []

    # Header
    story.append(Paragraph("ZENITH HEALTHCARE", title_style))
    story.append(Paragraph("Patient Intake &amp; Referral Form", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a4f8a")))
    story.append(Spacer(1, 0.4 * cm))

    # Urgency badge
    urgency_style = ParagraphStyle(
        "Urgency",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.white,
        backColor=u_color,
        borderPad=4,
        spaceAfter=10,
    )
    story.append(Paragraph(f"  TRIAGE PRIORITY: {urgency}  ", urgency_style))
    story.append(Spacer(1, 0.3 * cm))

    def field(label, value):
        story.append(Paragraph(label, label_style))
        story.append(Paragraph(value or "—", value_style))

    # Patient details table
    story.append(Paragraph("PATIENT INFORMATION", section_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 0.2 * cm))

    data = [
        ["Patient Name:", patient["name"], "Date of Birth:", patient["dob"]],
        ["Form Date:", datetime.date.today().strftime("%d/%m/%Y"), "Form ID:", f"ZH-{abs(hash(patient['name'])) % 90000 + 10000}"],
    ]
    t = Table(data, colWidths=[4 * cm, 7 * cm, 4 * cm, 5 * cm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#777777")),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#777777")),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTNAME", (3, 0), (3, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.4 * cm))

    # Clinical section
    story.append(Paragraph("CLINICAL PRESENTATION", section_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 0.2 * cm))
    field("Presenting Symptoms", patient["symptoms"])
    field("Existing Medical Conditions", patient["conditions"])
    field("Current Medications", patient["medications"])
    field("Known Allergies", patient["allergies"])

    story.append(Paragraph("REFERRAL DETAILS", section_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 0.2 * cm))
    field("Reason for Referral", patient["reason"])

    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1a4f8a")))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "This document is confidential and intended solely for the named recipient. "
        "Zenith Healthcare Platform — AI-Assisted Triage System.",
        ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8,
                       textColor=colors.HexColor("#999999")),
    ))

    doc.build(story)


# ═══════════════════════════════════════════════════════════════
# Image generation (Pillow)
# ═══════════════════════════════════════════════════════════════
def generate_image(patient: dict, out_path: Path, fmt: str = "PNG") -> None:
    from PIL import Image, ImageDraw, ImageFont

    W, H = 900, 1200
    img = Image.new("RGB", (W, H), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Try to load a nicer font; fall back to default
    try:
        if sys.platform == "darwin":
            font_path = "/Library/Fonts/Arial.ttf"
            bold_path = "/Library/Fonts/Arial Bold.ttf"
        elif sys.platform.startswith("linux"):
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        else:  # Windows
            font_path = "C:/Windows/Fonts/arial.ttf"
            bold_path = "C:/Windows/Fonts/arialbd.ttf"
        f_title  = ImageFont.truetype(font_path, 28)
        f_sub    = ImageFont.truetype(font_path, 14)
        f_label  = ImageFont.truetype(font_path, 11)
        f_value  = ImageFont.truetype(font_path, 13)
        f_small  = ImageFont.truetype(font_path, 10)
        f_bold   = ImageFont.truetype(bold_path, 14)
    except OSError:
        f_title = f_sub = f_label = f_value = f_small = f_bold = ImageFont.load_default()

    urgency_bg = {"HIGH": (192, 57, 43), "MEDIUM": (230, 126, 34), "LOW": (39, 174, 96)}
    u_bg = urgency_bg.get(patient["urgency"], (100, 100, 100))

    # Top banner
    draw.rectangle([0, 0, W, 80], fill=(26, 79, 138))
    draw.text((20, 14), "ZENITH HEALTHCARE", fill=(255, 255, 255), font=f_title)
    draw.text((22, 52), "Patient Intake & Referral Form", fill=(180, 210, 255), font=f_sub)

    # Urgency strip
    draw.rectangle([0, 80, W, 116], fill=u_bg)
    draw.text((20, 90), f"  TRIAGE PRIORITY: {patient['urgency']}  ",
              fill=(255, 255, 255), font=f_bold)

    # Separator line
    y = 130
    draw.line([20, y, W - 20, y], fill=(26, 79, 138), width=2)

    def section_header(title: str, ypos: int) -> int:
        draw.rectangle([20, ypos, W - 20, ypos + 26], fill=(235, 242, 250))
        draw.text((24, ypos + 5), title, fill=(26, 79, 138), font=f_bold)
        return ypos + 34

    def field_row(label: str, value: str, ypos: int, max_width: int = 60) -> int:
        draw.text((30, ypos), label + ":", fill=(119, 119, 119), font=f_label)
        wrapped = textwrap.wrap(value or "—", width=max_width)
        for line in wrapped:
            draw.text((200, ypos), line, fill=(20, 20, 20), font=f_value)
            ypos += 18
        return ypos + 4

    # Patient info
    y = section_header("PATIENT INFORMATION", y + 10)
    y = field_row("Patient Name", patient["name"], y)
    y = field_row("Date of Birth", patient["dob"], y)
    y = field_row("Form Date", datetime.date.today().strftime("%d/%m/%Y"), y)
    form_id = f"ZH-{abs(hash(patient['name'])) % 90000 + 10000}"
    y = field_row("Form ID", form_id, y)

    # Clinical
    y = section_header("CLINICAL PRESENTATION", y + 6)
    y = field_row("Presenting Symptoms", patient["symptoms"], y, 55)
    y = field_row("Existing Conditions", patient["conditions"], y, 55)
    y = field_row("Current Medications", patient["medications"], y, 55)
    y = field_row("Known Allergies", patient["allergies"], y, 55)

    # Referral
    y = section_header("REFERRAL DETAILS", y + 6)
    y = field_row("Reason for Referral", patient["reason"], y, 55)

    # Footer
    draw.line([20, H - 40, W - 20, H - 40], fill=(26, 79, 138), width=1)
    draw.text((20, H - 28),
              "CONFIDENTIAL — Zenith Healthcare Platform — AI-Assisted Triage System",
              fill=(160, 160, 160), font=f_small)

    quality_kwargs = {"quality": 88} if fmt.upper() == "JPEG" else {}
    img.save(str(out_path), format=fmt, **quality_kwargs)


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print("Zenith Healthcare - Test Document Generator")
    print("=" * 60)
    print(f"Output directory: {OUT_DIR}\n")

    # First 4 patients → PDF
    pdf_patients = PATIENTS[:4]
    # Next 3 → PNG
    png_patients = PATIENTS[3:6]
    # Next 3 → JPG (overlap intentional for variety)
    jpg_patients = PATIENTS[5:8]

    for p in pdf_patients:
        slug = p["name"].lower().replace(" ", "_").replace("'", "")
        path = OUT_DIR / f"intake_{slug}.pdf"
        generate_pdf(p, path)
        print(f"  [PDF] {path.name}")

    for p in png_patients:
        slug = p["name"].lower().replace(" ", "_").replace("'", "")
        path = OUT_DIR / f"intake_{slug}.png"
        generate_image(p, path, fmt="PNG")
        print(f"  [PNG] {path.name}")

    for p in jpg_patients:
        slug = p["name"].lower().replace(" ", "_").replace("'", "")
        path = OUT_DIR / f"intake_{slug}.jpg"
        generate_image(p, path, fmt="JPEG")
        print(f"  [JPG] {path.name}")

    total = len(pdf_patients) + len(png_patients) + len(jpg_patients)
    print(f"\nDone! {total} test documents created in sample_data/test_documents/")
    print("\nUpload them at http://localhost:5000")


if __name__ == "__main__":
    main()
