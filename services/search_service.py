"""
Azure AI Search Service
Indexes patient records for intelligent knowledge mining.

AUTH_MODE=apikey  : uses AZURE_SEARCH_KEY (copy from Azure Portal)
AUTH_MODE=managed : uses Managed Identity (DefaultAzureCredential) — no keys required
"""

import logging
import json
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchFieldDataType,
)
from azure.core.credentials import AzureKeyCredential
from config import Config

logger = logging.getLogger(__name__)


class SearchService:
    """Manages indexing and querying of patient intake records via Azure AI Search."""

    def __init__(self):
        self.endpoint = Config.SEARCH_ENDPOINT
        self.index_name = Config.SEARCH_INDEX
        self._search_client = None
        self._index_client = None

    def _get_credential(self):
        if Config.AUTH_MODE == "managed":
            from config import get_credential
            return get_credential()
        return AzureKeyCredential(Config.SEARCH_KEY)

    @property
    def index_client(self):
        if self._index_client is None:
            self._index_client = SearchIndexClient(
                endpoint=self.endpoint,
                credential=self._get_credential(),
            )
        return self._index_client

    @property
    def search_client(self):
        if self._search_client is None:
            self._search_client = SearchClient(
                endpoint=self.endpoint,
                index_name=self.index_name,
                credential=self._get_credential(),
            )
        return self._search_client

    def create_index(self):
        """Create or update the patient intake search index."""
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
            SearchableField(name="patient_name", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SearchableField(name="date_of_birth", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="symptoms", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="existing_conditions", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="medications", type=SearchFieldDataType.String),
            SearchableField(name="allergies", type=SearchFieldDataType.String),
            SearchableField(name="referral_reason", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="full_text", type=SearchFieldDataType.String),
            SimpleField(name="urgency_level", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SimpleField(name="upload_date", type=SearchFieldDataType.String, filterable=True, sortable=True),
            SimpleField(name="blob_name", type=SearchFieldDataType.String),
        ]

        index = SearchIndex(name=self.index_name, fields=fields)
        self.index_client.create_or_update_index(index)
        logger.info("Search index '%s' created/updated.", self.index_name)

    def index_patient_record(self, record: dict):
        """Add or update a patient record in the search index."""
        document = {
            "id": str(record.get("id", "")),
            "patient_name": record.get("patient_name", ""),
            "date_of_birth": record.get("date_of_birth", ""),
            "symptoms": record.get("symptoms", ""),
            "existing_conditions": record.get("existing_conditions", ""),
            "medications": record.get("medications", ""),
            "allergies": record.get("allergies", ""),
            "referral_reason": record.get("referral_reason", ""),
            "full_text": record.get("full_text", ""),
            "urgency_level": record.get("urgency_level", "Normal"),
            "upload_date": str(record.get("upload_date", "")),
            "blob_name": record.get("blob_name", ""),
        }

        result = self.search_client.upload_documents(documents=[document])
        logger.info("Indexed patient record ID=%s, success=%s", document["id"], result[0].succeeded)

    def search(self, query: str, filters: str | None = None, top: int = 10) -> list:
        """
        Search patient records.
        query:   free-text search string
        filters: OData filter expression (e.g., "urgency_level eq 'High'")
        """
        results = self.search_client.search(
            search_text=query,
            filter=filters,
            top=top,
            include_total_count=True,
        )

        documents = []
        for result in results:
            documents.append(dict(result))

        logger.info("Search returned %d results for query='%s'", len(documents), query)
        return documents

    def search_by_urgency(self, urgency: str) -> list:
        """Filter records by urgency level."""
        return self.search(query="*", filters=f"urgency_level eq '{urgency}'")
