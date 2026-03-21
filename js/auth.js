/**
 * Voice2Sign authentication page logic.
 */

let selectedUserType = "hearing";

function simpleTogglePassword() {
    const input = document.getElementById("password");
    if (!input) return;
    input.type = input.type === "password" ? "text" : "password";
}

function togglePassword(inputId, iconId) {
    const input = document.getElementById(inputId);
    const icon = document.getElementById(iconId);
    if (!input) return;
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    if (icon) {
        icon.style.opacity = show ? "1" : "0.65";
    }
}

function checkPasswordStrength(password) {
    let score = 0;
    if (password.length >= 8) score += 1;
    if (/[A-Z]/.test(password)) score += 1;
    if (/[0-9]/.test(password)) score += 1;
    if (/[^A-Za-z0-9]/.test(password)) score += 1;

    const strengthFill = document.getElementById("strengthFill");
    const strengthText = document.getElementById("strengthText");
    if (!strengthFill || !strengthText) return score;

    const labels = ["Weak", "Fair", "Good", "Strong"];
    const colors = ["#ef4444", "#f59e0b", "#84cc16", "#22c55e"];
    const width = Math.max(score, 1) * 25;

    strengthFill.style.width = `${width}%`;
    strengthFill.style.background = colors[Math.max(score - 1, 0)];
    strengthText.textContent = password ? `Password strength: ${labels[Math.max(score - 1, 0)]}` : "Use 8+ chars with mixed types";

    return score;
}

function selectUserType(type) {
    selectedUserType = type;
    document.querySelectorAll(".user-type-btn").forEach((btn) => {
        btn.classList.toggle("active", btn.dataset.type === type);
    });
}

function simulateAuth(message, redirectTo) {
    const submitBtn = document.querySelector("button[type='submit']");
    if (submitBtn) submitBtn.classList.add("btn-loading");
    setTimeout(() => {
        if (submitBtn) submitBtn.classList.remove("btn-loading");
        Toast.show(message);
        setTimeout(() => {
            window.location.href = redirectTo;
        }, 700);
    }, 700);
}

function handleLogin(event) {
    event.preventDefault();
    const email = document.getElementById("email")?.value?.trim();
    const password = document.getElementById("password")?.value;

    if (!email || !password) {
        Toast.show("Please enter email and password.");
        return;
    }
    simulateAuth("Signed in successfully.", "dashboard.html");
}

function handleSignup(event) {
    event.preventDefault();

    const firstName = document.getElementById("firstName")?.value?.trim();
    const lastName = document.getElementById("lastName")?.value?.trim();
    const email = document.getElementById("email")?.value?.trim();
    const password = document.getElementById("password")?.value || "";
    const confirmPassword = document.getElementById("confirmPassword")?.value || "";
    const termsAccepted = document.getElementById("terms")?.checked;

    if (!firstName || !lastName || !email) {
        Toast.show("Please complete all required fields.");
        return;
    }
    if (password !== confirmPassword) {
        Toast.show("Passwords do not match.");
        return;
    }
    if (checkPasswordStrength(password) < 2) {
        Toast.show("Please choose a stronger password.");
        return;
    }
    if (!termsAccepted) {
        Toast.show("Please accept terms to continue.");
        return;
    }

    localStorage.setItem("userType", selectedUserType);
    simulateAuth("Account created successfully.", "dashboard.html");
}

function loginWithGoogle() {
    Toast.show("Google sign in coming soon.");
}

function loginWithFacebook() {
    Toast.show("Facebook sign in coming soon.");
}

document.addEventListener("DOMContentLoaded", () => {
    const passwordInput = document.getElementById("password");
    if (passwordInput) {
        passwordInput.addEventListener("input", (event) => {
            checkPasswordStrength(event.target.value);
        });
    }

    const initialTypeBtn = document.querySelector(".user-type-btn.active");
    if (initialTypeBtn) {
        selectedUserType = initialTypeBtn.dataset.type || "hearing";
    }
});
