"""
SQLite-backed exam state for Exam Attendance System.
Reliably stores attendance data during exams, avoiding in-memory state loss.
"""

from __future__ import annotations

import datetime
import sqlite3
import os
import threading
from dataclasses import dataclass, field
from typing import Any

DATABASE_URL = os.environ.get("DATABASE_URL", "app.db")
DB_PATH = DATABASE_URL
if DB_PATH.startswith("sqlite:///"):
    DB_PATH = DB_PATH.replace("sqlite:///", "")

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    with conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS exam_sessions (
                id TEXT PRIMARY KEY,
                exam_name TEXT,
                exam_date TEXT,
                session_type TEXT,
                is_finalized INTEGER DEFAULT 0,
                created_at TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                register_no TEXT,
                name TEXT,
                department TEXT,
                subject TEXT,
                hall TEXT,
                seat_no TEXT,
                session_id TEXT,
                roll_number TEXT,
                year TEXT,
                side_of_seat TEXT,
                venue TEXT,
                class_name TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                is_present INTEGER DEFAULT 1,
                marked_by TEXT,
                timestamp TEXT,
                session_id TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                role TEXT,
                expiry REAL
            )
        ''')
    conn.close()

init_db()


@dataclass
class Student:
    student_name: str
    register_number: str
    roll_number: str
    department: str
    year: str
    hall_number: str
    seat_number: str
    side_of_seat: str | None = None
    venue: str | None = None
    class_name: str | None = None


@dataclass
class HallSubmission:
    hall_number: str
    faculty_name: str
    absent_register_numbers: list[str]
    total_students: int
    present_count: int
    absent_count: int
    submitted_at: str


class ExamState:
    """SQLite-backed state for the current exam."""

    _lock = threading.Lock()

    def reset(self) -> None:
        """Wipe all state (manual reset on new exam)."""
        with self._lock:
            conn = get_db()
            with conn:
                conn.execute("DELETE FROM students")
                conn.execute("DELETE FROM attendance")
                conn.execute("DELETE FROM exam_sessions")
            conn.close()

    def create_exam(self, date: str, exam_type: str) -> None:
        self.reset()
        with self._lock:
            conn = get_db()
            with conn:
                created_at = datetime.datetime.now().isoformat()
                conn.execute('''
                    INSERT INTO exam_sessions (id, exam_date, session_type, is_finalized, created_at)
                    VALUES ('current', ?, ?, 0, ?)
                ''', (date, exam_type, created_at))
            conn.close()

    @property
    def is_created(self) -> bool:
        conn = get_db()
        row = conn.execute("SELECT 1 FROM exam_sessions LIMIT 1").fetchone()
        conn.close()
        return row is not None

    @property
    def is_finalized(self) -> bool:
        conn = get_db()
        row = conn.execute("SELECT is_finalized FROM exam_sessions LIMIT 1").fetchone()
        conn.close()
        return bool(row['is_finalized']) if row else False

    @is_finalized.setter
    def is_finalized(self, value: bool) -> None:
        with self._lock:
            conn = get_db()
            with conn:
                conn.execute("UPDATE exam_sessions SET is_finalized = ?", (1 if value else 0,))
            conn.close()

    @property
    def exam_date(self) -> str | None:
        conn = get_db()
        row = conn.execute("SELECT exam_date FROM exam_sessions LIMIT 1").fetchone()
        conn.close()
        return row['exam_date'] if row else None

    @property
    def exam_type(self) -> str | None:
        conn = get_db()
        row = conn.execute("SELECT session_type FROM exam_sessions LIMIT 1").fetchone()
        conn.close()
        return row['session_type'] if row else None

    # ── Multi-session storage ──

    def load_seating_plan(self, students: list[dict[str, Any]], session_id: str) -> dict[str, Any]:
        """Load validated student dicts directly into the database."""
        with self._lock:
            conn = get_db()
            with conn:
                # Clear previous data for this session to avoid duplicates
                conn.execute("DELETE FROM students WHERE session_id = ?", (session_id,))
                conn.execute("DELETE FROM attendance WHERE session_id = ?", (session_id,))

                for s in students:
                    conn.execute('''
                        INSERT INTO students (
                            name, register_no, roll_number, department, year,
                            hall, seat_no, side_of_seat, venue, class_name, session_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        str(s.get("Student Name", "")),
                        str(s.get("Register Number", "")),
                        str(s.get("Roll Number", "")),
                        str(s.get("Department", "")),
                        str(s.get("Year", "")),
                        str(s.get("Hall Number", "")),
                        str(s.get("Seat Number", "")),
                        str(s.get("side_of_seat", "")),
                        str(s.get("venue", "")),
                        str(s.get("Class", "")),
                        session_id
                    ))
            
            # Count total students and halls for response
            res = conn.execute('SELECT COUNT(*) as c, COUNT(DISTINCT hall) as h FROM students WHERE session_id = ?', (session_id,)).fetchone()
            total_students = res['c']
            total_halls = res['h']
            halls_res = conn.execute('SELECT DISTINCT hall FROM students WHERE session_id = ?', (session_id,)).fetchall()
            halls = [r['hall'] for r in halls_res]
            conn.close()

            return {
                "session": session_id,
                "total_students": total_students,
                "total_halls": total_halls,
                "halls": halls,
            }

    @property
    def seating_loaded(self) -> bool:
        conn = get_db()
        row = conn.execute("SELECT 1 FROM students LIMIT 1").fetchone()
        conn.close()
        return row is not None

    @property
    def seating_plans(self) -> dict[str, dict[str, list[Student]]]:
        conn = get_db()
        cursor = conn.execute("SELECT * FROM students")
        rows = cursor.fetchall()
        conn.close()

        plans = {}
        for r in rows:
            sid = r['session_id']
            hall = r['hall']
            if sid not in plans:
                plans[sid] = {}
            if hall not in plans[sid]:
                plans[sid][hall] = []
            
            student = Student(
                student_name=r['name'],
                register_number=r['register_no'],
                roll_number=r['roll_number'],
                department=r['department'],
                year=r['year'],
                hall_number=r['hall'],
                seat_number=r['seat_no'],
                side_of_seat=r['side_of_seat'],
                venue=r['venue'],
                class_name=r['class_name']
            )
            plans[sid][hall].append(student)
        return plans

    @property
    def submissions(self) -> dict[str, dict[str, HallSubmission]]:
        conn = get_db()
        # Find which halls have been submitted
        query = '''
            SELECT a.session_id, a.marked_by, s.hall, MAX(a.timestamp) as max_timestamp,
                   COUNT(a.id) as total_attendance,
                   SUM(a.is_present) as present,
                   COUNT(a.id) - SUM(a.is_present) as absent
            FROM attendance a
            JOIN students s ON a.student_id = s.id
            GROUP BY a.session_id, s.hall, a.marked_by
        '''
        rows = conn.execute(query).fetchall()

        subs = {}
        for r in rows:
            sid = r['session_id']
            hall = r['hall']
            if sid not in subs:
                subs[sid] = {}
            
            abs_query = '''
                SELECT s.register_no 
                FROM attendance a
                JOIN students s ON a.student_id = s.id
                WHERE a.session_id = ? AND s.hall = ? AND a.is_present = 0
            '''
            abs_rows = conn.execute(abs_query, (sid, hall)).fetchall()
            absents = [rx['register_no'] for rx in abs_rows]
            
            subs[sid][hall] = HallSubmission(
                hall_number=hall,
                faculty_name=r['marked_by'],
                absent_register_numbers=absents,
                total_students=r['total_attendance'],
                present_count=r['present'],
                absent_count=r['absent'],
                submitted_at=r['max_timestamp']
            )
        conn.close()
        return subs

    # ── Attendance ──

    def submit_attendance(
        self, session_id: str, hall_number: str, faculty_name: str, absent_reg_numbers: list[str]
    ) -> HallSubmission:
        with self._lock:
            conn = get_db()
            timestamp = datetime.datetime.now().isoformat()
            
            with conn:
                students = conn.execute(
                    "SELECT id, register_no FROM students WHERE hall = ? AND session_id = ?",
                    (hall_number, session_id)
                ).fetchall()
                
                total = len(students)
                absent_count = len(absent_reg_numbers)
                present_count = total - absent_count
                
                absent_set = set(absent_reg_numbers)

                for s in students:
                    stud_id = s['id']
                    reg_no = s['register_no']
                    is_present = 0 if reg_no in absent_set else 1
                    
                    conn.execute('''
                        INSERT INTO attendance (student_id, is_present, marked_by, timestamp, session_id)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (stud_id, is_present, faculty_name, timestamp, session_id))
            
            conn.close()

            return HallSubmission(
                hall_number=hall_number,
                faculty_name=faculty_name,
                absent_register_numbers=absent_reg_numbers,
                total_students=total,
                present_count=present_count,
                absent_count=absent_count,
                submitted_at=timestamp,
            )

    # ── Dashboard & Lookups ──

    def get_dashboard(self, session_id: str | None = None) -> dict[str, Any]:
        target_session = session_id or ("MODEL" if self.exam_type == "MODEL" else "FN")
        
        # Load from properties
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
        stats = {}
        session_halls = self.seating_plans.get(session_id, {})
        session_subs = self.submissions.get(session_id, {})
        
        for hall_students in session_halls.values():
            for s in hall_students:
                dept = s.department or "Unknown"
                year = s.year or "Unknown"
                if dept not in stats:
                    stats[dept] = {}
                if year not in stats[dept]:
                    stats[dept][year] = {"total": 0, "present": 0, "absent": 0}
                stats[dept][year]["total"] += 1

        for hall_number, sub in session_subs.items():
            absent_regs = set(sub.absent_register_numbers)
            hall_students = session_halls.get(hall_number, [])
            
            for s in hall_students:
                dept = s.department or "Unknown"
                year = s.year or "Unknown"
                if s.register_number in absent_regs:
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

    def lookup_student(self, register_number: str) -> dict[str, Any]:
        reg_key = register_number.strip().upper()
        
        conn = get_db()
        rows = conn.execute(
            "SELECT name, hall, seat_no, venue, session_id FROM students WHERE UPPER(register_no) = ?",
            (reg_key,)
        ).fetchall()
        conn.close()

        results = {}
        for r in rows:
            results[r['session_id']] = {
                "name": r['name'],
                "hall": r['hall'],
                "seat": r['seat_no'],
                "venue": r['venue'],
            }
        return results

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
        conn = get_db()
        row = conn.execute("SELECT created_at FROM exam_sessions LIMIT 1").fetchone()
        conn.close()
        
        if not row:
            return False
            
        created_at = row['created_at']
        if not created_at:
            return False
            
        created_date = created_at.split("T")[0]
        today = datetime.date.today().isoformat()
        
        if today != created_date:
            self.reset()
            return True
        return False

    # ── Session Management ──

    def save_token(self, token: str, role: str, expiry: float) -> None:
        with self._lock:
            conn = get_db()
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO sessions (token, role, expiry) VALUES (?, ?, ?)",
                    (token, role, expiry)
                )
            conn.close()

    def verify_token_db(self, token: str) -> dict | None:
        conn = get_db()
        row = conn.execute(
            "SELECT role, expiry FROM sessions WHERE token = ?",
            (token,)
        ).fetchone()
        conn.close()
        
        if not row:
            return None
            
        import time
        if time.time() > row['expiry']:
            self.revoke_token_db(token)
            return None
            
        return {"role": row['role']}

    def revoke_token_db(self, token: str) -> None:
        with self._lock:
            conn = get_db()
            with conn:
                conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.close()

    def clear_tokens_db(self) -> None:
        with self._lock:
            conn = get_db()
            with conn:
                conn.execute("DELETE FROM sessions")
            conn.close()


exam_state = ExamState()
