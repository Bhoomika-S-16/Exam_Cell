"""
Excel seating-plan parser and validator for the new complex layout.
"""

from __future__ import annotations

import io
import re
from typing import Any

import pandas as pd

def parse_seating_plan(file_bytes: bytes, detect_sessions: bool = False) -> tuple[dict[str, list[dict[str, Any]]] | list[dict[str, Any]], list[str]]:
    """
    Parse an uploaded Excel file.
    If detect_sessions is True, returns a dict mapping session_id -> list of students.
    Otherwise returns a flat list of students.
    """
    errors: list[str] = []
    
    # Structure for detected sessions
    session_data: dict[str, list[dict[str, Any]]] = {"FN": [], "AN": [], "MODEL": []}
    flat_students: list[dict[str, Any]] = []

    try:
        xl = pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl")
    except Exception as exc:
        return ({} if detect_sessions else []), [f"Cannot read Excel file: {exc}"]

    for sheet_name in xl.sheet_names:
        try:
            df = xl.parse(sheet_name, header=None)
            if df.empty or len(df) < 6:
                continue

            # 1. Extract Venue/Hall from E4
            venue_full = ""
            for r, c in [(3,4), (3,3), (3,5), (2,4), (4,4)]:
                if len(df) > r and len(df.columns) > c:
                    val = str(df.iloc[r, c]).strip()
                    if val and val.lower() not in ["nan", "none"]:
                        venue_full = val
                        break

            hall_number = venue_full.split("-")[0].split(",")[0].strip()
            if not hall_number or hall_number == "nan":
                hall_number = sheet_name
            
            # 2. Extract Side of Seat from A5
            side_of_seat = str(df.iloc[4, 0] if len(df.columns) > 0 else "").strip()
            
            # 3. Extract data starting from Row 6
            data_df = df.iloc[5:].copy()
            data_df.columns = ["Class", "Seat Number", "Register Number", "Student Name"] + list(data_df.columns[4:])
            data_df["Class"] = data_df["Class"].replace(["nan", "None", "", None], pd.NA).ffill()
            
            headers_row = data_df.iloc[0]
            dept_col_idx = -1
            for i, col_val in enumerate(headers_row):
                if "DEPT" in str(col_val).upper() or "DEPARTMENT" in str(col_val).upper():
                    dept_col_idx = i
                    break

            if "REGISTER" in str(headers_row.get("Register Number", "")).upper():
                data_df = data_df.iloc[1:]
            
            data_df = data_df.dropna(subset=["Register Number", "Student Name"])
            
            sheet_students = []
            for _, row in data_df.iterrows():
                reg_num = str(row["Register Number"]).strip()
                if not reg_num or reg_num.lower() in ["nan", "none"]:
                    continue
                    
                class_str = str(row["Class"]).strip()
                dept_clean = ""
                if dept_col_idx != -1 and dept_col_idx < len(row):
                    dept_clean = str(row.iloc[dept_col_idx]).strip()
                
                if not dept_clean or dept_clean.lower() in ["nan", "none"]:
                    dept_clean = class_str
                    for prefix in ["III", "II", "I"]:
                        if dept_clean.startswith(prefix + " "):
                            dept_clean = dept_clean[len(prefix):].strip()
                            break
                dept_clean = "".join(re.findall(r'[A-Za-z0-9]+', dept_clean))
                
                year = "Unknown"
                match = re.search(r'\b(I|II|III|IV|V)\b', class_str)
                if match:
                    year = match.group(0)

                seat_num = str(row["Seat Number"]).strip()
                if side_of_seat:
                    if "LEFT" in side_of_seat.upper():
                        seat_num += "L"
                    elif "RIGHT" in side_of_seat.upper():
                        seat_num += "R"

                student = {
                    "Student Name": str(row["Student Name"]).strip(),
                    "Register Number": reg_num,
                    "Roll Number": str(row.get("Roll Number", "-")).strip(),
                    "Department": dept_clean,
                    "Year": year,
                    "Hall Number": hall_number,
                    "Seat Number": seat_num,
                    "side_of_seat": side_of_seat,
                    "venue": venue_full,
                    "Class": class_str
                }
                sheet_students.append(student)

            if detect_sessions:
                # Assign to FN/AN based on sheet name
                target = "MODEL"
                if "FN" in sheet_name.upper(): target = "FN"
                elif "AN" in sheet_name.upper(): target = "AN"
                session_data[target].extend(sheet_students)
            else:
                flat_students.extend(sheet_students)

        except Exception as e:
            errors.append(f"Error in sheet '{sheet_name}': {str(e)}")

    if detect_sessions:
        # Filter out empty sessions
        session_data = {k: v for k, v in session_data.items() if v}
        if not any(session_data.values()) and not errors:
            return {}, ["No valid data found in any sheet."]
        return session_data, errors
    else:
        if not flat_students and not errors:
            return [], ["No valid data found in any sheet."]
        return flat_students, errors
