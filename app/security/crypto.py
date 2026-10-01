import os
import base64
import hashlib
import logging
from typing import Dict, Optional, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger("project_npn")


class SecurityVault:
    """
    Secrets Management & Vector AES-256-GCM Encryption at Rest Service.
    - Encrypts float32 vectors/payloads for pgsodium/AES-256 compliance.
    - Rotates LLM API keys via sidecar configuration pattern.
    """

    def __init__(self, master_key: Optional[str] = None):
        raw_key = (master_key or os.getenv("NPN_MASTER_KEY", "npn_secret_master_encryption_key_32b")).encode("utf-8")
        self.key_bytes = hashlib.sha256(raw_key).digest()  # 256-bit key
        self.aesgcm = AESGCM(self.key_bytes)
        self.key_rotation_store: Dict[str, str] = {
            "gemini": os.getenv("GEMINI_API_KEY", ""),
            "groq": os.getenv("GROQ_API_KEY", ""),
            "openai": os.getenv("OPENAI_API_KEY", "")
        }

    def encrypt_bytes(self, data: bytes) -> bytes:
        """Encrypts byte array with AES-256-GCM and prepends 12-byte random nonce."""
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, data, None)
        return nonce + ciphertext

    def decrypt_bytes(self, encrypted_data: bytes) -> bytes:
        """Decrypts AES-256-GCM byte array extracting 12-byte nonce."""
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        return self.aesgcm.decrypt(nonce, ciphertext, None)

    def rotate_api_keys(self) -> Dict[str, str]:
        """Sidecar key rotation method (re-reads env/Vault secrets every 24 hours)."""
        logger.info("Executing 24-hour sidecar secrets rotation for LLM API keys...")
        self.key_rotation_store["gemini"] = os.getenv("GEMINI_API_KEY", self.key_rotation_store["gemini"])
        self.key_rotation_store["groq"] = os.getenv("GROQ_API_KEY", self.key_rotation_store["groq"])
        self.key_rotation_store["openai"] = os.getenv("OPENAI_API_KEY", self.key_rotation_store["openai"])
        return self.key_rotation_store


_vault = None


def get_security_vault() -> SecurityVault:
    global _vault
    if _vault is None:
        _vault = SecurityVault()
    return _vault
