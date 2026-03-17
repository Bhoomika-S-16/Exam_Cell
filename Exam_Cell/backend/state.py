"""
In-memory exam state for Exam Attendance System.
All data lives here and is wiped on restart or new day.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Student:
    student_name: str
    register_number: str
    roll_number: str
    department: str
    year: str
    hall_number: str
    seat_number: str
    side_of_seat: str | None = None  # "Left side" or "Right side"
    venue: str | None = None         # Full venue string from E4
    class_name: str | None = None    # "III B.COM"


@dataclass
class HallSubmission:
    hall_number: str
    faculty_name: str
    absent_register_numbers: list[str]
    total_students: int
    present_count: int
    absent_count: int
    submitted_at: str  # ISO datetime string


@dataclass
class ExamState:
    """Singleton-style in-memory state for the current exam."""

    # Exam metadata
    exam_date: str | None = None           # "2026-02-17"
    exam_type: str | None = None           # "CIA" | "MODEL"
    is_created: bool = False
    is_finalized: bool = False

    # Multi-session storage: session_id -> hall_number -> list[Student]
    # session_id values: "FN", "AN", "MODEL"
    seating_plans: dict[str, dict[str, list[Student]]] = field(default_factory=dict)
    
    # Submissions: session_id -> hall_number -> HallSubmission
    submissions: dict[str, dict[str, HallSubmission]] = field(default_factory=dict)

    # Fast lookup index: register_number (upper) -> session_id -> Student
    _lookup_map: dict[str, dict[str, Student]] = field(default_factory=dict)

    # Track creation date for auto-reset
    _created_date: str | None = None
    
    # Thread safety
    _lock: Any = field(default_factory=__import__("threading").Lock)

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def reset(self) -> None:
        """Wipe all state (manual reset on new exam)."""
        with self._lock:
            self.exam_date = None
            self.exam_type = None
            self.is_created = False
            self.is_finalized = False
            self.seating_plans.clear()
            self.submissions.clear()
            self._lookup_map.clear()
            self._created_date = None

    # ── Exam creation ──────────────────────────────────────────────────────

    def create_exam(self, date: str, exam_type: str) -> None:
        self.reset()
        self.exam_date = date
        self.exam_type = exam_type
        self.is_created = True
        self._created_date = datetime.date.today().isoformat()

    # ── Seating plan ───────────────────────────────────────────────────────

    def load_seating_plan(self, students: list[dict[str, Any]], session_id: str) -> dict[str, Any]:
        """Load validated student dicts into the session-keyed structure."""
        with self._lock:
            if session_id not in self.seating_plans:
                self.seating_plans[session_id] = {}
            if session_id not in self.submissions:
                self.submissions[session_id] = {}

            # Reset session data before reload
            session_halls = self.seating_plans[session_id]
            session_halls.clear()
            self.submissions[session_id].clear()

            for s in students:
                student = Student(
                    student_name=str(s["Student Name"]),
                    register_number=str(s["Register Number"]),
                    roll_number=str(s["Roll Number"]),
                    department=str(s["Department"]),
                    year=str(s["Year"]),
                    hall_number=str(s["Hall Number"]),
                    seat_number=str(s["Seat Number"]),
                    side_of_seat=str(s.get("side_of_seat", "")),
                    venue=str(s.get("venue", "")),
                    class_name=str(s.get("Class", "")),
                )
                hall = student.hall_number
                if hall not in session_halls:
                    session_halls[hall] = []
                session_halls[hall].append(student)

                # Update lookup map
                reg_key = student.register_number.strip().upper()
                if reg_key not in self._lookup_map:
                    self._lookup_map[reg_key] = {}
                self._lookup_map[reg_key][session_id] = student

            total_students = sum(len(v) for v in session_halls.values())
            return {
                "session": session_id,
                "total_students": total_students,
                "total_halls": len(session_halls),
                "halls": list(session_halls.keys()),
            }

    @property
    def seating_loaded(self) -> bool:
        return any(len(halls) > 0 for halls in self.seating_plans.values())

    # ── Attendance ─────────────────────────────────────────────────────────

    def submit_attendance(
        self, session_id: str, hall_number: str, faculty_name: str, absent_reg_numbers: list[str]
    ) -> HallSubmission:
        with self._lock:
            session_halls = self.seating_plans.get(session_id, {})
            students = session_halls.get(hall_number, [])
            total = len(students)
            absent_count = len(absent_reg_numbers)
            present_count = total - absent_count

            submission = HallSubmission(
                hall_number=hall_number,
                faculty_name=faculty_name,
                absent_register_numbers=absent_reg_numbers,
                total_students=total,
                present_count=present_count,
                absent_count=absent_count,
                submitted_at=datetime.datetime.now().isoformat(),
            )
            
            if session_id not in self.submissions:
                self.submissions[session_id] = {}
            self.submissions[session_id][hall_number] = submission
            return submission

    # ── Dashboard ──────────────────────────────────────────────────────────

    def get_dashboard(self, session_id: str | None = None) -> dict[str, Any]:
        """Get stats for a specific session or overall if None."""
        # For now, let's keep it simple and return the requested session or FN by default
        target_session = session_id or ("MODEL" if self.exam_type == "MODEL" else "FN")
        
        session_halls = self.seating_plans.get(target_session, {})
        session_subs = self.submissions.get(target_session, {})
        
        halls_info = []
        for hall_number, students in sorted(session_halls.items()):
            sub = session_subs.get(hall_number)
            halls_info.append({
                "hall_number": hall_number,
                "total_students": len(students),
                "present_count": sub.present_count if sub else 0,
                "absent_count": sub.absent_count if sub else 0,
                "submitted": sub is not None,
                "faculty_name": sub.faculty_name if sub else None,
                "submission_time": sub.submitted_at if sub else None,
            })

        submitted_count = len(session_subs)
        total_halls = len(session_halls)

        return {
            "exam": {
                "date": self.exam_date,
                "type": self.exam_type,
                "session": target_session,
                "finalized": self.is_finalized,
            },
            "halls": halls_info,
            "summary": {
                "total_halls": total_halls,
                "submitted_halls": submitted_count,
                "all_submitted": submitted_count == total_halls and total_halls > 0,
            },
            "departments": self._get_department_stats(target_session),
        }

    def _get_department_stats(self, session_id: str) -> dict[str, dict[str, dict[str, int]]]:
        """Aggregate attendance stats per Department and Year for a session."""
        stats = {}
        session_halls = self.seating_plans.get(session_id, {})
        session_subs = self.submissions.get(session_id, {})
        
        # Initialize total counts from seating plan
        for hall_students in session_halls.values():
            for s in hall_students:
                dept = s.department or "Unknown"
                year = s.year or "Unknown"
                if dept not in stats:
                    stats[dept] = {}
                if year not in stats[dept]:
                    stats[dept][year] = {"total": 0, "present": 0, "absent": 0}
                stats[dept][year]["total"] += 1

        # Update with submission data
        for hall_number, sub in session_subs.items():
            absent_regs = set(sub.absent_register_numbers)
            hall_students = session_halls.get(hall_number, [])
            
            for s in hall_students:
                dept = s.department or "Unknown"
                year = s.year or "Unknown"
                is_absent = s.register_number in absent_regs
                
                if dept in stats and year in stats[dept]:
                    if is_absent:
                        stats[dept][year]["absent"] += 1
                    else:
                        stats[dept][year]["present"] += 1
        
        return stats

    def get_active_classes(self, session_id: str) -> list[str]:
        classes = set()
        session_halls = self.seating_plans.get(session_id, {})
        for hall_students in session_halls.values():
            for student in hall_students:
                if student.class_name:
                    classes.add(student.class_name)
        return sorted(list(classes))

    # ── Seat Finder / Lookup ───────────────────────────────────────────────

    def lookup_student(self, register_number: str) -> dict[str, Any]:
        """Find student seat info using O(1) index."""
        reg_key = register_number.strip().upper()
        
        with self._lock:
            # Get dict[session_id, Student]
            student_sessions = self._lookup_map.get(reg_key, {})
            
            results = {}
            for session_id, s in student_sessions.items():
                results[session_id] = {
                    "name": s.student_name,
                    "hall": s.hall_number,
                    "seat": s.seat_number,
                    "venue": s.venue,
                }
            return results

    # ── Absentee data ──────────────────────────────────────────────────────

    def get_absentees(self, session_id: str, report_type: str = "overall", filter_value: str | None = None) -> list[dict[str, str]]:
        absentees: list[dict[str, str]] = []
        session_subs = self.submissions.get(session_id, {})
        session_halls = self.seating_plans.get(session_id, {})
        
        for hall_number, sub in sorted(session_subs.items()):
            absent_set = set(sub.absent_register_numbers)
            students = session_halls.get(hall_number, [])
            for st in students:
                if st.register_number in absent_set:
                    if report_type == "class" and st.class_name != filter_value:
                        continue
                    
                    absentees.append({
                        "register_number": st.register_number,
                        "student_name": st.student_name,
                        "roll_number": st.roll_number,
                        "department": st.department,
                        "year": st.year,
                        "hall_number": st.hall_number,
                        "seat_number": st.seat_number,
                        "class_name": st.class_name,
                        "side_of_seat": st.side_of_seat,
                        "venue": st.venue,
                    })
        return absentees

    def check_day_reset(self) -> bool:
        if not self._created_date:
            return False
        today = datetime.date.today().isoformat()
        if today != self._created_date:
            self.reset()
            return True
        return False


# ── Global singleton ───────────────────────────────────────────────────────────
exam_state = ExamState()
