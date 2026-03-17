from flask import Flask, render_template, request, jsonify, session, redirect
import os
import pandas as pd

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

# ------------------------
# CONFIG
# ------------------------
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

FN_FILE = os.path.join(UPLOAD_FOLDER, "fn.xlsx")
AN_FILE = os.path.join(UPLOAD_FOLDER, "an.xlsx")

ADMIN_PASSWORD = "admin123"

# ------------------------
# GLOBAL DATAFRAMES
# ------------------------
fn_df = None
an_df = None

def load_excels():
    global fn_df, an_df

    fn_df = None
    an_df = None

    if os.path.exists(FN_FILE):
        fn_df = pd.read_excel(FN_FILE)
        fn_df.columns = fn_df.columns.str.strip().str.upper()

    if os.path.exists(AN_FILE):
        an_df = pd.read_excel(AN_FILE)
        an_df.columns = an_df.columns.str.strip().str.upper()

load_excels()

# ------------------------
# INDEX (STUDENT)
# ------------------------
@app.route("/")
def index():
    return render_template("index.html")

# ------------------------
# LOOKUP API
# ------------------------
@app.route("/lookup", methods=["POST"])
def lookup():
    data = request.get_json(silent=True)

    if not data or "reg" not in data:
        return jsonify({"error": "Invalid request"}), 400

    reg = str(data["reg"]).strip().upper()
    result = {}

    if fn_df is not None and "REGISTER NUMBER" in fn_df.columns:
        r = fn_df[fn_df["REGISTER NUMBER"].astype(str).str.upper() == reg]
        if not r.empty:
            row = r.iloc[0]
            result["FN"] = {
                "name": str(row["NAME"]),
                "hall": str(row["HALL"]),
                "seat": str(row["SEAT"])
            }

    if an_df is not None and "REGISTER NUMBER" in an_df.columns:
        r = an_df[an_df["REGISTER NUMBER"].astype(str).str.upper() == reg]
        if not r.empty:
            row = r.iloc[0]
            result["AN"] = {
                "name": str(row["NAME"]),
                "hall": str(row["HALL"]),
                "seat": str(row["SEAT"])
            }

    if not result:
        return jsonify({"error": "Register number not found"}), 404

    return jsonify(result)

# ------------------------
# ADMIN LOGIN
# ------------------------
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    session.clear()  # force password every time

    if request.method == "POST":
        password = request.form.get("password", "")

        if password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect("/admin")
        else:
            return render_template("admin_login.html", error="Invalid password")

    return render_template("admin_login.html")

# ------------------------
# ADMIN PANEL (PROTECTED)
# ------------------------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not session.get("admin_logged_in"):
        return redirect("/admin-login")

    # GET → show admin UI
    if request.method == "GET":
        return render_template("admin.html")

    # POST → upload Excel
    file = request.files.get("file")
    session_type = request.form.get("session")

    if not file or session_type not in ["FN", "AN"]:
        return jsonify({"status": "error"}), 400

    save_path = FN_FILE if session_type == "FN" else AN_FILE
    file.save(save_path)

    load_excels()

    return jsonify({"status": "ok"})

# ------------------------
# LOGOUT (OPTIONAL)
# ------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/admin-login")

# ------------------------
# RUN
# ------------------------
if __name__ == "__main__":
    app.run(debug=True, port=10000)
