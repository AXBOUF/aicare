"""
Azure AI Document Intelligence Service
Extracts structured clinical data from patient intake form PDFs.

AUTH_MODE=apikey  : uses DOCUMENT_INTELLIGENCE_KEY (copy from Azure Portal)
AUTH_MODE=managed : uses Managed Identity (DefaultAzureCredential) — no keys required
"""

import logging
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from config import Config
from services.openai_service import OpenAIService

logger = logging.getLogger(__name__)


class DocumentIntelligenceService:
    """Extracts structured medical information from intake form documents."""

    def __init__(self):
        self.endpoint = Config.DOC_INTELLIGENCE_ENDPOINT
        self._client = None
        self._openai = None

    @property
    def openai_service(self):
        if self._openai is None:
            self._openai = OpenAIService()
        return self._openai

    @property
    def client(self):
        if self._client is None:
            if Config.AUTH_MODE == "managed":
                from config import get_credential
                credential = get_credential()
            else:
                credential = AzureKeyCredential(Config.DOC_INTELLIGENCE_KEY)
            self._client = DocumentAnalysisClient(
                endpoint=self.endpoint,
                credential=credential,
            )
        return self._client

    def extract_from_pdf(self, pdf_bytes: bytes) -> dict:
        """
        Analyse a PDF/image using the prebuilt-layout model and extract
        key clinical fields.
        Returns a dict of extracted patient data with confidence scores.
        """
        poller = self.client.begin_analyze_document("prebuilt-layout", document=pdf_bytes)
        result = poller.result()

        extracted = self._parse_result(result)
        logger.info("Extracted %d fields from document", len(extracted.get("fields", {})))
        return extracted

    def extract_from_url(self, blob_url: str) -> dict:
        """Analyse a document from a blob URL."""
        poller = self.client.begin_analyze_document_from_url("prebuilt-layout", document_url=blob_url)
        result = poller.result()
        return self._parse_result(result)

    def _parse_result(self, result) -> dict:
        """
        Parse the Document Intelligence result into structured patient data.
        Extracts key-value pairs and full text content.
        """
        # Collect all key-value pairs with confidence
        fields = {}
        for kv_pair in result.key_value_pairs or []:
            if kv_pair.key and kv_pair.value:
                key_text = kv_pair.key.content.strip().lower()
                value_text = kv_pair.value.content.strip()
                confidence = kv_pair.confidence or 0.0
                fields[key_text] = {
                    "value": value_text,
                    "confidence": round(confidence, 4),
                }

        # Extract full text content from all pages
        full_text = ""
        for page in result.pages or []:
            for line in page.lines or []:
                full_text += line.content + "\n"

        # Map to clinical schema
        patient_data = {
            "patient_name": self._find_field(fields, ["patient name", "name", "full name", "patient"]),
            "date_of_birth": self._find_field(fields, ["date of birth", "dob", "d.o.b", "birth date"]),
            "symptoms": self._find_field(fields, ["symptoms", "presenting symptoms", "chief complaint", "complaint"]),
            "existing_conditions": self._find_field(fields, ["existing conditions", "medical history", "conditions", "past medical history"]),
            "medications": self._find_field(fields, ["medications", "current medications", "medicine", "drugs"]),
            "allergies": self._find_field(fields, ["allergies", "known allergies", "allergy"]),
            "referral_reason": self._find_field(fields, ["referral reason", "reason for referral", "referral", "reason"]),
            "full_text": full_text.strip(),
            "raw_fields": fields,
        }

        # If DI key-value pairs didn't yield patient name, fall back to AI extraction
        if not patient_data["patient_name"]["value"] and full_text.strip():
            logger.info("Key-value extraction yielded no fields — falling back to AI extraction")
            ai_fields = self.openai_service.enhance_extraction(full_text)
            for field_key in ("patient_name", "date_of_birth", "symptoms",
                               "existing_conditions", "medications", "allergies",
                               "referral_reason"):
                if not patient_data[field_key]["value"] and field_key in ai_fields:
                    patient_data[field_key] = ai_fields[field_key]

        return patient_data

    @staticmethod
    def _find_field(fields: dict, possible_keys: list) -> dict:
        """
        Search for a field value using multiple possible key names.
        Returns the value and confidence, or empty defaults.
        """
        for key in possible_keys:
            if key in fields:
                return fields[key]
        return {"value": "", "confidence": 0.0}
