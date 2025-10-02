import os
import logging
from typing import Optional
from enum import Enum
import keyring
from cryptography.fernet import Fernet
import base64
import hashlib

logger = logging.getLogger(__name__)


class ApiProvider(Enum):
    NVD = "nvd"
    CISA_KEV = "cisa_kev"
    EXPLOITDB = "exploitdb"


class ApiKeyManager:
    """Secure API key management using OS keyring services with encryption at rest"""

    def __init__(self):
        self.service_name = "hermes"
        self._encryption_key = self._get_or_create_encryption_key()

    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for additional security layer"""
        key_name = f"{self.service_name}_encryption_key"
        stored_key = keyring.get_password(self.service_name, key_name)

        if not stored_key:
            # Generate new encryption key
            key = Fernet.generate_key()
            keyring.set_password(self.service_name, key_name, key.decode())
            return key

        return stored_key.encode()

    def _encrypt_api_key(self, api_key: str) -> str:
        """Encrypt API key for additional security"""
        f = Fernet(self._encryption_key)
        encrypted = f.encrypt(api_key.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def _decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt API key"""
        f = Fernet(self._encryption_key)
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_key.encode())
        decrypted = f.decrypt(encrypted_bytes)
        return decrypted.decode()

    def store_api_key(self, provider: ApiProvider, api_key: str) -> bool:
        """Store API key securely using OS keyring services with encryption"""
        try:
            # Encrypt the API key before storing
            encrypted_key = self._encrypt_api_key(api_key)
            keyring.set_password(self.service_name, provider.value, encrypted_key)
            logger.info(f"Successfully stored API key for {provider.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to store API key for {provider.value}: {e}")
            return False

    def get_api_key(self, provider: ApiProvider) -> Optional[str]:
        """Retrieve API key from keyring with fallback to environment"""
        try:
            # Try keyring first
            encrypted_key = keyring.get_password(self.service_name, provider.value)
            if encrypted_key:
                try:
                    return self._decrypt_api_key(encrypted_key)
                except Exception as e:
                    logger.warning(f"Failed to decrypt stored key for {provider.value}: {e}")
                    # Fall through to environment variable fallback

            # Fallback to environment variable for development/testing
            env_var = f"{provider.value.upper()}_API_KEY"
            key = os.getenv(env_var)
            if key:
                logger.info(f"Using environment variable {env_var} for {provider.value}")
                return key

            logger.warning(f"No API key found for {provider.value}")
            return None

        except Exception as e:
            logger.error(f"Failed to retrieve API key for {provider.value}: {e}")
            return None

    def delete_api_key(self, provider: ApiProvider) -> bool:
        """Delete API key from keyring"""
        try:
            keyring.delete_password(self.service_name, provider.value)
            logger.info(f"Successfully deleted API key for {provider.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete API key for {provider.value}: {e}")
            return False

    def list_stored_providers(self) -> list[ApiProvider]:
        """List providers that have stored API keys"""
        stored_providers = []
        for provider in ApiProvider:
            if keyring.get_password(self.service_name, provider.value):
                stored_providers.append(provider)
        return stored_providers

    def validate_api_key_format(self, provider: ApiProvider, api_key: str) -> bool:
        """Validate API key format based on provider requirements"""
        if not api_key or not api_key.strip():
            return False

        # Provider-specific validation
        if provider == ApiProvider.NVD:
            # NVD API keys are typically UUIDs
            import re
            uuid_pattern = re.compile(
                r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
                re.IGNORECASE
            )
            return bool(uuid_pattern.match(api_key.strip()))

        elif provider == ApiProvider.CISA_KEV:
            # CISA KEV typically doesn't require API keys, but if they do,
            # they would likely be alphanumeric
            return len(api_key.strip()) >= 10 and api_key.strip().isalnum()

        elif provider == ApiProvider.EXPLOITDB:
            # ExploitDB API keys format (if they implement them)
            return len(api_key.strip()) >= 8

        return True  # Default to accepting the key