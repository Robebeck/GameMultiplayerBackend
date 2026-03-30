# Underleaf Backend Prototype

## Requirements
fastapi==0.111.0  
uvicorn==0.30.1  
websockets==12.0  

Install with:
pip install fastapi uvicorn websockets

---

## Run the Server
python -m uvicorn main:app --reload

---

## Endpoints

UI Prototype:
http://127.0.0.1:8000/ui

Get all players:
http://127.0.0.1:8000/players

Get a specific player:
http://127.0.0.1:8000/players/<player_id>

Example:
http://127.0.0.1:8000/players/1

---

## Data Access Layer

Player data is stored in a SQLite database (`underleaf.db`).

The data model is defined using a Pydantic class (`Player`), which ensures structured and consistent data.

The FastAPI backend exposes this data through REST API endpoints:
- `/players` returns all player records
- `/players/{player_id}` returns a specific player

This demonstrates separation of concerns between:
- data storage (SQLite)
- data structure (Pydantic model)
- data access (API endpoints)