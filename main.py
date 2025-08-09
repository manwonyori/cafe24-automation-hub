"""
Main entry point for Cafe24 Automation Hub
Simplified for Render deployment
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os
import sys

# Add src to path
sys.path.insert(0, 'src')

# Import the actual app
try:
    from web.app import app
    application = app
except ImportError:
    # Fallback simple app if import fails
    app = FastAPI(title="Cafe24 Automation Hub")
    
    @app.get("/")
    async def root():
        return {
            "message": "Cafe24 Automation Hub",
            "status": "running",
            "version": "2.0.0",
            "endpoints": {
                "health": "/health",
                "login": "/auth/login",
                "api": "/api"
            }
        }
    
    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    @app.get("/api")
    async def api_info():
        return {
            "message": "Cafe24 API",
            "version": "2.0.0"
        }
    
    application = app

# Export for Render
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(application, host="0.0.0.0", port=port)