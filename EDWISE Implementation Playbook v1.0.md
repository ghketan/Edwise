# EDWISE Implementation Playbook v1.0

**Builder:** Evidence-Grounded Project Playbook Builder v2.0, mode `BUILDER`\
**Status:** candidate (author self-review only; no independent review performed)\
**Date:** 2026-11-05\
**Tier:** M (justification in §0.2)\
**Format note:** delivered in two parts inside this document. Part 2 starts at §6.

## 0. Control variables, tools, and basis

### 0.1 Variables

| Variable | Value | Basis |
| --- | --- | --- |
| Mode | `GREENFIELD` | No repository supplied (S-001 lists none) |
| Maturity target | Functional prototype (maps to `MVP`) | S-001 §8 "functional prototype" |
| Decision enabled | Start implementation and know what to cut if behind | Default |
| Audience | Builder (solo) plus academic evaluators | INFERRED from S-001 §7 |
| Deadline | 45 days from start; calendar date `UNKNOWN` | S-001 §7 |
| Team | 1 developer, all roles | S-001 §7 |
| Budget | `UNKNOWN`; assume zero paid services (A-003) | not stated |
| Jurisdiction | `UNKNOWN` (Q-001) | not stated |
| Risk appetite | moderate | default |
| Confidentiality | internal | default |
| Language | English UI and output (A-004) | not stated |

### 0.2 Tier justification

Tier M. One institution, one platform family (web), one developer, 45 days. An ML module is present but, per v2.0 §2.2, that alone does not raise the tier. Education data about students triggers the regulated/high-harm module (§9) at M depth; this is added depth, not a tier promotion.

### 0.3 Tool capability declaration

| Capability | Status | Consequence |
| --- | --- | --- |
| File read/write | `AVAILABLE` | Used only to deliver this document |
| Repository inspection | `UNAVAILABLE` | No repository supplied |
| Web research | `AVAILABLE`, not exercised in this run | Every external fact below is `INFERRED`, `ASSUMED` or `UNKNOWN`, never `VERIFIED`. Re-verification is task T-001 |
| Code execution | `AVAILABLE`, not exercised | No result below is `MEASURED` |
| UI inspection | `UNAVAILABLE` | n/a |
| Independent reviewer | `UNAVAILABLE` | Audit in §15 is self-review |

### 0.4 Sources

| S-ID | Source | Status |
| --- | --- | --- |
| S-001 | EDWISE brief supplied by the user (problem, objectives, modules, stack, data strategy, constraints) | `USER_PROVIDED` |
| S-002 | Playbook Builder v2.0 prompt supplied by the user | `USER_PROVIDED` (governing instructions) |
| S-003 | UCI Student Performance dataset, named in S-001 §6 | Existence and contents `USER_PROVIDED`; schema details in this document are from the author's general knowledge and are `INFERRED` until T-001 |
| S-004 | Open University Learning Analytics Dataset (OULAD), named in S-001 §6 | Same treatment as S-003 |

No URL has been fetched. No license, record count, or column list is `VERIFIED`.

## 1. Decision brief

**Recommendation: `CONDITIONAL GO`.** The management core (roles, classes, attendance, marks, dashboards) is a well-trodden build and fits 45 days for one developer if scope is held. The ML layer is feasible only as a modest, honestly labeled analytics add-on, and it carries a structural risk: the only usable training data is public or synthetic, so no claim about real students can be supported.

**Conditions for GO:**

1. The walking skeleton (M-002) passes by day 12. If not, cut per D-010 immediately.
2. ML models are trained on public data, documented as such, and the product states plainly that synthetic and public-data models are demonstrations (R-015, C-001).
3. Real student data is not loaded unless Q-001 and Q-002 are resolved with an authorized person.

**Top five requirements:** R-001 server-enforced RBAC; R-003 verified student registration; R-004/R-005 attendance and marks with audit (R-014); R-007 students see only their own records; R-015 predictions presented as labeled estimates.

**Top risks:** K-001 scope overrun for a solo build; K-002 label/feature leakage producing inflated ML scores; K-003 teacher-visible predictions treated as verdicts on students; K-004 cross-user data exposure through missing object-level checks.

**First two weeks:** days 1–3 repo, Docker Compose with Postgres, schema v0, auth for three roles; days 4–7 EDA and leakage-safe baseline on the public dataset (risk-killing experiment E-001) while building class/enrollment CRUD; days 8–12 attendance recording and student dashboard, ending at the M-002 acceptance test.

## 2. Scope, non-goals, assumptions

### 2.1 In scope (from S-001)

Single institution; roles Administrator, Teacher, Student; sessions, classes, sections, subjects; enrollment and teacher assignment; attendance; exams and marks; assignments, submissions, feedback; dashboards per role; analytics; regression prediction; at-risk classification; K-Means exploration; rule-based recommendations; PDF and Excel reports; audit records; model evaluation with metrics.

### 2.2 Non-goals (this prototype)

- Multi-institution tenancy.
- Mobile apps, offline use, push notifications.
- Payments, fee management, timetabling, parent portal.
- Automated academic or disciplinary decisions of any kind.
- Deep learning, LLM-generated recommendations (S-001 says "initially rule-based").
- Production deployment to real students.
- Integration with an institutional ERP or LMS (none stated).

### 2.3 Assumptions

| A-ID | Assumption | Impact if false | Status |
| --- | --- | --- | --- |
| A-001 | One academic session is active at a time; history kept per session | Data model needs cross-session transfer rules | `ASSUMED` |
| A-002 | Marks use one numeric scale per exam (max marks stored per exam) | Normalization needed in analytics and ML | `ASSUMED` |
| A-003 | No paid services; local or free-tier hosting | Hosting, email verification options change | `ASSUMED` |
| A-004 | English-only UI | Localization module becomes applicable | `ASSUMED` |
| A-005 | An Administrator can supply a roster (admission number, name, class, section) for verification | If not, D-006 verification design fails; fall back to manual approval | `ASSUMED` |
| A-006 | Demo audience is evaluators, not real students | If real students, §9 regulated gates become P0 blockers | `ASSUMED` |

### 2.4 Open questions

| Q-ID | Question | Why it matters | Resolution path |
| --- | --- | --- | --- |
| Q-001 | Which jurisdiction governs the data, and who is the compliance owner? | Student (likely minor) data rules differ | Developer asks institution/supervisor before any real data |
| Q-002 | Will any real institutional records ever be loaded? | Determines whether §9 gates are blockers | Developer, before M-004 |
| Q-003 | Exact marks scale, grading terms, and number of exams per session | Drives schema and ML target definition | Developer asks institution or fixes by decision |
| Q-004 | Do students see predictions or at-risk flags? | Stigma and harm; see D-012 | Developer and supervisor, before M-004 |
| Q-005 | How is "verification" of a student account expected to work (roster match, teacher approval, email)? | R-003 design | Default D-006 applies if unanswered |

## 3. Feasibility and refutation

### 3.1 What would disprove the plan

1. Core CRUD plus RBAC cannot be completed and tested by day 28 (K-001).
2. The public dataset cannot be mapped to the EDWISE schema without inventing features, making "integrated" ML a fiction (K-005).
3. After leakage control, ML models do not beat a trivial baseline. This is an acceptable outcome if reported honestly (D-007); it is not acceptable to hide it.

### 3.2 Buildable lanes

| Lane | Description | Strength | Weakness | Use when |
| --- | --- | --- | --- | --- |
| A (proposed) | Modular monolith, FastAPI, ML artifacts trained offline and loaded for inference | Matches S-001 §5; one deployable; debuggable solo | Retraining is manual | Default |
| B | Same, but ML served from a separate small FastAPI process | Isolates sklearn dependency | Extra deployment unit for no prototype gain | Only if dependency conflicts appear |
| C | Management-only release with ML as notebooks | Safest schedule | Fails objectives 7–10 | Fallback if M-004 is at risk (D-010) |

### 3.3 Rejected approaches

| Approach | Appeal | Failure mechanism | Allowed narrow use | Never promise |
| --- | --- | --- | --- | --- |
| Train on synthetic data and report accuracy | Fast, perfectly clean data | Synthetic labels follow the generator's rules, so scores prove only that the model recovers the generator | UI demo, load testing, pipeline tests | Any accuracy on real students |
| Predict final grade using earlier-period grades from the same dataset without stating it | Very high R² | Earlier grades are near-duplicates of the target; metric does not reflect early-warning usefulness | Report as an explicit "with prior-grade features" variant next to a variant without them | That the model gives early warning |
| Random row split for student data | Default in tutorials | Rows from the same student or class leak across splits | Quick smoke tests only | Any generalization number |
| Auto-flagging with no human review | Looks "intelligent" | Harm from false positives; contradicts S-001 §1 | none | Automatic decisions |
| Microservices | Resume appeal | Solo schedule, S-001 §5 explicitly says modular monolith | none | n/a |

### 3.4 Fallback ladder for critical dependencies

| Dependency | If unavailable | Capability or claim becomes |
| --- | --- | --- |
| UCI or OULAD download or license issue (X-001) | Use the other, then synthetic only | Claim reduces to "pipeline demonstrated on synthetic data" |
| PostgreSQL in demo environment | SQLite for demo only via SQLAlchemy, tested separately | Concurrency and constraint behavior not demonstrated |
| Plotly or Recharts issue | Use the other | none |
| ReportLab PDF layout problems | Excel and on-screen report only | PDF deferred, recorded as scope change per D-010 |
| Email service for verification (X-002) | Admin-managed roster match plus teacher approval | No email-based confirmation claim |

### 3.5 Protected moments

Moments where error is hard to reverse or harms a student:

1. Changing or overwriting marks or attendance (needs audit entry, R-014).
2. Linking a self-registering account to a student record (wrong link exposes another student's data; R-003).
3. Showing an at-risk label to anyone (stigma; D-012).
4. Exporting reports (data leaves the system; log and role-restrict).

## 4. Requirement-to-proof map

Priority meaning (v2.0 §7): P0 blocks M-002/M-003; P1 required for the prototype target; P2 conditional. S-001 lists every analytics item as an objective, so none is demoted without a recorded scope change (D-010).

| R-ID | Requirement | Origin | Pri | Design | Acceptance (T-ID) | Status |
| --- | --- | --- | --- | --- | --- | --- |
| R-001 | Three roles; every endpoint enforces role and object scope on the server, never only in the UI | S-001 obj. 2 | P0 | D-004 | T-003 role/object matrix test; T-004 direct-URL tampering | `PLANNED` |
| R-002 | Admin manages sessions, classes, sections, subjects, teachers, enrollments, teacher assignments | S-001 obj. 1, 3 | P0 | D-002 | T-005 CRUD with constraint violations rejected | `PLANNED` |
| R-003 | Student self-registers with admission number and class; account is inactive until verified; one account per student record | S-001 §7 | P0 | D-006 | T-006 wrong class rejected, duplicate rejected, unverified cannot log in to data | `PLANNED` |
| R-004 | Teacher records and edits attendance only for assigned class and subject | S-001 obj. 4 | P0 | D-004 | T-007 | `PLANNED` |
| R-005 | Teacher creates exams and enters marks within max marks; edits are audited | S-001 obj. 4 | P0 | D-002, D-013 | T-008 | `PLANNED` |
| R-006 | Assignments, submissions, feedback | S-001 obj. 4 | P1 | D-002 | T-009 | `PLANNED` |
| R-007 | Student dashboard shows only that student's attendance, marks, assignments, feedback | S-001 obj. 5 | P0 | D-004 | T-003, T-004 | `PLANNED` |
| R-008 | Analytics: attendance trends, subject and exam comparison, class vs individual, declining performance | S-001 obj. 6 | P1 | D-009 | T-010 computed values equal hand-checked fixture | `PLANNED` |
| R-009 | Performance prediction with regression, compared to a baseline, shown as an estimate with an interval or error band | S-001 obj. 7 | P1 | D-005, D-007 | T-011, T-012 | `PLANNED` |
| R-010 | At-risk identification with a defined label rule and a classifier; reports precision, recall, F1 | S-001 obj. 8 | P1 | D-005, D-007 | T-011, T-012 | `PLANNED` |
| R-011 | K-Means exploration of student groups; presented as exploratory, not as categories of people | S-001 obj. 9 | P1 | D-005 | T-013 | `PLANNED` |
| R-012 | Rule-based recommendations, each traceable to the indicator that triggered it | S-001 obj. 10 | P1 | D-008 | T-014 | `PLANNED` |
| R-013 | PDF and Excel reports (student, class, attendance); role-restricted | S-001 obj. 11 | P1 | D-009 | T-015 | `PLANNED` |
| R-014 | Audit record for marks, attendance, role, enrollment and verification changes: who, when, old, new | S-001 obj. 13 | P0 | D-013 | T-016 | `PLANNED` |
| R-015 | Synthetic data and public-data models are labeled everywhere they surface; predictions carry "estimate, not a decision" language and model version | S-001 §6 | P0 | D-005, D-012 | T-017 UI and report text check | `PLANNED` |
| R-016 | Model evaluation uses grouped or time-aware splits, a trivial baseline, and reports uncertainty | S-001 obj. 12 | P1 | D-007 | T-012 | `PLANNED` |
| R-017 | No student personal data in logs, URLs, error pages, or client storage beyond the session token | S-001 obj. 13 | P0 | D-003, D-014 | T-018 negative scan | `PLANNED` |

Every P0/P1 R has at least one D and one T. Every T maps to an R (T-001 and T-002 are enabling checks, mapped in §10).

## 5. Architecture and decisions

### 5.1 Context and boundary

Browser SPA (React + Tailwind) → HTTPS/JSON → FastAPI modular monolith → PostgreSQL. ML training runs offline in notebooks or scripts that write versioned `joblib` artifacts plus a metadata record; the API loads the active artifact for inference. Trust zones: (1) browser, untrusted; (2) API, enforces all policy; (3) database and model artifacts, reachable only from the API. Actors: Administrator, Teacher, Student, and the developer as operator.

### 5.2 Module layout (backend)

`auth`, `institution` (sessions, classes, subjects, enrollments), `academics` (attendance, exams, marks, assignments), `analytics`, `ml` (inference, model registry), `reports`, `audit`. Modules call each other through service functions, not through shared ORM queries scattered in routers. Rationale: lets one person test modules independently and keeps the monolith honest.

### 5.3 Decision records

| D-ID | Decision | Status | Alternatives | Failure behavior | Reversal trigger |
| --- | --- | --- | --- | --- | --- |
| D-001 | Modular monolith: React SPA + FastAPI + PostgreSQL | `PROPOSED` (follows S-001 §5) | Microservices (rejected §3.3) | n/a | Dependency conflict forces Lane B |
| D-002 | SQLAlchemy models with Alembic migrations; constraints (unique, foreign key, check) in the database, not only in code. Alembic is the author's addition, not in S-001 | `PROPOSED` | Raw SQL; create\_all only | Migration failure blocks deploy, never auto-drops | Migration tooling costs > 1 day |
| D-003 | JWT access token (short lifetime) plus refresh handling; password hashing with a modern slow hash. Token storage choice (httpOnly cookie vs memory) decided at M-001 with CSRF consequences recorded | `PROPOSED` | Server sessions | Expired token returns 401 and clears client state | Security review finding |
| D-004 | RBAC plus object-level scoping: teacher access derives from the teacher-class-subject assignment table; student access derives from the linked student record. Implemented as one reusable authorization dependency, not per-route ad hoc checks | `PROPOSED` | UI-only hiding | Missing scope means deny | T-003 failure |
| D-005 | ML trained offline; artifact + metadata (data source, synthetic flag, feature list, split method, metrics, commit, date) stored in a `model_registry` table; API refuses to serve a model without metadata | `PROPOSED` | Train on request | If no valid model, UI shows "Prediction unavailable" | n/a |
| D-006 | Student verification: admin imports a roster (admission number, class, section, name); registration must match an unclaimed roster row; account activates on match, or on teacher/admin approval when no match exists. Unclaimed-row race handled by a unique constraint | `PROPOSED` (resolves Q-005 by default) | Email OTP (needs X-002) | Mismatch returns a generic error that does not reveal which field was wrong | Institution mandates another method |
| D-007 | ML protocol: define target and label rule first; split by student (and by time where data allows); compare to mean-predictor and last-score baselines; report each model with and without prior-grade features; report uncertainty (bootstrap or repeated grouped CV). Thresholds set before looking at final test results | `PROPOSED` | Random split | If no model beats baseline, report that and ship the baseline-based rule | n/a |
| D-008 | Recommendations are rules over indicators (attendance below a configurable threshold, mark drop over N exams, missing assignments); thresholds are configuration, shown to the teacher with the triggering numbers | `PROPOSED` | ML recommender (deferred per S-001) | No triggering data means no recommendation, never a generic one | n/a |
| D-009 | Analytics computed server-side with SQL/Pandas on request, cached only if measured slow; reports generated synchronously | `PROPOSED` | Background workers | Timeout returns an error with retry advice | Report time > target in T-015 |
| D-010 | Cut order if behind schedule, applied at fixed checkpoints: (1) PDF layout polish, (2) K-Means UI (keep notebook), (3) assignment submission files (keep metadata only), (4) at-risk classifier replaced by transparent rule, (5) regression replaced by baseline. Each cut is a recorded scope change with consequence and affected claims. Core P0 items are never cut | `PROPOSED` | none | n/a | n/a |
| D-011 | Charts with Recharts for dashboards; Plotly only if a needed chart is unavailable | `PROPOSED` | Either, per S-001 | n/a | n/a |
| D-012 | Predictions and at-risk flags are visible to teachers and admins only by default; students see their own marks and attendance, not model outputs, unless Q-004 is answered otherwise | `PROPOSED` | Show students their risk | n/a | Supervisor decision |
| D-013 | Audit log is append-only at application level (no update/delete endpoints), written in the same transaction as the change | `PROPOSED` | Separate async logging | Failed audit write fails the change | n/a |
| D-014 | Structured logs record user ID and request ID only; no names, admission numbers, marks, or tokens | `PROPOSED` | Verbose logging | n/a | n/a |

### 5.4 Truth language for model outputs (must show / must never imply)

Summarized here; per-screen rows are in §6.

- A prediction is "an estimate from patterns in past data, version X, trained on \[source\]".
- It must never imply certainty, a diagnosis, a cause, or a decision about a student.
- Missing, stale, or low-data inputs yield "Not enough data", never a number and never a green state.

## 6. Product, roles, and screens

### 6.1 Roles and journeys

| Role | Primary journey | Failure/recovery journey | Misuse to design against |
| --- | --- | --- | --- |
| Administrator | Create session, classes, subjects; import roster; assign teachers; enroll students | Fix a wrong enrollment; roll back by audited edit, never silent delete | Over-broad admin actions without trace |
| Teacher | Take attendance, create exams, enter marks, view class analytics and per-student estimates | Correct a mark; correction creates an audit entry with reason | Reading another teacher's class; treating an estimate as a verdict |
| Student | Register, wait for verification, view own attendance, marks, assignments, feedback | Registration rejected: generic message and contact route | Claiming another student's admission number |

### 6.2 Screen and state table

| UI-ID | User / purpose | Must show | Must never imply | Empty / error / stale | R / T links |
| --- | --- | --- | --- | --- | --- |
| UI-001 Login and student registration | All; sign in or claim a roster record | Generic errors; pending-verification state | That a given admission number exists or is already claimed | Locked after repeated failures; pending account sees only a status page | R-003, T-006 |
| UI-002 Admin setup | Admin; sessions, classes, roster import, assignments | Import preview with row-level rejects before commit | That a partial import succeeded in full | Failed rows listed with reason; nothing committed on parse failure | R-002, T-005 |
| UI-003 Attendance entry | Teacher; mark a class for a date | Saved/unsaved state, last saved time, who edited | That unmarked equals present | Unmarked students shown as Not recorded; save failure keeps the form data and says so | R-004, T-007 |
| UI-004 Marks entry | Teacher; enter marks for an exam | Max marks, blanks distinct from zero, validation per cell | That a blank is a zero or that absence is a fail | Out-of-range score rejected inline; edit asks for a reason and writes audit | R-005, R-014, T-008, T-016 |
| UI-005 Student detail (teacher) | Teacher; history, trends, estimate, recommendation | Estimate with error band, model version, data source label, data-through date, and the rule that triggered each recommendation | That the student will or will not succeed; that the cause is known | Fewer than the minimum exams: Not enough data (no number, no colour); model missing: Prediction unavailable | R-009, R-010, R-012, R-015, T-014, T-017 |
| UI-006 Student dashboard | Student; own records only | Data-through date; Not recorded states | Other students' data, rank, or model output (D-012) | Empty session: explanatory empty state | R-007, T-003, T-004 |
| UI-007 Reports | Teacher/Admin; PDF or Excel | Generation time, filters used, role of requester, synthetic-data banner where applicable | That a report is an official transcript | Failure shows an error and no partial file | R-013, T-015 |

Forbidden false-reassurance states: green or 'on track' shown when data is missing or stale; a numeric estimate shown with too little data; a blank mark rendered as 0; an unrecorded attendance day rendered as present.

### 6.3 Human factors

Teachers will see risk flags among many other tasks. Controls: the flag shows its reason (indicators and values), flags are sorted by evidence strength rather than only by score, and a teacher can record 'reviewed, no action' with a note, which is stored and does not suppress future flags. Language avoids 'failing student' and similar labels. Training note for any real use: estimates are a prompt to look at the record, not a finding (C-001).

## 7. Backend, data, and contracts

### 7.1 Data model (conceptual)

`users`; `students` (roster record, admission number unique per institution, linked to at most one user); `teachers`; `academic_sessions`; `classes` and `sections`; `subjects`; `class_subject_teacher` (the assignment that grants teacher scope); `enrollments` (student, class, session); `attendance_records`; `exams` (class\_subject, max\_marks, date, type); `marks` (exam, student, score nullable); `assignments`, `submissions`, `feedback`; `audit_log`; `model_registry`; `predictions` (student, model, session, value, interval, generated\_at, data\_through); `recommendation_rules` (configurable thresholds).

### 7.2 Invariants enforced in the database where possible

1. One attendance row per student, subject, date (unique key).
2. `score` is null or between 0 and the exam's `max_marks` (check constraint plus service validation).
3. A mark exists only for a student enrolled in the exam's class and session.
4. A roster record links to at most one user; a user links to at most one roster record.
5. Teacher write access to attendance, exams, and marks requires a matching `class_subject_teacher` row.
6. A prediction row cannot reference a model without registry metadata (D-005).
7. Audit rows are written in the same transaction as the change they describe (D-013).

### 7.3 Representative contracts

```yaml
contract_id: API-001
purpose: Teacher saves attendance for one class, subject, and date
version: v1
transport: HTTPS JSON
endpoint: PUT /api/v1/attendance
authentication: bearer token
authorization: role Teacher AND class_subject_teacher match (D-004); otherwise 404
idempotency: upsert on (student, subject, date); repeating the request yields the same state
request: class_subject_id, date, entries[{student_id, status in present|absent|late|excused}]
response: 200 with saved count and server timestamp; 422 lists invalid entries, none saved
errors: 401 unauthenticated; 404 out of scope or unknown; 409 session closed; 422 validation
audit_events: attendance.created, attendance.changed (old and new values)
linked_ids: R-004, R-014, T-007, T-016
```

```yaml
contract_id: API-002
purpose: Student claims a roster record
endpoint: POST /api/v1/auth/register-student
request: admission_number, class, password, contact (contact method per Q-005)
response: 202 pending verification in all non-error cases
errors: 422 malformed; 429 rate limited; no response distinguishes unknown from already-claimed
linked_ids: R-003, T-006
```

```yaml
contract_id: API-003
purpose: Teacher reads estimate for a student
endpoint: GET /api/v1/students/{id}/estimate
authorization: Teacher with scope over the student's current class, or Administrator
response: value, interval, model_version, data_source_label, is_synthetic, data_through, reason_codes; or status in not_enough_data|model_unavailable with no number
linked_ids: R-009, R-010, R-015, T-012, T-017
```

Error taxonomy: 401, 404 for out-of-scope objects (avoids confirming existence), 409 for state conflicts, 422 for validation, 429 for rate limits. Timestamps are UTC in storage and shown in the institution's local time (zone `UNKNOWN`, Q-003-adjacent; default to the browser's zone and record the assumption).

### 7.4 Observability

Structured request logs with request ID and user ID only (D-014); audit log viewable by Administrator; health endpoint; a simple admin page listing the active model and its metadata.

## 8. Data and machine learning

### 8.1 Intended use and claim boundary

Task: help a teacher notice students whose recorded marks, attendance, or assignment completion pattern resembles patterns that preceded lower results in the training data. Unit of analysis: one student in one session. Human action: teacher reviews the record. The model cannot show why a student is struggling, cannot show that an intervention will help, and cannot be assumed to transfer from public or synthetic data to this institution. Permitted claim:

> **C-001 (`TARGET`):** On the held-out students of the named dataset, using the split and metrics defined in D-007, model M achieves the reported error or recall with the stated uncertainty. This does not establish performance on students of this institution. Delivery status stays `TARGET` until T-012 produces an artefact with commit, date, environment, method, and owner.

### 8.2 Dataset register

| Data ID | Role | Provenance and eligibility | Status |
| --- | --- | --- | --- |
| DS-001 UCI Student Performance (S-003) | Regression and at-risk development and evaluation | Public; license, size, and columns to be checked in T-001. The author expects period grades G1, G2, G3 and an absences column (`INFERRED`) | `UNKNOWN` until T-001 |
| DS-002 OULAD (S-004) | At-risk label (pass, fail, withdrawn style outcomes) and activity features | Public; license and schema to be checked in T-001. The author expects click-stream, assessment, and outcome tables (`INFERRED`) | `UNKNOWN` until T-001 |
| DS-003 Synthetic institution data | Application demo, load, pipeline tests | Generated by a documented script with a fixed seed; every row flagged `is_synthetic` | `PLANNED` |
| DS-004 Real institutional records | Not planned | Blocked by Q-001, Q-002, G-001 | `BLOCKED` |

Rules: unknown license means quarantine (do not train). Models trained on DS-003 may be used only for pipeline testing and demo labeling, never for reported performance. The generator's rules are published in the repository so readers can see what a model could and could not learn from it.

### 8.3 Feature and leakage policy (D-007, D-015)

- D-015 (`PROPOSED`): features are limited to academic-behaviour inputs that exist in the EDWISE schema: prior marks, attendance rate, assignment completion, and counts of exams. Demographic, family, and socioeconomic columns present in public datasets are excluded from model inputs. Consequence: fairness slices across those attributes cannot be computed from the model's inputs; if required, they are computed on held-out predictions using the excluded columns for audit only, and the result is reported as a limitation.
- Schema adapter: a documented mapping from each public dataset to EDWISE feature names. Where a public dataset lacks a feature (for example assignment completion), the model for that dataset omits it. The mapping and omissions are part of model metadata (K-005).
- Split by student; by time where the dataset has time. No student appears in more than one split.
- Two variants always reported: with and without the most recent prior period grade. The without variant is the one that supports an early-warning claim.
- At-risk label rule is written before modelling (for example, final outcome below a pass line fixed in advance), with the pass line recorded as `ASSUMED` until Q-003.

### 8.4 Training and selection

Baselines: mean predictor and last-score predictor for regression; majority class and an attendance-threshold rule for at-risk. Candidates from S-001: Linear Regression, Decision Tree, Random Forest, Gradient Boosting; Logistic Regression, Decision Tree, Random Forest for at-risk; K-Means for exploration. Procedure targets (all `TARGET` until run):

1. Fix seeds and record library versions.
2. Select models by grouped cross-validation on the training portion only.
3. Choose the at-risk decision threshold on validation data, aiming at recall with a precision floor agreed with the supervisor before testing (value `UNKNOWN`).
4. Open the held-out test set once per model family; if it is opened again, record a new version and disclose.
5. Report: MAE, RMSE, R² against baselines; precision, recall, F1, precision-recall AUC, and a calibration check for the classifier; uncertainty by bootstrap over students.
6. K-Means: choose k by silhouette and by stability across seeds; describe clusters by their feature means; do not name clusters after types of people. Dropped if unstable (D-010).

### 8.5 Inference and freshness

Predictions are generated on demand from current database features and stored with model ID and data-through date. Minimum history before showing a number: `TARGET` of 2 completed exams in the session (basis: any estimate from one data point is a copy of that point). Below the minimum, the API returns not\_enough\_data and the UI shows no number. A model whose metadata is missing is not loaded (D-005).

### 8.6 Lifecycle

Model registry fields: ID, task, data source, is\_synthetic, feature list, split method, metrics with intervals, commit, date, owner. One model is active per task. Rollback means setting the previous model active. Drift monitoring for the prototype: store feature means per session and show a warning when the current session's means differ from training means beyond a recorded threshold (threshold `UNKNOWN`, set after T-012). Retire models trained on a different feature set when the schema changes.

### 8.7 Recommendations (D-008)

Each rule has an ID, an indicator, a configurable threshold, and a message template. Example structure: indicator attendance\_rate below threshold T1 over the last N sessions produces 'Attendance dropped from X% to Y%'. The recommendation card shows the triggering values. No rule fires on missing data.

## 9. Security, privacy, and regulated-domain handling

### 9.1 Threat and harm model

| Asset | Actor | Abuse case | Control | Test |
| --- | --- | --- | --- | --- |
| Student marks and attendance | Student | Reads or edits another student's record by changing an ID | Object-level checks (D-004), 404 on out-of-scope | T-003, T-004 |
| Marks | Teacher | Edits marks of a class not assigned | Assignment-based scope | T-007, T-008 |
| Admin functions | Any user | Privilege escalation through self-supplied role field | Role comes from the database, never from the request body | T-003 |
| Credentials | External | Password guessing | Slow hashing, rate limiting, lockout with recovery | T-003 |
| Roster | External | Enumeration through registration errors | Uniform responses (API-002) | T-006 |
| Reports | Insider | Exports leave the system | Role limits, export logging | T-015, T-016 |
| Dependencies | Supply chain | Vulnerable package | Pinned versions, vulnerability scan before M-005 | T-021 |

Residual-risk acceptor: the developer, flagged as a review-independence gap (G-003); a supervisor or peer should review the authorization code and T-003/T-004 results.

### 9.2 Data lifecycle

| Data class | Purpose | Retention and deletion | Must not appear in |
| --- | --- | --- | --- |
| Student identity and academic records | Core function | Per institution policy (`UNKNOWN`, Q-001); deletion removes the student's rows including predictions and audit snapshots as policy allows | logs, URLs, error pages, analytics, client storage other than session token |
| Credentials | Authentication | Hashes only | any log or export |
| Model inputs | Inference | Stored only as the prediction row's reason codes and data-through date, not full snapshots by default | public model artifacts |
| Public datasets | Training | Per license | the application database as if they were institutional records |

T-018 scans logs, URLs, and error responses for admission numbers, names, and tokens.

### 9.3 Regulated and high-harm handling (children, education decisions)

Students are likely minors and the system supports academic decisions, so this module applies at M depth. The prototype boundary is: synthetic and public data only (A-006). Real data requires, before loading: jurisdiction and compliance owner (Q-001), written authorization from the institution (Q-002), a data protection review by a qualified person, a decision on student visibility of predictions (Q-004), and a documented appeal route for any decision that cites a model output.

> **BLOCKER — G-001:** Real institutional data may not be loaded until Q-001, Q-002 and the qualified review are resolved. Owner: developer with institution contact. This blocks no prototype milestone.

This section is issue-spotting. It is not a legal conclusion and does not claim compliance with any law or standard.

## 10. Test and evidence matrix

| T-ID | Procedure and expected result | Linked | Type |
| --- | --- | --- | --- |
| T-001 | Fetch each public dataset's documentation; record license, row counts, columns, and recheck date; mark `VERIFIED` only with the source URL and retrieval date | R-009, R-010, R-016, X-001 | Enabling |
| T-002 | From a clean checkout, one command starts database, API, and frontend; migrations apply; seed runs | all P0, K-001 | Enabling |
| T-003 | Role and object matrix: for each endpoint and each role, a parametrized test asserts allow or 404/403; includes body-supplied role | R-001, R-007 | Positive and negative |
| T-004 | Tamper with IDs in URLs and bodies as Student and as Teacher of another class; expect no data returned | R-001, R-007 | Adversarial |
| T-005 | Create and edit institution entities; duplicate and orphan operations are rejected by the database | R-002 | Boundary |
| T-006 | Register with correct, wrong-class, duplicate, and unknown admission numbers; compare response bodies and timing for indistinguishability within a stated tolerance; unverified accounts cannot read data | R-003 | Adversarial |
| T-007 | Teacher saves attendance for assigned and unassigned classes; repeat requests are idempotent | R-004 | Positive and negative |
| T-008 | Marks above max, negative, blank, and edited values; every edit has an audit row | R-005, R-014 | Boundary |
| T-009 | Assignment, submission, and feedback lifecycle with scope checks | R-006 | Positive and negative |
| T-010 | Analytics outputs match a hand-computed fixture of at least 3 students, 2 subjects, 4 exams | R-008 | Regression |
| T-011 | Training script reproduces recorded metrics within a stated tolerance from the same seed and commit | R-009, R-010, R-016 | Reproducibility |
| T-012 | Run D-007 protocol; produce metrics table with baselines, both feature variants, and intervals; save artefacts with commit, date, environment, owner | R-009, R-010, R-016, C-001 | Evaluation |
| T-013 | Re-run K-Means across seeds and compare assignments; report stability | R-011 | Evaluation |
| T-014 | Each recommendation shows its triggering values; no recommendation on missing data | R-012 | Positive and negative |
| T-015 | PDF and Excel contain correct figures for the fixture, respect role scope, and fail cleanly | R-013 | Positive and negative |
| T-016 | Every audited operation writes exactly one audit row in the same transaction; forced failure leaves neither | R-014 | Failure injection |
| T-017 | Every screen showing a model output includes model version, source label, synthetic flag, and estimate wording; not\_enough\_data shows no number | R-015 | UI check |
| T-018 | Negative scan of logs, URLs, error responses, and browser storage for protected fields | R-017 | Negative |
| T-019 | Walking skeleton (M-002): teacher marks attendance, student sees it, wrong-role access is refused | R-001, R-004, R-007 | Acceptance |
| T-020 | Database backup and restore to a clean instance; row counts and constraints verified | R-014, K-006 | Recovery |
| T-021 | Dependency vulnerability scan and pinned-version check before release | K-007 | Supply chain |

All T records are `PLANNED`. None has been run.

## 11. Roadmap (45 days, solo)

Estimates are `TARGET` ranges. Hours per day are `UNKNOWN`, so the first checkpoint also measures actual velocity (days of work completed against plan) and the later dates are re-based at day 7.

| M-ID | Checkpoint | Days (target range) | Work | Exit proof | Stop or cut rule |
| --- | --- | --- | --- | --- | --- |
| M-001 | Feasibility proof | 1–7 (6–9) | Repo, compose environment, schema v0, auth for three roles, T-001, first baseline on one public dataset (E-001: does the adapter produce a usable table, and do baselines behave sensibly?) | T-001, T-002 | If E-001 shows the dataset cannot be mapped, switch to DS-002 or synthetic-only claims (§3.4) |
| M-002 | Walking skeleton | by day 12 (10–16) | Attendance entry end to end through real UI, API, database, student dashboard | T-019, T-003 partial | If past day 16, apply D-010 items 1–3 now |
| M-003 | Management core complete | by day 28 (24–34) | R-002 to R-007, R-014, R-017; analytics views (R-008) | T-003 to T-010, T-016, T-018 | Past day 34: apply D-010 items 4–5 and keep P0 only |
| M-004 | Analytics and ML integrated | by day 38 (34–42) | Training scripts, registry, inference endpoints, UI-005, recommendations, reports | T-011 to T-015, T-017 | Past day 42: ship baselines and rules, document models as notebooks |
| M-005 | Prototype ready | day 45 | Hardening, T-020, T-021, documentation, demo script with truth snapshot | all P0 T pass; P1 outcomes recorded honestly | No new features after day 41 |

Demo truth snapshot (prepare at M-005): build or commit, environment, data provenance (synthetic or public, by screen), what runs live, and the permitted claims (C-001 only in its bounded form). A recorded fallback demo, if used, is labeled as a recording.

Ordering principle: the risk-killing experiment E-001 runs in parallel with CRUD in week 1 so that the data question is answered before the ML UI is designed.

## 12. Risk register

| K-ID | Cause, event, consequence | Likelihood and impact (basis) | Earliest signal | Control and contingency | Owner |
| --- | --- | --- | --- | --- | --- |
| K-001 | Solo scope across web app, analytics, ML, and reports leads to P0 items unfinished | High, High (single developer, many objectives in S-001) | M-002 slips past day 12 | D-010 cut order; weekly velocity check | Developer |
| K-002 | Prior-grade or label-adjacent features leak the target and inflate scores | High, High (common in grade-prediction data) | Test R² far above baseline without the without-prior-grade variant | D-007 two variants, grouped splits, review by a second person (G-003) | Developer |
| K-003 | Teachers treat estimates as verdicts; students are stigmatized | Medium, High | Flags used without opening the record in pilot-style feedback | Reason codes, wording rules, D-012, T-017 | Developer, supervisor |
| K-004 | Missing object-level check exposes another user's data | Medium, High | T-003/T-004 failure | D-004 single authorization dependency; matrix tests | Developer |
| K-005 | Public dataset schema does not match EDWISE schema, so the integrated model is a stand-in | High, Medium | E-001 result | Adapter with documented omissions; model metadata states feature set; claim limited in C-001 | Developer |
| K-006 | Data loss or bad migration with no recovery | Medium, High | Failed restore in T-020 | Backups before migrations; T-020 | Developer |
| K-007 | Vulnerable dependency or weak token handling | Medium, Medium | T-021 findings | Pinned versions, scan, short token lifetime | Developer |
| K-008 | Synthetic-data results presented as real performance | Medium, High | A slide or report omits the label | R-015, T-017, truth snapshot | Developer |

## 13. Definition of done by checkpoint

### M-002 Walking skeleton

- [ ] DoD-001 Clean checkout starts the full stack with one command. Links: T-002. Artefact: command log and commit.
- [ ] DoD-002 Admin, teacher, and student can sign in; role enforced by the API. Links: R-001, T-003. Artefact: test report.
- [ ] DoD-003 Teacher attendance appears on the student dashboard; unrelated student sees nothing. Links: R-004, R-007, T-019. Artefact: test report and screen capture.

### M-003 Management core

- [ ] DoD-004 All P0 requirements R-001 to R-005, R-007, R-014, R-017 pass their T records. Artefact: test report with commit.
- [ ] DoD-005 Restore test passes. Links: T-020.
- [ ] DoD-006 Analytics match the fixture. Links: R-008, T-010.

### M-004 Analytics and ML

- [ ] DoD-007 Metrics table with baselines, both variants, and intervals exists as an artefact. Links: R-016, T-012.
- [ ] DoD-008 Every model-output screen carries source, version, and estimate wording. Links: R-015, T-017.
- [ ] DoD-009 Recommendations trace to indicators. Links: R-012, T-014.

### M-005 Prototype ready

- [ ] DoD-010 Dependency scan and pinned versions recorded. Links: T-021.
- [ ] DoD-011 Reports verified for scope and figures. Links: R-013, T-015.
- [ ] DoD-012 Demo truth snapshot written and C-001 wording matches measured results.

A checkpoint is `ACCEPTED` only when every in-scope box is checked or a waiver names approver, date, reason, and affected claims. In a solo project the approver is the developer, so waivers on security and evaluation items should be reviewed by a second person (G-003).

## 14. Gaps, external dependencies, and immediate action

| ID | Item | Owner and resolution |
| --- | --- | --- |
| G-001 | Real data blocked pending Q-001, Q-002, qualified review | Developer with institution contact |
| G-002 | No machine-readable registry file produced in this run; the tables here are the registry views | Developer may export to CSV or YAML from the tables |
| G-003 | No independent reviewer for security, evaluation, or release evidence | Developer to name a peer or supervisor before M-003 |
| X-001 | Availability and license of public datasets | T-001 |
| X-002 | Email delivery for verification, if chosen | Optional; default D-006 needs none |

Submission-facing reminder: this document is a plan. No code, test, dataset check, or metric exists yet, and none is claimed.

**Immediate next action:** create the repository and compose environment, then run T-001 and E-001 in parallel with the schema and auth work (days 1–7).

## 15. Author audit (self-review)

These checks were done by reading this document. No registry file exists, so they are manual scans, not queries, and `PASS` means only that the check was performed this way.

| Check | Result | Note |
| --- | --- | --- |
| Every P0/P1 R maps to a D and a T | PASS (manual) | §4 |
| Every T maps to an R, K, or enabling purpose | PASS (manual) | T-001, T-002, T-020, T-021 are enabling or risk-linked |
| Every K, Q, G has owner or resolution path | PASS (manual) | §2.4, §12, §14 |
| MEASURED, live, or reproduced labels used | none used | No artefacts exist |
| Screens have must show / must never imply | PASS (manual) | §6.2 |
| Critical dependencies have fallback or blocker | PASS (manual) | §3.4, G-001 |
| Consequential numbers carry label and basis | PARTIAL | Day ranges and the 2-exam minimum are `TARGET` with a basis; thresholds for precision floor, drift, and pass line are `UNKNOWN` by design |
| Omitted modules have project-specific reasons | PASS | Below |
| Reference leakage | PASS | No facts from other projects were used |

**Modules not applied:** real-time/streaming (no live event or latency promise in S-001); hardware (software only); commerce and marketplace (no money or multi-party exchange); offline/mobile (web only, S-001 §5); localization (single English locale assumed, A-004; revisit if that changes); vendor register (no critical paid third party; public datasets tracked as X-001); business/pilot (academic prototype, A-006; the demo truth snapshot in §11 covers the demonstration need).

**Limits of this playbook:** it was produced without web research, repository inspection, or code execution; dataset facts are inferred; legal and data-protection conclusions need qualified review; word count is below the Tier M planning range because the project is solo and the modules above were applied at the depth the brief supports, not padded to reach a length.
