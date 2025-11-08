from cryptography.fernet import Fernet
from typing import Union

class EncryptionService:
    """
    Service for handling AES-256 encryption and decryption.
    """
    def __init__(self, key: str):
        """
        Initializes the EncryptionService with a Fernet key.
        The key must be a URL-safe base64-encoded 32-byte key.
        """
        self.fernet = Fernet(key.encode('utf-8'))

    def encrypt(self, data: Union[str, bytes]) -> bytes:
        """
        Encrypts the given data.
        Args:
            data: The data to encrypt, either a string or bytes.
        Returns:
            The encrypted data as bytes.
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        return self.fernet.encrypt(data)

    def decrypt(self, encrypted_data: bytes) -> str:
        """
        Decrypts the given encrypted data.
        Args:
            encrypted_data: The encrypted data as bytes.
        Returns:
            The decrypted data as a string.
        """
        decrypted_bytes = self.fernet.decrypt(encrypted_data)
        return decrypted_bytes.decode('utf-8')
