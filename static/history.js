// =============================================================================
//  history.js  –  Resume History Page
//  Fetches all uploaded resumes from the database and renders them as cards
// =============================================================================


// Domain accent colours (same as script.js)
var DOMAIN_COLORS = {
    "Data Science":         "#f472b6",
    "Web Development":      "#60a5fa",
    "AI/ML":                "#a78bfa",
    "DevOps":               "#34d399",
    "Cybersecurity":        "#f87171",
    "Mobile Development":   "#fbbf24",
    "Cloud Computing":      "#67e8f9",
    "Software Engineering": "#818cf8",
    "UI/UX Design":         "#fb7185",
    "Big Data Engineering": "#4ade80",
    "NLP":                  "#c084fc",
    "QA & Testing":         "#fdba74"
};


// =============================================================================
//  INITIALISE
// =============================================================================

document.addEventListener("DOMContentLoaded", function() {
    loadHistory();
});


// =============================================================================
//  LOAD RESUME HISTORY FROM SERVER
// =============================================================================

function loadHistory() {
    showLoading(true);

    var xhr = new XMLHttpRequest();
    xhr.open("GET", "/api/history", true);

    xhr.onreadystatechange = function() {
        if (xhr.readyState !== 4) return;

        showLoading(false);

        if (xhr.status === 200) {
            var resumes = JSON.parse(xhr.responseText);

            if (resumes.length === 0) {
                showEmpty(true);
            } else {
                renderHistory(resumes);
            }

        } else if (xhr.status === 401) {
            // Not logged in — redirect to login
            window.location.href = "/login";
        } else {
            showEmpty(true);
        }
    };

    xhr.send();
}


// =============================================================================
//  RENDER RESUME CARDS
// =============================================================================

function renderHistory(resumes) {
    var grid = document.getElementById("history-grid");
    var html = "";

    for (var i = 0; i < resumes.length; i++) {
        html += makeResumeCard(resumes[i]);
    }

    grid.innerHTML = html;
}


function makeResumeCard(resume) {
    var score       = resume.score;
    var domainColor = DOMAIN_COLORS[resume.domain] || "#a78bfa";

    // Choose score colour
    var scoreColor = "#4ade80";
    if (score < 70) scoreColor = "#fbbf24";
    if (score < 45) scoreColor = "#f87171";

    // Format the upload date nicely
    var date = resume.uploaded_at.split(" ")[0];   // just the date part

    // Build matched skill tags (show up to 6)
    var matchedTags = "";
    var showCount   = Math.min(resume.matched_skills.length, 6);
    for (var i = 0; i < showCount; i++) {
        matchedTags += '<span class="tag tag-green">' + resume.matched_skills[i] + "</span>";
    }
    if (resume.matched_skills.length > 6) {
        var extra = resume.matched_skills.length - 6;
        matchedTags += '<span class="tag" style="border-color:#374151;color:#6b7280">+' + extra + ' more</span>';
    }

    return (
        '<div class="resume-card">' +

        // Coloured top bar
        '<div class="resume-card-bar" style="background:' + domainColor + '"></div>' +

        // Top row: filename + delete button
        '<div class="resume-card-top">' +
        '<div>' +
        '<div class="resume-filename">&#128196; ' + resume.filename + '</div>' +
        '<div class="resume-date">Uploaded: ' + date + '</div>' +
        '</div>' +
        '<button class="delete-btn" onclick="deleteResume(' + resume.id + ', this)">&#128465; Delete</button>' +
        '</div>' +

        // Score and domain
        '<div class="resume-meta">' +
        '<div class="resume-score" style="color:' + scoreColor + '">' + score + '%</div>' +
        '<div class="resume-badges">' +
        '<span class="resume-domain">' + resume.domain + '</span>' +
        '<span class="resume-level">' + resume.experience + '</span>' +
        '</div>' +
        '</div>' +

        // Matched skills
        '<div class="resume-skills-title">Matched Skills</div>' +
        '<div class="resume-tags">' + (matchedTags || '<span style="color:#6b7280;font-size:.75rem">No skills matched</span>') + '</div>' +

        // Summary
        '<div class="resume-summary">' + resume.summary + '</div>' +

        '</div>'
    );
}


// =============================================================================
//  DELETE A RESUME
// =============================================================================

function deleteResume(resumeId, buttonEl) {
    if (!confirm("Delete this resume from your history?")) return;

    buttonEl.disabled    = true;
    buttonEl.textContent = "Deleting...";

    var xhr = new XMLHttpRequest();
    xhr.open("DELETE", "/api/history/" + resumeId, true);

    xhr.onreadystatechange = function() {
        if (xhr.readyState !== 4) return;

        if (xhr.status === 200) {
            // Remove the card from the page smoothly
            var card = buttonEl.closest(".resume-card");
            card.style.transition = "opacity 0.3s";
            card.style.opacity    = "0";
            setTimeout(function() {
                card.remove();

                // If no cards left, show empty state
                var grid = document.getElementById("history-grid");
                if (grid.children.length === 0) {
                    showEmpty(true);
                }
            }, 300);
        } else {
            buttonEl.disabled    = false;
            buttonEl.textContent = "&#128465; Delete";
            alert("Could not delete. Please try again.");
        }
    };

    xhr.send();
}


// =============================================================================
//  UI HELPERS
// =============================================================================

function showLoading(visible) {
    document.getElementById("loading-box").style.display = visible ? "block" : "none";
}

function showEmpty(visible) {
    document.getElementById("empty-box").style.display = visible ? "block" : "none";
}
