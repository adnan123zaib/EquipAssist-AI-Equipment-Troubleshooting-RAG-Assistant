from contextlib import asynccontextmanager
from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.routes import router
from app.api.auth_routes import router as auth_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import Base,engine
from app.models import *

@asynccontextmanager
async def lifespan(app:FastAPI):
    configure_logging(); s=get_settings(); s.ensure_directories(); Base.metadata.create_all(engine); yield

app=FastAPI(title="EquipAssist AI API",version="1.0.0",lifespan=lifespan)
s=get_settings(); app.add_middleware(CORSMiddleware,allow_origins=[s.frontend_url],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(router,prefix="/api/v1")
app.include_router(auth_router,prefix="/api/v1",tags=["authentication"])

@app.exception_handler(Exception)
async def unhandled(_:Request,exc:Exception): return JSONResponse(status_code=500,content={"error":"internal_error","message":str(exc) if s.app_env=="development" else "Unexpected server error"})
