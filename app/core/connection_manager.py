from typing import Any
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    def number_of_connections(self):
        return len(self.active_connections)

    async def send_personal_message(self, json: Any, websocket: WebSocket):
        await websocket.send_json(json)

    async def broadcast(self, json: Any):
        for connection in self.active_connections:
            await connection.send_json(json)