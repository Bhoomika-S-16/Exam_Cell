/**
 * INVIGILATOR PORTAL — Standalone JavaScript
 * Focused only on attendance marking. Setup/Upload removed for security.
 */

const API = window.APP_CONFIG ? window.APP_CONFIG.getApiBase() : "http://localhost:8000/api";
let currentHall = null;
let absentSet = new Set();

// ─── INIT ───────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
    // Check if an exam session is already active
    checkExistingSession();
});

// ─── SESSION CHECK ───────────────────────────────────────────────────────────

async function checkExistingSession() {
    try {
        const response = await fetch(`${API}/demo/status`);
        if (!response.ok) return;
        const data = await response.json();

        // Update exam status badge in navbar
        const badge = document.getElementById("examStatusBadge");
        if (badge) {
            badge.classList.remove("hidden", "live", "finalized");
            if (data.is_finalized) {
                badge.textContent = "Finalized";
                badge.classList.add("finalized");
            } else {
                badge.textContent = "Live";
                badge.classList.add("live");
            }
            badge.classList.remove("hidden");
        }

        if (data.exam_active && data.seating_loaded) {
            // Populate exam info display
            document.getElementById("displayExamDate").textContent = data.exam.date;
            document.getElementById("displayExamType").textContent = data.exam.type;
            document.getElementById("activeExamInfo").classList.remove("hidden");
            document.getElementById("waitingState").classList.add("hidden");

            if (data.is_finalized) {
                showFinalizedMessage();
            } else {
                activateInvigilatorMode(data.exam);
            }
        } else {
            // Show waiting state if no exam or no seating
            document.getElementById("waitingState").classList.remove("hidden");
            document.getElementById("activeExamInfo").classList.add("hidden");
            document.getElementById("invigilatorPanel").classList.add("hidden");
        }
    } catch (error) {
        console.error("Failed to check session:", error);
    }
}

function showFinalizedMessage() {
    const info = document.getElementById("activeExamInfo");
    info.classList.add("hidden");

    document.getElementById("invigilatorPanel").classList.add("hidden");
    document.getElementById("waitingState").classList.add("hidden");

    // We reuse the waitingState block or just show a custom message
    const wrapper = document.querySelector(".page-wrapper");
    const msg = document.createElement("div");
    msg.className = "card";
    msg.style.textAlign = "center";
    msg.style.padding = "60px 20px";
    msg.innerHTML = `
        <div style="font-size: 48px; margin-bottom: 20px;">🔒</div>
        <h2 style="color: var(--primary); margin-bottom: 15px;">Submissions Closed</h2>
        <p style="color: var(--text-2); max-width: 400px; margin: 0 auto;">
            This examination session has been finalized by the admin. 
            New attendance submissions are no longer accepted.
        </p>
        <button class="btn btn-primary" style="margin-top: 30px;" onclick="location.reload()">Refresh Page</button>
    `;
    wrapper.appendChild(msg);
}

// ─── ACTIVATE INVIGILATOR MODE ───────────────────────────────────────────────

async function activateInvigilatorMode(exam) {
    document.getElementById("waitingState").classList.add("hidden");
    document.getElementById("invigilatorPanel").classList.remove("hidden");

    // Configure session selector based on exam type
    const hallSessionSel = document.getElementById("hallSession");
    const sessionGroup = hallSessionSel.closest(".form-group");

    if (exam.type === "CIA") {
        sessionGroup.classList.remove("hidden");
    } else {
        sessionGroup.classList.add("hidden");
        hallSessionSel.value = "MODEL";
    }

    initHalls();
}

async function initHalls() {
    absentSet = new Set();
    document.getElementById("attendanceStep").classList.add("hidden");
    document.getElementById("selectionStep").classList.remove("hidden");
    await loadHalls();
}

async function loadHalls() {
    const session = document.getElementById("hallSession")?.value || "FN";
    try {
        const res = await fetch(`${API}/invigilator/halls?session=${session}`);
        if (!res.ok) {
            showMessage("hallStatusMsg", "No active exam found for this session.", "error");
            const sel = document.getElementById("hallSelect");
            sel.innerHTML = '<option value="">— Select Hall —</option>';
            return;
        }
        const data = await res.json();
        const sel = document.getElementById("hallSelect");
        sel.innerHTML = '<option value="">— Select Hall —</option>';
        const submitted = new Set(data.submitted_halls || []);

        data.halls.forEach(h => {
            const opt = document.createElement("option");
            opt.value = h;
            opt.textContent = submitted.has(h) ? `${h} ✓ (Submitted)` : h;
            if (submitted.has(h)) opt.disabled = true;
            sel.appendChild(opt);
        });
        hideMessage("hallStatusMsg");
    } catch (e) {
        showMessage("hallStatusMsg", "Error loading halls: " + e.message, "error");
    }
}

// ─── STEP 1 — HALL SELECTION ─────────────────────────────────────────────────

function onHallChange() {
    currentHall = document.getElementById("hallSelect").value || null;
}

async function proceedToAttendance() {
    const faculty = document.getElementById("facultyName").value.trim();
    if (!faculty) {
        showMessage("hallStatusMsg", "Please enter your name before proceeding.", "error");
        return;
    }
    if (!currentHall) {
        showMessage("hallStatusMsg", "Please select a hall.", "error");
        return;
    }

    // Load students for selected hall
    const session = document.getElementById("hallSession").value;
    showMessage("hallStatusMsg", "Loading students…", "info");
    try {
        const res = await fetch(`${API}/invigilator/students/${currentHall}?session=${session}`);
        if (!res.ok) {
            const err = await res.json();
            showMessage("hallStatusMsg", err.detail || "Failed to load students.", "error");
            return;
        }
        const data = await res.json();
        renderStudents(data.students);
        document.getElementById("hallDisplay").textContent = currentHall;

        // Switch views
        document.getElementById("selectionStep").classList.add("hidden");
        document.getElementById("attendanceStep").classList.remove("hidden");
        window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
        showMessage("hallStatusMsg", "Error: " + e.message, "error");
    }
}

// ─── STEP 2 — ATTENDANCE TABLE ────────────────────────────────────────────────

function renderStudents(students) {
    absentSet = new Set();
    const tbody = document.getElementById("studentsTableBody");
    tbody.innerHTML = "";

    if (!students.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state">No students found for this hall.</td></tr>';
        return;
    }

    students.sort((a, b) => String(a.seat_number).localeCompare(String(b.seat_number), undefined, { numeric: true }));

    students.forEach(s => {
        const tr = document.createElement("tr");
        tr.dataset.reg = s.register_number;
        tr.innerHTML = `
            <td>${s.seat_number}</td>
            <td>${s.roll_number}</td>
            <td>${s.register_number}</td>
            <td>${s.student_name}</td>
            <td>${s.department}</td>
            <td>${s.year}</td>
            <td class="center">
                <input type="checkbox" data-reg="${s.register_number}"
                       onchange="toggleAbsent(this, '${s.register_number}')">
            </td>
        `;
        tbody.appendChild(tr);
    });

    document.getElementById("totalCount").textContent = students.length;
    document.getElementById("absentCount").textContent = 0;
}

function toggleAbsent(cb, reg) {
    const row = document.querySelector(`tr[data-reg="${reg}"]`);
    if (cb.checked) {
        absentSet.add(reg);
        if (row) row.classList.add("absent-row");
    } else {
        absentSet.delete(reg);
        if (row) row.classList.remove("absent-row");
    }
    document.getElementById("absentCount").textContent = absentSet.size;
}

function markAllAbsent() {
    document.querySelectorAll("#studentsTableBody input[type='checkbox']").forEach(cb => {
        cb.checked = true;
        toggleAbsent(cb, cb.dataset.reg);
    });
}

function markAllPresent() {
    document.querySelectorAll("#studentsTableBody input[type='checkbox']").forEach(cb => {
        cb.checked = false;
        toggleAbsent(cb, cb.dataset.reg);
    });
}

async function submitAttendance() {
    const faculty = document.getElementById("facultyName").value.trim();
    if (!faculty) {
        showMessage("submissionStatus", "Faculty name is missing — please go back and enter it.", "error");
        return;
    }

    const confirmMsg = absentSet.size === 0
        ? "All students marked PRESENT. Submit?"
        : `You have marked ${absentSet.size} student(s) as absent. Submit?`;

    if (!confirm(confirmMsg)) return;

    const session = document.getElementById("hallSession").value;
    showMessage("submissionStatus", "Submitting…", "info");

    try {
        const res = await fetch(`${API}/invigilator/attendance/submit`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session: session,
                hall_number: currentHall,
                faculty_name: faculty,
                absent_register_numbers: Array.from(absentSet)
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Submission failed");
        }

        const data = await res.json();
        showSuccessPanel(data);
    } catch (e) {
        showMessage("submissionStatus", "Error: " + e.message, "error");
    }
}

function goBackToSelection() {
    document.getElementById("attendanceStep").classList.add("hidden");
    document.getElementById("selectionStep").classList.remove("hidden");
    currentHall = null;
    document.getElementById("hallSelect").value = "";
    hideMessage("hallStatusMsg");
}

async function resetInvigilatorView() {
    document.getElementById("successPanel").classList.add("hidden");
    document.getElementById("invigilatorPanel").classList.remove("hidden");

    // Reset to selection step
    document.getElementById("attendanceStep").classList.add("hidden");
    document.getElementById("selectionStep").classList.remove("hidden");

    // Clear hall selection and absent set
    document.getElementById("hallSelect").value = "";
    currentHall = null;
    absentSet = new Set();

    // Refresh halls (mark newly submitted one as disabled)
    await loadHalls();
}

// ─── SUCCESS ──────────────────────────────────────────────────────────────────

function showSuccessPanel(data) {
    document.getElementById("invigilatorPanel").classList.add("hidden");
    const panel = document.getElementById("successPanel");
    panel.classList.remove("hidden");

    document.getElementById("successDetails").innerHTML = `
        <span class="dl">Hall : </span><span class="dv">${data.hall_number}</span> <br>
        <span class="dl">Faculty : </span><span class="dv">${data.faculty_name}</span> <br>
        <span class="dl">Total Students : </span><span class="dv">${data.total_students}</span> <br>
        <span class="dl">Present : </span><span class="dv" style="color:#16a34a">${data.present_count}</span> <br>
        <span class="dl">Absent : </span><span class="dv" style="color:#dc2626">${data.absent_count}</span> <br>
        <span class="dl">Submitted At : </span><span class="dv">${new Date(data.submitted_at).toLocaleString()}</span>
    `;
    panel.scrollIntoView({ behavior: "smooth" });
}

// ─── TOAST HELPERS ────────────────────────────────────────────────────────────

function showMessage(id, msg, type = "info") {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = msg;
    el.classList.remove("hidden");
    el.className = 'p-4 rounded-lg text-sm font-medium mb-6 border animate-[fadeIn_0.3s_ease-out] ';
    if (type === 'success') {
        el.classList.add('bg-[#003594]', 'text-white', 'border-blue-800', 'shadow-md');
    } else if (type === 'error') {
        el.classList.add('bg-red-50', 'text-red-800', 'border-red-200');
    } else {
        el.classList.add('bg-blue-50', 'text-blue-800', 'border-blue-200');
    }
    if (type === "success") {
        setTimeout(() => { el.classList.add("hidden"); }, 5000);
    }
}

function hideMessage(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add("hidden");
}
