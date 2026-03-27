from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json
import sqlite3
from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

app = FastAPI()
conn = sqlite3.connect('underleaf.db', check_same_thread=False)
cursor = conn.cursor()

cursor.executescript('''
CREATE TABLE IF NOT EXISTS players(
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT NOT NULL,
password TEXT NOT NULL,
login_state BOOLEAN DEFAULT FALSE
);

INSERT OR IGNORE INTO players (username, password, login_state)
VALUES
('L33TCARDGAMER', '1234', FALSE),
('BobTheBuilder', '1234', FALSE);

CREATE TABLE IF NOT EXISTS friends(
player_id INTEGER,
friend_id INTEGER,
PRIMARY KEY (player_id, friend_id)
);

INSERT OR IGNORE INTO friends VALUES (1,2);
INSERT OR IGNORE INTO friends VALUES (2,1);

''')

conn.commit()
conn.close()


app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return {"status": "ok", "service": "underleaf-backend"}

@app.get("/ui")
async def ui_prototype():
    return FileResponse("static/index.html")

@app.post("/login")
async def login(request: LoginRequest):
    conn = sqlite3.connect('underleaf.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, password FROM players WHERE username = ?', (request.username,))
    row = cursor.fetchone()
    
    if row is None:
        conn.close()
        return {"status": "error", "message": "Invalid username or password"}
        
    player_id, db_password = row
    
    if db_password == request.password:
        cursor.execute('UPDATE players SET login_state = TRUE WHERE id = ?', (player_id,))
        conn.commit()
        conn.close()
        return {
            "status": "success", 
            "message": f"Welcome {request.username}",
            "data": {"player_id": player_id, "username": request.username}
        }
    else:
        conn.close()
        return {"status": "error", "message": "Invalid username or password"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Receive text from the WebSocket
            data_str = await websocket.receive_text()
            try:
                # Parse as JSON to expect the payload structure
                data = json.loads(data_str)
                
                # Check for correlation ID
                request_id = data.get("request_id", "unknown")
                action_type = data.get("type", "UNKNOWN")
                
                # Sample logic: simulate processing a MOVE or CARD action
                if action_type == "MOVE":
                    response = {
                        "request_id": request_id,
                        "status": "success",
                        "message": "Move action processed",
                        "data": {
                            "new_position": {"x": 10, "y": 0, "z": 5}
                        }
                    }
                elif action_type == "CARD":
                    response = {
                        "request_id": request_id,
                        "status": "success",
                        "message": "Card played successfully",
                        "data": {
                            "card_id": data.get("params", {}).get("card_id"),
                            "damage_dealt": 15
                        }
                    }
                else:
                    response = {
                        "request_id": request_id,
                        "status": "error",
                        "message": f"Unknown action type: {action_type}"
                    }
                
                # Send the response back
                await websocket.send_text(json.dumps(response))
                
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON format"}))
                
    except WebSocketDisconnect:
        print("Client disconnected")
