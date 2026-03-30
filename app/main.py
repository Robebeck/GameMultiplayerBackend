from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json
import sqlite3
import os
from pydantic import BaseModel
from typing import List

class LoginRequest(BaseModel):
    username: str
    password: str

class Player(BaseModel):
    id: int
    username: str
    login_state: bool

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'underleaf.db')

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
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

# get route for all players as a list when no specific id provided in url
@app.get("/players", response_model=List[Player])
async def get_all_players():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, login_state FROM players ORDER BY username ASC')
    rows = cursor.fetchall()
    conn.close()
    
    return [Player(id=row[0], username=row[1], login_state=bool(row[2])) for row in rows]

# get route for player when player id provided in url
@app.get("/players/{player_id}", response_model=Player)
async def get_player(player_id: int):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, login_state FROM players WHERE id = ?', (player_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        raise HTTPException(status_code=404, detail="Player not found")
        
    return Player(id=row[0], username=row[1], login_state=bool(row[2]))

@app.get("/ui")
async def ui_prototype():
    return FileResponse("static/index.html")

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
