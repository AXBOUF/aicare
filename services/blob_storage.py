"""
Azure Blob Storage Service
Handles secure upload and retrieval of patient intake form PDFs.

AUTH_MODE=apikey  : uses AZURE_STORAGE_CONNECTION_STRING (copy from Azure Portal)
AUTH_MODE=managed : uses Managed Identity (DefaultAzureCredential) — no keys required
"""

import uuid
import logging
from azure.storage.blob import BlobServiceClient, ContentSettings
from config import Config

logger = logging.getLogger(__name__)


class BlobStorageService:
    """Manages patient document uploads in Azure Blob Storage."""

    def __init__(self):
        self.container_name = Config.STORAGE_CONTAINER
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if Config.AUTH_MODE == "managed":
                from config import get_credential
                self._client = BlobServiceClient(
                    account_url=Config.get_storage_account_url(),
                    credential=get_credential(),
                )
            else:
                # apikey mode — connection string from Azure Portal
                self._client = BlobServiceClient.from_connection_string(
                    Config.STORAGE_CONNECTION_STRING
                )
        return self._client

    def ensure_container(self):
        """Create the blob container if it does not exist."""
        container_client = self.client.get_container_client(self.container_name)
        if not container_client.exists():
            container_client.create_container()
            logger.info("Created blob container: %s", self.container_name)

    def upload_document(self, file_stream, original_filename: str) -> dict:
        """
        Upload a patient intake form to Azure Blob Storage.
        Returns metadata about the uploaded blob.
        """
        self.ensure_container()

        # Generate a unique blob name to prevent collisions
        file_ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "pdf"
        blob_name = f"{uuid.uuid4()}.{file_ext}"

        blob_client = self.client.get_blob_client(
            container=self.container_name,
            blob=blob_name,
        )

        content_settings = ContentSettings(content_type="application/pdf")
        blob_client.upload_blob(file_stream, content_settings=content_settings, overwrite=True)

        logger.info("Uploaded blob: %s", blob_name)

        return {
            "blob_name": blob_name,
            "blob_url": blob_client.url,
            "original_filename": original_filename,
        }

    def get_blob_url(self, blob_name: str) -> str:
        """Return the URL of a blob."""
        blob_client = self.client.get_blob_client(
            container=self.container_name,
            blob=blob_name,
        )
        return blob_client.url

    def download_blob(self, blob_name: str) -> bytes:
        """Download blob content as bytes."""
        blob_client = self.client.get_blob_client(
            container=self.container_name,
            blob=blob_name,
        )
        return blob_client.download_blob().readall()

    def list_blobs(self) -> list:
        """List all blobs in the patient intake container."""
        container_client = self.client.get_container_client(self.container_name)
        return [blob.name for blob in container_client.list_blobs()]
