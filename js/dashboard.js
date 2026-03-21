/**
 * Voice2Sign dashboard interactions.
 */

let currentMode = localStorage.getItem("userType") || "hearing";
let chatCounter = 3;
let sidebarCollapsed = localStorage.getItem("sidebarCollapsed") === "true";
let micActive = false;
let cameraActive = false;
let API_BASE_URL = localStorage.getItem("apiBaseUrl") || "http://127.0.0.1:8000";
let micStream = null;
let cameraStream = null;

function syncCameraPanelUi(isActive) {
    const panel = document.getElementById("cameraPanel");
    const button = document.getElementById("cameraBtn");
    const preview = document.getElementById("cameraPreview");
    if (panel) panel.style.display = isActive ? "" : "none";
    if (button) button.classList.toggle("active", isActive);
    if (!isActive && preview) preview.srcObject = null;
    setCameraLive(isActive);
}

/* ── Sidebar ── */
function toggleSidebar() {
    sidebarCollapsed = !sidebarCollapsed;
    localStorage.setItem("sidebarCollapsed", String(sidebarCollapsed));
    const shell = document.querySelector(".dashboard-shell");
    const sidebar = document.getElementById("sidebar");
    if (shell) shell.classList.toggle("sidebar-collapsed", sidebarCollapsed);
    if (sidebar) sidebar.classList.toggle("sidebar-collapsed", sidebarCollapsed);
}

/* ── Section switching ── */
function showSection(section) {
    document.querySelectorAll(".sb-nav-item").forEach((btn) => btn.classList.remove("active"));
    document.querySelectorAll(".section-chat").forEach((el) => el.classList.remove("section-hidden"));
    document.getElementById("preferencesPanel").classList.remove("is-visible");
    document.getElementById("settingsPanel").classList.remove("is-visible");
    document.getElementById("profilePanel").classList.remove("is-visible");

    if (section === "chat") {
        const btn = document.querySelector('.sb-nav-item[data-section="chat"]');
        if (btn) btn.classList.add("active");
        return;
    }

    document.querySelectorAll(".section-chat").forEach((el) => el.classList.add("section-hidden"));

    if (section === "preferences") {
        document.getElementById("preferencesPanel").classList.add("is-visible");
        const btn = document.querySelector('.sb-nav-item[data-section="preferences"]');
        if (btn) btn.classList.add("active");
        return;
    }

    if (section === "settings") {
        document.getElementById("settingsPanel").classList.add("is-visible");
        const btn = document.querySelector('.sb-nav-item[data-section="settings"]');
        if (btn) btn.classList.add("active");
        return;
    }

    if (section === "profile") {
        document.getElementById("profilePanel").classList.add("is-visible");
        return;
    }
}

/* ── Profile display ── */
function updateProfileDisplay() {
    const profileRaw = localStorage.getItem("profileSettings");
    let name = "Elias Amaba";
    if (profileRaw) {
        try {
            const p = JSON.parse(profileRaw);
            if (p.name) name = p.name;
        } catch (e) {}
    }
    const userNameDisplay = document.getElementById("userNameDisplay");
    if (userNameDisplay) userNameDisplay.textContent = name;
}

/* ── Settings / Profile save ── */
function saveSettings() {
    const value = document.getElementById("apiBaseInput")?.value?.trim();
    if (!value) return;
    API_BASE_URL = value;
    localStorage.setItem("apiBaseUrl", value);
    Toast.show("Settings saved.");
}

function saveProfileSettings() {
    const profile = {
        name: document.getElementById("profileNameInput")?.value?.trim() || "",
        email: document.getElementById("profileEmailInput")?.value?.trim() || "",
        language: document.getElementById("profileLanguageInput")?.value?.trim() || ""
    };
    localStorage.setItem("profileSettings", JSON.stringify(profile));
    updateProfileDisplay();
    Toast.show("Profile settings saved.");
}

/* ── Backend API call ── */
async function callInputApi(type, active) {
    const response = await fetch(`${API_BASE_URL}/api/input/${type}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active })
    });
    if (!response.ok) throw new Error(`API request failed: ${response.status}`);
    return response.json();
}

/* ── Camera live indicator ── */
function setCameraLive(isLive) {
    const dot = document.getElementById("cameraDot");
    const stateText = document.getElementById("cameraStateText");
    if (dot) dot.classList.toggle("live", isLive);
    if (stateText) {
        stateText.textContent = isLive ? "Live" : "Off";
        if (isLive) {
            stateText.removeAttribute("data-off");
        } else {
            stateText.setAttribute("data-off", "");
        }
    }
}

/* ── Mic recording indicator ── */
function setMicRecording(isRecording) {
    const indicator = document.getElementById("micIndicator");
    if (indicator) indicator.style.display = isRecording ? "flex" : "none";
}

/* ── Handle mic/camera input ── */
async function handleInput(type) {
    const isMic = type === "mic";
    const nextState = isMic ? !micActive : !cameraActive;
    const btn = document.getElementById(isMic ? "micBtn" : "cameraBtn");

    try {
        if (isMic) {
            if (nextState) {
                micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            } else if (micStream) {
                micStream.getTracks().forEach((t) => t.stop());
                micStream = null;
            }
            setMicRecording(nextState);
        } else {
            if (!navigator.mediaDevices?.getUserMedia) {
                throw new Error("Camera API not supported in this browser.");
            }
            if (nextState) {
                cameraStream = await navigator.mediaDevices.getUserMedia({
                    video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" }
                });
                const video = document.getElementById("cameraPreview");
                if (video) video.srcObject = cameraStream;
                syncCameraPanelUi(true);
            } else if (cameraStream) {
                cameraStream.getTracks().forEach((t) => t.stop());
                cameraStream = null;
                syncCameraPanelUi(false);
            } else {
                syncCameraPanelUi(false);
            }
        }

        const result = await callInputApi(type, nextState);
        if (isMic) {
            micActive = result.active;
            setMicRecording(micActive);
        } else {
            cameraActive = result.active;
            if (!cameraActive && cameraStream) {
                cameraStream.getTracks().forEach((t) => t.stop());
                cameraStream = null;
            }
            syncCameraPanelUi(cameraActive);
        }

        if (btn) btn.classList.toggle("active", result.active);
        const label = isMic ? "Microphone" : "Camera";
        Toast.show(`${label} ${result.active ? "on" : "off"}.`, 2000, isMic ? "mic" : "default");
    } catch (error) {
        if (isMic && micStream) { micStream.getTracks().forEach((t) => t.stop()); micStream = null; setMicRecording(false); }
        if (!isMic && cameraStream) { cameraStream.getTracks().forEach((t) => t.stop()); cameraStream = null; syncCameraPanelUi(false); }
        const label = isMic ? "Microphone" : "Camera";
        Toast.show(`${label} unavailable. Check browser permissions.`);
        console.warn(`${label} error:`, error);
    }
}

/* ── Chat messages ── */
function removeWelcomeCard() {
    const welcome = document.getElementById("welcomeCard");
    if (welcome) {
        welcome.style.opacity = "0";
        welcome.style.transform = "translateY(-8px)";
        welcome.style.transition = "opacity 0.18s, transform 0.18s";
        setTimeout(() => welcome.remove(), 190);
    }
}

function addUserMessage(text) {
    if (!text?.trim()) return;
    removeWelcomeCard();
    const chatBody = document.getElementById("chatBody");
    if (!chatBody) return;
    const item = document.createElement("div");
    item.className = "message user";
    item.textContent = text.trim();
    chatBody.appendChild(item);
    chatBody.scrollTop = chatBody.scrollHeight;
}

function addAssistantMessage(text) {
    const chatBody = document.getElementById("chatBody");
    if (!chatBody) return;
    const item = document.createElement("div");
    item.className = "message assistant";
    item.textContent = text;
    chatBody.appendChild(item);
    chatBody.scrollTop = chatBody.scrollHeight;
}

function sendMessage() {
    const input = document.getElementById("composerInput");
    if (!input) return;
    const value = input.value.trim();
    if (!value) return;
    addUserMessage(value);
    input.value = "";
    setTimeout(() => addAssistantMessage(`Demo response for: "${value}"`), 500);
}

function exampleHearing() {
    addUserMessage("Can you translate this sign gesture?");
    setTimeout(() => addAssistantMessage("Recognized sign: Hello. Confidence: 97%."), 500);
}

function exampleDeaf() {
    addUserMessage("Please convert this speech to sign output.");
    setTimeout(() => addAssistantMessage('Speech processed: "How are you today?" → Sign sequence generated.'), 500);
}

/* ── Conversation list ── */
function togglePin(button) {
    const isPinned = button.dataset.pinned === "true";
    button.dataset.pinned = isPinned ? "false" : "true";
    button.innerHTML = isPinned
        ? `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"/></svg>`
        : `<svg fill="currentColor" viewBox="0 0 24 24"><path d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"/></svg>`;
    Toast.show(isPinned ? "Conversation unpinned." : "Conversation pinned.");
}

function deleteChat(button) {
    const row = button.closest(".chat-item");
    if (row) {
        row.style.opacity = "0";
        row.style.transform = "translateX(-8px)";
        row.style.transition = "opacity 0.18s, transform 0.18s";
        setTimeout(() => row.remove(), 185);
    }
    Toast.show("Conversation deleted.");
}

function addConversation(title) {
    const list = document.getElementById("chatList");
    if (!list) return;
    chatCounter += 1;
    document.querySelectorAll(".chat-item").forEach((i) => i.classList.remove("active"));
    const row = document.createElement("div");
    row.className = "chat-item active";
    row.setAttribute("onclick", "document.querySelectorAll('.chat-item').forEach(i=>i.classList.remove('active'));this.classList.add('active')");
    row.innerHTML = `
        <svg class="chat-item-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/></svg>
        <span class="chat-item-name">${title || `Conversation ${chatCounter}`}</span>
        <div class="chat-item-actions">
            <button data-pinned="false" onclick="event.stopPropagation();togglePin(this)" aria-label="Pin"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"/></svg></button>
            <button onclick="event.stopPropagation();deleteChat(this)" aria-label="Delete"><svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg></button>
        </div>`;
    list.prepend(row);
}

function createNewChat() {
    addConversation("New conversation");
    Toast.show("Started a new conversation.");
}

/* ── Init ── */
document.addEventListener("DOMContentLoaded", () => {
    if (typeof ThemeManager !== "undefined") {
        ThemeManager.updateThemeIcons(ThemeManager.getCurrentTheme());
    }

    const apiBaseInput = document.getElementById("apiBaseInput");
    if (apiBaseInput) apiBaseInput.value = API_BASE_URL;

    const shell = document.querySelector(".dashboard-shell");
    const sidebar = document.getElementById("sidebar");
    if (shell) shell.classList.toggle("sidebar-collapsed", sidebarCollapsed);
    if (sidebar) sidebar.classList.toggle("sidebar-collapsed", sidebarCollapsed);
    syncCameraPanelUi(false);

    updateProfileDisplay();

    const profileRaw = localStorage.getItem("profileSettings");
    if (profileRaw) {
        try {
            const profile = JSON.parse(profileRaw);
            if (document.getElementById("profileNameInput")) document.getElementById("profileNameInput").value = profile.name || "";
            if (document.getElementById("profileEmailInput")) document.getElementById("profileEmailInput").value = profile.email || "";
            if (document.getElementById("profileLanguageInput")) document.getElementById("profileLanguageInput").value = profile.language || "";
        } catch (e) {}
    }

    const composerInput = document.getElementById("composerInput");
    if (composerInput) {
        composerInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
        });
    }

});
