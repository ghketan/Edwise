# EDWISE — Frontend Architectural & UX/UI Specification
**Version:** 1.0.0  
**Target System:** EDWISE Learning Analytics Platform  
**Specification Basis:** EDWISE Implementation Playbook v1.0, Academic Integrity Guardrails, & Modular Monolith API Contracts  
**Target Stack:** React 18 SPA + Vite + Tailwind CSS + Recharts + Lucide Icons  

---

## 1. Executive Overview & Design Philosophy

The EDWISE frontend is an **evidence-grounded, role-aware academic management and learning analytics single-page application (SPA)**. Built to accompany the FastAPI modular monolith backend, it provides dedicated, scoped interfaces for three primary stakeholders: **Administrators**, **Teachers**, and **Students**.

Unlike conventional educational dashboards that casually display vanity metrics or aggregate averages, EDWISE is architected around **strict academic integrity, algorithmic transparency, and psychological safety**:

1. **Truth in UI & Zero False Reassurance (R-015, C-001):**
   - The UI never renders optimistic green "on track" states when underlying data is missing or stale.
   - Blank exam marks are strictly rendered as *Unrecorded / Blank* and are never coerced to zero.
   - Unmarked attendance records are rendered as *Not Recorded* and never assumed to be present.
   - Missing data states are plainly declared: *"Not enough data"* rather than displaying speculative numbers.
2. **Strict Minimum 2-Exam Safeguard for ML Estimates (R-009, R-010, UI-005):**
   - Predictive machine learning models (Linear Regression, Random Forest, XGBoost) and at-risk classifications are withheld if a student has fewer than 2 graded exams. In this state, no numeric score or color band is rendered.
   - When displayed, predictions are explicitly labeled as **"Estimates, not academic verdicts"**, indicating model version, uncertainty interval ($\pm \Delta$), data-through date, and training provenance.
3. **Anti-Stigma Student Experience (D-012, UI-006):**
   - Students have full visibility into their own records (attendance, graded coursework, exam marks, doubt answers, and personalized study tips).
   - Machine learning risk tags ("At-Risk", "Challenging", "Probable Fail") are **strictly prohibited** from the student view. Only teachers and administrators may inspect diagnostic risk indicators.
4. **Mandatory Audited Modifications (R-014, D-013, UI-004):**
   - Any modification to previously recorded student marks or historical attendance triggers an inescapable modal requiring an explicit academic justification reason. This reason is atomically committed to the immutable audit trail.
5. **Anti-Enumeration Roster Claiming (UI-001, API-002, R-003):**
   - Student self-registration returns a uniform `202 Accepted` response regardless of whether an admission number is valid, invalid, or already claimed, mitigating enumeration and reconnaissance attacks.

---

## 2. Technology Stack & Client Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        EDWISE React SPA (Vite)                         │
├────────────────────────────────────────────────────────────────────────┤
│  Routing & Guards:     React Router v6 (Role-Based ProtectedRoute)     │
│  State Management:     React Context (AuthContext) + Local React State │
│  Styling & UI Kit:     Tailwind CSS v3 + Lucide React Icons            │
│  Charts & Visuals:     Recharts (Bar, Line, Cartesian, Responsive)     │
│  HTTP & Security:      Axios / Fetch with JWT Interceptor Lifecycle    │
│  Validation:           In-browser pre-flight schema & boundary checks  │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ HTTPS / JSON Bearer Auth
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend Engine                          │
│  (/api/v1/auth, /institution, /academics, /analytics, /ml, /reports)   │
└────────────────────────────────────────────────────────────────────────┘
```

### Core Libraries & Utilities
- **Framework:** `React 18` with functional components and hooks (`useState`, `useEffect`, `useMemo`, `useCallback`, `useRef`).
- **Build Tool:** `Vite` with fast HMR and optimized production bundling.
- **Styling Engine:** `Tailwind CSS` utilizing a clean, institutional palette (Slate neutral background, Indigo primary accents, Emerald success indicators, Rose alerts, and Amber warnings).
- **Iconography:** `lucide-react` for semantic iconography (GraduationCap, ShieldCheck, Sliders, Trophy, CalendarCheck, BookOpen, AlertTriangle).
- **Data Visualizations:** `Recharts` for accessible SVG charts (exam grade distributions, attendance trend lines, student vs. class comparative metrics).
- **File Handling:** Multipart form-data clients for bulk CSV imports and student homework attachments (PDF/JPEG/PNG).

---

## 3. Global Navigation & Layout Architecture

### 3.1 Layout Structure (`AppLayout`)
The master application shell consists of:
- **Top Navigation Bar (`Navbar.jsx`):**
  - Brand header with institution logo and title.
  - Active academic session badge (e.g., `Active Session: 2026-2027`).
  - Active user identity pill: displays user name, role badge (`ADMINISTRATOR`, `TEACHER`, or `STUDENT`), and associated class/subject scopes.
  - One-click Logout button that invalidates tokens and purges client memory.
- **Collapsible Sidebar (`Sidebar.jsx`):**
  - Dynamically renders navigation links matching the authenticated user's assigned role.
  - Responsive drawer on mobile viewports (< 768px); fixed sticky sidebar on desktop.
- **Main Viewport (`<main>`):**
  - Contained, responsive container (`max-w-7xl mx-auto p-4 sm:p-6`) with smooth scrolling and error boundary wrappers.

### 3.2 Role-Based Routing Matrix

| Route Path | Component | Permitted Roles | Description |
| :--- | :--- | :--- | :--- |
| `/login` | `Login.jsx` | Public | Authentication & student self-service roster claiming |
| `/` | `RoleRedirect` | Authenticated | Redirects to `/admin`, `/teacher`, or `/student` based on JWT role |
| `/admin` | `AdminDashboard.jsx` | `ADMINISTRATOR` | Institution KPI overview & quick action hub |
| `/admin/users` | `UserManagement.jsx` | `ADMINISTRATOR` | User accounts, role assignment, verification status |
| `/admin/setup` | `SetupClasses.jsx` | `ADMINISTRATOR` | Sessions, classes, sections, subjects, teacher assignments |
| `/admin/roster` | `RosterImport.jsx` | `ADMINISTRATOR` | Student enrollment & interactive CSV bulk parser |
| `/admin/rules` | `RecommendationRules.jsx` | `ADMINISTRATOR` | Configurable intervention & risk rule thresholds |
| `/admin/models` | `ModelRegistry.jsx` | `ADMINISTRATOR` | ML model governance, feature drift, and active model switcher |
| `/admin/audit` | `AuditLogs.jsx` | `ADMINISTRATOR` | Filterable immutable audit trail explorer |
| `/teacher` | `TeacherDashboard.jsx` | `TEACHER`, `ADMINISTRATOR` | Scoped class overview, today's schedule, doubts badge |
| `/teacher/attendance` | `AttendanceEntry.jsx` | `TEACHER`, `ADMINISTRATOR` | Real-time attendance grid (subject & full-day) |
| `/teacher/marks` | `MarksEntry.jsx` | `TEACHER`, `ADMINISTRATOR` | Exam grading table, CSV import, audited modification modal |
| `/teacher/students/:id` | `StudentDetail.jsx` | `TEACHER`, `ADMINISTRATOR` | Multi-exam trajectory, class comparative charts, ML estimates |
| `/teacher/assignments` | `TeacherAssignments.jsx`| `TEACHER`, `ADMINISTRATOR` | Coursework creation, submission viewer, grading & feedback |
| `/teacher/analytics` | `AnalyticsReports.jsx` | `TEACHER`, `ADMINISTRATOR` | Score distributions, K-Means clustering, PDF/Excel export |
| `/student` | `StudentDashboard.jsx` | `STUDENT` | Personal academic hub, diagnostics, simulator, badges |
| `/student/assignments` | `StudentAssignments.jsx` | `STUDENT` | Homework submission portal with PDF file dropzone |

---

## 4. Detailed Role-Specific Workspaces & Page Specifications

```
                       ┌─────────────────────────┐
                       │     Authentication      │
                       │   & Roster Claiming     │
                       └────────────┬────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         ▼                          ▼                          ▼
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  Administrator   │      │     Teacher      │      │     Student      │
│    Workspace     │      │    Workspace     │      │    Workspace     │
├──────────────────┤      ├──────────────────┤      ├──────────────────┤
│ • Setup Classes  │      │ • Daily Attend.  │      │ • 3-Pillar Diag. │
│ • Roster Import  │      │ • Audited Marks  │      │ • What-If Sim.   │
│ • Model Registry │      │ • Student Detail │      │ • Attendance Goal│
│ • Audit Trail    │      │ • AI Lesson Plan │      │ • Badges & Rank  │
│ • User Mgmt      │      │ • Assignments    │      │ • Homework Drop  │
│ • Rec. Rules     │      │ • Doubt Hub      │      │ • Doubt Q&A      │
└──────────────────┘      └──────────────────┘      └──────────────────┘
```

---

### 4.1 Authentication & Student Roster Claim Portal (`/login`)

#### Purpose
Handles role-based authentication and self-service account claiming for students pre-imported into institutional rosters.

#### Key Sections & Elements
1. **Interactive Tab Switcher:**
   - Smooth toggle between **"Sign In"** (all registered users) and **"Student Registration"** (unclaimed roster accounts).
2. **Sign In View:**
   - Username and password inputs with field validation.
   - Quick Demo Credential Pills (`Admin`, `Teacher Sarah`, `Student Alex`) enabling one-click test logins during demonstrations.
   - Clear error banner displaying standardized server error messages without leaking stack traces.
3. **Student Roster Claim View (UI-001, API-002, R-003):**
   - Fields: Official Admission Number (`e.g., STU1003`), Class Selector dropdown, Password creation (8 to 72 characters, enforced bcrypt limit), optional Contact Email and Phone.
   - Informational Callout: Explains that registration matches official records uploaded by institutional administrators.
   - **Anti-Enumeration Uniform Response:** When submitted, the form displays a uniform informational alert: *"Registration request received and being processed against official rosters."* It never reveals whether the admission number existed or was previously claimed.

---

### 4.2 Administrator Workspace

#### 4.2.1 Setup Classes & Institution Structure (`/admin/setup`)
- **Academic Session Selector:** Active session badge with creation form for upcoming academic years.
- **Class & Section Manager:** Displays configured grades (`Grade 10`, `Grade 11`) and sections (`A`, `B`). Allows creation with capacity limits.
- **Subject Registry:** Lists subjects with unique institutional codes (`MATH101`, `SCI101`).
- **Teacher Assignment Scoping Table (`ClassSubjectTeacher`):**
  - Crucial authorization matrix defining teacher BOLA boundaries.
  - Interactive table showing Class, Section, Subject, and Assigned Faculty.
  - Action buttons to add bindings or revoke teacher access.

#### 4.2.2 Roster Import & Pre-Flight Validation (`/admin/roster`)
- **Two Import Modalities:**
  1. *Manual Single Student Entry Form:* Direct entry of Admission Number, Full Name, Class ID, Roll Number, and Email.
  2. *Bulk CSV Import Engine (UI-002):*
     - Pasteable CSV text area or drag-and-drop file upload.
     - **Pre-Flight Parsing & In-Browser Validation:** Before sending requests to the backend, an interactive client parser audits every row.
     - Displays two dynamic preview panes:
       - **Valid Rows Table:** Shows parsed admission numbers, names, and class IDs with a green checkmark.
       - **Rejection Log:** Displays row-by-row syntax or foreign-key errors (e.g., *"Row 4: Class ID '99' does not exist"*, *"Row 7: Missing admission number"*).
     - Commit Button remains disabled until all blocking syntax errors are resolved, ensuring zero partial-failure corruptions.

#### 4.2.3 Model Registry & Algorithmic Governance (`/admin/models`)
- **Truth Banner (R-015):** Explicitly states: *"Models trained offline on benchmark educational datasets. Demonstration performance estimates only."*
- **Model Registry Card Grid:**
  - Displays each trained model artifact: **Linear Regression**, **Random Forest Regressor**, and **XGBoost Regressor**.
  - Displays metadata: Model Version, Split Methodology (Student-grouped CV), Baseline MAE/RMSE comparisons, and Exclusion of Demographic Attributes (D-015 compliant).
  - **Active Model Selector:** Teachers use whichever model is marked active. Admins can click *"Set as Active Inference Engine"* with an immediate UI status update.
- **Feature Drift Diagnostic Table:**
  - Compares baseline training distributions against live operational student data across key features (attendance percentage, assignment completion rate, exam averages).
  - Emits color-coded alerts if distribution shifts exceed acceptable thresholds.

#### 4.2.4 Recommendation Rule Thresholds (`/admin/rules`)
- Configurable rule builder controlling automated academic intervention prompts:
  - *Attendance Deficit Threshold:* Interactive range slider (default: `75.0%`).
  - *Consecutive Exam Drop Delta:* Range slider (default: `10.0% drop over 2 consecutive exams`).
  - *Homework Non-Completion Threshold:* Range slider (default: `30% pending assignments`).
- Save changes button with confirmation toast and immediate application across teacher student detail pages.

#### 4.2.5 Immutable Audit Trail Explorer (`/admin/audit`)
- Real-time audit log viewer enforcing **R-014** and **D-013**.
- **Interactive Search & Filter Bar:**
  - Filter by Action (`marks.updated`, `attendance.recorded`, `user.verified`, `model.switched`).
  - Filter by User ID, Date Range, or Target Student ID.
- **Audit Detail Table:**
  - Columns: Timestamp (UTC converted to local), Actor Name & Role, Action Type, Target Entity, Old Value vs. New Value diff pill, and Mandatory Justification Reason.

---

### 4.3 Teacher Workspace

#### 4.3.1 Attendance Entry Sheet (`/teacher/attendance`)
- **Scope Selector:** Dropdown automatically populated strictly with classes and subjects assigned to the logged-in teacher (`ClassSubjectTeacher` scoping).
- **Date Picker & Full-Day Toggle:**
  - Calendar picker defaulted to today's local date.
  - Switcher between *Single Subject Attendance* and *Full-Day Homeroom Attendance*.
- **Interactive Attendance Table (UI-003, R-004):**
  - Lists enrolled students ordered by roll number and name.
  - **5 Explicit State Buttons per Row:**
    - `[ Present ]` (Emerald)
    - `[ Absent ]` (Rose)
    - `[ Late ]` (Amber)
    - `[ Excused ]` (Sky)
    - `[ Not Recorded ]` (Slate outline - default initial state)
  - **Strict Principle:** Unmarked students are explicitly saved as *Not Recorded*—never implicitly defaulted to present.
- **Batch Shortcuts:**
  - *"Mark All Unmarked as Present"* (convenience helper with confirmation).
  - *"Clear All"*.
- **Unsaved State Indicator & Conflict Guard:**
  - Sticky footer banner showing dirty state: *"You have unsaved changes for 24 students"*.
  - Save button with loading spinner and timestamp badge: *"Last saved: 11:42 AM by Teacher Sarah"*.

#### 4.3.2 Audited Marks Entry Table (`/teacher/marks`)
- **3-Tier Cascade Selector:** `Select Class` $\rightarrow$ `Select Subject` $\rightarrow$ `Select Exam`.
- **Exam Management Tools:**
  - *"Create New Exam"* modal: Exam Name, Exam Type (`unit_test`, `mid_term`, `final`), Max Marks (e.g., 100), Weightage, Exam Date, and Time Slot.
  - *"Upload Exam Datesheet"* button: Supports PDF/Image uploads with direct download links for students.
  - *"Bulk CSV Marks Import"* button: Uploads structured CSV with automated roll number/admission number matching.
- **Grading Grid (UI-004, R-005):**
  - Columns: Roll Number, Admission Number, Student Name, Numeric Score Input, Absent Toggle Checkbox, Remarks / Feedback Input.
  - **In-Line Boundary Validation:** Cell borders immediately flash rose if input $< 0$ or $> \text{Max Marks}$. Form submission is locked while invalid cells exist.
  - **Blanks vs. Zero Distinction:** Leaving a cell empty records a `null` score (Blank/Pending). Teachers must check the *"Absent"* box to record formal absence.
- **Mandatory Audit Modal (`AuditModal.jsx`):**
  - If a teacher edits any mark that was previously saved, clicking *"Save Evaluation"* intercepts the transaction.
  - An unavoidable modal appears:
    > *"Audited Evaluation Update (R-014): You are modifying previously recorded marks for one or more students. Academic regulations require a mandatory reason for this update."*
  - Requires a descriptive text reason (e.g., *"Re-evaluation of question 4 after student contest"*). Commits atomically to `/api/v1/marks/audited`.

#### 4.3.3 Student Academic Detail & ML Diagnostics (`/teacher/students/:id`)
- **Student Profile Header:** Full name, admission number, roll number, class & section, contact details.
- **Truth Banner (R-015):** Displays model governance metadata: Active algorithm, feature list, and training source.
- **Historical Performance Trajectory:**
  - Interactive Recharts bar/line chart plotting student exam scores chronologically alongside class subject averages.
- **ML Grade Estimate & Uncertainty Band (R-009, R-010):**
  - **Minimum 2-Exam Safeguard Enforcement:**
    - If the student has $< 2$ graded exams, the UI renders an informational slate box:
      > **"Not Enough Data for Performance Estimate"**  
      > *In accordance with academic fairness safeguards, score estimates require at least 2 historical exam records. No speculative prediction is rendered.*
    - Zero numeric scores and zero false-reassurance colors are rendered in this state.
  - If $\ge 2$ exams exist:
    - Displays point estimate (e.g., `78.4%`) with explicit error bounds: `[ ±4.2% Interval ]`.
    - Shows estimated risk category: `Low Risk`, `Moderate Risk`, or `High Risk`.
- **Automated Rule-Based Academic Recommendations (R-012):**
  - Actionable recommendation cards linked directly to triggering facts:
    - *"Attendance alert: Student attendance is at 68.2%, below the 75% CBSE safe threshold."*
    - *"Score drop detected: 14.5% decline between Unit Test 1 and Mid-Term."*
  - Interactive action buttons: *"Mark as Reviewed"*, *"Schedule Remedial Session"*.

#### 4.3.4 Coursework & Assignment Hub (`/teacher/assignments`)
- **Assignment Creator:** Title, subject selector, max points, due date-time picker, rich instructions, and reference material upload.
- **Submissions Review Grid:**
  - List of all enrolled students with live status pills: `Submitted`, `Graded`, `Pending`.
  - Preview button to open student-submitted handwritten PDF or image files directly in a clean modal viewer.
  - Inline grading inputs: Points Awarded (validated $\le \text{Max Points}$) and qualitative pedagogical feedback.

#### 4.3.5 Reports & Class Analytics (`/teacher/analytics`)
- **Attendance Rate Distribution Chart:** Visualizes percentage of students in Safe ($\ge 75\%$), Warning ($65-74\%$), and Critical ($< 65\%$) attendance brackets.
- **Exam Score Histogram:** Displays score quartiles and standard deviation across selected subjects.
- **K-Means Student Groupings (R-011):**
  - Visual exploration of student learning patterns based on attendance and assignment engagement.
  - Strictly labeled: *"Exploratory learning clusters for pedagogical planning; does not represent permanent student categories."*
- **Synchronous Report Exports (UI-007, R-013):**
  - One-click downloads with live spinner states:
    - `[ Download Official PDF Report ]`: Formatted ReportLab document with school headers and metadata.
    - `[ Export Analytics Excel (.xlsx) ]`: Multi-sheet spreadsheet generated via OpenPyXL.

#### 4.3.6 Teacher Doubt Resolution Hub (`TeacherDoubtHub.jsx`)
- Filter doubts by status: `Unresolved Questions` vs. `Answered`.
- Displays student name, subject tag, timestamp, and the student's question.
- Integrated answer editor: Textarea with *"Submit Verified Answer"* action that marks the doubt resolved and alerts the student.

#### 4.3.7 AI Remedial Lesson Plan Modal (`AiLessonPlanModal.jsx`)
- Interactive tool allowing teachers to generate targeted intervention plans.
- Selects a target class; backend analyzes lowest-scoring subjects and attendance bottlenecks.
- Renders an actionable 4-week remedial curriculum: priority revision concepts, suggested practice problem sets, and estimated weekly hours needed to achieve grade recovery.

---

### 4.4 Student Workspace

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Student Academic Hub                            │
├───────────────────────────────────┬────────────────────────────────────┤
│  Top Metrics:                     │  Exam Schedule & Countdown:        │
│  • Attendance Rate: 84.2%         │  • Mathematics (Final) - In 4 Days │
│  • Average Exam Score: 76.5%      │  • [ Download Datesheet PDF ]      │
│  • Coursework Turned In: 9 / 10   │                                    │
├───────────────────────────────────┴────────────────────────────────────┤
│  Subject Performance Diagnostics (3 Pillars):                          │
│  [ Mathematics ] [ Science ] [ English ] [ Social Studies ]            │
│  ├── Pillar 1: Evaluated Exams (Average: 78.0%, 3 exams on record)     │
│  ├── Pillar 2: Attendance Rate (88.5%, 23/26 sessions attended)        │
│  └── Pillar 3: Coursework Completion (4/4 assignments submitted)       │
│  └── Diagnostic Summary: Low Risk • Recommended study: 45 min/day      │
├───────────────────────────────────┬────────────────────────────────────┤
│  75% Attendance Goal Planner:     │  Interactive What-If Simulator:    │
│  • Current: 84.2% (Target: 75.0%) │  • 4 Sliders: UT, Mid, HW, Attend. │
│  • Safe Skips Available: 3 days   │  • Projected Score: 81.2%          │
│  • [========|====] Target Marker  │  • Recommended Study Time: 1.5h/d  │
├───────────────────────────────────┴────────────────────────────────────┤
│  Achievement Badges & Class Rank:                                      │
│  [🏆 Top Scorer] [⚡ Quick Submitter] [⭐ 100% Attendance] [🔒 Locked]  │
├───────────────────────────────────┬────────────────────────────────────┤
│  Student Doubt Box:               │  Coursework & Homework Dropzone:   │
│  • Ask question to teacher        │  • Upload handwritten PDF/Image    │
│  • View answered questions        │  • View grades & teacher remarks   │
└───────────────────────────────────┴────────────────────────────────────┘
```

#### 4.4.1 Student Dashboard Overview (`/student`)
- **Personalized Header:** Welcomes student by name with admission number and current enrolled grade/section.
- **Personal KPI Cards:**
  - *Overall Attendance Rate:* Live percentage with color coding.
  - *Exam Performance Average:* Average percentage across evaluated exams.
  - *Coursework Turn-in Rate:* Completed vs. assigned homework tasks.
- **Strict Anti-Stigma Guardrail (D-012):** No machine learning risk labels or peer comparison rankings are shown on this page.

#### 4.4.2 Subject Performance Diagnostic (`SubjectPerformanceDiagnostic.jsx`)
- **Subject Tab Switcher:** Allows the student to toggle between enrolled subjects (Mathematics, Science, English, etc.).
- **3-Pillar Academic Analysis:**
  1. *Pillar 1: Evaluated Exams:* Average exam score, list of graded tests with individual scores and maximum marks, and flags for absent exams.
  2. *Pillar 2: Subject Attendance:* Total sessions held, sessions attended, absences, and subject attendance percentage.
  3. *Pillar 3: Coursework Assignments:* Turn-in ratio, average assignment score, and count of pending tasks.
- **Diagnostic Feedback & Study Recommendation:**
  - Evaluates composite performance and provides positive, constructive study recommendations (e.g., *"Recommended study pace: 45 minutes daily to maintain excellence"*).

#### 4.4.3 Interactive What-If AI Score Predictor (`WhatIfSimulatorCard.jsx`)
- An empowering, gamified simulation tool allowing students to explore how their future efforts affect their academic outcomes.
- **Subject Selector:** Choose which subject to simulate.
- **4 Real-Time Synchronized Sliders:**
  1. *Unit Test Score Slider:* `0%` to `100%` (Step: 1)
  2. *Mid-Term Score Slider:* `0%` to `100%` (Step: 1)
  3. *Assignment Score Slider:* `0%` to `100%` (Step: 1)
  4. *Attendance Rate Slider:* `0%` to `100%` (Step: 1)
- **Debounced Live Inference Engine:**
  - Debounces slider movements by 60ms and dispatches payload to `/api/v1/ml/predict-live`.
  - Renders forecasted score (e.g., `82.4%`) powered by the active regression model.
  - Displays dynamic study guidance: Recommended study hours per day, with clear indicators if extra effort is required to meet targets.
  - Multi-model comparative view: Shows secondary estimates across Linear, Random Forest, and XGBoost baselines.

#### 4.4.4 75% Attendance Goal Planner (`AttendanceGoalCard.jsx`)
- Directly addresses institutional requirements (e.g., CBSE 75% mandatory attendance rule).
- **Progress Bar with Target Threshold Marker:**
  - Dual-colored progress bar depicting current attendance rate.
  - Vertical target marker permanently fixed at the 75% benchmark.
- **Actionable Mathematical Calculations:**
  - **In Warning Zone ($< 75\%$):** Displays exact count of consecutive classes the student must attend without absence to recover to 75%:
    $$\text{Classes Needed} = \left\lceil \frac{0.75 \times \text{Total} - \text{Attended}}{0.25} \right\rceil$$
  - **In Safe Zone ($\ge 75\%$):** Displays exact number of "safe skips" available before falling below 75%:
    $$\text{Safe Skips} = \left\lfloor \frac{\text{Attended} - 0.75 \times \text{Total}}{0.75} \right\rfloor$$

#### 4.4.5 Achievement Badges Showcase (`AchievementBadgesCard.jsx`)
- Positive reinforcement card celebrating student consistency and progress:
  - *Trophy:* Top 10% Academic Achiever.
  - *CalendarCheck:* Perfect Attendance Streak ($\ge 95\%$).
  - *Zap:* Fast Homework Submitter.
  - *Star:* Consistent High Performer across all subjects.
  - *Rocket:* Most Improved Student (consecutive score increase).
- Visual states: Distinct gold/indigo glow for unlocked badges; clean grayed-out padlock for locked badges with clear unlocking instructions.
- Displays class rank banner (e.g., `Class Rank: #3 of 38`).

#### 4.4.6 Student Doubt Box (`StudentDoubtBox.jsx`)
- Self-service academic inquiry system.
- **Submission Form:**
  - Select subject dropdown.
  - Textarea to formulate the doubt or question.
  - *"Submit Question to Faculty"* button.
- **Doubts Feed:**
  - Displays student's doubts with live status badges: `Pending Faculty Review` (Amber) vs. `Resolved` (Emerald).
  - Shows verified teacher response, answering teacher's name, and timestamp.

#### 4.4.7 Student Homework & File Dropzone (`/student/assignments`)
- Left pane: Interactive list of active assignments with due dates and submission statuses.
- Right pane: Detailed assignment view with teacher instructions.
- **Submission Dropzone:**
  - Text editor for typed solutions or explanations.
  - External resource link input (e.g., Google Docs / GitHub link).
  - **Handwritten Solution File Dropzone:** Allows dragging and dropping PDF documents or PNG/JPEG homework scans.
  - One-click submit button with upload progress bar and instant submission receipt.

---

## 5. Comprehensive Catalog of Interactive Elements

| Category | Component / Element | User Interaction | Visual Feedback & State Transitions | Backend Endpoint |
| :--- | :--- | :--- | :--- | :--- |
| **Simulators** | `WhatIfSimulatorCard` Sliders | Drag range inputs (0-100%) for 4 academic variables | Debounced live score update, study hour badge animation, color shifts | `POST /api/v1/ml/predict-live` |
| **Goal Planners** | `AttendanceGoalCard` Progress | Visual marker at 75% target | Bar fills; switches between red warning banner and green safe skip counter | `GET /api/v1/analytics/attendance-goal` |
| **Grading** | Audited Marks Input Cell | Type numeric score in table cell | Instant red border if $> \text{Max Marks}$; preserves blank if empty | `PUT /api/v1/marks/audited` |
| **Compliance** | `AuditModal` Justification | Modal opens on modifying existing marks | Blocks submission until reason string ($\ge 5$ chars) is entered | `POST /api/v1/audit/log` |
| **Attendance** | Multi-State Attendance Buttons | Click Present / Absent / Late / Excused | Pill illuminates in color; dirty counter increments in sticky footer | `PUT /api/v1/attendance` |
| **Import Tools**| CSV Pre-Flight Parser | Paste raw CSV text or drop file | Displays two tables: validated rows with checkmarks vs. syntax errors | `POST /api/v1/institution/roster/import` |
| **AI Assistants**| `AiLessonPlanModal` Generator | Select class and click Generate | Skeleton loading animation; renders 4-week remedial plan with weak topics | `GET /api/v1/analytics/ai-lesson-plan` |
| **Governance** | Model Switcher Toggle | Click *"Set Active Engine"* in table | Table re-sorts; active badge moves; updates inference pipeline | `POST /api/v1/ml/models/{id}/switch` |
| **Q&A** | Doubt Thread Resolver | Teacher types response in doubt card | Card shifts from pending list to answered tab; student sees resolution | `POST /api/v1/doubts/{id}/answer` |
| **Gamification**| `AchievementBadgesCard` | Hover on badge icons | Tooltip reveals unlocking requirements and criteria progress | `GET /api/v1/students/{id}/badges` |
| **Reporting** | Synchronous Export Buttons | Click PDF or Excel export | Button displays spinner; triggers native browser download stream | `GET /api/v1/reports/pdf`, `/excel` |
| **Diagnostics**| Subject Pillar Accordion | Click subject tabs in diagnostic card | Transitions between subjects; updates exam, attendance, and coursework pillars | `GET /api/v1/students/{id}/diagnostic` |

---

## 6. Truth in UI: Anti-False Reassurance Guardrails

The frontend strictly enforces the following non-negotiable presentation rules:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   FORBIDDEN FALSE REASSURANCE STATES                  │
├────────────────────────────────────────────────────────────────────────┤
│  ❌ NEVER render green or "on track" when data is missing or stale.    │
│  ❌ NEVER render a speculative number when fewer than 2 exams exist.   │
│  ❌ NEVER render a blank mark as a 0 or fail.                          │
│  ❌ NEVER render an unrecorded attendance session as present.          │
│  ❌ NEVER render automated machine learning risk tags to students.     │
└────────────────────────────────────────────────────────────────────────┘
```

### Implementation Patterns

#### 1. The Minimum 2-Exam Safeguard (R-009, R-010, UI-005)
```jsx
// Frontend Guard: Teacher Student Detail
if (gradedExamsCount < 2) {
  return (
    <div className="p-4 rounded-xl bg-slate-100 border border-slate-200 text-slate-700">
      <div className="flex items-center gap-2 font-semibold text-xs">
        <AlertCircle className="w-4 h-4 text-slate-500" />
        <span>Performance Estimate Withheld: Insufficient Data</span>
      </div>
      <p className="text-[11px] text-slate-500 mt-1">
        In accordance with academic fairness standards, score estimates require at least 2 historical exams.
        No speculative score or color status is rendered.
      </p>
    </div>
  );
}
```

#### 2. Blanks vs. Zero Distinction in Marks Entry (UI-004)
```jsx
// Preserving null values across table cells
const handleScoreChange = (studentId, rawValue) => {
  setMarksState(prev => ({
    ...prev,
    [studentId]: {
      ...prev[studentId],
      score: rawValue === '' ? '' : rawValue, // Kept empty, never coerced to 0
      is_absent: false
    }
  }));
};
```

#### 3. Unmarked Attendance as "Not Recorded" (UI-003)
```jsx
// Unmarked students explicitly preserved
const payloadEntries = Object.entries(entries).map(([studentId, status]) => ({
  student_id: parseInt(studentId, 10),
  status: status || 'unrecorded' // Never defaults to 'present'
}));
```

---

## 7. State Management, API Client & Security Lifecycle

### 7.1 Authentication Context (`AuthContext.jsx`)
- **Token Management:**
  - Short-lived JWT `access_token` held in memory/storage.
  - Automatic `refresh_token` rotation.
  - On receiving `401 Unauthorized`, the client clears session state and redirects to `/login`.
- **Identity & Scopes:**
  - Decodes token payload to store `user` (`id`, `username`, `role`).
  - Fetches associated role profile: `teacherProfile` (with assigned classes and subjects) or `studentProfile` (with admission number and enrolled class).
  - Globally exposes `activeSession` allowing users to switch between academic years where authorized.

### 7.2 API Client Interceptors (`api/client.js`)
- **Request Interceptor:**
  - Injects `Authorization: Bearer <token>` on all outgoing requests.
  - Attaches unique `X-Request-ID` for end-to-end audit traceability.
- **Response Interceptor:**
  - Standardizes error structures using `extractApiError()`.
  - Distinguishes validation errors (`422 Unprocessable Entity`), permission denials (`403 Forbidden`), and scoping misses (`404 Not Found`).

---

## 8. Visual Design System & Accessibility

- **Palette:**
  - *Primary Neutral:* Slate (`bg-slate-50`, `text-slate-900`, `border-slate-200`).
  - *Brand & Focus:* Indigo (`bg-indigo-600`, `text-indigo-700`, `ring-indigo-500`).
  - *Academic Success:* Emerald (`bg-emerald-50`, `text-emerald-700`, `border-emerald-200`).
  - *Warnings & Remedial Prompts:* Amber (`bg-amber-50`, `text-amber-800`, `border-amber-200`).
  - *Errors & Attendance Deficits:* Rose (`bg-rose-50`, `text-rose-700`, `border-rose-200`).
- **Typography:**
  - Font Family: Clean system sans-serif (`Inter`, `-apple-system`, `Segoe UI`).
  - Strict hierarchical text scale: Headers `text-sm sm:text-base font-bold`, body `text-xs`, secondary metadata `text-[11px]`, and status labels `text-[10px] uppercase font-semibold`.
  - Numeric metrics rendered with tabular numbers (`font-mono`) to prevent visual layout jitter during live updates.
- **Accessibility & Responsiveness:**
  - Form controls include explicit `<label>` tags with matching `htmlFor` identifiers.
  - Full keyboard navigability across data tables, modal dialogs, and slider inputs.
  - High-contrast text exceeding WCAG AA standards across all alert states.
  - Mobile-first responsive layouts: Data tables wrapped in horizontal scroll containers (`overflow-x-auto`) to guarantee zero layout breaking on mobile devices.

---

## 9. Verification & Acceptance Checklist

To verify that the frontend implementation meets all specifications and Playbook requirements, validate the following test matrix:

- [x] **UI-001 (Auth & Roster Claim):** Student registration returns uniform `202 Accepted` response with no admission number enumeration leak.
- [x] **UI-002 (Admin Setup):** Bulk roster CSV parser flags invalid rows with specific row numbers before committing to backend.
- [x] **UI-003 (Attendance Sheet):** Unmarked students save as `unrecorded`; unsaved change indicators function correctly.
- [x] **UI-004 (Audited Marks):** Score boundaries ($0 \le score \le max\_marks$) enforced inline; modifying existing marks forces `AuditModal` justification prompt.
- [x] **UI-005 (Teacher Student Detail):** Students with $< 2$ exams render *"Not Enough Data"*; no premature estimates or reassurance colors appear.
- [x] **UI-006 (Student Dashboard):** Personal records rendered exclusively; ML risk tags and peer rank distributions hidden to prevent stigma.
- [x] **UI-007 (Reports):** PDF and Excel reports trigger clean synchronous downloads with loading states.
- [x] **Interactive Simulator:** What-If range sliders debounce and dynamically fetch multi-model predictions via `/api/v1/ml/predict-live`.
- [x] **Attendance Goal Planner:** 75% target threshold marker accurately computes consecutive sessions needed or safe skips remaining.
- [x] **Coursework Upload:** Students can attach handwritten homework scans (PDF/PNG/JPEG); teachers can inspect submissions in modal viewer.
