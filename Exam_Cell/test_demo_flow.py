"""Quick end-to-end API test for the invigilator demo flow."""
import urllib.request
import urllib.parse
import json

BASE = "http://localhost:8000/api"

# Step 1: Setup exam
params = urllib.parse.urlencode({"date": "2026-02-20", "exam_type": "CIA", "session": "Forenoon"}).encode()
req = urllib.request.Request(f"{BASE}/demo/setup-exam", data=params, method="POST")
with urllib.request.urlopen(req) as r:
    print("Setup exam:", json.loads(r.read()))

# Step 2: Upload sample Excel using multipart
sample = r"c:\Users\bhoom\OneDrive\Desktop\Exam_Cell\frontend\sample_seating.xlsx"
boundary = "WebKitFormBoundaryTest1234"
with open(sample, "rb") as f:
    file_data = f.read()

cdisp = 'Content-Disposition: form-data; name="file"; filename="sample_seating.xlsx"'
ctype_file = "Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

body = (
    ("--" + boundary + "\r\n").encode()
    + (cdisp + "\r\n").encode()
    + (ctype_file + "\r\n\r\n").encode()
    + file_data
    + ("\r\n--" + boundary + "--\r\n").encode()
)

req2 = urllib.request.Request(
    f"{BASE}/demo/upload-seating",
    data=body,
    method="POST",
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
)
with urllib.request.urlopen(req2) as r:
    data = json.loads(r.read())
    print("Upload seating:", data)

# Step 3: Get halls
with urllib.request.urlopen(f"{BASE}/invigilator/halls") as r:
    data = json.loads(r.read())
    print("Halls:", data["halls"], "| Exam:", data["exam"])

# Step 4: Get students for first hall
first_hall = data["halls"][0]
with urllib.request.urlopen(f"{BASE}/invigilator/students/{first_hall}") as r:
    data = json.loads(r.read())
    students = data["students"]
    print(f"{first_hall} students ({len(students)}):", [s["student_name"] for s in students[:3]], "...")
    first_reg = students[0]["register_number"]

# Step 5: Submit attendance (mark first student absent)
payload = json.dumps({
    "hall_number": first_hall,
    "faculty_name": "Dr. Test Invigilator",
    "absent_register_numbers": [first_reg],
}).encode()
req3 = urllib.request.Request(
    f"{BASE}/invigilator/attendance/submit",
    data=payload,
    method="POST",
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req3) as r:
    data = json.loads(r.read())
    print("Submitted attendance:", data)

# Step 6: Reset
req4 = urllib.request.Request(f"{BASE}/demo/reset", data=b"", method="POST")
with urllib.request.urlopen(req4) as r:
    print("Reset:", json.loads(r.read()))

print("\nALL TESTS PASSED!")
