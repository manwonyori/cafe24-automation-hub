"""
OAuth Authentication Manager for Cafe24
Handles OAuth flow, token management, and authentication
"""

import base64
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlencode

from ..config.settings import settings
from .token_manager import TokenManager
from .exceptions import AuthenticationError, TokenExpiredError

logger = logging.getLogger(__name__)

class AuthManager:
    """Cafe24 OAuth authentication manager"""
    
    def __init__(self):
        """Initialize authentication manager"""
        self.settings = settings
        self.token_manager = TokenManager(settings.encryption_key)
        self._validate_credentials()
    
    def _validate_credentials(self):
        """Validate required credentials are present"""
        if not self.settings.cafe24_client_id or not self.settings.cafe24_client_secret:
            raise AuthenticationError(
                "Missing Cafe24 credentials. Please set CAFE24_CLIENT_ID and CAFE24_CLIENT_SECRET"
            )
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Generate OAuth authorization URL
        
        Args:
            state: Optional state parameter for CSRF protection
        
        Returns:
            Authorization URL
        """
        params = {
            'response_type': 'code',
            'client_id': self.settings.cafe24_client_id,
            'redirect_uri': self.settings.redirect_uri,
            'scope': ' '.join(self.settings.get_scopes())
        }
        
        if state:
            params['state'] = state
        
        base_url = f"{self.settings.cafe24_base_url}/oauth/authorize"
        return f"{base_url}?{urlencode(params)}"
    
    async def exchange_code_for_token(self, authorization_code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token
        
        Args:
            authorization_code: OAuth authorization code
        
        Returns:
            Token response data
        """
        import httpx
        
        # Prepare authentication header
        auth_string = f"{self.settings.cafe24_client_id}:{self.settings.cafe24_client_secret}"
        auth_bytes = base64.b64encode(auth_string.encode()).decode()
        
        # Token request
        token_url = f"{self.settings.cafe24_base_url}/oauth/token"
        
        headers = {
            'Authorization': f'Basic {auth_bytes}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'authorization_code',
            'code': authorization_code,
            'redirect_uri': self.settings.redirect_uri
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(token_url, headers=headers, data=data)
                response.raise_for_status()
                
                token_data = response.json()
                
                # Save tokens
                self._save_tokens(token_data)
                
                logger.info("Successfully exchanged code for tokens")
                return token_data
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to exchange code: {e.response.text}")
            raise AuthenticationError(f"Token exchange failed: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Unexpected error during token exchange: {e}")
            raise AuthenticationError(f"Token exchange failed: {str(e)}")
    
    async def refresh_access_token(self) -> str:
        """
        Refresh access token using refresh token
        
        Returns:
            New access token
        """
        import httpx
        
        # Get refresh token
        refresh_token = self.token_manager.get_token('refresh')
        if not refresh_token:
            raise TokenExpiredError("No refresh token available. Please re-authenticate.")
        
        # Prepare authentication header
        auth_string = f"{self.settings.cafe24_client_id}:{self.settings.cafe24_client_secret}"
        auth_bytes = base64.b64encode(auth_string.encode()).decode()
        
        # Token refresh request
        token_url = f"{self.settings.cafe24_base_url}/oauth/token"
        
        headers = {
            'Authorization': f'Basic {auth_bytes}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(token_url, headers=headers, data=data)
                response.raise_for_status()
                
                token_data = response.json()
                
                # Save new tokens
                self._save_tokens(token_data)
                
                logger.info("Successfully refreshed access token")
                return token_data['access_token']
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to refresh token: {e.response.text}")
            
            # If refresh failed, clear tokens
            self.token_manager.clear_all()
            raise TokenExpiredError("Token refresh failed. Please re-authenticate.")
        except Exception as e:
            logger.error(f"Unexpected error during token refresh: {e}")
            raise AuthenticationError(f"Token refresh failed: {str(e)}")
    
    async def get_valid_token(self) -> str:
        """
        Get valid access token, refreshing if necessary
        
        Returns:
            Valid access token
        """
        # Try to get existing token
        access_token = self.token_manager.get_token('access')
        
        if access_token:
            # Check if token is about to expire (within 5 minutes)
            token_info = self.token_manager.get_token_info('access')
            if token_info and token_info.get('expires_in_seconds', 0) > 300:
                return access_token
            
            # Token is expired or about to expire, try to refresh
            logger.info("Access token expired or expiring soon, attempting refresh")
            try:
                return await self.refresh_access_token()
            except TokenExpiredError:
                raise
        
        # No token available
        raise AuthenticationError(
            "No valid access token. Please authenticate using the authorization URL."
        )
    
    def _save_tokens(self, token_data: Dict[str, Any]):
        """
        Save tokens from OAuth response
        
        Args:
            token_data: OAuth token response
        """
        # Save access token
        if 'access_token' in token_data:
            expires_in = token_data.get('expires_in', 7200)
            self.token_manager.save_token(
                'access',
                token_data['access_token'],
                expires_in,
                {
                    'token_type': token_data.get('token_type', 'Bearer'),
                    'scope': token_data.get('scope', '')
                }
            )
        
        # Save refresh token if provided
        if 'refresh_token' in token_data:
            # Refresh tokens typically last 30 days
            self.token_manager.save_token(
                'refresh',
                token_data['refresh_token'],
                2592000  # 30 days in seconds
            )
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authorization headers for API requests
        
        Returns:
            Headers dict with authorization
        """
        access_token = self.token_manager.get_token('access')
        if not access_token:
            raise AuthenticationError("No access token available")
        
        return {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'X-Cafe24-Api-Version': self.settings.api_version
        }
    
    async def get_async_auth_headers(self) -> Dict[str, str]:
        """
        Get authorization headers for async API requests
        
        Returns:
            Headers dict with authorization
        """
        access_token = await self.get_valid_token()
        
        return {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'X-Cafe24-Api-Version': self.settings.api_version
        }
    
    def is_authenticated(self) -> bool:
        """
        Check if user is authenticated
        
        Returns:
            True if valid access token exists
        """
        token = self.token_manager.get_token('access')
        return token is not None
    
    def get_token_info(self) -> Dict[str, Any]:
        """
        Get information about current tokens
        
        Returns:
            Token information
        """
        info = {
            'authenticated': self.is_authenticated(),
            'access_token': None,
            'refresh_token': None
        }
        
        # Get access token info
        access_info = self.token_manager.get_token_info('access')
        if access_info:
            info['access_token'] = {
                'exists': True,
                'expires_at': access_info.get('expires_at'),
                'expires_in_seconds': access_info.get('expires_in_seconds'),
                'is_expired': access_info.get('is_expired')
            }
        
        # Get refresh token info
        refresh_info = self.token_manager.get_token_info('refresh')
        if refresh_info:
            info['refresh_token'] = {
                'exists': True,
                'expires_at': refresh_info.get('expires_at'),
                'expires_in_seconds': refresh_info.get('expires_in_seconds'),
                'is_expired': refresh_info.get('is_expired')
            }
        
        return info
    
    def logout(self):
        """Clear all tokens (logout)"""
        self.token_manager.clear_all()
        logger.info("User logged out, all tokens cleared")