#!/usr/bin/env python3
"""
Cafe24 API Connection Test Script
Tests the complete authentication and API flow
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.config.settings import settings
from src.core.auth_manager import AuthManager
from src.core.token_manager import TokenManager
from src.api.client import Cafe24Client
from src.api.products import ProductAPI

class APITester:
    """Test class for API functionality"""
    
    def __init__(self):
        print("[TESTER] Cafe24 API Connection Tester v2.0")
        print("=" * 50)
        
        self.auth_manager = None
        self.client = None
        self.product_api = None
        
    def print_config(self):
        """Print current configuration (without secrets)"""
        print("\n📋 Configuration:")
        print(f"  Mall ID: {settings.cafe24_mall_id}")
        print(f"  Environment: {settings.environment}")
        print(f"  API Version: {settings.api_version}")
        print(f"  Base URL: {settings.cafe24_base_url}")
        print(f"  Redirect URI: {settings.redirect_uri}")
        print(f"  Client ID: {settings.cafe24_client_id[:10]}..." if settings.cafe24_client_id else "  ❌ Client ID not set")
        print(f"  Client Secret: {'✅ Set' if settings.cafe24_client_secret else '❌ Not set'}")
        print(f"  Encryption Key: {'✅ Set' if settings.encryption_key else '❌ Not set'}")
    
    def check_dependencies(self):
        """Check if all required dependencies are available"""
        print("\n🔍 Checking Dependencies:")
        
        required_packages = [
            'httpx',
            'cryptography',
            'python-dotenv'
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                print(f"  ✅ {package}")
            except ImportError:
                print(f"  ❌ {package}")
                missing_packages.append(package)
        
        if missing_packages:
            print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
            print("Install with: pip install " + " ".join(missing_packages))
            return False
        
        return True
    
    async def test_token_manager(self):
        """Test token encryption and storage"""
        print("\n🔐 Testing Token Manager:")
        
        try:
            token_manager = TokenManager(settings.encryption_key)
            
            # Test save/retrieve
            test_token = "test_token_12345"
            success = token_manager.save_token("test", test_token, expires_in=3600)
            
            if not success:
                print("  ❌ Failed to save token")
                return False
            
            retrieved_token = token_manager.get_token("test")
            
            if retrieved_token != test_token:
                print("  ❌ Token retrieval failed")
                return False
            
            print("  ✅ Token encryption/decryption working")
            
            # Test token info
            info = token_manager.get_token_info("test")
            if info:
                print(f"  ✅ Token info: expires in {info.get('expires_in_seconds')}s")
            
            # Cleanup
            token_manager.delete_token("test")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Token manager test failed: {e}")
            return False
    
    async def test_auth_manager(self):
        """Test authentication manager"""
        print("\n🔑 Testing Authentication Manager:")
        
        try:
            self.auth_manager = AuthManager()
            print("  ✅ Auth manager initialized")
            
            # Check if already authenticated
            if self.auth_manager.is_authenticated():
                print("  ✅ Already authenticated")
                token_info = self.auth_manager.get_token_info()
                
                access_info = token_info.get('access_token')
                if access_info:
                    if access_info['is_expired']:
                        print("  ⚠️ Access token expired")
                    else:
                        expires_in = access_info.get('expires_in_seconds', 0)
                        print(f"  ✅ Access token valid (expires in {expires_in}s)")
                
                return True
            else:
                print("  ⚠️ Not authenticated")
                auth_url = self.auth_manager.get_authorization_url()
                print(f"\n🔗 Authorization URL:")
                print(f"  {auth_url}")
                print("\n📝 Instructions:")
                print("  1. Open the URL above in your browser")
                print("  2. Authorize the application")
                print("  3. Copy the 'code' parameter from the callback URL")
                print("  4. Run this script again with the code")
                
                # Check if code provided via environment
                auth_code = os.getenv('CAFE24_AUTH_CODE')
                if auth_code:
                    print(f"\n🔄 Using auth code from environment...")
                    await self.auth_manager.exchange_code_for_token(auth_code)
                    print("  ✅ Successfully exchanged code for token")
                    return True
                else:
                    # Ask for code interactively
                    try:
                        code = input("\nEnter authorization code (or press Enter to skip): ").strip()
                        if code:
                            await self.auth_manager.exchange_code_for_token(code)
                            print("  ✅ Successfully exchanged code for token")
                            return True
                        else:
                            print("  ⏭️ Skipping authentication for now")
                            return False
                    except KeyboardInterrupt:
                        print("\n  ⏭️ Skipping authentication")
                        return False
                
        except Exception as e:
            print(f"  ❌ Auth manager test failed: {e}")
            return False
    
    async def test_api_client(self):
        """Test basic API client functionality"""
        print("\n🌐 Testing API Client:")
        
        if not self.auth_manager or not self.auth_manager.is_authenticated():
            print("  ⏭️ Skipping (not authenticated)")
            return False
        
        try:
            self.client = Cafe24Client(self.auth_manager)
            
            # Test ping
            is_connected = await self.client.ping()
            if is_connected:
                print("  ✅ API connection successful")
            else:
                print("  ❌ API ping failed")
                return False
            
            # Get API info
            api_info = await self.client.get_api_info()
            if api_info.get('connected'):
                print(f"  ✅ API Info:")
                print(f"    Mall ID: {api_info.get('mall_id')}")
                print(f"    API Version: {api_info.get('api_version')}")
                print(f"    Requests this minute: {api_info.get('rate_limit', {}).get('current_count', 0)}")
            
            return True
            
        except Exception as e:
            print(f"  ❌ API client test failed: {e}")
            return False
    
    async def test_product_api(self):
        """Test product API functionality"""
        print("\n🛍️ Testing Product API:")
        
        if not self.client:
            print("  ⏭️ Skipping (API client not available)")
            return False
        
        try:
            self.product_api = ProductAPI(self.client)
            
            # Test get products
            print("  🔍 Fetching first 5 products...")
            result = await self.product_api.get_products(limit=5)
            
            products = result.get('products', [])
            print(f"  ✅ Retrieved {len(products)} products")
            
            if products:
                # Show first product info
                first_product = products[0]
                print(f"  📦 Sample Product:")
                print(f"    Product No: {first_product.get('product_no')}")
                print(f"    Name: {first_product.get('product_name', 'N/A')}")
                print(f"    Price: {first_product.get('price', 'N/A')}")
                print(f"    Stock: {first_product.get('stock_quantity', 'N/A')}")
                
                # Test individual product retrieval
                product_no = first_product.get('product_no')
                if product_no:
                    print(f"  🔍 Fetching product details for #{product_no}...")
                    product_detail = await self.product_api.get_product(product_no)
                    
                    if product_detail:
                        print("  ✅ Product detail retrieved successfully")
                    else:
                        print("  ⚠️ Product detail not found")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Product API test failed: {e}")
            return False
    
    async def test_product_search(self):
        """Test product search functionality"""
        print("\n🔍 Testing Product Search:")
        
        if not self.product_api:
            print("  ⏭️ Skipping (Product API not available)")
            return False
        
        try:
            # Search for products with a common term
            search_terms = ["치킨", "닭", "만원"]
            
            for term in search_terms:
                print(f"  🔍 Searching for '{term}'...")
                results = await self.product_api.search_products(term, limit=3)
                
                if results:
                    print(f"    ✅ Found {len(results)} products")
                    for product in results[:2]:  # Show first 2
                        name = product.get('product_name', 'N/A')
                        print(f"      - {name}")
                else:
                    print(f"    ℹ️ No products found for '{term}'")
                
                break  # Only test first term to avoid rate limits
            
            return True
            
        except Exception as e:
            print(f"  ❌ Product search test failed: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            await self.client.close()
    
    async def run_all_tests(self):
        """Run all tests in sequence"""
        print("🧪 Starting API Connection Tests\n")
        
        try:
            # Configuration check
            self.print_config()
            
            # Dependency check
            if not self.check_dependencies():
                return False
            
            # Run tests
            tests = [
                ("Token Manager", self.test_token_manager()),
                ("Auth Manager", self.test_auth_manager()),
                ("API Client", self.test_api_client()),
                ("Product API", self.test_product_api()),
                ("Product Search", self.test_product_search())
            ]
            
            passed_tests = 0
            total_tests = len(tests)
            
            for test_name, test_coro in tests:
                try:
                    result = await test_coro
                    if result:
                        passed_tests += 1
                except Exception as e:
                    print(f"  ❌ {test_name} failed with error: {e}")
            
            # Summary
            print("\n" + "=" * 50)
            print(f"📊 Test Results: {passed_tests}/{total_tests} tests passed")
            
            if passed_tests == total_tests:
                print("🎉 All tests passed! API is fully functional.")
                return True
            elif passed_tests >= total_tests - 2:
                print("✅ Core functionality working. Some optional features may need attention.")
                return True
            else:
                print("⚠️ Some critical issues found. Please check the errors above.")
                return False
                
        finally:
            await self.cleanup()

def main():
    """Main function"""
    # Check if .env file exists
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ .env file not found!")
        print("Please create .env file with your Cafe24 API credentials.")
        print("See .env.example for reference.")
        return 1
    
    # Run tests
    tester = APITester()
    result = asyncio.run(tester.run_all_tests())
    
    return 0 if result else 1

if __name__ == "__main__":
    sys.exit(main())