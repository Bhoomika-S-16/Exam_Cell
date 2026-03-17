/**
 * Student Seat Finder Logic
 */

const API_BASE = window.APP_CONFIG ? window.APP_CONFIG.getApiBase() : "http://localhost:8000/api";

async function findSeat() {
    const regInput = document.getElementById("regNumber");
    const regNum = regInput.value.trim();
    const resultsDiv = document.getElementById("results");
    const errorDiv = document.getElementById("errorMsg");
    const sessionsList = document.getElementById("sessionsList");

    // Reset UI
    resultsDiv.style.display = "none";
    errorDiv.style.display = "none";
    sessionsList.innerHTML = "";

    if (!regNum) {
        showError("Please enter your Register Number.");
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/student/lookup/${encodeURIComponent(regNum)}`);

        if (!response.ok) {
            if (response.status === 404) {
                showError("Register number not found. Please check and try again.");
            } else {
                const data = await response.json();
                showError(data.detail || "An error occurred. Please try again later.");
            }
            return;
        }

        const data = await response.json();
        displayResults(data, regNum);
    } catch (error) {
        console.error("Fetch failed:", error);

        if (error instanceof TypeError) {
            showError("Unable to reach server. Possible CORS or network issue.");
        } else {
            showError("Unexpected error occurred.");
        }
    }
}

function displayResults(data, regNum) {
    const resultsDiv = document.getElementById("results");
    const sessionsList = document.getElementById("sessionsList");
    const nameEl = document.getElementById("studentName");
    const regEl = document.getElementById("studentReg");

    if (data.length === 0) {
        showError("No active seating found for this Register Number.");
        return;
    }

    // Use the name from the first found session
    nameEl.textContent = data[0].student_name;
    regEl.textContent = regNum.toUpperCase();

    sessionsList.innerHTML = data.map(sessionInfo => {
        const sessionLabel = getSessionLabel(sessionInfo.session);
        // Fallback for exam_type if not provided
        const examType = sessionInfo.exam_type || "Examination";

        return `
            <div class="session-card">
                <div class="session-title">
                    <span>${sessionLabel}</span>
                    <span class="session-badge">${examType}</span>
                </div>
                <div class="data-row">
                    <span class="data-label">Venue / Hall</span>
                    <span class="data-value">${sessionInfo.hall_number || 'N/A'}</span>
                </div>
                <div class="data-row">
                    <span class="data-label">Seat Number</span>
                    <span class="data-value">${sessionInfo.seat_number || 'N/A'}</span>
                </div>
            </div>
        `;
    }).join('');

    resultsDiv.style.display = "block";
}

function getSessionLabel(session) {
    if (session === "FN") return "Forenoon Session";
    if (session === "AN") return "Afternoon Session";
    if (session === "MODEL") return "Model Examination";
    return "Examination Session";
}

function showError(msg) {
    const errorDiv = document.getElementById("errorMsg");
    errorDiv.textContent = msg;
    errorDiv.style.display = "block";
}

// Allow pressing Enter key
document.getElementById("regNumber").addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
        findSeat();
    }
});
