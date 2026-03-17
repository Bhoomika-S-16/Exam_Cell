import os
import sys
import pandas as pd
import io

# Add backend to path to import excel_utils
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from excel_utils import parse_seating_plan

def create_sample_excel():
    # Create a dummy Excel file with the specific layout
    # Layout:
    # E4: Venue
    # A5: Side of Seat
    # A6: Class
    # B6, C6, D6: Headers
    # Row 7+: Data
    
    data = [
        [None] * 10, # Row 1
        [None] * 10, # Row 2
        [None] * 10, # Row 3
        [None, None, None, None, "Main Hall - 1st Floor"], # Row 4 (E4 at Index 3,4)
        ["Left Side"], # Row 5 (A5 at Index 4,0)
        ["III B.COM", "Desk No", "Register Number", "Student Name", "Dept."], # Row 6 (index 5)
        [None, "D1", "REG001", "John Doe", "B.COM"], # Row 7
        [None, "D2", "REG002", "Jane Smith", "B.COM"], # Row 8
    ]
    
    df = pd.DataFrame(data)
    
    buf = io.BytesIO()
    df.to_excel(buf, index=False, header=False, engine='openpyxl')
    return buf.getvalue()

def test_parsing():
    print("Generating sample Excel...")
    excel_bytes = create_sample_excel()
    
    print("Testing parse_seating_plan...")
    students, errors = parse_seating_plan(excel_bytes)
    
    if errors:
        print(f"FAILED: Errors found: {errors}")
        return
        
    print(f"SUCCESS: Found {len(students)} students.")
    for s in students:
        print(f" - {s['Student Name']} ({s['Register Number']}) | Dept: {s['Department']} | Class: {s['Class']} | Side: {s['side_of_seat']} | Venue: {s['venue']}")
        
    # Verify robust venue extraction (testing fallback to other cells)
    print("Testing robust venue (E4 merged)...")
    # Simulate a merged cell where E4 is empty but D4 has the value
    merged_data = [
        [None] * 10, [None] * 10, [None] * 10,
        [None, None, None, "Merged Hall - 1st Floor", None], # D4 (Index 3,3)
        ["Left Side"],
        ["III B.COM", "Desk No", "Register Number", "Student Name"],
        [None, "D1", "REG001", "John Doe"],
    ]
    df_merged = pd.DataFrame(merged_data)
    buf_merged = io.BytesIO()
    df_merged.to_excel(buf_merged, index=False, header=False, engine='openpyxl')
    students_merged, _ = parse_seating_plan(buf_merged.getvalue())
    assert students_merged[0]['venue'] == "Merged Hall - 1st Floor"
    assert students_merged[0]['Hall Number'] == "Merged Hall"
    print("SUCCESS: Robust venue extraction verified.")

    # Verify revised fields (Cleaned Dept and L/R Seats)
    assert len(students) == 2
    assert students[0]['Department'] == "BCOM" # B.COM -> BCOM
    assert students[0]['Seat Number'] == "D1L"  # D1 + Left Side -> D1L
    assert students[0]['venue'] == "Main Hall - 1st Floor"
    
    print("Verification complete!")

if __name__ == "__main__":
    test_parsing()
