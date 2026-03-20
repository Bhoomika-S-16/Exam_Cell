"""
Exam Attendance System — FastAPI Application
All API routes + static file serving for the frontend.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Annotated
from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Form, Query, Request, Depends
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import io

# ═══════════════════════════════════════════════════════════════════════════════
# PATH SETUP - Fix module import issues
# ═══════════════════════════════════════════════════════════════════════════════

# Get the directory where this script is located
BACKEND_DIR = Path(__file__).resolve().parent
print(f"[DEBUG] Backend directory: {BACKEND_DIR}")

# Add backend directory to Python path to ensure imports work
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Try to import modules with error handling
try:
    from services.auth import login, verify_token, verify_admin_token, verify_invigilator_token, revoke_token, clear_all_tokens
    print("[DEBUG] [OK] auth module imported")
except ImportError as e:
    print(f"[ERROR] Failed to import auth: {e}")
    sys.exit(1)

try:
    from core.state import exam_state
    print("[DEBUG] [OK] state module imported")
except ImportError as e:
    print(f"[ERROR] Failed to import state: {e}")
    sys.exit(1)

try:
    from services.excel_utils import parse_seating_plan
    print("[DEBUG] [OK] excel_utils module imported")
except ImportError as e:
    print(f"[ERROR] Failed to import excel_utils: {e}")
    sys.exit(1)

try:
    from services.reports import generate_pdf, generate_excel
    print("[DEBUG] [OK] reports module imported")
except ImportError as e:
    print(f"[ERROR] Failed to import reports: {e}")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════════
# APP SETUP
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(title="Exam Attendance System", version="1.0.0")

# CORS — allow specific origins for local development and cloud use
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "*")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,  # Allow credentials
    allow_methods=["*"],
    allow_headers=["*"],  # Allow all headers including X-Auth-Token
)

# Resolve frontend directory
# Try multiple possible locations
possible_frontend_paths = [
    BACKEND_DIR.parent / "frontend",  # ../frontend
    BACKEND_DIR / "frontend",  # ./frontend
    BACKEND_DIR / ".." / ".." / "frontend",  # ../../frontend
]

FRONTEND_DIR = None
for path in possible_frontend_paths:
    resolved_path = path.resolve()
    if resolved_path.exists():
        FRONTEND_DIR = resolved_path
        print(f"[DEBUG] [OK] Found frontend directory: {FRONTEND_DIR}")
        break

if FRONTEND_DIR is None:
    print(f"[ERROR] Frontend directory NOT FOUND!")
    print(f"[DEBUG] Checked paths:")
    for path in possible_frontend_paths:
        print(f"  - {path.resolve()}")
    print("[DEBUG] Creating fallback with parent/frontend path...")
    FRONTEND_DIR = BACKEND_DIR.parent / "frontend"

print(f"[DEBUG] Using frontend directory: {FRONTEND_DIR}")
if FRONTEND_DIR.exists():
    admin_exists = (FRONTEND_DIR / "admin.html").exists()
    invig_exists = (FRONTEND_DIR / "invigilator.html").exists()
    print(f"[DEBUG] admin.html exists: {admin_exists}")
    print(f"[DEBUG] invigilator.html exists: {invig_exists}")
else:
    print(f"[WARNING] Frontend directory does not exist yet: {FRONTEND_DIR}")


# ── Day-reset middleware ───────────────────────────────────────────────────────

# @app.middleware("http")
# async def day_reset_middleware(request: Request, call_next):
#     """Automatically reset exam state if the day has changed."""
#     if exam_state.check_day_reset():
#         clear_all_tokens()
#     response = await call_next(request)
#     return response


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def require_admin(x_auth_token: str | None = Header(None)) -> str:
    """Dependency: validate admin token from X-Auth-Token header."""
    if not x_auth_token or not verify_admin_token(x_auth_token):
        raise HTTPException(status_code=401, detail="Unauthorized — invalid or missing admin token")
    return x_auth_token


def require_invigilator(x_auth_token: str | None = Header(None)) -> str:
    """Dependency: validate invigilator token from X-Auth-Token header."""
    if not x_auth_token or not verify_invigilator_token(x_auth_token):
        raise HTTPException(status_code=401, detail="Unauthorized — invalid or missing invigilator token")
    return x_auth_token


# ═══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

from pydantic import BaseModel as _BaseModel

class LoginRequest(_BaseModel):
    username: str
    password: str
    role: str  # 'admin' or 'invigilator'


@app.post("/api/auth/login")
def auth_login(payload: LoginRequest):
    """Login endpoint for admin and invigilator"""
    result = login(payload.username, payload.password)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    # Verify the user's selected role matches their credential role
    if result["role"] != payload.role:
        raise HTTPException(
            status_code=403,
            detail=f"Your credentials are for the '{result['role']}' role, not '{payload.role}'"
        )
    return {
        "token": result["token"],
        "role": result["role"],
        "message": "Login successful",
    }


@app.get("/api/auth/verify")
def auth_verify(x_auth_token: str | None = Header(None)):
    """Verify that a token is still valid"""
    info = verify_token(x_auth_token)
    if info is None:
        raise HTTPException(status_code=401, detail="Token invalid or expired")
    return {"valid": True, "role": info["role"]}


@app.post("/api/auth/logout")
def auth_logout(x_auth_token: str | None = Header(None)):
    """Logout — revoke the token"""
    if x_auth_token:
        revoke_token(x_auth_token)
    return {"message": "Logged out successfully"}


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/health")
def health():
    """Health check endpoint - useful for debugging"""
    return {
        "status": "ok",
        "exam_active": exam_state.is_created,
        "frontend_path": str(FRONTEND_DIR),
        "frontend_exists": FRONTEND_DIR.exists()
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — EXAM MANAGEMENT (NO AUTH REQUIRED)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/admin/exam/create")
def create_exam(
    date: str = Form(...),
    exam_type: str = Form(...),
    _token: str = Depends(require_admin)
):
    """Create a new exam session"""
    print(f"[DEBUG] Received create_exam request: date={date}, exam_type={exam_type}")
    
    if not date:
        raise HTTPException(status_code=400, detail="Date is required")
    
    if not exam_type:
        raise HTTPException(status_code=400, detail="Exam type is required")
    
    if exam_type not in ("CIA", "MODEL"):
        raise HTTPException(status_code=400, detail="Exam type must be CIA or MODEL")

    try:
        exam_state.create_exam(date, exam_type)
        print(f"[DEBUG] Exam created successfully: {date} {exam_type}")
        return {
            "message": "Exam created successfully",
            "date": date,
            "type": exam_type,
        }
    except Exception as e:
        print(f"[ERROR] Failed to create exam: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create exam: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — SEATING PLAN (NO AUTH REQUIRED)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/admin/seating-plan/upload")
async def upload_seating_plan(
    file: UploadFile = File(...),
    session: str = Form("MODEL"),
    _token: str = Depends(require_admin)
):
    """Upload and parse seating plan Excel file"""
    print(f"[DEBUG] Seating plan upload: file={file.filename}, session={session}")
    
    if not exam_state.is_created:
        raise HTTPException(status_code=400, detail="Create an exam first")

    if exam_state.is_finalized:
        raise HTTPException(status_code=400, detail="Exam is finalized, cannot upload")

    if session not in ("FN", "AN", "MODEL", "BOTH"):
        raise HTTPException(status_code=400, detail="Invalid session identifier")

    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    if not (file.filename.endswith(".xlsx") or file.filename.endswith(".xls")):
        raise HTTPException(status_code=400, detail="Only .xlsx or .xls files accepted")

    try:
        file_bytes = await file.read()
        
        # If session is BOTH, we detect sessions from sheet names
        detect_sessions = (session == "BOTH")
        parsed_data, errors = parse_seating_plan(file_bytes, detect_sessions=detect_sessions)

        if errors:
            print(f"[DEBUG] Seating plan validation errors: {errors}")
            raise HTTPException(status_code=400, detail={"message": "Validation failed", "errors": errors})

        if detect_sessions:
            # parsed_data is a dict mapping FN/AN -> list of students
            results = {}
            for sess_id, students in parsed_data.items():
                res = exam_state.load_seating_plan(students, sess_id)
                results[sess_id] = res
            
            print(f"[DEBUG] Dual-session seating loaded: {list(results.keys())}")
            return {
                "message": "Dual-session seating plan loaded successfully",
                "sessions_loaded": list(results.keys()),
                "details": results
            }
        else:
            # parsed_data is a flat list
            result = exam_state.load_seating_plan(parsed_data, session)
            print(f"[DEBUG] Seating plan loaded for session {session}")
            return {
                "message": f"Seating plan for {session} loaded successfully",
                **result,
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Seating plan upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/api/admin/status")
def get_exam_status(_token: str = Depends(require_admin)):
    """Get current exam status"""
    return {
        "is_created": exam_state.is_created,
        "is_finalized": exam_state.is_finalized,
        "seating_loaded": exam_state.seating_loaded,
        "exam_date": exam_state.exam_date,
        "exam_type": exam_state.exam_type,
        "active_sessions": list(exam_state.seating_plans.keys())
    }


# ADMIN — DASHBOARD (NO AUTH REQUIRED)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/admin/dashboard")
def get_dashboard(session: str = Query(None), _token: str = Depends(require_admin)):
    """Get dashboard data for a session"""
    if not exam_state.is_created:
        raise HTTPException(status_code=400, detail="No active exam")

    try:
        return exam_state.get_dashboard(session)
    except Exception as e:
        print(f"[ERROR] Dashboard error: {e}")
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")


@app.get("/api/admin/classes")
def get_classes(session: str = Query(...), _token: str = Depends(require_admin)):
    """Get list of classes for a session"""
    if not exam_state.is_created:
        raise HTTPException(status_code=400, detail="No active exam")

    if session not in exam_state.seating_plans:
        return {"classes": []}

    try:
        return {"classes": exam_state.get_active_classes(session)}
    except Exception as e:
        print(f"[ERROR] Classes error: {e}")
        raise HTTPException(status_code=500, detail=f"Classes error: {str(e)}")

@app.get("/api/admin/absentees")
def get_absentees(
    department: str = Query(...),
    year: str = Query(...),
    session: str = Query(...),
    _token: str = Depends(require_admin)
):
    results = []

    session_subs = exam_state.submissions.get(session, {})
    session_halls = exam_state.seating_plans.get(session, {})

    for hall_number, sub in session_subs.items():
        absent_set = set(sub.absent_register_numbers)
        for student in session_halls.get(hall_number, []):
            if (
                student.department == department and
                student.year == year and
                student.register_number in absent_set
            ):
                results.append({
                    "register_number": student.register_number,
                    "student_name": student.student_name,
                    "hall_number": hall_number,
                    "seat_number": student.seat_number
                })

    return {
        "department": department,
        "year": year,
        "session": session,
        "absentees": results
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — FINALIZE (NO AUTH REQUIRED)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/admin/exam/finalize")
def finalize_exam(_token: str = Depends(require_admin)):
    """Finalize the exam and lock submissions"""
    if not exam_state.is_created:
        raise HTTPException(status_code=400, detail="No active exam")

    if exam_state.is_finalized:
        raise HTTPException(status_code=400, detail="Exam already finalized")

    try:
        exam_state.is_finalized = True
        print("[DEBUG] Exam finalized")
        return {"message": "Exam finalized successfully"}
    except Exception as e:
        print(f"[ERROR] Finalize failed: {e}")
        raise HTTPException(status_code=500, detail=f"Finalize failed: {str(e)}")


@app.post("/api/admin/exam/reset")
def reset_exam(_token: str = Depends(require_admin)):
    """Reset exam state entirely"""
    try:
        exam_state.reset()
        print("[DEBUG] Exam reset")
        return {"message": "Exam session reset successfully"}
    except Exception as e:
        print(f"[ERROR] Reset failed: {e}")
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — REPORTS (NO AUTH REQUIRED)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/admin/reports/pdf")
def download_pdf_report(
    session: str = Query(...),
    report_type: str = Query("overall"),
    filter_value: str = Query(None),
    _token: str = Depends(require_admin)
):
    """Generate and download PDF report"""
    if not exam_state.is_created:
        raise HTTPException(status_code=400, detail="No active exam")

    if report_type not in ("hall", "department", "overall", "class"):
        raise HTTPException(status_code=400, detail="report_type must be hall, department, class, or overall")

    try:
        absentees = exam_state.get_absentees(session, report_type, filter_value)
        exam_info = {
            "date": exam_state.exam_date,
            "type": exam_state.exam_type,
            "session": session,
        }

        pdf_bytes = generate_pdf(absentees, exam_info, report_type)
        
        # Prefix filename if not finalized
        prefix = "" if exam_state.is_finalized else "PROVISIONAL_"
        filename = f"{prefix}Absentees_{exam_state.exam_date}_{session}_{report_type}.pdf"

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        print(f"[ERROR] PDF report failed: {e}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@app.get("/api/admin/reports/excel")
def download_excel_report(
    session: str = Query(...),
    report_type: str = Query("overall"),
    filter_value: str = Query(None),
    _token: str = Depends(require_admin)
):
    """Generate and download Excel report"""
    if not exam_state.is_created:
        raise HTTPException(status_code=400, detail="No active exam")

    if report_type not in ("hall", "department", "overall", "class"):
        raise HTTPException(status_code=400, detail="report_type must be hall, department, or overall")

    try:
        absentees = exam_state.get_absentees(session, report_type, filter_value)
        exam_info = {
            "date": exam_state.exam_date,
            "type": exam_state.exam_type,
            "session": session,
        }

        excel_bytes = generate_excel(absentees, exam_info, report_type)
        
        # Prefix filename if not finalized
        prefix = "" if exam_state.is_finalized else "PROVISIONAL_"
        filename = f"{prefix}Absentees_{exam_state.exam_date}_{session}_{report_type}.xlsx"

        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        print(f"[ERROR] Excel report failed: {e}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# INVIGILATOR — ROUTES (no auth required)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/invigilator/status")
def get_invigilator_status(_token: str = Depends(require_invigilator)):
    """Get current exam status for invigilator portal"""
    return {
        "exam_active": exam_state.is_created,
        "seating_loaded": exam_state.seating_loaded,
        "is_finalized": exam_state.is_finalized,
        "exam": {
            "date": exam_state.exam_date,
            "type": exam_state.exam_type,
            "active_sessions": list(exam_state.seating_plans.keys())
        } if exam_state.is_created else None,
    }


@app.get("/api/invigilator/halls")
def get_halls(session: str = Query("FN"), _token: str = Depends(require_invigilator)):
    """Get list of halls for invigilator"""
    if not exam_state.is_created:
        raise HTTPException(status_code=400, detail="No active exam")

    if session not in exam_state.seating_plans:
        raise HTTPException(status_code=400, detail=f"Seating plan for session '{session}' not loaded")

    try:
        session_halls = exam_state.seating_plans[session]
        session_subs = exam_state.submissions.get(session, {})

        halls = sorted(session_halls.keys())
        submitted_halls = list(session_subs.keys())

        return {
            "halls": halls,
            "submitted_halls": submitted_halls,
            "exam": {
                "date": exam_state.exam_date,
                "type": exam_state.exam_type,
                "session": session,
            },
        }
    except Exception as e:
        print(f"[ERROR] Get halls failed: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/api/invigilator/students/{hall_number}")
def get_hall_students(hall_number: str, session: str = Query("FN"), _token: str = Depends(require_invigilator)):
    """Get student list for a specific hall"""
    if not exam_state.is_created:
        raise HTTPException(status_code=400, detail="No active exam")

    try:
        session_halls = exam_state.seating_plans.get(session, {})
        if hall_number not in session_halls:
            raise HTTPException(status_code=404, detail=f"Hall '{hall_number}' not found in session '{session}'")

        session_subs = exam_state.submissions.get(session, {})
        if hall_number in session_subs:
            raise HTTPException(
                status_code=400,
                detail=f"Attendance for Hall '{hall_number}' in session '{session}' already submitted",
            )

        students = session_halls[hall_number]
        return {
            "hall_number": hall_number,
            "session": session,
            "students": [
                {
                    "student_name": s.student_name,
                    "register_number": s.register_number,
                    "roll_number": s.roll_number,
                    "department": s.department,
                    "year": s.year,
                    "seat_number": s.seat_number,
                }
                for s in sorted(students, key=lambda x: x.seat_number)
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Get students failed: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


from pydantic import BaseModel


class AttendanceSubmission(BaseModel):
    session: str
    hall_number: str
    faculty_name: str
    absent_register_numbers: list[str]


@app.post("/api/invigilator/attendance/submit")
def submit_attendance(payload: AttendanceSubmission, _token: str = Depends(require_invigilator)):
    """Submit attendance for a hall"""
    if not exam_state.is_created:
        raise HTTPException(status_code=400, detail="No active exam")

    if exam_state.is_finalized:
        raise HTTPException(status_code=400, detail="Exam is finalized, submissions closed")

    try:
        session_id = payload.session
        if session_id not in exam_state.seating_plans:
             raise HTTPException(status_code=400, detail=f"Session '{session_id}' not loaded")

        session_halls = exam_state.seating_plans[session_id]
        if payload.hall_number not in session_halls:
            raise HTTPException(status_code=404, detail=f"Hall '{payload.hall_number}' not found in session '{session_id}'")

        session_subs = exam_state.submissions.get(session_id, {})
        if payload.hall_number in session_subs:
            raise HTTPException(
                status_code=400,
                detail=f"Attendance for Hall '{payload.hall_number}' in session '{session_id}' already submitted.",
            )

        if not payload.faculty_name or not payload.faculty_name.strip():
            raise HTTPException(status_code=400, detail="Faculty name is required")

        # Validate register numbers
        hall_reg_numbers = {s.register_number for s in session_halls[payload.hall_number]}
        invalid = [r for r in payload.absent_register_numbers if r not in hall_reg_numbers]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid register numbers for this hall: {invalid}",
            )

        submission = exam_state.submit_attendance(
            session_id=session_id,
            hall_number=payload.hall_number,
            faculty_name=payload.faculty_name.strip(),
            absent_reg_numbers=payload.absent_register_numbers,
        )

        print(f"[DEBUG] Attendance submitted: {payload.hall_number} in {session_id}")

        return {
            "message": "Attendance submitted successfully",
            "session": session_id,
            "hall_number": submission.hall_number,
            "faculty_name": submission.faculty_name,
            "total_students": submission.total_students,
            "present_count": submission.present_count,
            "absent_count": submission.absent_count,
            "submitted_at": submission.submitted_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Attendance submission failed: {e}")
        raise HTTPException(status_code=500, detail=f"Submission failed: {str(e)}")


class StudentSeatInfo(BaseModel):
    session: str
    hall_number: str
    seat_number: str
    student_name: str
    register_number: str
    venue: str | None = None
    exam_type: str | None = None

@app.get("/api/student/lookup/{reg_num}", response_model=list[StudentSeatInfo])
def student_lookup(reg_num: str):
    """Look up student seat information"""
    if not exam_state.is_created:
        raise HTTPException(status_code=400, detail="No active exam")
    
    try:
        raw_results = exam_state.lookup_student(reg_num)
        if not raw_results:
            raise HTTPException(status_code=404, detail="Register number not found")
        
        # Flatten results into a list of structured objects
        results = []
        for session_id, info in raw_results.items():
            results.append(StudentSeatInfo(
                session=session_id,
                hall_number=info["hall"],
                seat_number=info["seat"],
                student_name=info["name"],
                register_number=reg_num,
                venue=info["venue"],
                exam_type=exam_state.exam_type
            ))
        
        return results
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Student lookup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Lookup failed: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# STATIC FILE SERVING (Frontend)
# ═══════════════════════════════════════════════════════════════════════════════

# Serve specific HTML pages
@app.get("/")
@app.get("/admin-login")
async def serve_admin_login():
    """Serve admin login page"""
    login_path = FRONTEND_DIR / "html" / "admin_login.html"
    if not login_path.exists():
        raise HTTPException(status_code=404, detail=f"Admin login page not found at {login_path}")
    return FileResponse(login_path)


@app.get("/invigilator-login")
async def serve_invigilator_login():
    """Serve invigilator login page"""
    login_path = FRONTEND_DIR / "html" / "invig_login.html"
    if not login_path.exists():
        raise HTTPException(status_code=404, detail=f"Invigilator login page not found at {login_path}")
    return FileResponse(login_path)


@app.get("/admin.html")
@app.get("/admin")
async def serve_admin():
    """Serve admin dashboard"""
    admin_path = FRONTEND_DIR / "html" / "admin.html"
    if not admin_path.exists():
        raise HTTPException(status_code=404, detail=f"Admin page not found at {admin_path}")
    return FileResponse(admin_path)


@app.get("/invigilator.html")
@app.get("/invigilator")
async def serve_invigilator():
    """Serve invigilator page"""
    invig_path = FRONTEND_DIR / "html" / "invigilator.html"
    if not invig_path.exists():
        raise HTTPException(status_code=404, detail=f"Invigilator page not found at {invig_path}")
    return FileResponse(invig_path)


@app.get("/lookup.html")
@app.get("/viewer")
async def serve_lookup():
    """Serve student lookup page"""
    lookup_path = FRONTEND_DIR / "html" / "lookup.html"
    if not lookup_path.exists():
        raise HTTPException(status_code=404, detail=f"Lookup page not found at {lookup_path}")
    return FileResponse(lookup_path)


# Mount static files (CSS, JS) — must come after explicit routes
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
else:
    print(f"[WARNING] Static files mount skipped - frontend directory doesn't exist")


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "=" * 60)
    print("  EXAM ATTENDANCE SYSTEM")
    print("  Server starting on http://localhost:8000")
    print("  Admin Login:       http://localhost:8000/admin-login")
    print("  Invig Login:       http://localhost:8000/invigilator-login")
    print("  Admin:             http://localhost:8000/admin")
    print("  Invigilator:       http://localhost:8000/invigilator")
    print("  Lookup:            http://localhost:8000/lookup.html")
    print("  Health:            http://localhost:8000/api/health")
    print("=" * 60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")