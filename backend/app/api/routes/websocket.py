from fastapi import APIRouter
import socketio
import json

router = APIRouter(tags=["WebSocket"])

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio)

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
    
async def broadcast_incident_update(incident_id: str, event_type: str, data: dict):
    await sio.emit(event_type, {
        "incident_id": incident_id,
        "data": data
    })


async def broadcast_report_update(report_id: str, event_type: str, data: dict):
    """Broadcast real-time verification and status updates for a specific report."""
    await sio.emit(event_type, {
        "report_id": report_id,
        "data": data
    })

