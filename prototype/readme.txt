Prototype with login using username and password authenticated via HTTP POST.  Game actions (Move and Card actions) are requested and replied to via WebSockets.



install requirements
----------------
fastapi==0.111.0
uvicorn==0.30.1
websockets==12.0


run 
python -m uvicorn main:app --reload

navigate to http://127.0.0.1:8000/ui
