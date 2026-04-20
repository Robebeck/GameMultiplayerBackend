document.addEventListener("DOMContentLoaded", () => {
    const wsUrl = "ws://" + window.location.host + "/ws";
    let socket = null;

    const statusDot = document.getElementById("ws-status-dot");
    const statusText = document.getElementById("ws-status-text");
    const logContainer = document.getElementById("log-container");
    
    // UI Buttons
    const btnIdentify = document.getElementById("btn-identify");
    const btnRegister = document.getElementById("btn-register");
    const inputUsername = document.getElementById("username-input");
    const inputPassword = document.getElementById("password-input");
    const identityStatus = document.getElementById("identity-status");

    const btnMove = document.getElementById("btn-move");
    const btnCard = document.getElementById("btn-card");
    const btnClear = document.getElementById("btn-clear");
    
    const btnAddFriend = document.getElementById("btn-add-friend");
    const inputAddFriendUsername = document.getElementById("add-friend-username");
    const btnRefreshFriends = document.getElementById("btn-refresh-friends");

    // Tab buttons
    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabContents = document.querySelectorAll(".tab-content");

    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            tabBtns.forEach(b => b.classList.remove("active"));
            tabContents.forEach(c => c.classList.remove("active"));
            btn.classList.add("active");
            document.getElementById(btn.dataset.tab).classList.add("active");
        });
    });

    let pendingIdentify = null;
    let pendingRegister = null;

    function connect() {
        if (socket && (socket.readyState === WebSocket.CONNECTING || socket.readyState === WebSocket.OPEN)) {
            return;
        }

        addLog("Connecting to server at " + wsUrl + "...", "system");
        socket = new WebSocket(wsUrl);

        socket.onopen = (event) => {
            statusDot.classList.add("connected");
            statusText.textContent = "Connected";
            statusText.style.color = "var(--success)";
            addLog("WebSocket Connection Established.", "system");
            
            if (pendingIdentify) {
                sendRequest("IDENTIFY", pendingIdentify);
                pendingIdentify = null;
            }
            if (pendingRegister) {
                sendRequest("REGISTER", pendingRegister);
                pendingRegister = null;
            }
        };

        socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                addLog(JSON.stringify(data, null, 2), "received");
                handleServerMessage(data);
            } catch (e) {
                addLog(event.data, "received");
            }
        };

        socket.onclose = (event) => {
            statusDot.classList.remove("connected");
            statusText.textContent = "Disconnected";
            statusText.style.color = "var(--error)";
            addLog("WebSocket Connection Closed.", "error");
            identityStatus.textContent = "Not Logged In";
            identityStatus.className = "status-badge offline";
            
            renderFriendsList([]); // Clear friends on disconnect
        };

        socket.onerror = (error) => {
            addLog("WebSocket Error occurred.", "error");
        };
    }

    function sendMessage(payload) {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(payload));
            addLog(JSON.stringify(payload, null, 2), "sent");
        } else {
            addLog("Cannot send message. WebSocket is not connected.", "error");
        }
    }

    function generateReqId() {
        return Date.now() + "_" + Math.floor(Math.random() * 1000);
    }

    function handleServerMessage(data) {
        switch (data.type) {
            case "REGISTER_SUCCESS":
                alert("Registration successful! You can now log in.");
                break;
            case "IDENTIFY_SUCCESS":
                identityStatus.textContent = "Logged In";
                identityStatus.className = "status-badge online";
                // immediately fetch friends
                sendRequest("GET_FRIENDS", {});
                break;
            case "FRIENDS_LIST":
                renderFriendsList(data.data);
                break;
            case "INCOMING_FRIEND_REQUEST":
            case "FRIEND_REQUEST_ACCEPTED":
            case "FRIEND_STATUS_UPDATE":
            case "FRIEND_UPDATED":
            case "FRIEND_REQUEST_SENT":
            case "FRIEND_ACCEPTED":
                // refresh lists
                sendRequest("GET_FRIENDS", {});
                break;
            case "LOBBY_INVITE_RECEIVED":
                alert(`You received a lobby invite from Player ID: ${data.data.from_id}`);
                break;
        }
    }

    function sendRequest(type, params) {
        sendMessage({ request_id: generateReqId(), type, params });
    }

    btnIdentify.addEventListener("click", () => {
        const username = inputUsername.value;
        const password = inputPassword.value;
        if (!username || !password) return;
        
        pendingIdentify = { username: username, password: password };
        
        if (!socket || socket.readyState === WebSocket.CLOSED || socket.readyState === WebSocket.CLOSING) {
            connect();
        } else {
            sendRequest("IDENTIFY", pendingIdentify);
            pendingIdentify = null;
        }
    });

    btnRegister.addEventListener("click", () => {
        const username = inputUsername.value;
        const password = inputPassword.value;
        if (!username || !password) return;
        
        pendingRegister = { username: username, password: password };
        
        if (!socket || socket.readyState === WebSocket.CLOSED || socket.readyState === WebSocket.CLOSING) {
            connect();
        } else {
            sendRequest("REGISTER", pendingRegister);
            pendingRegister = null;
        }
    });

    btnMove.addEventListener("click", () => sendRequest("MOVE", { target_x: 10, target_z: 5 }));
    btnCard.addEventListener("click", () => sendRequest("CARD", { card_id: "fireball_01" }));
    btnClear.addEventListener("click", () => { logContainer.innerHTML = ""; });

    btnAddFriend.addEventListener("click", () => {
        const friendUsername = inputAddFriendUsername.value;
        if (!friendUsername) return;
        sendRequest("FRIEND_REQUEST", { target_username: friendUsername });
        inputAddFriendUsername.value = "";
    });

    btnRefreshFriends.addEventListener("click", () => {
        sendRequest("GET_FRIENDS", {});
    });

    function renderFriendsList(friends) {
        const tabFriends = document.getElementById("tab-friends");
        const tabRequests = document.getElementById("tab-requests");
        const tabBlocked = document.getElementById("tab-blocked");

        tabFriends.innerHTML = "";
        tabRequests.innerHTML = "";
        tabBlocked.innerHTML = "";

        if (friends.length === 0) {
            tabFriends.innerHTML = "<p>No friends found.</p>";
            tabRequests.innerHTML = "<p>No pending requests.</p>";
            tabBlocked.innerHTML = "<p>No blocked users.</p>";
            return;
        }

        let hasFriends = false;
        let hasRequests = false;
        let hasBlocked = false;

        friends.forEach(f => {
            if (f.status === 'accepted') {
                tabFriends.appendChild(createFriendElement(f, 'friend'));
                hasFriends = true;
            } else if (f.status === 'pending') {
                tabRequests.appendChild(createFriendElement(f, 'request'));
                hasRequests = true;
            } else if (f.status === 'blocked') {
                tabBlocked.appendChild(createFriendElement(f, 'blocked'));
                hasBlocked = true;
            }
        });

        if (!hasFriends) tabFriends.innerHTML = "<p>No friends found.</p>";
        if (!hasRequests) tabRequests.innerHTML = "<p>No pending requests.</p>";
        if (!hasBlocked) tabBlocked.innerHTML = "<p>No blocked users.</p>";
    }

    function createFriendElement(f, type) {
        const div = document.createElement("div");
        div.className = "friend-item";

        let statusDot = `<div class="dot ${f.login_state ? 'connected' : ''}"></div>`;
        
        let actions = "";
        if (type === 'friend') {
            actions = `
                <button class="action-icon-btn invite" data-id="${f.id}">Invite</button>
                <button class="action-icon-btn block" data-id="${f.id}">Block</button>
            `;
        } else if (type === 'request') {
            if (!f.is_requester) {
                // we are receiving it
                actions = `
                    <button class="action-icon-btn accept" data-id="${f.id}">Accept</button>
                    <button class="action-icon-btn reject" data-id="${f.id}">Reject</button>
                `;
            } else {
                actions = `<span style="font-size: 0.8rem; color: var(--text-muted)">Sent</span>`;
            }
        } else if (type === 'blocked') {
            // usually unblock option, we can reuse reject to delete the relationship
            actions = `<button class="action-icon-btn reject" data-id="${f.id}">Unblock</button>`;
        }

        div.innerHTML = `
            <div class="friend-info">
                ${type === 'friend' ? statusDot : ''}
                <div>
                    <div class="friend-name">${f.username} <span class="friend-id">#${f.id}</span></div>
                    <div style="font-size:0.7rem; color: var(--text-muted)">${type === 'friend' ? (f.login_state ? 'Online' : 'Offline') : ''}</div>
                </div>
            </div>
            <div class="friend-actions">
                ${actions}
            </div>
        `;

        const btnInvite = div.querySelector(".invite");
        if (btnInvite) btnInvite.addEventListener("click", () => sendRequest("LOBBY_INVITE", { friend_id: f.id }));
        
        const btnBlock = div.querySelector(".block");
        if (btnBlock) btnBlock.addEventListener("click", () => sendRequest("FRIEND_BLOCK", { target_id: f.id }));

        const btnAccept = div.querySelector(".accept");
        if (btnAccept) btnAccept.addEventListener("click", () => sendRequest("FRIEND_ACCEPT", { requester_id: f.id }));

        const btnReject = div.querySelector(".reject");
        if (btnReject) {
            btnReject.addEventListener("click", () => sendRequest("FRIEND_REJECT", { target_id: f.id }));
        }

        return div;
    }

    function addLog(message, type) {
        const entry = document.createElement("div");
        entry.className = `log-entry ${type}`;
        
        const timestamp = document.createElement("span");
        timestamp.className = "log-timestamp";
        
        const now = new Date();
        timestamp.textContent = now.toLocaleTimeString() + "." + now.getMilliseconds().toString().padStart(3, '0');
        
        const content = document.createElement("div");
        content.className = "log-content";
        content.textContent = message;
        
        entry.appendChild(timestamp);
        entry.appendChild(content);
        
        logContainer.prepend(entry);
        logContainer.scrollTop = 0;
    }
});
