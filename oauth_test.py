#!/usr/bin/env python3
"""
OAuth Authentication Test for Cafe24
Interactive test for real API authentication
"""

import asyncio
import sys
import webbrowser
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.config.settings import settings
from src.core.auth_manager import AuthManager
from src.api.client import Cafe24Client
from src.api.products import ProductAPI

class OAuthTester:
    """Interactive OAuth testing"""
    
    def __init__(self):
        self.auth_manager = AuthManager()
        
    async def run_oauth_flow(self):
        """Run complete OAuth authentication flow"""
        print("=" * 60)
        print("Cafe24 OAuth Authentication Test")
        print("=" * 60)
        
        print(f"\n[CONFIG] Current Settings:")
        print(f"Mall ID: {settings.cafe24_mall_id}")
        print(f"Client ID: {settings.cafe24_client_id[:10]}...")
        print(f"Redirect URI: {settings.redirect_uri}")
        
        # Check if already authenticated
        if self.auth_manager.is_authenticated():
            print("\n[STATUS] Already authenticated!")
            token_info = self.auth_manager.get_token_info()
            
            access_info = token_info.get('access_token')
            if access_info and not access_info.get('is_expired'):
                print(f"Access token expires in: {access_info.get('expires_in_seconds')}s")
                
                # Ask if user wants to test with existing token
                choice = input("\nUse existing token? (y/n): ").strip().lower()
                if choice == 'y':
                    return await self.test_api_calls()
                else:
                    # Clear tokens and start fresh
                    self.auth_manager.logout()
                    print("Cleared existing tokens")
        
        # Start OAuth flow
        print("\n[OAUTH] Starting OAuth Authentication Flow")
        print("-" * 40)
        
        # Generate authorization URL
        auth_url = self.auth_manager.get_authorization_url(state="test123")
        
        print(f"\n[STEP 1] Authorization URL Generated:")
        print(f"{auth_url}")
        
        # Ask if user wants to open browser automatically
        open_browser = input("\nOpen this URL in browser automatically? (y/n): ").strip().lower()
        
        if open_browser == 'y':
            try:
                webbrowser.open(auth_url)
                print("Browser opened with authorization URL")
            except Exception as e:
                print(f"Could not open browser: {e}")
                print("Please copy and paste the URL manually")
        
        print(f"\n[STEP 2] Instructions:")
        print("1. Complete the authorization in your browser")
        print("2. You will be redirected to: " + settings.redirect_uri)
        print("3. Copy the 'code' parameter from the URL")
        print("4. Paste it below")
        
        # Get authorization code from user
        print(f"\n[INPUT] Waiting for authorization code...")
        while True:
            try:
                auth_code = input("Enter authorization code (or 'q' to quit): ").strip()
                
                if auth_code.lower() == 'q':
                    print("Authentication cancelled")
                    return False
                
                if not auth_code:
                    print("Please enter a valid authorization code")
                    continue
                
                break
                
            except KeyboardInterrupt:
                print("\nAuthentication cancelled")
                return False
        
        # Exchange code for token
        print(f"\n[STEP 3] Exchanging code for access token...")
        try:
            token_data = await self.auth_manager.exchange_code_for_token(auth_code)
            
            print("[SUCCESS] Token exchange successful!")
            print(f"Access token received: {token_data.get('access_token', '')[:20]}...")
            print(f"Token type: {token_data.get('token_type', 'N/A')}")
            print(f"Expires in: {token_data.get('expires_in', 'N/A')} seconds")
            
            if 'refresh_token' in token_data:
                print("Refresh token also received")
            
            return await self.test_api_calls()
            
        except Exception as e:
            print(f"[ERROR] Token exchange failed: {e}")
            return False
    
    async def test_api_calls(self):
        """Test actual API calls with authenticated token"""
        print(f"\n[API TEST] Testing authenticated API calls")
        print("-" * 40)
        
        try:
            # Create API client
            client = Cafe24Client(self.auth_manager)
            product_api = ProductAPI(client)
            
            # Test 1: API Info
            print("[TEST 1] Getting API info...")
            api_info = await client.get_api_info()
            
            if api_info.get('connected'):
                print(f"[OK] API connected successfully")
                print(f"Mall ID: {api_info.get('mall_id')}")
                print(f"API Version: {api_info.get('api_version')}")
            else:
                print(f"[ERROR] API connection failed: {api_info.get('error')}")
                return False
            
            # Test 2: Get Products
            print(f"\n[TEST 2] Fetching products...")
            result = await product_api.get_products(limit=5)
            
            products = result.get('products', [])
            print(f"[OK] Retrieved {len(products)} products")
            
            if products:
                print(f"\n[SAMPLE] First product:")
                first = products[0]
                print(f"  Product No: {first.get('product_no')}")
                print(f"  Name: {first.get('product_name', 'N/A')}")
                print(f"  Price: {first.get('price', 'N/A')}")
                print(f"  Display: {first.get('display', 'N/A')}")
                
                # Test 3: Get Product Detail
                product_no = first.get('product_no')
                if product_no:
                    print(f"\n[TEST 3] Getting product detail for #{product_no}...")
                    detail = await product_api.get_product(product_no)
                    
                    if detail:
                        print(f"[OK] Product detail retrieved")
                        print(f"  Stock: {detail.get('stock_quantity', 'N/A')}")
                        print(f"  Category: {detail.get('category_name', 'N/A')}")
                    else:
                        print(f"[WARNING] Product detail not found")
            
            # Test 4: Search Products  
            print(f"\n[TEST 4] Searching products...")
            search_results = await product_api.search_products("치킨", limit=3)
            
            if search_results:
                print(f"[OK] Found {len(search_results)} products matching '치킨'")
                for i, product in enumerate(search_results[:2], 1):
                    name = product.get('product_name', 'N/A')
                    print(f"  {i}. {name}")
            else:
                print(f"[INFO] No products found matching '치킨'")
            
            # Cleanup
            await client.close()
            
            print(f"\n[SUCCESS] All API tests completed successfully!")
            print(f"Your Cafe24 API integration is working perfectly.")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] API test failed: {e}")
            return False
    
    def show_next_steps(self):
        """Show next steps after successful authentication"""
        print(f"\n" + "=" * 60)
        print("AUTHENTICATION SUCCESSFUL! 🎉")
        print("=" * 60)
        
        print(f"\n[NEXT STEPS]")
        print("1. ✅ OAuth authentication working")
        print("2. ✅ API calls successful") 
        print("3. 🔄 Ready to build web interface")
        print("4. 🚀 Ready for deployment")
        
        print(f"\n[TOKEN STATUS]")
        token_info = self.auth_manager.get_token_info()
        if token_info.get('access_token'):
            expires_in = token_info['access_token'].get('expires_in_seconds', 0)
            print(f"Access token: Valid for {expires_in} seconds")
        
        if token_info.get('refresh_token'):
            refresh_expires = token_info['refresh_token'].get('expires_in_seconds', 0)
            print(f"Refresh token: Valid for {refresh_expires} seconds")

async def main():
    """Main function"""
    tester = OAuthTester()
    
    try:
        success = await tester.run_oauth_flow()
        
        if success:
            tester.show_next_steps()
            return 0
        else:
            print(f"\n[FAILED] Authentication test failed")
            print("Please check your Cafe24 API credentials and try again")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n[CANCELLED] Test cancelled by user")
        return 1
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    print("Starting OAuth authentication test...")
    sys.exit(asyncio.run(main()))