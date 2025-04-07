from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List, Dict
import re

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, username: str):
        self.active_connections[username] = websocket

    def disconnect(self, username: str):
        self.active_connections.pop(username, None)

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)

    async def send_user_list(self):
        user_list = list(self.active_connections.keys())
        for connection in self.active_connections.values():
            await connection.send_text(f"USERS:{','.join(user_list)}")

    async def send_private_message(self, recipient: str, message: str):
        if recipient in self.active_connections:
            await self.active_connections[recipient].send_text(message)

def formating_bold(text: str):
    print(re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text))
    return re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    

manager = ConnectionManager()
messages: List[str] = []

@app.websocket("/ws/chat")
async def chat(websocket: WebSocket):
    try:
        await websocket.accept()

        username = await websocket.receive_text()
        await manager.connect(websocket, username)
        await manager.broadcast(f"{username} joined the chat")
        await manager.send_user_list()

        for message in messages:
            await websocket.send_text(message)

        while True:
            message = await websocket.receive_text()
            if message.startswith("@"):
                parts = message.split(" ", 1)
                if len(parts)>1:
                    recipient = parts[0][1:]
                    private_msg = formating_bold(parts[1])
                    formatted_message = f"[Private] {username} to {recipient}: {private_msg}"
                    await manager.send_private_message(recipient, formatted_message)
                    await websocket.send_text(f"[Private] You to {recipient}: {private_msg}")
            else:
                formatted_message = f"{username}: {formating_bold(message)}"
                messages.append(formatted_message)
                await manager.broadcast(formatted_message)

    except WebSocketDisconnect:
        if username:
            manager.disconnect(username)
            await manager.broadcast(f"{username} left the chat")
            await manager.send_user_list()
        await websocket.close()