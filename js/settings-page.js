function saveAppSettings() {
    const settings = {
        apiBaseUrl: document.getElementById("apiBaseUrl")?.value?.trim() || "",
        defaultLanguage: document.getElementById("defaultLanguage")?.value || "English",
        responseStyle: document.getElementById("responseStyle")?.value || "balanced",
        autoCamera: !!document.getElementById("autoCamera")?.checked,
        soundAlerts: !!document.getElementById("soundAlerts")?.checked
    };

    if (settings.apiBaseUrl && typeof ApiClient !== "undefined") {
        ApiClient.setBaseUrl(settings.apiBaseUrl);
    }
    localStorage.setItem("appSettings", JSON.stringify(settings));
    Toast.show("Settings saved.");
}

async function testBackendConnection() {
    if (typeof ApiClient === "undefined") {
        Toast.show("API client unavailable.");
        return;
    }
    try {
        await ApiClient.request("/api/health", { method: "GET" });
        Toast.show("Backend connection successful.");
    } catch (error) {
        Toast.show("Backend not reachable yet.");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const saved = localStorage.getItem("appSettings");
    if (!saved) {
        if (typeof ApiClient !== "undefined") {
            document.getElementById("apiBaseUrl").value = ApiClient.getBaseUrl();
        }
        return;
    }

    try {
        const settings = JSON.parse(saved);
        if (settings.apiBaseUrl) document.getElementById("apiBaseUrl").value = settings.apiBaseUrl;
        if (settings.defaultLanguage) document.getElementById("defaultLanguage").value = settings.defaultLanguage;
        if (settings.responseStyle) document.getElementById("responseStyle").value = settings.responseStyle;
        if (typeof settings.autoCamera === "boolean") document.getElementById("autoCamera").checked = settings.autoCamera;
        if (typeof settings.soundAlerts === "boolean") document.getElementById("soundAlerts").checked = settings.soundAlerts;
    } catch (error) {
        console.warn("Failed to load settings.", error);
    }
});
