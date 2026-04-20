from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json
import sqlite3
import os
from pydantic import BaseModel
from typing import List, Dict, Optional

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
('BobTheBuilder', '1234', FALSE),
('Alice', '1234', FALSE);

CREATE TABLE IF NOT EXISTS friend_relationships (
    requester_id INTEGER,
    receiver_id INTEGER,
    status TEXT CHECK(status IN ('pending', 'accepted', 'blocked')) DEFAULT 'pending',
    PRIMARY KEY (requester_id, receiver_id),
    FOREIGN KEY(requester_id) REFERENCES players(id),
    FOREIGN KEY(receiver_id) REFERENCES players(id)
);
''')

conn.commit()
conn.close()

app.mount("/static", StaticFiles(directory="static"), name="static")

# State
active_connections: Dict[int, WebSocket] = {}

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

async def notify_friends(player_id: int, message: dict):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT requester_id, receiver_id 
        FROM friend_relationships 
        WHERE (requester_id = ? OR receiver_id = ?) AND status = 'accepted'
    ''', (player_id, player_id))
    rows = cursor.fetchall()
    conn.close()
    
    for row in rows:
        friend_id = row['requester_id'] if row['receiver_id'] == player_id else row['receiver_id']
        if friend_id in active_connections:
            friend_ws = active_connections[friend_id]
            try:
                await friend_ws.send_text(json.dumps(message))
            except Exception:
                pass

@app.get("/")
async def root():
    return {"status": "ok", "service": "underleaf-backend"}

@app.get("/players", response_model=List[Player])
async def get_all_players():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, login_state FROM players ORDER BY username ASC')
    rows = cursor.fetchall()
    conn.close()
    
    return [Player(id=row['id'], username=row['username'], login_state=bool(row['login_state'])) for row in rows]

@app.get("/players/{player_id}", response_model=Player)
async def get_player(player_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, login_state FROM players WHERE id = ?', (player_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        raise HTTPException(status_code=404, detail="Player not found")
        
    return Player(id=row['id'], username=row['username'], login_state=bool(row['login_state']))

@app.get("/ui")
async def ui_prototype():
    return FileResponse("static/index.html")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    current_player_id = None
    try:
        while True:
            data_str = await websocket.receive_text()
            try:
                data = json.loads(data_str)
                request_id = data.get("request_id", "unknown")
                action_type = data.get("type", "UNKNOWN")
                
                # Handling IDENTIFY separately with credentials
                if action_type == "REGISTER":
                    username = data.get("params", {}).get("username")
                    password = data.get("params", {}).get("password")
                    
                    if username and password:
                        conn = get_db()
                        cursor = conn.cursor()
                        cursor.execute('SELECT id FROM players WHERE username = ?', (username,))
                        row = cursor.fetchone()
                        
                        if row:
                            conn.close()
                            await websocket.send_text(json.dumps({
                                "request_id": request_id,
                                "type": "ERROR",
                                "status": "error",
                                "message": "Username already exists."
                            }))
                        else:
                            cursor.execute('INSERT INTO players (username, password, login_state) VALUES (?, ?, 0)', (username, password))
                            conn.commit()
                            conn.close()
                            
                            await websocket.send_text(json.dumps({
                                "request_id": request_id,
                                "type": "REGISTER_SUCCESS",
                                "status": "success",
                                "message": f"Successfully registered user {username}"
                            }))
                    else:
                        await websocket.send_text(json.dumps({
                            "request_id": request_id,
                            "type": "ERROR",
                            "status": "error",
                            "message": "Username and password required for registration."
                        }))
                    continue
                    
                if action_type == "IDENTIFY":
                    username = data.get("params", {}).get("username")
                    password = data.get("params", {}).get("password")
                    
                    if username and password:
                        conn = get_db()
                        cursor = conn.cursor()
                        cursor.execute('SELECT id FROM players WHERE username = ? AND password = ?', (username, password))
                        row = cursor.fetchone()
                        
                        if row:
                            current_player_id = int(row['id'])
                            active_connections[current_player_id] = websocket
                            
                            # Update DB login state
                            cursor.execute('UPDATE players SET login_state = 1 WHERE id = ?', (current_player_id,))
                            conn.commit()
                            conn.close()
                            
                            await websocket.send_text(json.dumps({
                                "request_id": request_id,
                                "type": "IDENTIFY_SUCCESS",
                                "status": "success",
                                "message": f"Successfully authenticated as {username}"
                            }))
                            await notify_friends(current_player_id, {
                                "type": "FRIEND_STATUS_UPDATE",
                                "data": {
                                    "player_id": current_player_id,
                                    "login_state": True
                                }
                            })
                        else:
                            conn.close()
                            await websocket.send_text(json.dumps({
                                "request_id": request_id,
                                "type": "ERROR",
                                "status": "error",
                                "message": "Invalid username or password."
                            }))
                    else:
                        await websocket.send_text(json.dumps({
                            "request_id": request_id,
                            "type": "ERROR",
                            "status": "error",
                            "message": "Username and password required."
                        }))
                    continue
                
                if current_player_id is None:
                    await websocket.send_text(json.dumps({
                        "request_id": request_id,
                        "type": "ERROR",
                        "status": "error",
                        "message": "Unauthorized. Please IDENTIFY first."
                    }))
                    continue
                
                if action_type == "MOVE":
                    response = {
                        "request_id": request_id,
                        "type": "MOVE_RESULT",
                        "status": "success",
                        "message": "Move action processed",
                        "data": {"new_position": {"x": 10, "y": 0, "z": 5}}
                    }
                    await websocket.send_text(json.dumps(response))
                elif action_type == "CARD":
                    response = {
                        "request_id": request_id,
                        "type": "CARD_RESULT",
                        "status": "success",
                        "message": "Card played successfully",
                        "data": {"card_id": data.get("params", {}).get("card_id"), "damage_dealt": 15}
                    }
                    await websocket.send_text(json.dumps(response))
                elif action_type == "FRIEND_REQUEST":
                    target_username = data.get("params", {}).get("target_username")
                    
                    conn = get_db()
                    cur = conn.cursor()
                    
                    cur.execute('SELECT id FROM players WHERE username = ?', (target_username,))
                    row = cur.fetchone()
                    
                    if not row:
                        await websocket.send_text(json.dumps({"request_id": request_id, "type": "ERROR", "status": "error", "message": "Target player does not exist."}))
                        conn.close()
                        continue
                        
                    target_id = row['id']
                    
                    if target_id == current_player_id:
                        await websocket.send_text(json.dumps({"request_id": request_id, "type": "ERROR", "status": "error", "message": "Cannot add yourself."}))
                        conn.close()
                        continue
                        
                    cur.execute('''SELECT status FROM friend_relationships 
                                   WHERE (requester_id = ? AND receiver_id = ?) 
                                   OR (requester_id = ? AND receiver_id = ?)''', 
                                   (current_player_id, target_id, target_id, current_player_id))
                    existing = cur.fetchone()
                    if existing:
                        await websocket.send_text(json.dumps({"request_id": request_id, "type": "ERROR", "status": "error", "message": f"Relationship already exists: {existing['status']}"}))
                    else:
                        cur.execute('''INSERT INTO friend_relationships (requester_id, receiver_id, status) VALUES (?, ?, 'pending')''', (current_player_id, target_id))
                        conn.commit()
                        await websocket.send_text(json.dumps({"request_id": request_id, "type": "FRIEND_REQUEST_SENT", "status": "success"}))
                        if target_id in active_connections:
                            await active_connections[target_id].send_text(json.dumps({
                                "type": "INCOMING_FRIEND_REQUEST",
                                "data": {"requester_id": current_player_id}
                            }))
                    conn.close()
                
                elif action_type == "FRIEND_ACCEPT":
                    requester_id = data.get("params", {}).get("requester_id")
                    conn = get_db()
                    cur = conn.cursor()
                    cur.execute('''UPDATE friend_relationships SET status = 'accepted' WHERE requester_id = ? AND receiver_id = ? AND status = 'pending' ''', (requester_id, current_player_id))
                    if cur.rowcount > 0:
                        conn.commit()
                        await websocket.send_text(json.dumps({"request_id": request_id, "type": "FRIEND_ACCEPTED", "status": "success"}))
                        if requester_id in active_connections:
                            await active_connections[requester_id].send_text(json.dumps({
                                "type": "FRIEND_REQUEST_ACCEPTED",
                                "data": {"receiver_id": current_player_id}
                            }))
                    else:
                        await websocket.send_text(json.dumps({"request_id": request_id, "type": "ERROR", "status": "error", "message": "No pending request."}))
                    conn.close()
                    
                elif action_type == "FRIEND_REJECT" or action_type == "FRIEND_BLOCK":
                    target_id = data.get("params", {}).get("target_id")
                    # If reject, target_id is the requester of the pending request we are deleting.
                    # If block, target_id is who we want to block (could be requester or a friend)
                    new_status = 'blocked' if action_type == "FRIEND_BLOCK" else 'rejected'
                    
                    conn = get_db()
                    cur = conn.cursor()
                    if new_status == 'rejected':
                        cur.execute('''DELETE FROM friend_relationships WHERE requester_id = ? AND receiver_id = ? AND status = 'pending' ''', (target_id, current_player_id))
                    else:
                        cur.execute('''SELECT 1 FROM friend_relationships WHERE (requester_id = ? AND receiver_id = ?) OR (requester_id = ? AND receiver_id = ?)''', (target_id, current_player_id, current_player_id, target_id))
                        if cur.fetchone():
                            cur.execute('''UPDATE friend_relationships SET status = 'blocked', requester_id = ?, receiver_id = ? WHERE (requester_id = ? AND receiver_id = ?) OR (requester_id = ? AND receiver_id = ?)''', 
                                        (current_player_id, target_id, target_id, current_player_id, current_player_id, target_id))
                        else:
                            cur.execute('''INSERT INTO friend_relationships (requester_id, receiver_id, status) VALUES (?, ?, 'blocked')''', (current_player_id, target_id))

                    conn.commit()
                    await websocket.send_text(json.dumps({"request_id": request_id, "type": "FRIEND_UPDATED", "status": "success", "message": f"User {new_status}"}))
                    conn.close()

                elif action_type == "GET_FRIENDS":
                    conn = get_db()
                    cur = conn.cursor()
                    cur.execute('''
                        SELECT fr.requester_id, fr.receiver_id, fr.status,
                               p1.username as req_username, p2.username as recv_username,
                               p1.login_state as req_online, p2.login_state as recv_online
                        FROM friend_relationships fr
                        JOIN players p1 ON fr.requester_id = p1.id
                        JOIN players p2 ON fr.receiver_id = p2.id
                        WHERE fr.requester_id = ? OR fr.receiver_id = ?
                    ''', (current_player_id, current_player_id))
                    rows = cur.fetchall()
                    conn.close()
                    
                    friends_list = []
                    for row in rows:
                        other_id = row['receiver_id'] if row['requester_id'] == current_player_id else row['requester_id']
                        other_username = row['recv_username'] if row['requester_id'] == current_player_id else row['req_username']
                        other_online = bool(row['recv_online']) if row['requester_id'] == current_player_id else bool(row['req_online'])
                        is_requester = row['requester_id'] == current_player_id
                        status = row['status']

                        # If they blocked us, we do not see them as blocked explicitly, or do we?
                        # Usually, if we are the receiver of a block, we just don't see them.
                        if status == 'blocked' and not is_requester:
                             continue

                        friends_list.append({
                            "id": other_id,
                            "username": other_username,
                            "login_state": other_online,
                            "status": status,
                            "is_requester": is_requester
                        })
                        
                    await websocket.send_text(json.dumps({
                        "request_id": request_id,
                        "type": "FRIENDS_LIST",
                        "status": "success",
                        "data": friends_list
                    }))
                    
                elif action_type == "LOBBY_INVITE":
                    friend_id = data.get("params", {}).get("friend_id")
                    if friend_id in active_connections:
                        await active_connections[friend_id].send_text(json.dumps({
                            "type": "LOBBY_INVITE_RECEIVED",
                            "data": {
                                "from_id": current_player_id
                            }
                        }))
                        await websocket.send_text(json.dumps({"request_id": request_id, "type": "LOBBY_INVITE_SENT", "status": "success"}))
                    else:
                        await websocket.send_text(json.dumps({"request_id": request_id, "type": "ERROR", "status": "error", "message": "Friend is not online."}))

                else:
                    await websocket.send_text(json.dumps({"request_id": request_id, "type": "ERROR", "status": "error", "message": f"Unknown action type: {action_type}"}))
                
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "ERROR", "error": "Invalid JSON format"}))
                
    except WebSocketDisconnect:
        if current_player_id is not None:
            if current_player_id in active_connections:
                del active_connections[current_player_id]
            conn = get_db()
            conn.execute('UPDATE players SET login_state = 0 WHERE id = ?', (current_player_id,))
            conn.commit()
            conn.close()
            await notify_friends(current_player_id, {
                "type": "FRIEND_STATUS_UPDATE",
                "data": {
                    "player_id": current_player_id,
                    "login_state": False
                }
            })
