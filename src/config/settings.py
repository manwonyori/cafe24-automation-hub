"""
Application Settings Management
Centralized configuration using environment variables
"""

import os
from pathlib import Path
from typing import Optional, List
from functools import lru_cache
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings:
    """Application configuration settings"""
    
    def __init__(self):
        """Initialize settings from environment variables"""
        # Load .env file if exists
        self._load_env_file()
        
        # Cafe24 API Configuration
        self.cafe24_mall_id: str = os.getenv('CAFE24_MALL_ID', 'manwonyori')
        self.cafe24_client_id: str = os.getenv('CAFE24_CLIENT_ID', '')
        self.cafe24_client_secret: str = os.getenv('CAFE24_CLIENT_SECRET', '')
        self.cafe24_service_key: Optional[str] = os.getenv('CAFE24_SERVICE_KEY')
        
        # Security Settings
        self.encryption_key: str = os.getenv('ENCRYPTION_KEY', self._generate_key())
        self.jwt_secret: str = os.getenv('JWT_SECRET', 'change-me-in-production')
        
        # API Configuration
        self.api_version: str = os.getenv('API_VERSION', '2024-06-01')
        self.api_timeout: int = int(os.getenv('API_TIMEOUT', '30'))
        self.max_retries: int = int(os.getenv('MAX_RETRIES', '3'))
        
        # Environment
        self.environment: str = os.getenv('ENVIRONMENT', 'development')
        self.debug: bool = os.getenv('DEBUG', 'False').lower() == 'true'
        self.log_level: str = os.getenv('LOG_LEVEL', 'INFO')
        
        # Database
        self.database_url: str = os.getenv('DATABASE_URL', 'sqlite:///cafe24.db')
        
        # Redis (Optional)
        self.redis_url: Optional[str] = os.getenv('REDIS_URL')
        
        # Monitoring (Optional)
        self.sentry_dsn: Optional[str] = os.getenv('SENTRY_DSN')
        
        # Validate configuration
        self._validate_config()
    
    def _load_env_file(self):
        """Load .env file if exists"""
        env_file = Path('.env')
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv()
                logger.info("Loaded .env file")
            except ImportError:
                logger.warning("python-dotenv not installed, skipping .env file")
    
    def _generate_key(self) -> str:
        """Generate a default encryption key (for development only)"""
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(32))
    
    def _validate_config(self):
        """Validate required configuration"""
        errors = []
        
        if not self.cafe24_client_id:
            errors.append("CAFE24_CLIENT_ID is required")
        
        if not self.cafe24_client_secret:
            errors.append("CAFE24_CLIENT_SECRET is required")
        
        if self.environment == 'production':
            if self.encryption_key == self._generate_key():
                errors.append("ENCRYPTION_KEY must be set in production")
            
            if self.jwt_secret == 'change-me-in-production':
                errors.append("JWT_SECRET must be changed in production")
            
            if self.debug:
                errors.append("DEBUG should be False in production")
        
        if errors:
            for error in errors:
                logger.error(f"Configuration Error: {error}")
            
            if self.environment == 'production':
                raise ValueError("Configuration validation failed")
    
    @property
    def cafe24_base_url(self) -> str:
        """Get Cafe24 API base URL"""
        return f"https://{self.cafe24_mall_id}.cafe24api.com/api/v2"
    
    @property
    def redirect_uri(self) -> str:
        """Get OAuth redirect URI"""
        # Check for explicit environment variable first
        if os.getenv('CAFE24_REDIRECT_URI'):
            return os.getenv('CAFE24_REDIRECT_URI')
        # Fallback to default based on environment
        if os.getenv('RENDER') or self.environment == 'production':
            return "https://cafe24-automation.onrender.com/auth/callback"
        return "http://localhost:3000/auth/callback"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == 'production'
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == 'development'
    
    def get_scopes(self) -> List[str]:
        """Get required API scopes"""
        # Return empty list to use default scopes
        # Cafe24 will use the scopes configured in the app settings
        return []
    
    def to_dict(self) -> dict:
        """Convert settings to dictionary (excluding sensitive data)"""
        return {
            'environment': self.environment,
            'cafe24_mall_id': self.cafe24_mall_id,
            'api_version': self.api_version,
            'debug': self.debug,
            'log_level': self.log_level,
            'api_timeout': self.api_timeout,
            'max_retries': self.max_retries,
            'scopes': self.get_scopes()
        }
    
    def __repr__(self) -> str:
        """String representation of settings"""
        return f"<Settings: {self.environment} - Mall: {self.cafe24_mall_id}>"

# Create singleton instance
@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

# Export settings instance
settings = get_settings()