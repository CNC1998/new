// =============================================================================
//  auth.js  –  Login, Register, and Logout functions
//  Used on: login.html, register.html, index.html, history.html
// =============================================================================


// =============================================================================
//  LOGIN
// =============================================================================

function loginUser() {
    var email    = document.getElementById("email").value.trim();
    var password = document.getElementById("password").value.trim();

    // Basic front-end validation before sending to server
    if (!email || !password) {
        showAuthError("Please enter your email and password.");
        return;
    }

    // Disable the button and show loading
    setAuthButtonLoading("login-btn", "login-btn-text", true, "Logging in...");

    // Send login request to the Python backend
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/login", true);
    xhr.setRequestHeader("Content-Type", "application/json");

    xhr.onreadystatechange = function() {
        if (xhr.readyState !== 4) return;

        setAuthButtonLoading("login-btn", "login-btn-text", false, "Login");
        var data = JSON.parse(xhr.responseText);

        if (xhr.status === 200) {
            // Login success — go to main page
            window.location.href = "/";
        } else {
            showAuthError(data.error || "Login failed. Please try again.");
        }
    };

    xhr.send(JSON.stringify({ email: email, password: password }));
}


// =============================================================================
//  REGISTER
// =============================================================================

function registerUser() {
    var username  = document.getElementById("username").value.trim();
    var email     = document.getElementById("email").value.trim();
    var password  = document.getElementById("password").value.trim();
    var confirm   = document.getElementById("confirm-password").value.trim();

    // Front-end validation
    if (!username || !email || !password || !confirm) {
        showAuthError("All fields are required.");
        return;
    }

    if (password.length < 6) {
        showAuthError("Password must be at least 6 characters.");
        return;
    }

    if (password !== confirm) {
        showAuthError("Passwords do not match.");
        return;
    }

    if (!email.includes("@")) {
        showAuthError("Please enter a valid email address.");
        return;
    }

    // Disable button and show loading
    setAuthButtonLoading("register-btn", "register-btn-text", true, "Creating account...");

    // Send register request to the Python backend
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/register", true);
    xhr.setRequestHeader("Content-Type", "application/json");

    xhr.onreadystatechange = function() {
        if (xhr.readyState !== 4) return;

        setAuthButtonLoading("register-btn", "register-btn-text", false, "Create Account");
        var data = JSON.parse(xhr.responseText);

        if (xhr.status === 201) {
            // Account created — show success then redirect to login
            showAuthSuccess("Account created! Redirecting to login...");
            setTimeout(function() {
                window.location.href = "/login";
            }, 1500);
        } else {
            showAuthError(data.error || "Registration failed. Please try again.");
        }
    };

    xhr.send(JSON.stringify({ username: username, email: email, password: password }));
}


// =============================================================================
//  LOGOUT
// =============================================================================

function logoutUser() {
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/logout", true);

    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4) {
            // Redirect to login page after logout
            window.location.href = "/login";
        }
    };

    xhr.send();
}


// =============================================================================
//  LOAD CURRENT USER INFO  (shown in navbar)
// =============================================================================

function loadCurrentUser() {
    var usernameEl = document.getElementById("nav-username");
    if (!usernameEl) return;

    var xhr = new XMLHttpRequest();
    xhr.open("GET", "/api/me", true);

    xhr.onreadystatechange = function() {
        if (xhr.readyState !== 4) return;

        if (xhr.status === 200) {
            var data = JSON.parse(xhr.responseText);
            usernameEl.textContent = "Hi, " + data.username;
        } else {
            // Session expired — redirect to login
            window.location.href = "/login";
        }
    };

    xhr.send();
}

// Load user info when the page opens (for index.html and history.html)
document.addEventListener("DOMContentLoaded", function() {
    loadCurrentUser();
});


// =============================================================================
//  UI HELPER FUNCTIONS
// =============================================================================

function showAuthError(message) {
    var errorEl = document.getElementById("auth-error");
    if (!errorEl) return;
    errorEl.textContent   = message;
    errorEl.style.display = "block";

    // Hide success box if shown
    var successEl = document.getElementById("auth-success");
    if (successEl) successEl.style.display = "none";
}

function showAuthSuccess(message) {
    var successEl = document.getElementById("auth-success");
    if (!successEl) return;
    successEl.textContent   = message;
    successEl.style.display = "block";

    // Hide error box if shown
    var errorEl = document.getElementById("auth-error");
    if (errorEl) errorEl.style.display = "none";
}

function setAuthButtonLoading(btnId, textId, isLoading, label) {
    var btn     = document.getElementById(btnId);
    var btnText = document.getElementById(textId);
    if (!btn || !btnText) return;

    btn.disabled    = isLoading;
    btnText.textContent = label;
}
