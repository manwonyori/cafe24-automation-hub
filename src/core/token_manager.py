"""
Secure Token Management
Handles encryption, storage, and retrieval of sensitive tokens
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import logging
import base64

logger = logging.getLogger(__name__)

class TokenManager:
    """Secure token storage and management"""
    
    def __init__(self, encryption_key: str, storage_path: Optional[Path] = None):
        """
        Initialize token manager
        
        Args:
            encryption_key: Key for token encryption
            storage_path: Path for token storage (default: .tokens.encrypted)
        """
        self.encryption_key = encryption_key
        self.storage_path = storage_path or Path('.tokens.encrypted')
        self._cipher = self._init_cipher()
        self._redis_client = self._init_redis()
    
    def _init_cipher(self):
        """Initialize encryption cipher"""
        try:
            from cryptography.fernet import Fernet
            
            # Ensure key is properly formatted
            if len(self.encryption_key) == 32:
                # Convert 32-char string to proper Fernet key
                key = base64.urlsafe_b64encode(self.encryption_key.encode()[:32])
            else:
                # Use provided key as-is or generate new one
                try:
                    key = self.encryption_key.encode()
                    Fernet(key)  # Validate key
                except:
                    logger.warning("Invalid encryption key, generating new one")
                    key = Fernet.generate_key()
            
            return Fernet(key)
        except ImportError:
            logger.error("cryptography package not installed")
            raise ImportError("Please install cryptography: pip install cryptography")
    
    def _init_redis(self):
        """Initialize Redis client (optional)"""
        try:
            import redis
            redis_url = os.getenv('REDIS_URL')
            
            if not redis_url:
                return None
            
            client = redis.from_url(redis_url, decode_responses=True)
            client.ping()
            logger.info("Redis connection established")
            return client
        except Exception as e:
            logger.debug(f"Redis not available: {e}")
            return None
    
    def save_token(self, 
                   token_type: str, 
                   token: str, 
                   expires_in: int = 7200,
                   additional_data: Optional[Dict] = None) -> bool:
        """
        Save token with encryption
        
        Args:
            token_type: Type of token (access, refresh, etc.)
            token: Token value to save
            expires_in: Expiration time in seconds
            additional_data: Additional metadata to store
        
        Returns:
            Success status
        """
        try:
            # Prepare token data
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            data = {
                'token': token,
                'expires_at': expires_at.isoformat(),
                'created_at': datetime.now().isoformat(),
                'type': token_type
            }
            
            if additional_data:
                data.update(additional_data)
            
            # Encrypt token
            encrypted_token = self._cipher.encrypt(token.encode()).decode()
            data['token'] = encrypted_token
            
            # Save to Redis if available
            if self._redis_client:
                key = f"cafe24:token:{token_type}"
                self._redis_client.setex(
                    key,
                    expires_in,
                    json.dumps(data)
                )
                logger.debug(f"Token saved to Redis: {token_type}")
            
            # Always save to file as backup
            self._save_to_file(token_type, data)
            
            logger.info(f"Token saved successfully: {token_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save token: {e}")
            return False
    
    def get_token(self, token_type: str) -> Optional[str]:
        """
        Retrieve and decrypt token
        
        Args:
            token_type: Type of token to retrieve
        
        Returns:
            Decrypted token or None if not found/expired
        """
        try:
            # Try Redis first
            if self._redis_client:
                key = f"cafe24:token:{token_type}"
                data_str = self._redis_client.get(key)
                
                if data_str:
                    data = json.loads(data_str)
                    logger.debug(f"Token retrieved from Redis: {token_type}")
                else:
                    data = None
            else:
                data = None
            
            # Fallback to file
            if not data:
                data = self._load_from_file(token_type)
                
                if not data:
                    logger.debug(f"Token not found: {token_type}")
                    return None
            
            # Check expiration
            expires_at = datetime.fromisoformat(data['expires_at'])
            if datetime.now() > expires_at:
                logger.warning(f"Token expired: {token_type}")
                self.delete_token(token_type)
                return None
            
            # Decrypt token
            encrypted_token = data['token'].encode()
            decrypted_token = self._cipher.decrypt(encrypted_token).decode()
            
            logger.debug(f"Token retrieved successfully: {token_type}")
            return decrypted_token
            
        except Exception as e:
            logger.error(f"Failed to retrieve token: {e}")
            return None
    
    def delete_token(self, token_type: str) -> bool:
        """
        Delete a token
        
        Args:
            token_type: Type of token to delete
        
        Returns:
            Success status
        """
        try:
            # Delete from Redis
            if self._redis_client:
                key = f"cafe24:token:{token_type}"
                self._redis_client.delete(key)
            
            # Delete from file
            tokens = self._load_all_tokens()
            if token_type in tokens:
                del tokens[token_type]
                self._save_all_tokens(tokens)
            
            logger.info(f"Token deleted: {token_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete token: {e}")
            return False
    
    def refresh_token(self, token_type: str, new_expires_in: int) -> bool:
        """
        Refresh token expiration
        
        Args:
            token_type: Type of token to refresh
            new_expires_in: New expiration time in seconds
        
        Returns:
            Success status
        """
        token = self.get_token(token_type)
        if token:
            return self.save_token(token_type, token, new_expires_in)
        return False
    
    def _save_to_file(self, token_type: str, data: Dict):
        """Save token to encrypted file"""
        tokens = self._load_all_tokens()
        tokens[token_type] = data
        self._save_all_tokens(tokens)
    
    def _load_from_file(self, token_type: str) -> Optional[Dict]:
        """Load token from encrypted file"""
        tokens = self._load_all_tokens()
        return tokens.get(token_type)
    
    def _load_all_tokens(self) -> Dict:
        """Load all tokens from file"""
        if not self.storage_path.exists():
            return {}
        
        try:
            with open(self.storage_path, 'rb') as f:
                encrypted_data = f.read()
                
                if not encrypted_data:
                    return {}
                
                decrypted_data = self._cipher.decrypt(encrypted_data)
                return json.loads(decrypted_data)
        except Exception as e:
            logger.debug(f"Could not load tokens from file: {e}")
            return {}
    
    def _save_all_tokens(self, tokens: Dict):
        """Save all tokens to file"""
        try:
            data = json.dumps(tokens).encode()
            encrypted_data = self._cipher.encrypt(data)
            
            # Ensure directory exists
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.storage_path, 'wb') as f:
                f.write(encrypted_data)
        except Exception as e:
            logger.error(f"Failed to save tokens to file: {e}")
    
    def clear_all(self) -> bool:
        """Clear all stored tokens"""
        try:
            # Clear Redis
            if self._redis_client:
                pattern = "cafe24:token:*"
                for key in self._redis_client.scan_iter(match=pattern):
                    self._redis_client.delete(key)
            
            # Clear file
            if self.storage_path.exists():
                self.storage_path.unlink()
            
            logger.info("All tokens cleared")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear tokens: {e}")
            return False
    
    def get_token_info(self, token_type: str) -> Optional[Dict[str, Any]]:
        """
        Get token metadata (without the actual token)
        
        Args:
            token_type: Type of token
        
        Returns:
            Token metadata or None
        """
        try:
            # Try Redis first
            if self._redis_client:
                key = f"cafe24:token:{token_type}"
                data_str = self._redis_client.get(key)
                
                if data_str:
                    data = json.loads(data_str)
                else:
                    data = None
            else:
                data = self._load_from_file(token_type)
            
            if not data:
                return None
            
            # Remove sensitive token value
            info = data.copy()
            info.pop('token', None)
            
            # Add expiration status
            expires_at = datetime.fromisoformat(info['expires_at'])
            info['is_expired'] = datetime.now() > expires_at
            info['expires_in_seconds'] = int((expires_at - datetime.now()).total_seconds())
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get token info: {e}")
            return None