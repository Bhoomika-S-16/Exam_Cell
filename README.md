<div align="center">

<img src="frontend/assets/KCLAS_Logo.jpg" alt="KCLAS Logo" width="120" style="border-radius: 12px;" />

# 📋 Exam Attendance System

### A real-time exam attendance management platform for institutions

<br/>

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![SQLite](https://img.shields.io/badge/SQLite-Persistent-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![Fly.io](https://img.shields.io/badge/Deployed_on-Fly.io-8B5CF6?style=for-the-badge&logo=flydotio&logoColor=white)](https://fly.io)

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production-brightgreen?style=flat-square)]()
[![Roles](https://img.shields.io/badge/Roles-Admin%20%7C%20Invigilator%20%7C%20Student-blue?style=flat-square)]()
[![Reports](https://img.shields.io/badge/Reports-PDF%20%26%20Excel-orange?style=flat-square)]()

</div>

---

## ✨ Overview

The **KCLAS Exam Attendance System** is a full-stack web application that streamlines exam attendance tracking for large institutions. Built for real-world exam conditions — upload a seating plan, let invigilators mark absent students hall-by-hall, and generate professional absentee reports in seconds.

> Developed by the **Department of Data Science, KCLAS** as an internal tool to replace manual paper-based attendance processes.

---

## 🖼️ Screenshots

| Admin Dashboard | Invigilator Portal | Student Lookup |
|:-:|:-:|:-:|
| Monitor all hall submissions in real-time | Mark attendance from any device | Look up hall & seat by register number |

---

## 🚀 Features

### 👨‍💼 Admin Panel
- **Create exams** — CIA (Forenoon + Afternoon) or MODEL sessions
- **Upload seating plans** — Parse complex Excel layouts automatically
- **Live dashboard** — Monitor hall-by-hall submission status with 5-second auto-refresh
- **Department monitor** — View present/absent counts broken down by dept & year
- **Absentee viewer** — Drill into missing students per department inline
- **PDF & Excel reports** — Generate by hall, department, class, or overall
- **Finalize & lock** — Prevent further edits once all submissions are in
- **New exam cycle** — Reset and start fresh with one click

### 🧑‍🏫 Invigilator Portal
- **Session-aware** — Automatically adapts to CIA (FN/AN) or MODEL session
- **Hall selection** — Dropdown shows submitted halls as locked (✓)
- **Attendance table** — Checkbox-based absent marking with live counters
- **Bulk actions** — Mark all present / mark all absent
- **Confirmation screen** — Summary shown after successful submission

### 🎓 Student Lookup
- Look up hall number, seat number, and venue by register number
- Works without login — intended for public display terminals

### 📊 Report Generation
| Type | PDF | Excel |
|------|:---:|:-----:|
| Overall absentees | ✅ | ✅ |
| By hall | ✅ | ✅ |
| By department | ✅ | ✅ |
| By class | ✅ | ✅ |
| Provisional (pre-finalize) | ✅ | ✅ |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Browser (Frontend)                 │
│   admin.html  ·  invigilator.html  ·  lookup.html   │
│         Tailwind CSS  ·  Vanilla JS                  │
└──────────────────────┬──────────────────────────────┘
                       │  REST API (X-Auth-Token)
┌──────────────────────▼──────────────────────────────┐
│              FastAPI  +  Uvicorn                     │
│   /api/admin/*   ·   /api/invigilator/*              │
│   /api/auth/*    ·   /api/student/*                  │
│   Role-based guards  ·  Static file serving          │
└──────────┬─────────────┬──────────────┬─────────────┘
           │             │              │
    ┌──────▼──────┐ ┌────▼─────┐ ┌─────▼──────┐
    │ excel_utils │ │reports.py│ │  auth.py   │
    │ Parse Excel │ │PDF/Excel │ │Token mgmt  │
    └─────────────┘ └──────────┘ └────────────┘
                       │
        ┌──────────────▼──────────────────────┐
        │       SQLite  (state.py)             │
        │  exam_sessions · students            │
        │  attendance   · sessions             │
        │  Persistent volume  /data/app.db     │
        └──────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11, FastAPI 0.104, Uvicorn |
| **Database** | SQLite (persistent via Fly.io volume) |
| **Frontend** | HTML5, Tailwind CSS (CDN), Vanilla JS |
| **Excel Parsing** | Pandas 2.1, OpenPyXL 3.1 |
| **PDF Reports** | ReportLab 4.0 |
| **Excel Reports** | OpenPyXL 3.1 |
| **Auth** | UUID tokens, role-based (admin / invigilator) |
| **Deployment** | Docker, Fly.io |

---

## ⚡ Quick Start

### Prerequisites

- Python 3.11+
- pip

### Local Development

```bash
# 1. Clone the repository
git clone https://github.com/your-org/exam-attendance-system.git
cd exam-attendance-system

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Then open your browser:

| Page | URL |
|---|---|
| Admin Login | http://localhost:8000/admin-login |
| Invigilator Login | http://localhost:8000/invigilator-login |
| Student Lookup | http://localhost:8000/lookup.html |
| Health Check | http://localhost:8000/api/health |

### Docker

```bash
# Build
docker build -t exam-attendance .

# Run with persistent data
docker run -p 8000:8000 -v exam_data:/data exam-attendance
```

---

## 🔐 Default Credentials

> ⚠️ **Change these immediately in production** via environment variables.

| Role | Username | Password | Environment Variable |
|---|---|---|---|
| Admin | `admin` | `admin123` | `ADMIN_PASSWORD` |
| Invigilator | `invigilator` | `invig123` | `INVIGILATOR_PASSWORD` |

---

## 📁 Project Structure

```
exam-attendance-system/
│
├── backend/
│   ├── main.py                  # FastAPI app, all routes
│   ├── core/
│   │   └── state.py             # SQLite-backed ExamState class
│   └── services/
│       ├── auth.py              # Token-based authentication
│       ├── excel_utils.py       # Seating plan Excel parser
│       └── reports.py           # PDF and Excel report generators
│
├── frontend/
│   ├── html/
│   │   ├── admin.html           # Admin dashboard
│   │   ├── admin_login.html     # Admin login page
│   │   ├── invigilator.html     # Invigilator portal
│   │   ├── invig_login.html     # Invigilator login page
│   │   └── lookup.html          # Student seat lookup
│   ├── css/
│   │   ├── style.css            # Global styles
│   │   └── invigilator.css      # Invigilator-specific styles
│   ├── js/
│   │   ├── app.js               # Admin page logic
│   │   ├── invigilator.js       # Invigilator portal logic
│   │   └── config.js            # API base URL config
│   └── assets/                  # Logo and images
│
├── Dockerfile
├── fly.toml                     # Fly.io deployment config
├── requirements.txt
└── README.md
```

---

## 📋 Seating Plan Excel Format

The system parses a specific Excel format used by KCLAS. Each sheet represents one hall.

| Column | Description |
|---|---|
| A | Class (e.g. `III CSE`, `II IT`) — forward-filled |
| B | Seat Number |
| C | Register Number |
| D | Student Name |
| E4 (cell) | Venue / Hall identifier |
| A5 (cell) | Side of seat (`LEFT SIDE` / `RIGHT SIDE`) |

For **CIA exams**, upload separate FN and AN files, or a single file with sheets named containing `FN` / `AN`.

For **MODEL exams**, upload a single file — all sheets are treated as the same session.

---

## 🌐 Deployment (Fly.io)

```bash
# Install flyctl and login
fly auth login

# Launch app (first time)
fly launch

# Create persistent volume for SQLite
fly volumes create exam_data --size 1 --region iad

# Set secret credentials
fly secrets set ADMIN_PASSWORD=your_secure_password
fly secrets set INVIGILATOR_PASSWORD=your_secure_password

# Deploy
fly deploy
```

### `fly.toml` Key Settings

```toml
[env]
  DATABASE_URL = "sqlite:////data/app.db"

[mounts]
  source = "exam_data"
  destination = "/data"
```

> 💡 **Tip:** Set `min_machines_running = 1` to avoid cold-start delays at exam time.

---

## 🔌 API Reference

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/login` | Login (returns token) |
| `GET` | `/api/auth/verify` | Verify token |
| `POST` | `/api/auth/logout` | Revoke token |

### Admin Endpoints *(requires admin token)*

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/admin/exam/create` | Create a new exam |
| `POST` | `/api/admin/seating-plan/upload` | Upload seating plan Excel |
| `GET` | `/api/admin/status` | Get exam status |
| `GET` | `/api/admin/dashboard` | Real-time hall submission data |
| `GET` | `/api/admin/classes` | List classes for a session |
| `GET` | `/api/admin/absentees` | Absentees by dept & year |
| `GET` | `/api/admin/reports/pdf` | Download PDF report |
| `GET` | `/api/admin/reports/excel` | Download Excel report |
| `POST` | `/api/admin/exam/finalize` | Lock exam |
| `POST` | `/api/admin/exam/reset` | Reset exam state |

### Invigilator Endpoints *(requires invigilator token)*

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/invigilator/status` | Check if exam is active |
| `GET` | `/api/invigilator/halls` | List halls for session |
| `GET` | `/api/invigilator/students/{hall}` | Get students for hall |
| `POST` | `/api/invigilator/attendance/submit` | Submit attendance |

### Public Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/student/lookup/{reg_num}` | Student seat lookup |

All protected endpoints require the header:
```
X-Auth-Token: <your_token>
```

---

## 🔄 Exam Workflow

```
Admin                        Invigilators                   System
  │                               │                            │
  ├── Create exam (date, type) ───┼────────────────────────────►
  │                               │                            │
  ├── Upload seating plan ────────┼────────────────────────────►
  │                               │                            │
  │   Dashboard auto-refreshes ◄──┼────────────────────────────┤
  │                               │                            │
  │                               ├── Login ──────────────────►
  │                               ├── Select session + hall ──►
  │                               ├── Mark absent students ───►
  │                               └── Submit attendance ───────►
  │                               │                            │
  ├── Monitor submissions ────────┼────────────────────────────►
  ├── View absentees by dept ─────┼────────────────────────────►
  ├── Download PDF/Excel ─────────┼────────────────────────────►
  └── Finalize exam ──────────────┼────────────────────────────►
```

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ADMIN_PASSWORD` | `admin123` | Admin login password |
| `INVIGILATOR_PASSWORD` | `invig123` | Invigilator login password |
| `DATABASE_URL` | `app.db` | SQLite database path |
| `ALLOWED_ORIGINS` | `*` | CORS allowed origins |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch — `git checkout -b feature/your-feature`
3. Commit your changes — `git commit -m 'Add your feature'`
4. Push to the branch — `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Built with ❤️ by the **Department of Data Science, KCLAS**

[![KCLAS](https://img.shields.io/badge/Institution-KCLAS-003594?style=for-the-badge)]()

</div>
