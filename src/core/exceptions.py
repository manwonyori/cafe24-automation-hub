"""
Custom Exceptions for Cafe24 Automation Hub
"""

class Cafe24Error(Exception):
    """Base exception for all Cafe24 related errors"""
    pass

class AuthenticationError(Cafe24Error):
    """Authentication related errors"""
    pass

class TokenExpiredError(AuthenticationError):
    """Token has expired"""
    pass

class TokenNotFoundError(AuthenticationError):
    """Token not found in storage"""
    pass

class APIError(Cafe24Error):
    """API request related errors"""
    
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data

class RateLimitError(APIError):
    """API rate limit exceeded"""
    pass

class ValidationError(Cafe24Error):
    """Data validation errors"""
    pass

class ConfigurationError(Cafe24Error):
    """Configuration related errors"""
    pass

class NetworkError(Cafe24Error):
    """Network connectivity errors"""
    pass