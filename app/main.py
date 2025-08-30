from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_database
from app.api.routes import ai_processor

def create_application() -> FastAPI:
    app = FastAPI(
        title="AI Work Assistant API",
        description="Professional AI Assistant for Task Management",
        version="1.0.0",
        debug=settings.DEBUG
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(ai_processor.router, prefix="/api/v1", tags=["AI Processor"])
    
    @app.on_event("startup")
    async def startup_event():
        init_database()
    
    return app

app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )