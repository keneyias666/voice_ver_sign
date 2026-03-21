/**
 * Shared API client for backend integration readiness.
 * All pages can use this module; calls gracefully fail if backend is unavailable.
 */
(function initApiClient() {
    const API_DEFAULT = "http://127.0.0.1:8000";

    const ApiClient = {
        getBaseUrl() {
            return localStorage.getItem("apiBaseUrl") || API_DEFAULT;
        },

        setBaseUrl(url) {
            if (!url) return;
            localStorage.setItem("apiBaseUrl", url);
        },

        async request(path, options = {}) {
            const url = `${this.getBaseUrl()}${path}`;
            const response = await fetch(url, {
                headers: {
                    "Content-Type": "application/json",
                    ...(options.headers || {})
                },
                ...options
            });

            let payload = null;
            try {
                payload = await response.json();
            } catch (error) {
                payload = null;
            }

            if (!response.ok) {
                const message = payload?.detail || payload?.message || `Request failed: ${response.status}`;
                throw new Error(message);
            }
            return payload;
        },

        login(email, password) {
            return this.request("/api/auth/login", {
                method: "POST",
                body: JSON.stringify({ email, password })
            });
        },

        signup(data) {
            return this.request("/api/auth/signup", {
                method: "POST",
                body: JSON.stringify(data)
            });
        },

        forgotPassword(email) {
            return this.request("/api/auth/forgot-password", {
                method: "POST",
                body: JSON.stringify({ email })
            });
        },

        getPreferences() {
            return this.request("/api/preferences", { method: "GET" });
        },

        savePreferences(preferences) {
            return this.request("/api/preferences", {
                method: "PUT",
                body: JSON.stringify(preferences)
            });
        }
    };

    window.ApiClient = ApiClient;
})();
