from typing import Dict, List, Optional
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["WebSockets"])


class ConnectionManager:
    def __init__(self):
        # Map of project_id -> list of active WebSocket connections
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, project_id: int, websocket: WebSocket):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)

    def disconnect(self, project_id: int, websocket: WebSocket):
        if project_id in self.active_connections:
            if websocket in self.active_connections[project_id]:
                self.active_connections[project_id].remove(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]

    async def broadcast_progress(self, project_id: int, stage: str, percent: float, message: str, extra: Optional[dict] = None):
        if project_id in self.active_connections:
            payload = {
                "project_id": project_id,
                "stage": stage,
                "percent": round(percent * 100.0, 1) if percent <= 1.0 else round(percent, 1),
                "message": message,
                "extra": extra or {}
            }
            raw = json.dumps(payload)
            dead_connections = []
            for connection in self.active_connections[project_id]:
                try:
                    await connection.send_text(raw)
                except Exception:
                    dead_connections.append(connection)
            for dead in dead_connections:
                self.disconnect(project_id, dead)


ws_manager = ConnectionManager()


@router.websocket("/ws/projects/{project_id}")
async def websocket_project_progress(websocket: WebSocket, project_id: int):
    """Streams live optimization engine analysis and simulated machining progress."""
    await ws_manager.connect(project_id, websocket)
    try:
        while True:
            # Keep connection open; receive client heartbeat/messages if any
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        ws_manager.disconnect(project_id, websocket)
    except Exception:
        ws_manager.disconnect(project_id, websocket)
