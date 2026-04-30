from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import ws_router, session_router, export_router, upload_router
from app.database import create_tables
import asyncio

app = FastAPI(title="Debate Analyzer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"], # Added * for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_router.router)
app.include_router(session_router.router, prefix="/api")
app.include_router(export_router.router, prefix="/api")
app.include_router(upload_router.router, prefix="/api")

@app.on_event("startup")
async def startup():
    await create_tables()

@app.get("/health")
async def health():
    return {"status": "ok"}
