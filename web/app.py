"""
FastAPI Web Application for Cafe24 Automation Hub
Provides web interface and OAuth callback handling
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn

from src.config.settings import settings
from src.core.auth_manager import AuthManager
from src.api.client import Cafe24Client
from src.api.products import ProductAPI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Cafe24 Automation Hub",
    description="Secure automation system for Cafe24 e-commerce platform",
    version="2.0.0"
)

# Setup templates
import os
from pathlib import Path

# Get the absolute path to templates directory
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

# Check if templates directory exists
if not TEMPLATES_DIR.exists():
    # Try alternate path for production
    TEMPLATES_DIR = Path("/opt/render/project/src/web/templates")
    if not TEMPLATES_DIR.exists():
        logger.error(f"Templates directory not found. Tried: {BASE_DIR / 'templates'} and {TEMPLATES_DIR}")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Global instances
auth_manager = AuthManager()
cafe24_client = None
product_api = None

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    global cafe24_client, product_api
    
    logger.info("Starting Cafe24 Automation Hub...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Mall ID: {settings.cafe24_mall_id}")
    
    # Initialize clients if authenticated
    if auth_manager.is_authenticated():
        cafe24_client = Cafe24Client(auth_manager)
        product_api = ProductAPI(cafe24_client)
        logger.info("API clients initialized with existing authentication")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global cafe24_client
    
    if cafe24_client:
        await cafe24_client.close()
    
    logger.info("Cafe24 Automation Hub shut down")

# Dependency to get authenticated API client
async def get_authenticated_client():
    """Dependency to ensure user is authenticated"""
    if not auth_manager.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    global cafe24_client
    if not cafe24_client:
        cafe24_client = Cafe24Client(auth_manager)
    
    return cafe24_client

async def get_product_api():
    """Dependency to get Product API"""
    client = await get_authenticated_client()
    
    global product_api
    if not product_api:
        product_api = ProductAPI(client)
    
    return product_api

# Routes
@app.get("/")
async def home(request: Request):
    """Home page"""
    is_authenticated = auth_manager.is_authenticated()
    
    # For production, return JSON response to avoid template issues
    if settings.is_production or os.getenv('RENDER'):
        return {
            "message": "Cafe24 Automation Hub",
            "status": "running",
            "authenticated": is_authenticated,
            "mall_id": settings.cafe24_mall_id,
            "environment": settings.environment,
            "login_url": "/auth/login",
            "health_url": "/health",
            "api_docs": "/docs"
        }
    
    # For local development, use templates
    try:
        return templates.TemplateResponse("home.html", {
            "request": request,
            "is_authenticated": is_authenticated,
            "mall_id": settings.cafe24_mall_id,
            "environment": settings.environment
        })
    except Exception as e:
        logger.error(f"Template error: {e}")
        return {
            "message": "Cafe24 Automation Hub",
            "status": "running",
            "authenticated": is_authenticated,
            "mall_id": settings.cafe24_mall_id,
            "environment": settings.environment,
            "login_url": "/auth/login",
            "health_url": "/health"
        }

@app.get("/auth/login")
async def login():
    """Initiate OAuth login"""
    try:
        auth_url = auth_manager.get_authorization_url(state="webapp_auth")
        return RedirectResponse(url=auth_url)
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@app.get("/auth/callback")
async def auth_callback(
    request: Request, 
    code: Optional[str] = None, 
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None
):
    """Handle OAuth callback"""
    # Check for OAuth errors first
    if error:
        error_msg = f"{error}: {error_description}" if error_description else error
        return JSONResponse(status_code=400, content={
            "error": True,
            "message": error_msg
        })
    
    if not code:
        return JSONResponse(status_code=400, content={
            "error": True,
            "message": "Authorization code not provided"
        })
    
    try:
        # Exchange code for token
        token_data = await auth_manager.exchange_code_for_token(code)
        
        # Initialize API clients
        global cafe24_client, product_api
        cafe24_client = Cafe24Client(auth_manager)
        product_api = ProductAPI(cafe24_client)
        
        logger.info("OAuth authentication successful")
        
        # For production, return JSON or redirect
        if settings.is_production or os.getenv('RENDER'):
            return RedirectResponse(url="/")
        
        # For local development, use templates
        try:
            return templates.TemplateResponse("auth_success.html", {
                "request": request,
                "token_info": token_data
            })
        except:
            return RedirectResponse(url="/")
        
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        
        # For production, return JSON error
        if settings.is_production or os.getenv('RENDER'):
            return JSONResponse(status_code=400, content={
                "error": True,
                "message": f"Authentication failed: {str(e)}"
            })
        
        # For local development, use templates
        try:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": f"Authentication failed: {str(e)}"
            })
        except:
            return JSONResponse(status_code=400, content={
                "error": True,
                "message": f"Authentication failed: {str(e)}"
            })

@app.get("/auth/logout")
async def logout():
    """Logout and clear tokens"""
    global cafe24_client, product_api
    
    # Close API client
    if cafe24_client:
        await cafe24_client.close()
        cafe24_client = None
        product_api = None
    
    # Clear tokens
    auth_manager.logout()
    
    return RedirectResponse(url="/")

@app.get("/auth/status")
async def auth_status():
    """Get authentication status"""
    return {
        "authenticated": auth_manager.is_authenticated(),
        "token_info": auth_manager.get_token_info() if auth_manager.is_authenticated() else None
    }

# API Routes
@app.get("/api/products")
async def get_products(
    limit: int = 10,
    offset: int = 0,
    product_api: ProductAPI = Depends(get_product_api)
):
    """Get products via API"""
    try:
        result = await product_api.get_products(limit=min(limit, 100), offset=offset)
        return result
    except Exception as e:
        logger.error(f"Get products failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/products/{product_no}")
async def get_product(
    product_no: str,
    product_api: ProductAPI = Depends(get_product_api)
):
    """Get single product"""
    try:
        product = await product_api.get_product(product_no)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get product failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/products/{product_no}/price")
async def update_product_price(
    product_no: str,
    price_data: Dict[str, Any],
    product_api: ProductAPI = Depends(get_product_api)
):
    """Update product price"""
    try:
        new_price = price_data.get('price')
        if not new_price:
            raise HTTPException(status_code=400, detail="Price is required")
        
        success = await product_api.update_product_price(
            product_no, 
            new_price,
            price_data.get('retail_price'),
            price_data.get('supply_price')
        )
        
        if success:
            return {"success": True, "message": "Price updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Price update failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update price failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search")
async def search_products(
    q: str,
    limit: int = 20,
    product_api: ProductAPI = Depends(get_product_api)
):
    """Search products"""
    try:
        results = await product_api.search_products(q, limit=min(limit, 100))
        return {
            "query": q,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Dashboard Routes
@app.get("/dashboard")
async def dashboard(request: Request, client: Cafe24Client = Depends(get_authenticated_client)):
    """Main dashboard"""
    try:
        # Get basic API info
        api_info = await client.get_api_info()
        
        # For production, return JSON
        if settings.is_production or os.getenv('RENDER'):
            return {
                "api_info": api_info,
                "mall_id": settings.cafe24_mall_id,
                "authenticated": True
            }
        
        # For local development, use templates
        try:
            return templates.TemplateResponse("dashboard.html", {
                "request": request,
                "api_info": api_info,
                "mall_id": settings.cafe24_mall_id
            })
        except:
            return {
                "api_info": api_info,
                "mall_id": settings.cafe24_mall_id,
                "authenticated": True
            }
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        
        if settings.is_production or os.getenv('RENDER'):
            raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")
        
        try:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": f"Dashboard error: {str(e)}"
            })
        except:
            raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")

@app.get("/products")
async def products_page(request: Request):
    """Products management page"""
    # For production, return JSON
    if settings.is_production or os.getenv('RENDER'):
        return {
            "message": "Products API",
            "endpoints": {
                "list": "/api/products",
                "detail": "/api/products/{product_no}",
                "search": "/api/search?q={query}",
                "update_price": "/api/products/{product_no}/price"
            }
        }
    
    # For local development, use templates
    try:
        return templates.TemplateResponse("products.html", {
            "request": request
        })
    except:
        return {
            "message": "Products API",
            "endpoints": {
                "list": "/api/products",
                "detail": "/api/products/{product_no}",
                "search": "/api/search?q={query}",
                "update_price": "/api/products/{product_no}/price"
            }
        }

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "environment": settings.environment,
        "authenticated": auth_manager.is_authenticated()
    }

# API info endpoint for root when templates fail
@app.get("/api")
async def api_info():
    """API information endpoint"""
    return {
        "message": "Cafe24 Automation Hub API",
        "version": "2.0.0",
        "status": "running",
        "environment": settings.environment,
        "mall_id": settings.cafe24_mall_id,
        "authenticated": auth_manager.is_authenticated()
    }

# Run the app
def run_server():
    """Run the FastAPI server"""
    uvicorn.run(
        "web.app:app",
        host="0.0.0.0" if settings.is_production else "127.0.0.1",
        port=int(settings.redirect_uri.split(':')[-1].split('/')[0]) if settings.redirect_uri.startswith('http://localhost') else 8000,
        reload=settings.is_development,
        log_level=settings.log_level.lower()
    )

if __name__ == "__main__":
    run_server()