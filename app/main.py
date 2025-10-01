from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_database
from app.services.scheduler_service import start_scheduler, stop_scheduler
from app.api.routes import ai_processor, auth, chatgpt_integration, onboarding, websocket_notifications, notifications, tasks, upload, reminders

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
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(chatgpt_integration.router, prefix="/api/v1/chatgpt", tags=["ChatGPT Integration"])
    app.include_router(onboarding.router, prefix="/api/v1/onboarding", tags=["Onboarding"])
    app.include_router(websocket_notifications.router, prefix="/api/v1", tags=["WebSocket Notifications"])
    app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])
    app.include_router(tasks.router, prefix="/api/v1", tags=["Tasks"])
    app.include_router(upload.router, prefix="/api/v1/upload", tags=["File Upload"])
    app.include_router(reminders.router, prefix="/api/v1", tags=["Reminders"])
    
    @app.on_event("startup")
    async def startup_event():
        init_database()
        # Start the reminder scheduler
        await start_scheduler()
    
    @app.on_event("shutdown")
    async def shutdown_event():
        # Stop the reminder scheduler
        await stop_scheduler()
    
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