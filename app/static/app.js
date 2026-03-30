document.addEventListener("DOMContentLoaded", () => {
    const wsUrl = "ws://" + window.location.host + "/ws";
    let socket = null;

    const statusDot = document.getElementById("ws-status-dot");
    const statusText = document.getElementById("ws-status-text");
    const logContainer = document.getElementById("log-container");
    
    // UI Buttons
    const btnMove = document.getElementById("btn-move");
    const btnCard = document.getElementById("btn-card");
    const btnClear = document.getElementById("btn-clear");

    function connect() {
        addLog("Connecting to server at " + wsUrl + "...", "system");
        socket = new WebSocket(wsUrl);

        socket.onopen = (event) => {
            statusDot.classList.add("connected");
            statusText.textContent = "Connected";
            statusText.style.color = "var(--success)";
            addLog("WebSocket Connection Established.", "system");
        };

        socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                addLog(JSON.stringify(data, null, 2), "received");
            } catch (e) {
                addLog(event.data, "received");
            }
        };

        socket.onclose = (event) => {
            statusDot.classList.remove("connected");
            statusText.textContent = "Disconnected";
            statusText.style.color = "var(--error)";
            addLog("WebSocket Connection Closed.", "error");

            // Attempt to reconnect after a delay
            setTimeout(connect, 3000);
        };

        socket.onerror = (error) => {
            addLog("WebSocket Error occurred.", "error");
        };
    }

    function sendMessage(payload) {
        if (socket && socket.readyState === WebSocket.OPEN) {
            const jsonStr = JSON.stringify(payload);
            socket.send(jsonStr);
            addLog(JSON.stringify(payload, null, 2), "sent");
        } else {
            addLog("Cannot send message. WebSocket is not connected.", "error");
        }
    }

    btnMove.addEventListener("click", () => {
        const reqId = Date.now() + "_" + Math.floor(Math.random() * 1000);
        const payload = {
            request_id: reqId,
            type: "MOVE",
            params: {
                target_x: 10,
                target_z: 5
            }
        };
        sendMessage(payload);
    });

    btnCard.addEventListener("click", () => {
        const reqId = Date.now() + "_" + Math.floor(Math.random() * 1000);
        const payload = {
            request_id: reqId,
            type: "CARD",
            params: {
                card_id: "fireball_01"
            }
        };
        sendMessage(payload);
    });

    btnClear.addEventListener("click", () => {
        logContainer.innerHTML = "";
    });

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
        
        logContainer.appendChild(entry);
        
        // Auto-scroll to bottom
        logContainer.scrollTop = logContainer.scrollHeight;
    }

    // Initialize connection
    connect();
});
