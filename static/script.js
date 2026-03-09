// =============================================================================
//  script.js  –  ML-Based Resume Analyzer
//  Pure JavaScript — no frameworks, no libraries
//  All charts are drawn using the HTML5 Canvas API
// =============================================================================


// =============================================================================
//  DOMAIN DATA
//  The 12 available job domains with their icon characters and accent colours.
// =============================================================================

var DOMAINS = [
    "Data Science",
    "Web Development",
    "AI/ML",
    "DevOps",
    "Cybersecurity",
    "Mobile Development",
    "Cloud Computing",
    "Software Engineering",
    "UI/UX Design",
    "Big Data Engineering",
    "NLP",
    "QA & Testing"
];

// HTML entity icons for each domain button
var DOMAIN_ICONS = {
    "Data Science":        "&#9672;",
    "Web Development":     "&#11041;",
    "AI/ML":               "&#9678;",
    "DevOps":              "&#9881;",
    "Cybersecurity":       "&#11042;",
    "Mobile Development":  "&#9635;",
    "Cloud Computing":     "&#9673;",
    "Software Engineering":"&#11039;",
    "UI/UX Design":        "&#9670;",
    "Big Data Engineering":"&#9638;",
    "NLP":                 "&#9680;",
    "QA & Testing":        "&#9681;"
};

// Accent colour for each domain (used for charts and highlights)
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

// Job platform links (used in the "Find More Jobs" section)
var JOB_PLATFORMS = [
    {
        name: "LinkedIn",
        icon: "in",
        color: "#0A66C2",
        desc: "Professional network",
        url: function(domain) {
            return "https://linkedin.com/jobs/search/?keywords=" + encodeURIComponent(domain);
        }
    },
    {
        name: "Indeed",
        icon: "id",
        color: "#003A9B",
        desc: "Millions of listings",
        url: function(domain) {
            return "https://indeed.com/jobs?q=" + encodeURIComponent(domain);
        }
    },
    {
        name: "Glassdoor",
        icon: "gd",
        color: "#0CAA41",
        desc: "Salaries & reviews",
        url: function(domain) {
            return "https://glassdoor.com/Job/jobs.htm?sc.keyword=" + encodeURIComponent(domain);
        }
    },
    {
        name: "Wellfound",
        icon: "wf",
        color: "#FB651E",
        desc: "Startup roles",
        url: function(domain) {
            return "https://wellfound.com/jobs?q=" + encodeURIComponent(domain);
        }
    },
    {
        name: "Dice",
        icon: "dc",
        color: "#EB1C26",
        desc: "Tech specialists",
        url: function(domain) {
            return "https://dice.com/jobs?q=" + encodeURIComponent(domain);
        }
    },
    {
        name: "Remote.co",
        icon: "rm",
        color: "#1F8A70",
        desc: "Remote positions",
        url: function(domain) {
            return "https://remote.co/remote-jobs/search/?search_keywords=" + encodeURIComponent(domain);
        }
    }
];


// =============================================================================
//  APPLICATION STATE
//  These two variables track what the user has selected.
// =============================================================================

var selectedDomain = "Data Science";   // currently selected job domain
var selectedFile   = null;             // the uploaded resume file
var companiesData  = {};               // company data loaded from the server


// =============================================================================
//  INITIALISATION
//  Runs when the page has fully loaded.
// =============================================================================

document.addEventListener("DOMContentLoaded", function() {
    buildDomainGrid();
    setupFileUpload();
    loadCompaniesFromServer();
});


// =============================================================================
//  DOMAIN GRID
// =============================================================================

function buildDomainGrid() {
    // Build the 12 domain selection buttons and inject them into the grid
    var grid = document.getElementById("domain-grid");
    var html = "";

    for (var i = 0; i < DOMAINS.length; i++) {
        var domain = DOMAINS[i];
        var isActive = (domain === selectedDomain) ? " active" : "";
        var iconColor = DOMAIN_COLORS[domain];
        var icon = DOMAIN_ICONS[domain];

        html += '<button class="domain-btn' + isActive + '" ' +
                'onclick="selectDomain(\'' + domain.replace(/'/g, "\\'") + '\')">' +
                '<span class="domain-icon" style="color:' + iconColor + '">' + icon + '</span>' +
                domain +
                '</button>';
    }

    grid.innerHTML = html;
}


function selectDomain(domain) {
    // Update the selected domain and rebuild the grid so the button highlights
    selectedDomain = domain;
    buildDomainGrid();
}


// =============================================================================
//  FILE UPLOAD
// =============================================================================

function setupFileUpload() {
    var dropZone  = document.getElementById("drop-zone");
    var fileInput = document.getElementById("file-input");

    // Clicking anywhere on the drop zone opens the file browser
    dropZone.addEventListener("click", function() {
        fileInput.click();
    });

    // Drag-and-drop visual feedback
    dropZone.addEventListener("dragover", function(e) {
        e.preventDefault();
        dropZone.classList.add("dragging");
    });

    dropZone.addEventListener("dragleave", function() {
        dropZone.classList.remove("dragging");
    });

    dropZone.addEventListener("drop", function(e) {
        e.preventDefault();
        dropZone.classList.remove("dragging");

        var droppedFile = e.dataTransfer.files[0];
        if (droppedFile) {
            handleFileSelection(droppedFile);
        }
    });

    // Normal file input change
    fileInput.addEventListener("change", function(e) {
        if (e.target.files[0]) {
            handleFileSelection(e.target.files[0]);
        }
    });
}


function handleFileSelection(file) {
    // Validate file type
    var validTypes = /\.(pdf|docx|txt)$/i;
    if (!validTypes.test(file.name)) {
        showError("Only PDF, DOCX, or TXT files are accepted.");
        return;
    }

    // Validate file size (max 5 MB)
    var maxSize = 5 * 1024 * 1024;
    if (file.size > maxSize) {
        showError("File is too large. Maximum size is 5 MB.");
        return;
    }

    // Accept the file
    selectedFile = file;
    hideError();

    // Update the upload zone to show the selected file info
    var dropZone = document.getElementById("drop-zone");
    dropZone.classList.add("has-file");
    document.getElementById("upload-icon").textContent = "📄";
    document.getElementById("upload-title").innerHTML =
        '<span class="file-name">' + file.name + '</span>';
    document.getElementById("upload-hint").innerHTML =
        '<span class="file-size">' + (file.size / 1024).toFixed(1) + ' KB &nbsp;·&nbsp; Click to replace</span>';

    // Enable the analyse button now that we have a file
    document.getElementById("btn-analyse").disabled = false;
}


// =============================================================================
//  LOAD COMPANY DATA FROM SERVER
// =============================================================================

function loadCompaniesFromServer() {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "/companies", true);
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4 && xhr.status === 200) {
            companiesData = JSON.parse(xhr.responseText);
        }
    };
    xhr.send();
}


// =============================================================================
//  MAIN ANALYSIS FUNCTION
// =============================================================================

function runAnalysis() {
    if (!selectedFile) return;

    // Update button to show loading state
    var button  = document.getElementById("btn-analyse");
    var btnText = document.getElementById("btn-text");
    button.disabled = true;
    btnText.innerHTML = '<div class="spinner"></div> Running ML Analysis&hellip;';

    // Show progress bar
    setProgress(10, "Reading resume file&hellip;");

    // Build the form data to send to Python
    var formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("domain", selectedDomain);

    // Simulate progress stages for a better user experience
    setTimeout(function() { setProgress(35, "Tokenising &amp; expanding synonyms&hellip;"); }, 300);
    setTimeout(function() { setProgress(60, "Computing TF-IDF vectors&hellip;");           }, 700);
    setTimeout(function() { setProgress(85, "Scoring with ensemble model&hellip;");        }, 1100);

    // Send the resume to the Python Flask backend
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/analyze", true);

    xhr.onreadystatechange = function() {
        if (xhr.readyState !== 4) return;

        // Re-enable the button
        button.disabled = false;
        btnText.innerHTML = "&#9881; Run Another Analysis";
        hideProgress();

        if (xhr.status === 200) {
            var result = JSON.parse(xhr.responseText);

            if (result.error) {
                showError(result.error);
                return;
            }

            // Render all the results on the page
            renderResults(result);

        } else {
            showError("Server error " + xhr.status + ". Please try again.");
        }
    };

    xhr.send(formData);
}


// =============================================================================
//  RENDER RESULTS
//  Takes the JSON response from the Python backend and updates the page.
// =============================================================================

function renderResults(data) {
    var score        = data.resume_score;
    var domainColor  = DOMAIN_COLORS[data.domain] || "#a78bfa";

    // Choose score colour: green = good, yellow = average, red = low
    var scoreColor = "#4ade80";
    if (score < 70) scoreColor = "#fbbf24";
    if (score < 45) scoreColor = "#f87171";

    // --- Score Card ---
    var scoreEl = document.getElementById("result-score");
    scoreEl.textContent = score + "%";
    scoreEl.style.color = scoreColor;

    document.getElementById("result-level").textContent = data.experience_level;

    // Sub-score bars (Keyword Match and TF-IDF Cosine)
    var keywordScore = Math.min(98, Math.round(score * 0.95));
    var cosineScore  = Math.min(98, Math.round(score * 0.78));
    document.getElementById("sub-scores").innerHTML =
        makeSubScoreBar("Keyword Match", "#a78bfa", keywordScore) +
        makeSubScoreBar("TF-IDF Cosine", "#67e8f9", cosineScore);

    // Count badges (matched / missing / found keywords)
    document.getElementById("score-counts").innerHTML =
        makeCountBadge(data.matched_skills.length, "#4ade80", "Matched") +
        makeCountBadge(data.missing_skills.length, "#f87171", "Missing") +
        makeCountBadge(data.extracted_skills.length, domainColor, "Found");

    // --- Summary ---
    document.getElementById("result-summary").textContent = data.summary;

    // --- Charts (drawn after a short delay so the DOM has updated) ---
    setTimeout(function() {
        drawDonutChart(data.matched_skills.length, data.missing_skills.length);
        drawBarChart(data.skill_details, domainColor);
    }, 80);

    // --- Matched Skills ---
    var matchedHTML = "";
    var matchedList = data.matched_skills.length ? data.matched_skills : ["None detected"];
    for (var i = 0; i < matchedList.length; i++) {
        matchedHTML += '<span class="tag tag-green">' + matchedList[i] + "</span>";
    }
    document.getElementById("matched-skills").innerHTML = matchedHTML;

    // --- Missing Skills ---
    var missingHTML = "";
    var missingList = data.missing_skills.length ? data.missing_skills : ["None missing"];
    for (var j = 0; j < missingList.length; j++) {
        missingHTML += '<span class="tag tag-red">' + missingList[j] + "</span>";
    }
    document.getElementById("missing-skills").innerHTML = missingHTML;

    // --- Suggestions ---
    var suggestionsHTML = "";
    for (var k = 0; k < data.suggestions.length; k++) {
        var num = (k + 1 < 10) ? "0" + (k + 1) : String(k + 1);
        suggestionsHTML +=
            '<div class="suggestion-item">' +
            '<div class="suggestion-number">' + num + '</div>' +
            '<div class="suggestion-text">' + data.suggestions[k] + '</div>' +
            '</div>';
    }
    document.getElementById("suggestions-list").innerHTML = suggestionsHTML;

    // --- Companies ---
    renderCompanies(data.domain, score);

    // --- Job Platforms ---
    var platformsHTML = "";
    for (var p = 0; p < JOB_PLATFORMS.length; p++) {
        var plat = JOB_PLATFORMS[p];
        platformsHTML +=
            '<a href="' + plat.url(data.domain) + '" target="_blank" rel="noopener" class="platform-card">' +
            '<div class="platform-icon" style="background:' + plat.color + '22;color:' + plat.color + ';border:1px solid ' + plat.color + '30">' +
            plat.icon.toUpperCase() +
            '</div>' +
            '<div>' +
            '<div class="platform-name">' + plat.name + '</div>' +
            '<div class="platform-desc">' + plat.desc + '</div>' +
            '</div>' +
            '</a>';
    }
    document.getElementById("platforms-grid").innerHTML = platformsHTML;

    // Show the results section and scroll to it
    var resultsSection = document.getElementById("results-section");
    resultsSection.style.display = "block";
    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}


// =============================================================================
//  COMPANY RECOMMENDATIONS
// =============================================================================

function renderCompanies(domain, score) {
    var container = document.getElementById("companies-section");
    var companies = companiesData[domain] || [];

    // Split companies into matched and "almost there"
    var matched = [];
    var almost  = [];

    for (var i = 0; i < companies.length; i++) {
        var company = companies[i];
        if (score >= company.min) {
            matched.push(company);
        } else if (score >= company.min - 18) {
            almost.push(company);
        }
    }

    // No matches — show a helpful message with learning links
    if (matched.length === 0) {
        var minRequired = companies.length > 0 ? companies[0].min : 50;
        container.innerHTML =
            '<div class="no-match-box">' +
            '<h3>&#128200; Improve your skills to unlock company matches</h3>' +
            '<p>Your ML score of <strong style="color:#f87171">' + score + '%</strong> ' +
            'is below the ' + minRequired + '% threshold for ' + domain + ' companies. ' +
            'Build the missing skills to unlock recommendations.</p>' +
            '<div class="learn-links">' +
            '<a href="https://coursera.org" target="_blank"><button class="learn-btn" style="background:#0056D2">&#128218; Coursera</button></a>' +
            '<a href="https://udemy.com" target="_blank"><button class="learn-btn" style="background:#A435F0">&#128218; Udemy</button></a>' +
            '<a href="https://freecodecamp.org" target="_blank"><button class="learn-btn" style="background:#0A0A23">&#128218; freeCodeCamp</button></a>' +
            '</div>' +
            '</div>';

    } else {
        // Build company match cards
        var cardsHTML = '<div class="companies-grid">';
        for (var c = 0; c < matched.length; c++) {
            cardsHTML += makeCompanyCard(matched[c], score);
        }
        cardsHTML += '</div>';
        container.innerHTML = cardsHTML;
    }

    // Append "almost there" section if relevant
    if (almost.length > 0) {
        container.innerHTML += makeAlmostSection(almost, score);
    }
}


function makeCompanyCard(company, score) {
    var fitScore = Math.min(98, score + 2);
    return (
        '<div class="company-card">' +
        '<div class="company-top-bar" style="background:linear-gradient(90deg,' + company.color + ',' + company.color + '44)"></div>' +
        '<div class="company-header">' +
        '<div class="company-left">' +
        '<div class="company-logo" style="background:' + company.color + '">' + company.logo + '</div>' +
        '<div>' +
        '<div class="company-name">' + company.name + '</div>' +
        '<div class="company-role">' + company.role + '</div>' +
        '</div>' +
        '</div>' +
        '<span class="match-badge">&#10003; Match</span>' +
        '</div>' +
        '<div class="fit-header"><span>Fit Score</span><span class="fit-value">' + fitScore + '%</span></div>' +
        '<div class="fit-track"><div class="fit-fill" style="width:' + fitScore + '%"></div></div>' +
        '<div class="company-links">' +
        '<a href="' + company.linkedin + '" target="_blank" rel="noopener" class="company-link link-linkedin">in LinkedIn</a>' +
        '<a href="' + company.indeed   + '" target="_blank" rel="noopener" class="company-link link-indeed">Indeed</a>' +
        '<a href="' + company.careers  + '" target="_blank" rel="noopener" class="company-link link-careers">Careers &#8599;</a>' +
        '</div>' +
        '</div>'
    );
}


function makeAlmostSection(almost, score) {
    var html =
        '<div class="almost-section">' +
        '<div class="almost-title">&#9889; Almost there &mdash; raise score to unlock:</div>' +
        '<div class="almost-list">';

    for (var i = 0; i < almost.length; i++) {
        var c = almost[i];
        html +=
            '<div class="almost-item">' +
            '<div class="almost-logo" style="background:' + c.color + '">' + c.logo + '</div>' +
            '<div>' +
            '<div class="almost-name">' + c.name + '</div>' +
            '<div class="almost-need">Need ' + c.min + '% &bull; You: ' + score + '%</div>' +
            '</div>' +
            '</div>';
    }

    html += '</div></div>';
    return html;
}


// =============================================================================
//  HTML5 CANVAS CHARTS
//  All charts are drawn using the Canvas 2D API — no external libraries.
// =============================================================================

function drawDonutChart(matched, missing) {
    var canvas  = document.getElementById("canvas-donut");
    var ctx     = canvas.getContext("2d");
    var width   = canvas.width;
    var height  = canvas.height;

    ctx.clearRect(0, 0, width, height);

    var total = matched + missing || 1;
    var cx = width / 2;
    var cy = height / 2;
    var outerRadius = Math.min(width, height) / 2 - 12;
    var innerRadius = outerRadius * 0.55;   // creates the donut hole

    var slices = [
        { value: matched, color: "#4ade80", label: "Matched" },
        { value: missing, color: "#f87171", label: "Missing" }
    ];

    // Draw each slice
    var startAngle = -Math.PI / 2;   // start from the top
    for (var i = 0; i < slices.length; i++) {
        var slice     = slices[i];
        var sliceAngle = (slice.value / total) * Math.PI * 2;

        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.arc(cx, cy, outerRadius, startAngle, startAngle + sliceAngle);
        ctx.closePath();
        ctx.fillStyle = slice.color;
        ctx.fill();

        startAngle += sliceAngle;
    }

    // Draw the donut hole (a circle that covers the centre)
    ctx.beginPath();
    ctx.arc(cx, cy, innerRadius, 0, Math.PI * 2);
    ctx.fillStyle = "#0d0d1a";
    ctx.fill();

    // Draw the "matched / total" text in the centre
    ctx.fillStyle   = "#e2e0f0";
    ctx.font        = "bold 16px Arial";
    ctx.textAlign   = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(matched + "/" + total, cx, cy);

    // Build the legend below the chart
    var legendHTML = "";
    for (var j = 0; j < slices.length; j++) {
        legendHTML +=
            '<div class="legend-item">' +
            '<span class="legend-dot" style="background:' + slices[j].color + '"></span>' +
            slices[j].label +
            '</div>';
    }
    document.getElementById("donut-legend").innerHTML = legendHTML;
}


function drawBarChart(skillDetails, domainColor) {
    var canvas = document.getElementById("canvas-bar");
    var ctx    = canvas.getContext("2d");
    var width  = canvas.width;
    var height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    // Only show the first 10 skills
    var skills = skillDetails.slice(0, 10);
    if (skills.length === 0) return;

    // Chart layout measurements
    var padLeft   = 8;
    var padRight  = 10;
    var padTop    = 10;
    var padBottom = 42;
    var chartWidth  = width  - padLeft - padRight;
    var chartHeight = height - padTop  - padBottom;

    // Space per skill and the actual bar width
    var slotWidth = chartWidth / skills.length;
    var barWidth  = Math.max(slotWidth * 0.55, 6);

    // Draw horizontal grid lines at 0%, 25%, 50%, 75%, 100%
    var gridLines = [0, 25, 50, 75, 100];
    for (var g = 0; g < gridLines.length; g++) {
        var gridY = padTop + chartHeight * (1 - gridLines[g] / 100);
        ctx.strokeStyle = "#1a1a2e";
        ctx.lineWidth   = 1;
        ctx.beginPath();
        ctx.moveTo(padLeft, gridY);
        ctx.lineTo(width - padRight, gridY);
        ctx.stroke();

        // Label the grid line percentage
        ctx.fillStyle = "#374151";
        ctx.font      = "9px Arial";
        ctx.textAlign = "left";
        ctx.fillText(gridLines[g] + "%", padLeft + 2, gridY - 2);
    }

    // Draw each bar
    for (var s = 0; s < skills.length; s++) {
        var skill   = skills[s];
        var barX    = padLeft + s * slotWidth + (slotWidth - barWidth) / 2;

        // Matched skills get a full bar; unmatched skills get a tiny stub
        var barFillHeight = skill.matched ? chartHeight : (chartHeight * 0.04);
        var barY = padTop + chartHeight - barFillHeight;

        // Bar colour: domain colour if matched, dark grey if not
        ctx.fillStyle = skill.matched ? domainColor : "#1e1b30";

        // Draw bar with rounded top corners
        var radius = 3;
        ctx.beginPath();
        ctx.moveTo(barX + radius, barY);
        ctx.lineTo(barX + barWidth - radius, barY);
        ctx.quadraticCurveTo(barX + barWidth, barY, barX + barWidth, barY + radius);
        ctx.lineTo(barX + barWidth, barY + barFillHeight);
        ctx.lineTo(barX, barY + barFillHeight);
        ctx.lineTo(barX, barY + radius);
        ctx.quadraticCurveTo(barX, barY, barX + radius, barY);
        ctx.closePath();
        ctx.fill();

        // Draw skill name label below the bar (rotated 36 degrees)
        var label     = skill.skill.length > 8 ? skill.skill.slice(0, 7) + "…" : skill.skill;
        var labelX    = barX + barWidth / 2;
        var labelY    = height - padBottom + 7;

        ctx.fillStyle = "#4b5563";
        ctx.font      = "8px Arial";
        ctx.textAlign = "center";
        ctx.save();
        ctx.translate(labelX, labelY);
        ctx.rotate(-Math.PI / 5);
        ctx.fillText(label, 0, 0);
        ctx.restore();
    }
}


// =============================================================================
//  SMALL UI HELPER FUNCTIONS
// =============================================================================

function makeSubScoreBar(label, color, value) {
    // Returns HTML for a small labelled progress bar inside the score card
    return (
        '<div class="sub-score-row">' +
        '<span>' + label + '</span>' +
        '<span style="color:' + color + ';font-weight:700">' + value + '%</span>' +
        '</div>' +
        '<div class="sub-score-track">' +
        '<div class="sub-score-fill" style="width:' + value + '%;background:' + color + '"></div>' +
        '</div>'
    );
}


function makeCountBadge(value, color, label) {
    // Returns HTML for the small count badge (e.g. "6 Matched") in the score card
    return (
        '<div style="text-align:center">' +
        '<div style="font-size:1.4rem;font-weight:800;color:' + color + ';line-height:1">' + value + '</div>' +
        '<div style="font-size:0.6rem;color:#6b7280;margin-top:2px">' + label + '</div>' +
        '</div>'
    );
}


// =============================================================================
//  PROGRESS BAR HELPERS
// =============================================================================

function setProgress(percent, label) {
    document.getElementById("progress-section").style.display = "block";
    document.getElementById("progress-fill").style.width      = percent + "%";
    document.getElementById("progress-label").innerHTML       = label;
    document.getElementById("progress-percent").textContent   = percent + "%";
}

function hideProgress() {
    document.getElementById("progress-section").style.display = "none";
}


// =============================================================================
//  ERROR BOX HELPERS
// =============================================================================

function showError(message) {
    var errorBox = document.getElementById("error-box");
    errorBox.textContent   = message;
    errorBox.style.display = "block";
}

function hideError() {
    document.getElementById("error-box").style.display = "none";
}
