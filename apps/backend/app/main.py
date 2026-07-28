import asyncio
import json
from typing import Dict, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import os
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import engine, Base
from app.api.api import api_router

# Import models to ensure they are registered with Base metadata before creation
from app.models.job import Job
from app.models.style_reference import StyleReference
from app.models.rewrite_pair import RewritePair
from app.models.platform_metadata import PlatformMetadata
from app.models.blog_post import BlogPost

# Create database tables (SQLite/PostgreSQL fallback)
Base.metadata.create_all(bind=engine)

# Static directory setup for serving processed images
UPLOAD_DIR = "/tmp/creator_arc_uploads" if os.name != 'nt' else "C:/temp/creator_arc_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS configuration
origins = [
    "http://localhost:3000",  # Next.js local development
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Connection Manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)


manager = ConnectionManager()


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(client_id, websocket)
    try:
        # Keep connection open and listen for user messages if any
        while True:
            data = await websocket.receive_text()
            # Echo or process if needed, usually clients only listen
            await manager.send_personal_message({"status": "received", "data": data}, client_id)
    except WebSocketDisconnect:
        manager.disconnect(client_id)


# Include API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Serve upload assets statically
app.mount("/static", StaticFiles(directory=UPLOAD_DIR), name="static")


@app.get("/")
def read_root():
    return {"message": f"Welcome to the {settings.PROJECT_NAME} API!"}
