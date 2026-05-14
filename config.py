"""
Zenith Healthcare AI Platform - Configuration
Loads all settings from environment variables (.env file).

AUTH MODE (set AUTH_MODE in .env):
  "apikey"  — use API keys copied from the Azure Portal (recommended for students starting out)
  "managed" — use Managed Identity / DefaultAzureCredential for all services (production best practice)
  "auto"    — try key-based auth first; if the service rejects it (e.g. key auth disabled on the
               storage account), automatically fall back to Managed Identity for that service only.
               Recommended when your org disables key auth on some but not all resources.

Students: copy .env.example to .env and fill in your Azure resource details.
Start with AUTH_MODE=apikey and API keys, then explore managed/auto if needed.
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Managed Identity / Key Vault helpers (only imported when needed)
# ---------------------------------------------------------------------------
_credential = None


def get_credential():
    """Return a shared DefaultAzureCredential instance (singleton).
    Only used when AUTH_MODE=managed.
    """
    global _credential
    if _credential is None:
        from azure.identity import DefaultAzureCredential
        _credential = DefaultAzureCredential()
    return _credential


class Config:
    """Application configuration loaded from environment variables."""

    # ---------------------------------------------------------------------------
    # Auth mode — controls whether API keys or Managed Identity is used
    # ---------------------------------------------------------------------------
    # "apikey"  → keys come from .env (easy for first-time Azure Portal setup)
    # "managed" → uses DefaultAzureCredential for all services (production best practice)
    # "auto"    → tries key-based first; falls back to Managed Identity per-service if denied
    AUTH_MODE = os.environ.get("AUTH_MODE", "apikey").lower()

    # ---------------------------------------------------------------------------
    # Flask
    # ---------------------------------------------------------------------------
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")

    # ---------------------------------------------------------------------------
    # Azure Key Vault (optional — only used when AUTH_MODE=managed)
    # ---------------------------------------------------------------------------
    KEY_VAULT_URL = os.environ.get("AZURE_KEY_VAULT_URL", "")

    # ---------------------------------------------------------------------------
    # Azure Blob Storage
    #   apikey  mode → uses a connection string from the Portal
    #   managed mode → uses the storage account name; Managed Identity handles auth
    # ---------------------------------------------------------------------------
    STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")
    STORAGE_ACCOUNT_NAME = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME", "")
    STORAGE_CONTAINER = os.environ.get("AZURE_STORAGE_CONTAINER", "patient-intake-forms")

    @classmethod
    def get_storage_account_url(cls):
        name = cls.STORAGE_ACCOUNT_NAME or (
            cls.STORAGE_CONNECTION_STRING.split("AccountName=")[1].split(";")[0]
            if "AccountName=" in cls.STORAGE_CONNECTION_STRING else ""
        )
        return f"https://{name}.blob.core.windows.net" if name else ""

    # ---------------------------------------------------------------------------
    # Azure AI Document Intelligence
    # ---------------------------------------------------------------------------
    DOC_INTELLIGENCE_ENDPOINT = os.environ.get("DOCUMENT_INTELLIGENCE_ENDPOINT", "")
    DOC_INTELLIGENCE_KEY = os.environ.get("DOCUMENT_INTELLIGENCE_KEY", "")

    # ---------------------------------------------------------------------------
    # Azure MySQL Flexible Server
    # ---------------------------------------------------------------------------
    MYSQL_HOST = os.environ.get("AZURE_MYSQL_HOST", "")
    MYSQL_DATABASE = os.environ.get("AZURE_MYSQL_DATABASE", "zenith_healthcare")
    MYSQL_USERNAME = os.environ.get("AZURE_MYSQL_USERNAME", "")
    MYSQL_PASSWORD = os.environ.get("AZURE_MYSQL_PASSWORD", "")
    # Path to the downloaded DigiCert SSL cert.
    # Falls back to the local file you downloaded in Downloads.
    MYSQL_SSL_CA = os.environ.get(
        "AZURE_MYSQL_SSL_CA",
        "/home/mun/Downloads/DigiCertGlobalRootG2.crt.pem",
    )

    _mysql_password_cache = None

    @classmethod
    def get_mysql_password(cls):
        """Return the MySQL password.

        apikey  mode → read directly from AZURE_MYSQL_PASSWORD in .env
        auto    mode → read directly from AZURE_MYSQL_PASSWORD in .env (Key Vault not used)
        managed mode → fetch from Azure Key Vault (secret name: mysql-admin-password),
                       with a fallback to AZURE_MYSQL_PASSWORD if Key Vault is not configured
        """
        if cls._mysql_password_cache is not None:
            return cls._mysql_password_cache

        if cls.AUTH_MODE in ("apikey", "auto") or not cls.KEY_VAULT_URL:
            # Simple path: password comes straight from .env
            pw = cls.MYSQL_PASSWORD
            if not pw:
                raise ValueError(
                    "AZURE_MYSQL_PASSWORD is not set in .env. "
                    "Open .env and add your MySQL admin password."
                )
            cls._mysql_password_cache = pw
            return pw

        # managed mode → retrieve from Azure Key Vault
        try:
            from azure.keyvault.secrets import SecretClient
            kv_client = SecretClient(vault_url=cls.KEY_VAULT_URL, credential=get_credential())
            secret = kv_client.get_secret("mysql-admin-password")
            cls._mysql_password_cache = secret.value
            logger.info("MySQL password retrieved from Key Vault.")
            return cls._mysql_password_cache
        except Exception as exc:
            logger.error("Failed to retrieve MySQL password from Key Vault: %s", exc)
            raise

    @classmethod
    def get_mysql_connection_config(cls):
        """Return a dict of connection params for mysql.connector.connect()."""
        config = {
            "host": cls.MYSQL_HOST,
            "database": cls.MYSQL_DATABASE,
            "user": cls.MYSQL_USERNAME,
            "password": cls.get_mysql_password(),
            "ssl_disabled": False,
        }
        if cls.MYSQL_SSL_CA and os.path.exists(cls.MYSQL_SSL_CA):
            config["ssl_ca"] = cls.MYSQL_SSL_CA
        return config

    # ---------------------------------------------------------------------------
    # Azure AI Search
    # ---------------------------------------------------------------------------
    SEARCH_ENDPOINT = os.environ.get("AZURE_SEARCH_ENDPOINT", "")
    SEARCH_KEY = os.environ.get("AZURE_SEARCH_KEY", "")
    SEARCH_INDEX = os.environ.get("AZURE_SEARCH_INDEX", "patient-intake-index")

    # ---------------------------------------------------------------------------
    # Azure OpenAI
    # ---------------------------------------------------------------------------
    OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
    OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY", "")
    OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
