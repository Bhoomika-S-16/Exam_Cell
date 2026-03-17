/**
 * EXAM ATTENDANCE SYSTEM - Frontend Application Logic
 * Handles admin dashboard, exam management, and invigilator attendance submission
 */
const DISABLE_BACKEND = false;
const API_BASE = window.APP_CONFIG ? window.APP_CONFIG.getApiBase() : `${window.location.protocol}//${window.location.hostname}:8000/api`;
let currentPage = null;
let currentHall = null;
let selectedAbsents = new Set();
let dashboardRefreshInterval = null;
let lastDashboardData = null;

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener("DOMContentLoaded", () => {
    const path = window.location.pathname;

    // Role-Based Access Control
    if (path.includes("admin.html") || path.endsWith("/admin")) {
        initAdminPage();
    } else if (path.includes("invigilator.html")) {
        // Invigilator is standalone
        initInvigilatorPage();
    } else if (path.includes("lookup.html")) {
        // Student page - handled by seat_finder.js
    }
});

// ============================================================================
// ADMIN PAGE FUNCTIONS
// ============================================================================

function initAdminPage() {
    // Set today's date as default
    const today = new Date().toISOString().split("T")[0];
    const dateInput = document.getElementById("examDate");
    if (dateInput) {
        dateInput.value = today;
    }

    // Setup logout button (if present)
    const logoutBtn = document.getElementById("logoutBtn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", logout);
    }

    // Check for existing session
    checkSessionStatus();
}

async function checkSessionStatus() {
    try {
        const response = await fetch(`${API_BASE}/admin/status`);

        if (!response.ok) return;

        const data = await response.json();
        if (data.is_created) {
            restoreSessionUI(data);
        }
    } catch (error) {
        console.error("Session check error:", error);
    }
}

function restoreSessionUI(status) {
    // Show sections if exam created
    document.getElementById("seatingSection").classList.remove("hidden");

    // Update session selectors based on exam type
    updateSessionSelectors(status.exam_type);

    if (status.seating_loaded) {
        document.getElementById("dashboardSection").classList.remove("hidden");
        document.getElementById("reportsSection").classList.remove("hidden");
        document.getElementById("finalizeSection").classList.remove("hidden");
        document.getElementById("deptMonitorSection").classList.remove("hidden");

        // Initial refresh
        refreshDashboard();
        if (!dashboardRefreshInterval) {
            dashboardRefreshInterval = setInterval(refreshDashboard, 5000);
        }
    }

    if (status.is_finalized) {
        const finalizeBtn = document.getElementById("finalizeBtn");
        if (finalizeBtn) {
            finalizeBtn.disabled = true;
            finalizeBtn.textContent = "✓ Finalized";
        }
        const resetBtn = document.getElementById("resetNewExamBtn");
        if (resetBtn) resetBtn.classList.remove("hidden");
    }

    // Update Status Badge
    const badge = document.getElementById("examStatusBadge");
    if (badge) {
        badge.classList.remove("hidden", "live", "finalized");
        if (status.is_finalized) {
            badge.textContent = "Finalized";
            badge.classList.add("finalized");
        } else {
            badge.textContent = "Live";
            badge.classList.add("live");
        }
    }
}

function updateSessionSelectors(examType) {
    const ciaGroup = document.getElementById("ciaUploadGroup");
    const modelGroup = document.getElementById("modelUploadGroup");
    const dashSel = document.getElementById("dashboardSession");
    const reportSel = document.getElementById("reportSession");

    if (!ciaGroup || !modelGroup || !dashSel || !reportSel) return;

    // Toggle Seating Upload Groups (use classList since they start with 'hidden' class which uses !important)
    if (examType === "CIA") {
        ciaGroup.classList.remove("hidden");
        modelGroup.classList.add("hidden");
    } else {
        ciaGroup.classList.add("hidden");
        modelGroup.classList.remove("hidden");
    }

    let options = [];
    if (examType === "CIA") {
        options = [
            { val: "FN", label: "Forenoon (FN)" },
            { val: "AN", label: "Afternoon (AN)" }
        ];
    } else {
        options = [
            { val: "MODEL", label: "Model Session" }
        ];
    }

    [dashSel, reportSel].forEach(sel => {
        const currentVal = sel.value;
        sel.innerHTML = options.map(o => `<option value="${o.val}">${o.label}</option>`).join("");
        if (currentVal && options.find(o => o.val === currentVal)) {
            sel.value = currentVal;
        }
    });

    if (!dashSel.value && options.length > 0) {
        dashSel.value = options[0].val;
    }
}

function handleExamTypeChange() {
    const examType = document.getElementById("examType").value;
    if (examType) {
        updateSessionSelectors(examType);
    }
}

async function createExam() {
    const date = document.getElementById("examDate").value;
    const examType = document.getElementById("examType").value;

    if (!date) {
        showMessage("examStatus", "Please select a date", "error");
        return;
    }

    if (!examType) {
        showMessage("examStatus", "Please select exam type", "error");
        return;
    }

    try {
        const params = new URLSearchParams({
            date: date,
            exam_type: examType
        });

        const response = await fetch(`${API_BASE}/admin/exam/create`, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            },
            body: params.toString()
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Failed to create exam");
        }

        showMessage("examStatus", "✓ Exam created successfully!", "success");

        // Update UI for the next step
        updateSessionSelectors(examType);

        // Show next sections
        setTimeout(() => {
            document.getElementById("seatingSection").classList.remove("hidden");
        }, 500);
    } catch (error) {
        showMessage("examStatus", `Error: ${error.message}`, "error");
    }
}

async function uploadSeatingPlan() {
    const ciaGroup = document.getElementById("ciaUploadGroup");
    const isCIA = ciaGroup && !ciaGroup.classList.contains("hidden");

    let uploads = [];
    if (isCIA) {
        const fileFN = document.getElementById("seatingFileFN").files[0];
        const fileAN = document.getElementById("seatingFileAN").files[0];
        if (fileFN) uploads.push({ file: fileFN, session: "FN" });
        if (fileAN) uploads.push({ file: fileAN, session: "AN" });
    } else {
        const fileMODEL = document.getElementById("seatingFileMODEL").files[0];
        if (fileMODEL) uploads.push({ file: fileMODEL, session: "MODEL" });
    }

    if (uploads.length === 0) {
        showMessage("uploadStatus", "Please select at least one file to upload", "error");
        return;
    }

    showMessage("uploadStatus", `⏳ Uploading ${uploads.length} session(s)...`, "info");

    try {
        for (const item of uploads) {
            const formData = new FormData();
            formData.append("file", item.file);
            formData.append("session", item.session);

            const response = await fetch(`${API_BASE}/admin/seating-plan/upload`, {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(`[${item.session}] ${error.detail || "Upload failed"}`);
            }
        }

        showMessage("uploadStatus", `✓ Seating plan(s) uploaded successfully!`, "success");

        // Show dashboard and reports
        setTimeout(() => {
            document.getElementById("dashboardSection").classList.remove("hidden");
            document.getElementById("reportsSection").classList.remove("hidden");
            document.getElementById("finalizeSection").classList.remove("hidden");
            document.getElementById("deptMonitorSection").classList.remove("hidden");

            // Start auto-refresh
            refreshDashboard();
            if (!dashboardRefreshInterval) {
                dashboardRefreshInterval = setInterval(refreshDashboard, 5000);
            }

            // Load classes for report selection
            loadClasses();
        }, 500);
    } catch (error) {
        showMessage("uploadStatus", `Error: ${error.message}`, "error");
    }
}

async function refreshDashboard() {
    const session = document.getElementById("dashboardSession")?.value || "";
    try {
        const response = await fetch(`${API_BASE}/admin/dashboard?session=${session}`);

        if (!response.ok) return;

        const data = await response.json();
        const tbody = document.getElementById("dashboardTable");
        tbody.innerHTML = "";

        // Build table rows
        data.halls.forEach(hall => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${hall.hall_number}</td>
                <td>${hall.total_students}</td>
                <td>${hall.present_count}</td>
                <td>${hall.absent_count}</td>
                <td>${hall.submitted ? '<span style="color: green; font-weight: bold;">✓ Submitted</span>' : '<span style="color: orange;">Pending</span>'}</td>
                <td>${hall.faculty_name || '-'}</td>
                <td>${hall.submission_time ? formatDateTime(hall.submission_time) : '-'}</td>
            `;
        });

        // Update summary
        const statusEl = document.getElementById("allSubmittedStatus");
        if (data.summary.all_submitted) {
            statusEl.textContent = "✓ All Halls Submitted";
            statusEl.style.color = "#27ae60";
        } else {
            statusEl.textContent = `${data.summary.submitted_halls}/${data.summary.total_halls} halls submitted`;
            statusEl.style.color = "#f39c12";
        }

        // Store data for department monitor and update it
        lastDashboardData = data;
        updateDeptSelect(data.departments);
        updateDeptMonitor();
    } catch (error) {
        console.error("Dashboard refresh error:", error);
    }
}

function updateDeptSelect(deptStats) {
    const sel = document.getElementById("deptSelect");
    if (!sel || !deptStats) return;

    const currentVal = sel.value;
    const depts = Object.keys(deptStats).sort();

    // Only rebuild if the list has changed
    const existingOptions = Array.from(sel.options).map(o => o.value).filter(v => v);
    if (JSON.stringify(existingOptions) === JSON.stringify(depts)) return;

    sel.innerHTML = '<option value="">-- Select Department --</option>';
    depts.forEach(d => {
        const opt = document.createElement("option");
        opt.value = d;
        opt.textContent = d;
        sel.appendChild(opt);
    });
    sel.value = currentVal;
}

function updateDeptMonitor() {
    const section = document.getElementById("deptMonitorSection");
    if (section) {
        section.classList.remove("hidden");
    }

    const sel = document.getElementById("deptSelect");
    const tbody = document.getElementById("deptTable");
    if (!sel || !tbody || !lastDashboardData) return;

    const dept = sel.value;
    if (!dept) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">Select a department to see data</td></tr>';
        return;
    }

    const stats = lastDashboardData.departments[dept];
    if (!stats) return;

    tbody.innerHTML = "";
    // Sorted years: I, II, III
    const years = ["I", "II", "III"].filter(y => stats[y]);
    // Add any other years found
    Object.keys(stats).forEach(y => {
        if (!years.includes(y)) years.push(y);
    });

    years.forEach(year => {
        const s = stats[year];
        const row = tbody.insertRow();
        const percent = s.total > 0 ? Math.round((s.present / s.total) * 100) : 0;
        const statusClass = s.absent > 0 ? 'style="color: #e67e22;"' : (s.present > 0 ? 'style="color: #27ae60; font-weight: bold;"' : '');

        row.innerHTML = `
            <td>Year ${year}</td>
            <td>${s.total}</td>
            <td>${s.present}</td>
            <td>${s.absent}</td>
            <td ${statusClass}>
                ${percent}% Present
            <br>
            <button class="btn btn-small" onclick="viewAbsentees('${dept}', '${year}')">
            View Absentees
            </button>
            </td> `;
    });
}
async function viewAbsentees(department, year) {
    const session = document.getElementById("dashboardSession").value;
    const section = document.getElementById("absenteesSection");
    const tbody = document.getElementById("absenteesTable");

    // Update section heading to show which dept/year is shown
    const heading = section.querySelector("h2");
    if (heading) heading.textContent = `Absent Students — ${department} Year ${year}`;

    try {
        const url = `${API_BASE}/admin/absentees?department=${encodeURIComponent(department)}&year=${encodeURIComponent(year)}&session=${encodeURIComponent(session)}`;
        const response = await fetch(url);

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Server error ${response.status}`);
        }

        const data = await response.json();
        tbody.innerHTML = "";

        if (!data.absentees || data.absentees.length === 0) {
            tbody.innerHTML =
                `<tr><td colspan="5" class="text-center text-slate-500 italic p-5">No absentees for ${department} Year ${year}</td></tr>`;
        } else {
            data.absentees.forEach(s => {
                const row = tbody.insertRow();
                row.innerHTML = `
                    <td class="p-3">${s.register_number}</td>
                    <td class="p-3">${s.student_name}</td>
                    <td class="p-3">${year}</td>
                    <td class="p-3">${s.hall_number}</td>
                    <td class="p-3">${s.seat_number}</td>
                `;
            });
        }

        // Use classList.remove instead of style.display to overcome !important hidden CSS
        section.classList.remove("hidden");
        section.scrollIntoView({ behavior: "smooth" });

    } catch (err) {
        console.error("viewAbsentees error:", err);
        alert(`Failed to load absentees: ${err.message}`);
    }
}

async function loadClasses() {
    const session = document.getElementById("reportSession")?.value;
    if (!session) return;

    try {
        const response = await fetch(`${API_BASE}/admin/classes?session=${session}`);

        if (!response.ok) return;

        const data = await response.json();
        const sel = document.getElementById("classSelect");
        if (!sel) return;

        sel.innerHTML = '<option value="">-- Select Class --</option>';
        data.classes.forEach(cls => {
            const opt = document.createElement("option");
            opt.value = cls;
            opt.textContent = cls;
            sel.appendChild(opt);
        });
    } catch (error) {
        console.error("Error loading classes:", error);
    }
}

async function downloadReport(reportType, format) {
    const session = document.getElementById("reportSession").value;
    try {
        let endpoint = format === "pdf"
            ? `/admin/reports/pdf?report_type=${reportType}&session=${session}`
            : `/admin/reports/excel?report_type=${reportType}&session=${session}`;

        if (reportType === "class") {
            const cls = document.getElementById("classSelect").value;
            if (!cls) {
                alert("Please select a class first.");
                return;
            }
            endpoint += `&filter_value=${encodeURIComponent(cls)}`;
        }

        const response = await fetch(`${API_BASE}${endpoint}`);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Failed to generate report");
        }

        // Get filename from header or create one
        const disposition = response.headers.get("content-disposition");
        let filename = `report.${format === "pdf" ? "pdf" : "xlsx"}`;
        if (disposition) {
            const match = disposition.match(/filename="([^"]+)"/);
            if (match) filename = match[1];
        }

        // Download file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

async function finalizeExam() {
    if (!confirm("⚠️ Are you sure? This will lock all further submissions and cannot be undone.")) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/admin/exam/finalize`, {
            method: "POST"
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Failed to finalize exam");
        }

        // Stop refreshing and show success
        clearInterval(dashboardRefreshInterval);
        const finalizeBtn = document.getElementById("finalizeBtn");
        if (finalizeBtn) {
            finalizeBtn.disabled = true;
            finalizeBtn.textContent = "✓ Finalized";
        }
        alert("✓ Exam finalized successfully! No further submissions will be accepted.");

        // Show "Start New Exam" button
        const resetBtn = document.getElementById("resetNewExamBtn");
        if (resetBtn) resetBtn.classList.remove("hidden");
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}

async function startNewExam() {
    if (!confirm("⚠️ This will WIPE the current finalized data and start a new exam. Are you sure?")) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/admin/exam/reset`, {
            method: "POST"
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Failed to reset exam");
        }

        // Redirect back or refresh to start fresh
        location.reload();
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
}


async function logout() {
    if (confirm("Are you sure you want to logout?")) {
        const token = sessionStorage.getItem('auth_token');
        try {
            await fetch(`${API_BASE}/auth/logout`, {
                method: 'POST',
                headers: { 'X-Auth-Token': token || '' }
            });
        } catch (e) { }
        sessionStorage.removeItem('auth_token');
        sessionStorage.removeItem('auth_role');
        window.location.href = '/login';
    }
}

// ============================================================================
// INVIGILATOR PAGE FUNCTIONS
// ============================================================================

async function initInvigilatorPage() {
    try {
        const response = await fetch(`${API_BASE}/invigilator/halls`);

        if (!response.ok) {
            showMessage("selectionStatus", "No active exam. Please contact admin.", "error");
            return;
        }

        const data = await response.json();
        const hallSelect = document.getElementById("hallSelect");

        // Disable halls that are already submitted
        if (data.submitted_halls && data.submitted_halls.length > 0) {
            const submittedSet = new Set(data.submitted_halls);
            Array.from(hallSelect.options).forEach(option => {
                if (submittedSet.has(option.value)) {
                    option.disabled = true;
                    option.textContent += " (Submitted)";
                }
            });
        }

        // Show exam info
        let examStr = "Exam active";
        const examInfo = document.getElementById("examInfo");
        const examInfoText = document.getElementById("examInfoText");
        if (examInfo && examInfoText) {
            examStr = `Exam: ${data.exam.date} - ${data.exam.type}`;
            if (data.exam.session) {
                examStr += ` (${data.exam.session})`;
            }
            examInfoText.textContent = examStr;
            examInfo.style.display = "block";
        }

        showMessage("selectionStatus", examStr, "info");
    } catch (error) {
        showMessage("selectionStatus", `Error: ${error.message}`, "error");
    }
}

async function loadHallStudents() {
    currentHall = document.getElementById("hallSelect").value;

    if (!currentHall) {
        document.getElementById("attendanceSection").style.display = "none";
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/invigilator/students/${currentHall}`);

        if (!response.ok) {
            throw new Error("Failed to load students");
        }

        const data = await response.json();
        const tbody = document.getElementById("studentsTable");
        tbody.innerHTML = "";
        selectedAbsents = new Set();

        // Build student rows
        data.students.forEach(student => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${student.seat_number}</td>
                <td>${student.roll_number}</td>
                <td>${student.register_number}</td>
                <td>${student.student_name}</td>
                <td><input type="checkbox" data-reg="${student.register_number}" 
                           onchange="toggleAbsent(this)"></td>
            `;
        });

        // Update counts
        document.getElementById("totalCount").textContent = data.students.length;
        document.getElementById("absentCount").textContent = "0";
        document.getElementById("hallDisplay").textContent = currentHall;

        // Don't show attendance section until explicitly clicked
    } catch (error) {
        showMessage("selectionStatus", `Error: ${error.message}`, "error");
    }
}

function proceedToAttendance() {
    const facultyName = document.getElementById("facultyName").value.trim();

    if (!facultyName) {
        showMessage("selectionStatus", "Please enter your name", "error");
        return;
    }

    if (!currentHall) {
        showMessage("selectionStatus", "Please select a hall", "error");
        return;
    }

    document.getElementById("selectionSection").style.display = "none";
    document.getElementById("attendanceSection").style.display = "block";

    // Scroll to attendance section
    document.getElementById("attendanceSection").scrollIntoView({ behavior: "smooth" });
}

function toggleAbsent(checkbox) {
    const regNum = checkbox.dataset.reg;
    if (checkbox.checked) {
        selectedAbsents.add(regNum);
    } else {
        selectedAbsents.delete(regNum);
    }

    // Update counter
    document.getElementById("absentCount").textContent = selectedAbsents.size;
}

function selectAll() {
    document.querySelectorAll("#studentsTable input[type='checkbox']").forEach(cb => {
        cb.checked = true;
        toggleAbsent(cb);
    });
}

function selectNone() {
    document.querySelectorAll("#studentsTable input[type='checkbox']").forEach(cb => {
        cb.checked = false;
        toggleAbsent(cb);
    });
}

async function submitAttendance() {
    const facultyName = document.getElementById("facultyName").value.trim();

    if (!facultyName) {
        showMessage("submissionStatus", "Faculty name is required", "error");
        return;
    }

    if (!currentHall) {
        showMessage("submissionStatus", "Hall is not selected", "error");
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/invigilator/attendance/submit`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                hall_number: currentHall,
                faculty_name: facultyName,
                absent_register_numbers: Array.from(selectedAbsents)
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Submission failed");
        }

        const data = await response.json();

        // Show success
        document.getElementById("attendanceSection").style.display = "none";
        document.getElementById("selectionSection").style.display = "none";
        document.getElementById("successSection").style.display = "block";

        const details = document.getElementById("successDetails");
        details.innerHTML = `
            <p><strong>Hall:</strong> ${data.hall_number}</p>
            <p><strong>Faculty:</strong> ${data.faculty_name}</p>
            <p><strong>Total Students:</strong> ${data.total_students}</p>
            <p><strong>Present:</strong> ${data.present_count}</p>
            <p><strong>Absent:</strong> ${data.absent_count}</p>
            <p><strong>Submitted At:</strong> ${formatDateTime(data.submitted_at)}</p>
        `;

        // Scroll to success section
        document.getElementById("successSection").scrollIntoView({ behavior: "smooth" });
    } catch (error) {
        showMessage("submissionStatus", `Error: ${error.message}`, "error");
    }
}

function goBackToSelection() {
    document.getElementById("attendanceSection").style.display = "none";
    document.getElementById("selectionSection").style.display = "block";
}

function resetForm() {
    document.getElementById("facultyName").value = "";
    document.getElementById("hallSelect").value = "";
    selectedAbsents = new Set();

    document.getElementById("attendanceSection").style.display = "none";
    document.getElementById("selectionSection").style.display = "block";
    document.getElementById("successSection").style.display = "none";

    // Scroll to top
    document.getElementById("selectionSection").scrollIntoView({ behavior: "smooth" });
}

function dismissError() {
    document.getElementById("errorSection").style.display = "none";
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function showMessage(elementId, message, type) {
    const el = document.getElementById(elementId);
    if (!el) return;

    el.textContent = message;
    el.className = `status-message ${type}`;
    el.style.display = "block";

    // Auto-hide success messages after 5 seconds
    if (type === "success") {
        setTimeout(() => {
            el.style.display = "none";
        }, 5000);
    }
}

function formatDateTime(isoString) {
    if (!isoString) return "-";
    const date = new Date(isoString);
    return date.toLocaleString();
}

function formatDate(isoString) {
    if (!isoString) return "-";
    const date = new Date(isoString);
    return date.toLocaleDateString();
}

// ============================================================================
// ERROR HANDLING
// ============================================================================

window.addEventListener("error", (event) => {
    console.error("Global error:", event.error);
});

window.addEventListener("unhandledrejection", (event) => {
    console.error("Unhandled promise rejection:", event.reason);
});