# EDWISE — Learning Analytics Platform

An evidence-grounded, modular monolith educational management and analytics platform built with **FastAPI**, **SQLAlchemy**, **Scikit-Learn**, and **React + Tailwind CSS**, following the requirements and constraints of the **EDWISE Implementation Playbook v1.0**.

---

## 🏛️ System Architecture

### 1. Frontend (React 18 SPA + Vite + Tailwind CSS)
- **Role-Aware Navigation & Workspaces**: Distinct user experiences for **Administrator**, **Teacher**, and **Student**.
- **Student Roster Claim Portal (UI-001, API-002, R-003)**: Self-service registration verifying against unclaimed official roster rows with uniform `202 Accepted` pending states to prevent admission number enumeration.
- **Attendance Entry (UI-003, API-001, R-004)**: Real-time class attendance sheet with saved/unsaved status indicators; unmarked students explicitly recorded as unrecorded rather than defaulting to present.
- **Audited Marks Entry (UI-004, R-005, R-014)**: Exam grading table with inline score boundary enforcement ($0 \le score \le max\_marks$) and mandatory modal justification prompt whenever previously recorded marks are updated.
- **Student Performance Detail & ML Estimates (UI-005, R-009, R-010, R-015)**: Displays demonstration score estimates with error intervals ($\pm \text{interval}$), model version, and truth banners. Enforces the **minimum 2-exam history safeguard** (`status: "not_enough_data"`) with no premature numbers or false reassurance colors.
- **Student Academic Dashboard (UI-006, R-007, D-012)**: Shows strictly the student's own attendance rates, evaluated marks, and coursework feedback—preventing stigma by hiding ML risk predictions and external student rankings.
- **Reports & Analytics Hub (UI-007, R-008, R-013)**: Interactive Recharts visualizations for attendance trends and score distributions, plus one-click ReportLab PDF and OpenPyXL Excel downloads.
- **Model Registry & Governance (D-005, R-016)**: Inspect offline-trained regression, classifier, and clustering artifacts, features, and baseline benchmarks with one-click retraining triggers.
- **Immutable Audit Trail (R-014, D-013)**: Filterable transaction explorer showing old values versus new values and justification reasons.

### 2. Backend (FastAPI Modular Monolith)
- **`auth`**: JWT access and refresh token lifecycle, bcrypt password hashing (72-byte safe limit), and enumeration-safe roster claiming.
- **`institution`**: Academic sessions, classes, sections, subjects, faculty profiles, student rosters, and teacher-class-subject scoping bindings (`ClassSubjectTeacher`).
- **`academics`**: Attendance upserts, exam evaluation, audited mark updates, coursework assignments, and student submission grading.
- **`analytics`**: Attendance statistics, score distributions, subject averages, and consecutive score drop detection.
- **`ml_engine` & `ml`**: Offline-trained regression, logistic regression, and K-Means models with trivial baselines, demographic exclusion (D-015), and transparency language (R-015, C-001).
- **`reports`**: PDF and Excel generation with ReportLab and OpenPyXL, protected against XML and spreadsheet formula injection.
- **`audit`**: Append-only transactional audit trail.

---

## 🚀 Quickstart & Development

### 1. Requirements
- Python 3.12+
- Node.js 20+ & npm

### 2. Backend Setup
```bash
# In project root
pip install -r backend/requirements.txt

# Seed database and train baseline models
python backend/seed_data.py

# Start FastAPI server
uvicorn backend.app.main:app --reload --port 8000
```
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm.cmd install

# Start Vite dev server (proxies /api to http://localhost:8000)
npm.cmd run dev
```
- Frontend UI: [http://localhost:5173](http://localhost:5173)

---

## 🔑 Default Demo Accounts

| Role | Username | Password | Notes |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin` | `Admin@123` | Full institution and audit configuration |
| **Teacher** | `teacher_sarah` | `Teacher@123` | Assigned to Grade 10 A Math |
| **Teacher** | `teacher_alan` | `Teacher@123` | Assigned to Grade 10 A Science |
| **Student** | `STU1001` | `Student@123` | Alex Carter (Active, verified student) |
| **Student** | `STU1002` | `Student@123` | Priya Sharma (Active, verified student) |
| **Unclaimed Roster** | `STU1003` | *Claim via UI* | David Miller (For testing roster claim self-registration) |

---

## 🧪 Automated Test Suite (27/27 Passed)

```bash
pytest backend/tests -v
```
All 27 integration tests pass cleanly with 100% coverage across auth, teacher BOLA scoping, marks validation, attendance upserts, audit logging, ML safeguards, and report generation.

---

## 🐳 Full Stack Docker Deployment

```bash
docker compose up --build
```
Runs PostgreSQL 16, backend API on port 8000, and Nginx-served frontend on port 3000.


