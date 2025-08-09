"""
Cafe24 API Client
Base client for all API interactions with retry logic and error handling
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
import json

from ..config.settings import settings
from ..core.auth_manager import AuthManager
from ..core.exceptions import (
    APIError, 
    RateLimitError, 
    NetworkError, 
    ValidationError,
    AuthenticationError
)

logger = logging.getLogger(__name__)

class Cafe24Client:
    """Main API client for Cafe24"""
    
    def __init__(self, auth_manager: Optional[AuthManager] = None):
        """
        Initialize API client
        
        Args:
            auth_manager: Optional pre-configured auth manager
        """
        self.settings = settings
        self.auth_manager = auth_manager or AuthManager()
        self._session_cache = {}
        self._rate_limit_reset = None
        self._requests_this_minute = 0
        
    async def _get_session(self):
        """Get or create HTTP session"""
        import httpx
        
        if 'httpx_client' not in self._session_cache:
            timeout = httpx.Timeout(
                connect=10.0,
                read=self.settings.api_timeout,
                write=10.0,
                pool=10.0
            )
            
            self._session_cache['httpx_client'] = httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=10)
            )
        
        return self._session_cache['httpx_client']
    
    async def close(self):
        """Close all open sessions"""
        if 'httpx_client' in self._session_cache:
            await self._session_cache['httpx_client'].aclose()
            del self._session_cache['httpx_client']
    
    async def _handle_rate_limit(self):
        """Handle rate limiting"""
        current_time = datetime.now()
        
        # Reset counter every minute
        if (self._rate_limit_reset is None or 
            (current_time - self._rate_limit_reset).total_seconds() >= 60):
            self._rate_limit_reset = current_time
            self._requests_this_minute = 0
        
        # Check if we're approaching rate limit
        if self._requests_this_minute >= 95:  # Leave buffer of 5 requests
            wait_time = 60 - (current_time - self._rate_limit_reset).total_seconds()
            if wait_time > 0:
                logger.warning(f"Rate limit approached, waiting {wait_time:.1f} seconds")
                await asyncio.sleep(wait_time)
                self._rate_limit_reset = datetime.now()
                self._requests_this_minute = 0
        
        self._requests_this_minute += 1
    
    async def request(self, 
                     method: str, 
                     endpoint: str,
                     params: Optional[Dict] = None,
                     data: Optional[Dict] = None,
                     json_data: Optional[Dict] = None,
                     headers: Optional[Dict] = None,
                     retry_count: int = None) -> Dict[str, Any]:
        """
        Make API request with retry logic
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            params: Query parameters
            data: Form data
            json_data: JSON data
            headers: Additional headers
            retry_count: Number of retries (uses settings default if None)
        
        Returns:
            API response data
        """
        if retry_count is None:
            retry_count = self.settings.max_retries
        
        # Handle rate limiting
        await self._handle_rate_limit()
        
        # Prepare URL
        if endpoint.startswith('http'):
            url = endpoint
        else:
            url = f"{self.settings.cafe24_base_url}/admin/{endpoint.lstrip('/')}"
        
        # Get authentication headers
        try:
            auth_headers = await self.auth_manager.get_async_auth_headers()
        except AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            raise
        
        # Merge headers
        request_headers = auth_headers.copy()
        if headers:
            request_headers.update(headers)
        
        # Get session
        session = await self._get_session()
        
        # Log request
        logger.debug(f"{method} {url} - Retry: {self.settings.max_retries - retry_count}")
        
        try:
            response = await session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json_data,
                headers=request_headers
            )
            
            # Handle different status codes
            if response.status_code == 200:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {'message': 'Success', 'data': response.text}
                    
            elif response.status_code == 201:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {'message': 'Created', 'data': response.text}
                    
            elif response.status_code == 204:
                return {'message': 'No Content'}
                
            elif response.status_code == 401:
                # Try to refresh token once
                if retry_count == self.settings.max_retries:
                    logger.info("Got 401, attempting token refresh")
                    try:
                        await self.auth_manager.refresh_access_token()
                        # Retry with refreshed token
                        return await self.request(
                            method, endpoint, params, data, json_data, headers, retry_count - 1
                        )
                    except Exception as refresh_error:
                        raise AuthenticationError(f"Authentication failed: {refresh_error}")
                else:
                    raise AuthenticationError("Invalid or expired token")
                    
            elif response.status_code == 429:
                # Rate limit exceeded
                retry_after = int(response.headers.get('Retry-After', 60))
                if retry_count > 0:
                    logger.warning(f"Rate limit exceeded, waiting {retry_after} seconds")
                    await asyncio.sleep(retry_after)
                    return await self.request(
                        method, endpoint, params, data, json_data, headers, retry_count - 1
                    )
                else:
                    raise RateLimitError("Rate limit exceeded")
                    
            elif 400 <= response.status_code < 500:
                # Client error
                error_data = {}
                try:
                    error_data = response.json()
                except:
                    error_data = {'message': response.text}
                
                error_msg = error_data.get('message', f'Client error: {response.status_code}')
                raise APIError(error_msg, response.status_code, error_data)
                
            elif 500 <= response.status_code < 600:
                # Server error - retry if possible
                if retry_count > 0:
                    wait_time = (self.settings.max_retries - retry_count + 1) * 2  # Exponential backoff
                    logger.warning(f"Server error {response.status_code}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    return await self.request(
                        method, endpoint, params, data, json_data, headers, retry_count - 1
                    )
                else:
                    raise APIError(f"Server error: {response.status_code}", response.status_code)
                    
        except asyncio.TimeoutError:
            if retry_count > 0:
                logger.warning("Request timeout, retrying...")
                return await self.request(
                    method, endpoint, params, data, json_data, headers, retry_count - 1
                )
            else:
                raise NetworkError("Request timeout")
                
        except Exception as e:
            if retry_count > 0 and not isinstance(e, (AuthenticationError, ValidationError)):
                logger.warning(f"Request failed: {e}, retrying...")
                await asyncio.sleep(1)
                return await self.request(
                    method, endpoint, params, data, json_data, headers, retry_count - 1
                )
            else:
                logger.error(f"Request failed after all retries: {e}")
                raise NetworkError(str(e))
    
    # Convenience methods for common HTTP verbs
    async def get(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> Dict:
        """Make GET request"""
        return await self.request('GET', endpoint, params=params, **kwargs)
    
    async def post(self, endpoint: str, data: Optional[Dict] = None, json_data: Optional[Dict] = None, **kwargs) -> Dict:
        """Make POST request"""
        return await self.request('POST', endpoint, data=data, json_data=json_data, **kwargs)
    
    async def put(self, endpoint: str, data: Optional[Dict] = None, json_data: Optional[Dict] = None, **kwargs) -> Dict:
        """Make PUT request"""
        return await self.request('PUT', endpoint, data=data, json_data=json_data, **kwargs)
    
    async def patch(self, endpoint: str, data: Optional[Dict] = None, json_data: Optional[Dict] = None, **kwargs) -> Dict:
        """Make PATCH request"""
        return await self.request('PATCH', endpoint, data=data, json_data=json_data, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> Dict:
        """Make DELETE request"""
        return await self.request('DELETE', endpoint, **kwargs)
    
    # Health check methods
    async def ping(self) -> bool:
        """Test API connectivity"""
        try:
            response = await self.get('products', params={'limit': 1})
            return 'products' in response or 'message' in response
        except Exception as e:
            logger.error(f"Ping failed: {e}")
            return False
    
    async def get_api_info(self) -> Dict[str, Any]:
        """Get API information and limits"""
        try:
            # This is a simple test endpoint
            await self.get('products', params={'limit': 1})
            
            return {
                'connected': True,
                'mall_id': self.settings.cafe24_mall_id,
                'api_version': self.settings.api_version,
                'base_url': self.settings.cafe24_base_url,
                'rate_limit': {
                    'requests_per_minute': 100,
                    'current_count': self._requests_this_minute
                }
            }
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }
    
    def __enter__(self):
        return self
    
    async def __aenter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()