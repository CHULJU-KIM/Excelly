# app/main.py
# Main FastAPI application entry point

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os

from app.core.config import settings
from app.core.exceptions import ExcellyException, handle_excelly_exception
from app.core.database import init_db
from app.api import chat, files

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_TITLE,
    description="AI 엑셀 해결사 '엑셀리' - OpenAI와 Gemini를 활용한 지능형 엑셀 도우미",
    version="6.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Include API routers
app.include_router(chat.router)
app.include_router(files.router)

# Global exception handler
@app.exception_handler(ExcellyException)
async def excelly_exception_handler(request: Request, exc: ExcellyException):
    return handle_excelly_exception(exc)

@app.get("/", response_class=HTMLResponse)
async def serve_home_page(request: Request):
    """Serve the main application page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Validate configuration
        settings.validate()
        
        return {
            "status": "healthy",
            "version": "6.0.0",
            "config_valid": True
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.get("/api/status")
async def get_full_status():
    """Get comprehensive service status"""
    try:
        from app.services.ai_service import ai_service
        from app.services.session_service import session_service
        
        ai_status = ai_service.get_service_status()
        session_stats = session_service.get_session_stats()
        
        return {
            "status": "healthy",
            "version": "6.0.0",
            "ai_service": ai_status,
            "session_service": session_stats,
            "config": {
                "debug": settings.DEBUG,
                "max_file_size_mb": settings.MAX_FILE_SIZE // (1024*1024),
                "session_timeout": settings.SESSION_TIMEOUT,
                "ai_timeout": settings.AI_REQUEST_TIMEOUT
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    
    # Validate configuration on startup
    try:
        settings.validate()
        print("✅ Configuration validated successfully")
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        exit(1)
    
    # Initialize database
    try:
        init_db()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        exit(1)
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning"
    )
