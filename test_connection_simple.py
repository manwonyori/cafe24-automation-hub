#!/usr/bin/env python3
"""
Simple Cafe24 API Connection Test
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.config.settings import settings
from src.core.token_manager import TokenManager

async def test_basic_setup():
    """Test basic setup and configuration"""
    print("=" * 50)
    print("Cafe24 API Connection Test - Simple Version")
    print("=" * 50)
    
    print("\n[1] Configuration Check:")
    print(f"Mall ID: {settings.cafe24_mall_id}")
    print(f"Environment: {settings.environment}")
    print(f"Client ID: {'Set' if settings.cafe24_client_id else 'Not set'}")
    print(f"Client Secret: {'Set' if settings.cafe24_client_secret else 'Not set'}")
    print(f"Encryption Key: {'Set' if settings.encryption_key else 'Not set'}")
    
    print("\n[2] Testing Token Manager:")
    try:
        token_manager = TokenManager(settings.encryption_key)
        
        # Test token save/retrieve
        test_token = "test123"
        token_manager.save_token("test", test_token, expires_in=3600)
        retrieved = token_manager.get_token("test")
        
        if retrieved == test_token:
            print("Token encryption: OK")
        else:
            print("Token encryption: FAILED")
            return False
            
        # Cleanup
        token_manager.delete_token("test")
        
    except Exception as e:
        print(f"Token Manager Error: {e}")
        return False
    
    print("\n[3] Testing Dependencies:")
    try:
        import httpx
        print("httpx: OK")
    except ImportError:
        print("httpx: MISSING")
        return False
    
    try:
        import cryptography
        print("cryptography: OK")
    except ImportError:
        print("cryptography: MISSING")
        return False
    
    print("\n[SUCCESS] Basic setup is working!")
    print("\nNext steps:")
    print("1. Get OAuth authorization code from Cafe24")
    print("2. Run full API test")
    
    return True

if __name__ == "__main__":
    result = asyncio.run(test_basic_setup())
    sys.exit(0 if result else 1)