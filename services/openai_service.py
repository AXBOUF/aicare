"""
Azure OpenAI RAG Service
Implements the AI Triage Assistant with Retrieval-Augmented Generation.

AUTH_MODE=apikey  : uses AZURE_OPENAI_KEY (copy from Azure Portal)
AUTH_MODE=managed : uses Managed Identity token provider — no keys required
"""

import logging
import json
from openai import AzureOpenAI
from config import Config
from services.search_service import SearchService
from prompts.system_messages import TRIAGE_ASSISTANT_SYSTEM_MESSAGE, EXTRACTION_ENHANCEMENT_PROMPT

logger = logging.getLogger(__name__)


class OpenAIService:
    """RAG-based clinical triage assistant using Azure OpenAI."""

    def __init__(self):
        self.deployment = Config.OPENAI_DEPLOYMENT
        self._client = None
        self.search_service = SearchService()

    @property
    def client(self):
        if self._client is None:
            if Config.AUTH_MODE == "managed":
                from azure.identity import get_bearer_token_provider
                from config import get_credential
                token_provider = get_bearer_token_provider(
                    get_credential(),
                    "https://cognitiveservices.azure.com/.default",
                )
                self._client = AzureOpenAI(
                    azure_endpoint=Config.OPENAI_ENDPOINT,
                    azure_ad_token_provider=token_provider,
                    api_version=Config.OPENAI_API_VERSION,
                    max_retries=6,
                    timeout=120.0,
                )
            else:
                # apikey mode — API key from Azure Portal
                self._client = AzureOpenAI(
                    azure_endpoint=Config.OPENAI_ENDPOINT,
                    api_key=Config.OPENAI_KEY,
                    api_version=Config.OPENAI_API_VERSION,
                    max_retries=6,
                    timeout=120.0,
                )
        return self._client

    def ask_triage_assistant(self, user_question: str, conversation_history: list | None = None) -> str:
        """
        Process a user query using RAG:
        1. Search the patient index for relevant records.
        2. Build a grounded prompt with retrieved context.
        3. Send to Azure OpenAI for a response.
        """
        # Step 1 - Retrieve relevant patient records from Azure AI Search
        search_results = self.search_service.search(query=user_question, top=5)
        context_text = self._format_search_results(search_results)

        # Step 2 - Build messages
        messages = [
            {"role": "system", "content": TRIAGE_ASSISTANT_SYSTEM_MESSAGE},
        ]

        # Include conversation history for multi-turn
        if conversation_history:
            messages.extend(conversation_history)

        # Augment user question with retrieved context
        augmented_prompt = (
            f"### Retrieved Patient Records\n{context_text}\n\n"
            f"### User Question\n{user_question}"
        )
        messages.append({"role": "user", "content": augmented_prompt})

        # Step 3 - Call Azure OpenAI
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            max_completion_tokens=1024,
        )

        assistant_reply = response.choices[0].message.content
        logger.info("Triage assistant responded to: %s", user_question[:80])
        return assistant_reply

    def summarise_patient(self, patient_record: dict) -> str:
        """Generate a clinical summary for a single patient record."""
        patient_context = json.dumps(
            {k: v for k, v in patient_record.items() if k != "full_text"},
            indent=2,
            default=str,
        )

        messages = [
            {"role": "system", "content": TRIAGE_ASSISTANT_SYSTEM_MESSAGE},
            {
                "role": "user",
                "content": (
                    f"Please provide a concise clinical summary of the following "
                    f"patient intake record. Include key findings, urgency assessment, "
                    f"and recommended next steps.\n\n{patient_context}"
                ),
            },
        ]

        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            max_completion_tokens=800,
        )

        return response.choices[0].message.content

    def enhance_extraction(self, full_text: str) -> dict:
        """
        Use GPT to extract structured patient fields from raw document text.
        Falls back to empty strings if parsing fails.
        """
        messages = [
            {"role": "system", "content": EXTRACTION_ENHANCEMENT_PROMPT},
            {"role": "user", "content": full_text},
        ]
        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                max_completion_tokens=600,
            )
            raw = response.choices[0].message.content.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            parsed = json.loads(raw)
            logger.info("AI extraction enhanced %d fields from document text", len(parsed))
            return {k: {"value": v, "confidence": 0.85} for k, v in parsed.items()}
        except Exception as exc:
            logger.warning("AI extraction enhancement failed: %s", exc)
            return {}

    @staticmethod
    def _format_search_results(results: list) -> str:
        """Format search results as context for the LLM."""
        if not results:
            return "No matching patient records found in the database."

        parts = []
        for i, doc in enumerate(results, 1):
            parts.append(
                f"--- Record {i} ---\n"
                f"Patient: {doc.get('patient_name', 'N/A')}\n"
                f"DOB: {doc.get('date_of_birth', 'N/A')}\n"
                f"Symptoms: {doc.get('symptoms', 'N/A')}\n"
                f"Conditions: {doc.get('existing_conditions', 'N/A')}\n"
                f"Medications: {doc.get('medications', 'N/A')}\n"
                f"Allergies: {doc.get('allergies', 'N/A')}\n"
                f"Referral Reason: {doc.get('referral_reason', 'N/A')}\n"
                f"Urgency: {doc.get('urgency_level', 'N/A')}\n"
                f"Upload Date: {doc.get('upload_date', 'N/A')}\n"
            )
        return "\n".join(parts)
