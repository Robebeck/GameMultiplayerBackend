# GameMultiplayerBackend
Backend for multiplayer client/server logic for Turn Based Strategy Card Game.

User Stories

As a player I ned to see game invitations so that I can join a lobby.
As a player I need to be able to invite players so that they can join my lobby.
As a player I ned to be able to start a game so that all players in the lobby join a game session.
As a player I need to be able to input game actions that are validated by the server to play the multiplayer game.
As a player I need to be able to receive updates about game state from the server to play the multiplayer game.


Use Cases

Logging in.
User opens client types, username and password into form.  Server receives these through http request response.  After
authentication user is logged in.  Server shares login state to other users.

Starting Lobby
Logged in user invites other user to lobby.  Invitation is received by server and passed via request response to invited user.
If user accepts they are placed into the same lobby which is a list of players who will join the same game session.

Starting Game
All users within the same lobby, stored as a list on server side join a game session.  At the start of game a websocket session
is started by the user on the client side when they press the start game button in the UI.  The game is loaded after this
websocket handshake is accepted, and at this point client and server interact without http request response needed.
