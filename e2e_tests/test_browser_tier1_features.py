from __future__ import annotations

from datetime import date, timedelta
import json
import re
import subprocess
from pathlib import Path
from typing import Dict, Tuple

import httpx
from playwright.sync_api import Page, expect
import pytest

from helpers.auth import api_login, auth_headers_for, ui_login, ui_logout
from helpers.seed_helpers import (
    ADMIN_CREDS,
    CLASS_ID,
    SESSION_ID,
    STUDENT_1_CREDS,
    STUDENT_1_ID,
    STUDENT_2_CREDS,
    STUDENT_2_ID,
    STUDENT_3_ID,
    SUBJECT_MATH_ID,
    SUBJECT_SCI_ID,
    TEACHER_SARAH_CREDS,
    claim_student_account,
    create_announcement,
    create_doubt,
    create_exam,
    unique_tag,
    upload_exam_datesheet,
)
from helpers.servers import FRONTEND_DIR, IsolatedStack
from helpers.watchers import BrowserErrorWatcher

pytestmark = [pytest.mark.tier1, pytest.mark.browser]


def _set_range_slider(locator, value: int) -> None:
    locator.evaluate(
        """(el, val) => {
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            setter.call(el, String(val));
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        }""",
        value,
    )


# ---------------------------------------------------------------------------
# F9: Frontend API Clients & Build
# ---------------------------------------------------------------------------

def test_T1_F9_01_frontend_build_and_doubts_api_client(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    build = subprocess.run(
        ["npm.cmd", "run", "build"],
        cwd=str(FRONTEND_DIR),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert build.returncode == 0, f"Frontend build failed:\n{build.stdout}\n{build.stderr}"

    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    q = f"Client module test doubt [{unique_tag()}]"
    created = page.evaluate(
        """async ({ sessionId, subjectId, question }) => {
            const mod = await import('/src/api/doubts.js');
            const createFn = mod.createDoubt || mod.doubtsApi?.createDoubt || mod.default?.createDoubt;
            const getFn = mod.getDoubts || mod.doubtsApi?.getDoubts || mod.default?.getDoubts;
            const ansFn = mod.answerDoubt || mod.doubtsApi?.answerDoubt || mod.default?.answerDoubt;
            if (!createFn || !getFn || !ansFn) {
                throw new Error('Missing doubts.js exports: ' + Object.keys(mod).join(','));
            }
            const c = await createFn({ session_id: sessionId, subject_id: subjectId, question });
            const list = await getFn({ session_id: sessionId });
            return { created: c, count: list.length };
        }""",
        {"sessionId": SESSION_ID, "subjectId": SUBJECT_MATH_ID, "question": q},
    )
    assert created["created"]["question"] == q
    assert created["count"] >= 1


def test_T1_F9_02_announcements_api_client_crud(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")

    title = f"Client Notice {unique_tag()}"
    res = page.evaluate(
        """async ({ sessionId, classId, title }) => {
            const mod = await import('/src/api/announcements.js');
            const getFn = mod.getAnnouncements || mod.announcementsApi?.getAnnouncements || mod.default?.getAnnouncements;
            const createFn = mod.createAnnouncement || mod.announcementsApi?.createAnnouncement || mod.default?.createAnnouncement;
            const delFn = mod.deleteAnnouncement || mod.announcementsApi?.deleteAnnouncement || mod.default?.deleteAnnouncement;
            if (!getFn || !createFn || !delFn) {
                throw new Error('Missing announcements.js exports: ' + Object.keys(mod).join(','));
            }
            const created = await createFn({ session_id: sessionId, class_id: classId, title, content: 'Body', priority: 'Normal' });
            const list = await getFn({ session_id: sessionId });
            const deleted = await delFn(created.id);
            return { created, listLen: list.length, deleted };
        }""",
        {"sessionId": SESSION_ID, "classId": CLASS_ID, "title": title},
    )
    assert res["created"]["title"] == title
    assert res["listLen"] >= 1
    assert res["deleted"]["status"] == "success"


def test_T1_F9_03_academics_api_client_datesheet_and_csv(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
) -> None:
    exam = create_exam(api_client, teacher_sarah_headers, name=f"F9 Exam {unique_tag()}", max_marks=50.0)
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")

    result = page.evaluate(
        """async ({ examId, sessionId }) => {
            const { academicsApi } = await import('/src/api/academics.js');
            const upFn = academicsApi?.uploadDatesheet;
            const dlFn = academicsApi?.downloadDatesheet;
            const csvFn = academicsApi?.uploadMarksCsv;
            if (!upFn || !dlFn || !csvFn) {
                throw new Error('Missing academics.js additions');
            }
            const pdfFile = new File(['%PDF-1.4 f9 test'], 'f9.pdf', { type: 'application/pdf' });
            const upRes = await upFn(examId, pdfFile);
            const dlRes = await dlFn(examId, 'f9.pdf');
            const csvFile = new File([`Admission Number,Exam ID,Score\\nSTU1001,${examId},45\\n`], 'f9.csv', { type: 'text/csv' });
            const csvRes = await csvFn(csvFile, sessionId, 'F9 client test');
            return { upRes, hasDl: Boolean(dlRes), csvRes };
        }""",
        {"examId": exam["id"], "sessionId": SESSION_ID},
    )
    assert result["upRes"]["status"] == "success"
    assert result["hasDl"] is True
    assert result["csvRes"]["imported_count"] == 1


def test_T1_F9_04_analytics_api_client_goal_plan_and_badges(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")

    res = page.evaluate(
        """async ({ studentId, classId, sessionId }) => {
            const { analyticsApi } = await import('/src/api/analytics.js');
            if (!analyticsApi.getAttendanceGoal || !analyticsApi.getAiLessonPlan || !analyticsApi.getStudentBadges) {
                throw new Error('Missing analytics.js additions');
            }
            const goal = await analyticsApi.getAttendanceGoal(studentId, sessionId, 75.0);
            const plan = await analyticsApi.getAiLessonPlan(classId, sessionId);
            const badges = await analyticsApi.getStudentBadges(studentId, sessionId);
            return { goal, plan, badges };
        }""",
        {"studentId": STUDENT_1_ID, "classId": CLASS_ID, "sessionId": SESSION_ID},
    )
    assert res["goal"]["target_rate"] == 75.0
    assert len(res["plan"]["weekly_schedule"]) == 3
    assert len(res["badges"]["badges"]) == 5


def test_T1_F9_05_ml_api_client_predict_live_and_switch_model(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    ui_login(page, stack.frontend_url, *ADMIN_CREDS, expected_url_part="/admin")

    res = page.evaluate(
        """async () => {
            const { mlApi } = await import('/src/api/ml.js');
            if (!mlApi.predictLive || !mlApi.switchModel) {
                throw new Error('Missing ml.js additions');
            }
            const sw = await mlApi.switchModel('xgboost');
            const pred = await mlApi.predictLive({
                unit_test_score: 82,
                mid_term_score: 84,
                assignment_score: 86,
                attendance_pct: 92,
            });
            return { sw, pred };
        }"""
    )
    assert res["sw"]["status"] == "success"
    assert "xgboost" in res["pred"]["active_model"].lower()


# ---------------------------------------------------------------------------
# F10: Student Upcoming Exam Schedules & Datesheet Download
# ---------------------------------------------------------------------------

def test_T1_F10_01_student_sees_future_exam_countdown_and_names(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
) -> None:
    exam_name = f"Future Algebra {unique_tag()}"
    create_exam(
        api_client,
        teacher_sarah_headers,
        name=exam_name,
        exam_date=date.today() + timedelta(days=4),
    )
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    expect(page.get_by_text(exam_name)).to_be_visible(timeout=10000)
    expect(page.get_by_text("4 Days Left").first).to_be_visible()
    expect(page.get_by_text("Mathematics").first).to_be_visible()


def test_T1_F10_02_student_sees_today_exam_badge(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
) -> None:
    exam_name = f"Today Exam {unique_tag()}"
    create_exam(api_client, teacher_sarah_headers, name=exam_name, exam_date=date.today())

    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    expect(page.get_by_text(exam_name)).to_be_visible(timeout=10000)
    expect(page.get_by_text("Today!").first).to_be_visible()


def test_T1_F10_03_student_sees_completed_status_on_past_exam(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    expect(page.get_by_text("Unit Test 1 - Algebra").first).to_be_visible(timeout=10000)
    expect(page.get_by_text("Completed").first).to_be_visible()


def test_T1_F10_04_student_downloads_exam_datesheet_pdf(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
) -> None:
    exam_name = f"Datesheet DL {unique_tag()}"
    exam = create_exam(
        api_client,
        teacher_sarah_headers,
        name=exam_name,
        exam_date=date.today() + timedelta(days=3),
    )
    pdf_bytes = b"%PDF-1.4 browser download verification\n%%EOF"
    upload_exam_datesheet(
        api_client,
        teacher_sarah_headers,
        exam["id"],
        filename="term_schedule.pdf",
        content=pdf_bytes,
    )

    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    expect(page.get_by_text(exam_name)).to_be_visible(timeout=10000)

    row = page.locator("tr, div, li").filter(has_text=exam_name).filter(
        has=page.get_by_role("button", name=re.compile(r"download|datesheet", re.I))
    ).last
    dl_btn = row.get_by_role("button", name=re.compile(r"download|datesheet", re.I)).first

    with page.expect_download() as dl_info:
        dl_btn.click()
    download = dl_info.value
    assert download.suggested_filename
    dl_path = download.path()
    assert dl_path is not None and Path(dl_path).read_bytes() == pdf_bytes


def test_T1_F10_05_student_exam_rows_show_date_and_timeslot(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    expect(page.get_by_text("09:00 AM - 12:00 PM").first).to_be_visible(timeout=10000)
    body_text = page.locator("main").inner_text()
    assert "undefined" not in body_text.lower()
    assert "nan" not in body_text.lower()


# ---------------------------------------------------------------------------
# F11: Student Class Notice Board / Announcements
# ---------------------------------------------------------------------------

def test_T1_F11_01_student_notice_board_displays_seeded_announcements(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    expect(page.get_by_text("Mid-Term Examination Datesheet Released")).to_be_visible(timeout=10000)
    expect(page.get_by_text("Mathematics Remedial & Problem Solving Clinic")).to_be_visible()


def test_T1_F11_02_student_notice_board_shows_priority_indicators(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    expect(page.get_by_text("Mid-Term Examination Datesheet Released")).to_be_visible(timeout=10000)
    expect(page.get_by_text("High", exact=False).first).to_be_visible()
    expect(page.get_by_text("Normal", exact=False).first).to_be_visible()


def test_T1_F11_03_student_notice_board_shows_author_and_target_scope(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    expect(page.get_by_text("All Classes").first).to_be_visible(timeout=10000)
    expect(page.get_by_text("Grade 10").first).to_be_visible()
    expect(page.get_by_text(re.compile(r"Sarah|Administration", re.I)).first).to_be_visible()


def test_T1_F11_04_newest_notice_appears_on_student_reload(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
) -> None:
    title = f"Lab Safety Briefing {unique_tag()}"
    ann = create_announcement(api_client, teacher_sarah_headers, class_id=CLASS_ID, title=title, priority="High")
    try:
        page, _ = page_with_watcher
        ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
        expect(page.get_by_text(title)).to_be_visible(timeout=10000)
    finally:
        api_client.delete(f"/api/v1/announcements/{ann['id']}", headers=teacher_sarah_headers)


def test_T1_F11_05_student_2_sees_notices_cleanly(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_2_CREDS, expected_url_part="/student")

    expect(page.get_by_text("Mid-Term Examination Datesheet Released")).to_be_visible(timeout=10000)


# ---------------------------------------------------------------------------
# F12: Student 75% Attendance Goal Planner Widget
# ---------------------------------------------------------------------------

def test_T1_F12_01_student_1_sees_100_pct_and_safe_skips(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    student_1_headers: Dict[str, str],
) -> None:
    goal = api_client.get(
        f"/api/v1/attendance/goal/{STUDENT_1_ID}",
        params={"session_id": SESSION_ID},
        headers=student_1_headers,
    ).json()

    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    expect(page.get_by_text(re.compile(r"75%|Attendance Goal", re.I)).first).to_be_visible(timeout=10000)
    expect(page.get_by_text(re.compile(r"100(\.0)?%")).first).to_be_visible()
    expect(page.get_by_text(re.compile(rf"\b{goal['safe_skips_available']}\b")).first).to_be_visible()


def test_T1_F12_02_student_1_goal_widget_shows_attended_counts_and_target(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    student_1_headers: Dict[str, str],
) -> None:
    goal = api_client.get(
        f"/api/v1/attendance/goal/{STUDENT_1_ID}",
        params={"session_id": SESSION_ID},
        headers=student_1_headers,
    ).json()

    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    expect(page.get_by_text(re.compile(r"75%", re.I)).first).to_be_visible(timeout=10000)
    expect(page.get_by_text(re.compile(rf"\b{goal['total_conducted']}\b")).first).to_be_visible()


def test_T1_F12_03_low_attendance_student_sees_warning_and_needed_classes(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    claim_student_account(stack.api_client, "STU1003", class_id=CLASS_ID, password="Student@123")
    admin_h = auth_headers_for(stack.api_client, ADMIN_CREDS)
    goal = stack.api_client.get(
        f"/api/v1/attendance/goal/{STUDENT_3_ID}",
        params={"session_id": SESSION_ID},
        headers=admin_h,
    ).json()
    assert goal["is_warning"] is True and goal["needed_consecutive_classes"] > 0

    ui_login(page, stack.frontend_url, "STU1003", "Student@123", expected_url_part="/student")
    expect(page.get_by_text(re.compile(rf"\b{goal['needed_consecutive_classes']}\b")).first).to_be_visible(timeout=10000)


def test_T1_F12_04_attendance_goal_network_call_succeeds_on_student_load(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    with page.expect_response(
        lambda r: f"/api/v1/attendance/goal/{STUDENT_1_ID}" in r.url and r.status == 200,
        timeout=15000,
    ) as resp_info:
        ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    data = resp_info.value.json()
    expect(page.get_by_text(re.compile(rf"\b{data['safe_skips_available']}\b")).first).to_be_visible()


def test_T1_F12_05_attendance_goal_responsive_desktop_and_mobile(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    expect(page.get_by_text(re.compile(r"Attendance Goal|75%", re.I)).first).to_be_visible(timeout=10000)

    page.set_viewport_size({"width": 375, "height": 812})
    expect(page.get_by_text(re.compile(r"Attendance Goal|75%", re.I)).first).to_be_visible()
    overflow = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth + 2")
    assert not overflow, "Mobile viewport has horizontal overflow"


# ---------------------------------------------------------------------------
# F13: Student Doubt Clearing Box
# ---------------------------------------------------------------------------

def test_T1_F13_01_student_doubt_box_displays_seeded_doubts_and_statuses(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    expect(page.get_by_text("quadratic factorisation", exact=False)).to_be_visible(timeout=10000)
    expect(page.get_by_text("practical assessment", exact=False)).to_be_visible()
    expect(page.get_by_text("Answered", exact=False).first).to_be_visible()
    expect(page.get_by_text("Pending", exact=False).first).to_be_visible()


def test_T1_F13_02_student_submits_new_doubt_in_ui(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    q_text = f"Explain eigenvalues and eigenvectors? [{unique_tag()}]"
    doubt_card = page.locator("section, div").filter(has_text=re.compile(r"Doubt Clearing|Ask a Doubt", re.I)).last
    doubt_card.locator("textarea, input[type='text']").first.fill(q_text)
    with page.expect_response(lambda r: "/api/v1/doubts" in r.url and r.request.method == "POST") as post_resp:
        doubt_card.get_by_role("button", name=re.compile(r"Submit|Ask|Send", re.I)).first.click()
    assert post_resp.value.status in (200, 201)

    expect(page.get_by_text(q_text)).to_be_visible(timeout=10000)
    expect(page.get_by_text("Pending", exact=False).first).to_be_visible()


def test_T1_F13_03_submitted_doubt_persists_across_reload(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    q_text = f"Persist doubt check [{unique_tag()}]"
    doubt_card = page.locator("section, div").filter(has_text=re.compile(r"Doubt Clearing|Ask a Doubt", re.I)).last
    doubt_card.locator("textarea, input[type='text']").first.fill(q_text)
    with page.expect_response(lambda r: "/api/v1/doubts" in r.url and r.request.method == "POST"):
        doubt_card.get_by_role("button", name=re.compile(r"Submit|Ask|Send", re.I)).first.click()

    page.reload(wait_until="domcontentloaded")
    expect(page.get_by_text(q_text)).to_be_visible(timeout=10000)


def test_T1_F13_04_student_filters_doubts_by_subject(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    expect(page.get_by_text("quadratic factorisation", exact=False)).to_be_visible(timeout=10000)
    doubt_card = page.locator("section, div").filter(has_text=re.compile(r"Doubt Clearing|My Doubts", re.I)).last
    filter_select = doubt_card.locator("select").filter(has_text=re.compile(r"All", re.I)).first
    filter_select.select_option(label="Science")
    expect(page.get_by_text("practical assessment", exact=False)).to_be_visible()
    expect(page.get_by_text("quadratic factorisation", exact=False)).not_to_be_visible()

    filter_select.select_option(index=0)
    expect(page.get_by_text("quadratic factorisation", exact=False)).to_be_visible()


def test_T1_F13_05_answered_doubt_renders_faculty_response(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    expect(page.get_by_text("b^2 - 4ac", exact=False)).to_be_visible(timeout=10000)


# ---------------------------------------------------------------------------
# F14: Student Achievement Badges
# ---------------------------------------------------------------------------

def test_T1_F14_01_student_sees_all_five_achievement_badges(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    for title in ("Top Performer", "Attendance Champ", "Subject Ace", "All-Rounder", "Active Learner"):
        expect(page.get_by_text(title, exact=False).first).to_be_visible(timeout=10000)


def test_T1_F14_02_top_student_unlocked_badges_match_api(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    with page.expect_response(
        lambda r: f"/api/v1/analytics/student-badges/{STUDENT_2_ID}" in r.url and r.status == 200,
        timeout=15000,
    ) as resp_info:
        ui_login(page, frontend_url, *STUDENT_2_CREDS, expected_url_part="/student")
    badges = {b["title"]: b["unlocked"] for b in resp_info.value.json()["badges"]}
    assert badges["Top Performer"] is True and badges["Attendance Champ"] is True
    for title in ("Top Performer", "Attendance Champ", "Subject Ace", "All-Rounder"):
        expect(page.get_by_text(title, exact=False).first).to_be_visible()


def test_T1_F14_03_low_metrics_student_renders_locked_badges_without_error(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    claim_student_account(stack.api_client, "STU1003", class_id=CLASS_ID, password="Student@123")
    with page.expect_response(
        lambda r: f"/api/v1/analytics/student-badges/{STUDENT_3_ID}" in r.url and r.status == 200,
        timeout=15000,
    ) as resp_info:
        ui_login(page, stack.frontend_url, "STU1003", "Student@123", expected_url_part="/student")
    badges = {b["title"]: b["unlocked"] for b in resp_info.value.json()["badges"]}
    assert badges["Top Performer"] is False
    assert badges["Active Learner"] is True
    expect(page.get_by_text("Active Learner", exact=False).first).to_be_visible()


def test_T1_F14_04_badge_cards_display_criteria_descriptions(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    with page.expect_response(
        lambda r: f"/api/v1/analytics/student-badges/{STUDENT_1_ID}" in r.url and r.status == 200,
        timeout=15000,
    ) as resp_info:
        ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    first_desc = resp_info.value.json()["badges"][0]["description"]
    expect(page.get_by_text(first_desc, exact=False).first).to_be_visible()


def test_T1_F14_05_badges_api_response_200_and_rendered_on_dashboard(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    with page.expect_response(
        lambda r: f"/api/v1/analytics/student-badges/{STUDENT_1_ID}" in r.url and r.status == 200,
        timeout=15000,
    ) as resp_info:
        ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    payload = resp_info.value.json()
    assert len(payload["badges"]) == 5
    expect(page.get_by_text("Achievement Badges", exact=False).first).to_be_visible()


# ---------------------------------------------------------------------------
# F15: Student Interactive "What-If" AI Score Predictor Simulator
# ---------------------------------------------------------------------------

def test_T1_F15_01_what_if_simulator_renders_four_range_sliders(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    expect(page.get_by_text(re.compile(r"What-If|Score Predictor", re.I)).first).to_be_visible(timeout=10000)
    sliders = page.locator('input[type="range"]')
    assert sliders.count() >= 4


def test_T1_F15_02_what_if_simulator_high_sliders_show_low_risk(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    sliders = page.locator('input[type="range"]')
    assert sliders.count() >= 4
    with page.expect_response(lambda r: "/api/v1/ml/predict-live" in r.url and r.status == 200, timeout=15000):
        for idx, val in enumerate((90, 92, 95, 96)):
            _set_range_slider(sliders.nth(idx), val)
    expect(page.get_by_text("Low Risk", exact=False).first).to_be_visible(timeout=10000)


def test_T1_F15_03_what_if_simulator_low_sliders_show_high_risk_and_study_hours(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    sliders = page.locator('input[type="range"]')
    assert sliders.count() >= 4
    with page.expect_response(lambda r: "/api/v1/ml/predict-live" in r.url and r.status == 200, timeout=15000) as resp_info:
        for idx, val in enumerate((40, 42, 45, 60)):
            _set_range_slider(sliders.nth(idx), val)
    data = resp_info.value.json()
    assert data["risk_level"] == "High Risk"
    assert data["recommended_study_hours"] >= 2.0
    expect(page.get_by_text("High Risk", exact=False).first).to_be_visible(timeout=10000)


def test_T1_F15_04_what_if_simulator_updates_dynamically_without_reload(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    sliders = page.locator('input[type="range"]')
    assert sliders.count() >= 4
    for idx, val in enumerate((82, 82, 82, 95)):
        _set_range_slider(sliders.nth(idx), val)

    with page.expect_response(lambda r: "/api/v1/ml/predict-live" in r.url and r.status == 200, timeout=15000) as resp_info:
        _set_range_slider(sliders.nth(3), 72)
    assert resp_info.value.json()["risk_level"] in ("Medium Risk", "High Risk")
    expect(page.get_by_text(re.compile(r"Medium Risk|High Risk")).first).to_be_visible()


def test_T1_F15_05_what_if_simulator_displays_active_model_and_study_hours(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    with page.expect_response(lambda r: "/api/v1/ml/predict-live" in r.url and r.status == 200, timeout=15000) as resp_info:
        ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    data = resp_info.value.json()
    expect(page.get_by_text(data["active_model"], exact=False).first).to_be_visible(timeout=10000)
    expect(page.get_by_text(re.compile(rf"{data['recommended_study_hours']}")).first).to_be_visible()


# ---------------------------------------------------------------------------
# F16: Teacher AI Remedial Lesson Plan Generator
# ---------------------------------------------------------------------------

def test_T1_F16_01_teacher_opens_ai_lesson_plan_modal(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")

    btn = page.get_by_role("button", name=re.compile(r"AI.*Lesson Plan|Remedial.*Plan", re.I)).first
    expect(btn).to_be_visible(timeout=10000)
    btn.click()
    expect(page.get_by_text("Grade 10").first).to_be_visible(timeout=10000)


def test_T1_F16_02_teacher_generates_ai_lesson_plan_for_grade_10(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")

    page.get_by_role("button", name=re.compile(r"AI.*Lesson Plan|Remedial.*Plan", re.I)).first.click()
    gen_btn = page.get_by_role("button", name=re.compile(r"Generate", re.I)).first
    with page.expect_response(lambda r: "/api/v1/analytics/ai-lesson-plan/" in r.url and r.status == 200, timeout=15000) as resp_info:
        gen_btn.click()
    plan = resp_info.value.json()
    expect(page.get_by_text(plan["focus_subject"], exact=False).first).to_be_visible(timeout=10000)
    expect(page.get_by_text(plan["performance_status"], exact=False).first).to_be_visible()


def test_T1_F16_03_ai_lesson_plan_displays_three_day_schedule(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")

    page.get_by_role("button", name=re.compile(r"AI.*Lesson Plan|Remedial.*Plan", re.I)).first.click()
    page.get_by_role("button", name=re.compile(r"Generate", re.I)).first.click()
    for day in ("Monday", "Wednesday", "Friday"):
        expect(page.get_by_text(day, exact=False).first).to_be_visible(timeout=10000)


def test_T1_F16_04_teacher_closes_ai_lesson_plan_modal_cleanly(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")

    page.get_by_role("button", name=re.compile(r"AI.*Lesson Plan|Remedial.*Plan", re.I)).first.click()
    expect(page.get_by_role("button", name=re.compile(r"Generate", re.I)).first).to_be_visible(timeout=10000)
    page.get_by_role("button", name=re.compile(r"Close|Cancel", re.I)).first.click()
    expect(page.get_by_role("button", name=re.compile(r"Generate", re.I))).not_to_be_visible()


def test_T1_F16_05_reopen_and_regenerate_lesson_plan_without_duplicates(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")

    open_btn = page.get_by_role("button", name=re.compile(r"AI.*Lesson Plan|Remedial.*Plan", re.I)).first
    open_btn.click()
    page.get_by_role("button", name=re.compile(r"Generate", re.I)).first.click()
    expect(page.get_by_text("Monday", exact=False).first).to_be_visible(timeout=10000)
    page.get_by_role("button", name=re.compile(r"Close|Cancel", re.I)).first.click()

    open_btn.click()
    page.get_by_role("button", name=re.compile(r"Generate", re.I)).first.click()
    assert page.get_by_text("Monday", exact=False).count() == 1


# ---------------------------------------------------------------------------
# F17: Teacher Class Notice Board / Announcements Management
# ---------------------------------------------------------------------------

def test_T1_F17_01_teacher_sees_existing_announcements(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")

    expect(page.get_by_text("Mid-Term Examination Datesheet Released")).to_be_visible(timeout=10000)
    expect(page.get_by_text("Mathematics Remedial & Problem Solving Clinic")).to_be_visible()


def test_T1_F17_02_teacher_creates_high_priority_class_announcement(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
) -> None:
    title = f"Quiz Tomorrow {unique_tag()}"
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")

    board = page.locator("section, div").filter(has_text=re.compile(r"Notice Board|Announcements", re.I)).last
    board.get_by_placeholder(re.compile(r"title", re.I)).first.fill(title)
    board.locator("textarea").first.fill("Chapter 4 short quiz.")
    board.locator("select").filter(has_text=re.compile(r"Normal|High", re.I)).first.select_option("High")
    board.locator("select").filter(has_text=re.compile(r"Grade 10", re.I)).first.select_option(label="Grade 10")

    with page.expect_response(lambda r: "/api/v1/announcements" in r.url and r.request.method == "POST") as resp_info:
        board.get_by_role("button", name=re.compile(r"Post|Create|Publish|Add", re.I)).first.click()
    assert resp_info.value.status == 200
    created_id = resp_info.value.json()["id"]
    try:
        expect(page.get_by_text(title)).to_be_visible(timeout=10000)
    finally:
        api_client.delete(f"/api/v1/announcements/{created_id}", headers=teacher_sarah_headers)


def test_T1_F17_03_teacher_creates_global_normal_announcement(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
) -> None:
    title = f"Assembly Schedule {unique_tag()}"
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")

    board = page.locator("section, div").filter(has_text=re.compile(r"Notice Board|Announcements", re.I)).last
    board.get_by_placeholder(re.compile(r"title", re.I)).first.fill(title)
    board.locator("textarea").first.fill("Starts 8:30 AM.")
    board.locator("select").filter(has_text=re.compile(r"All Classes", re.I)).first.select_option(label="All Classes")

    with page.expect_response(lambda r: "/api/v1/announcements" in r.url and r.request.method == "POST") as resp_info:
        board.get_by_role("button", name=re.compile(r"Post|Create|Publish|Add", re.I)).first.click()
    assert resp_info.value.status == 200
    created_id = resp_info.value.json()["id"]
    try:
        expect(page.get_by_text(title)).to_be_visible(timeout=10000)
        expect(page.get_by_text("All Classes").first).to_be_visible()
    finally:
        api_client.delete(f"/api/v1/announcements/{created_id}", headers=teacher_sarah_headers)


def test_T1_F17_04_created_announcement_persists_across_reload(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
) -> None:
    title = f"Persist Notice {unique_tag()}"
    ann = create_announcement(api_client, teacher_sarah_headers, title=title, priority="High")
    try:
        page, _ = page_with_watcher
        ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
        expect(page.get_by_text(title)).to_be_visible(timeout=10000)
        page.reload(wait_until="domcontentloaded")
        expect(page.get_by_text(title)).to_be_visible(timeout=10000)
    finally:
        api_client.delete(f"/api/v1/announcements/{ann['id']}", headers=teacher_sarah_headers)


def test_T1_F17_05_teacher_deletes_own_announcement_in_ui(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
) -> None:
    title = f"Delete UI Notice {unique_tag()}"
    create_announcement(api_client, teacher_sarah_headers, title=title)

    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    expect(page.get_by_text(title)).to_be_visible(timeout=10000)

    row = page.locator("div, li, tr").filter(has_text=title).filter(
        has=page.get_by_role("button", name=re.compile(r"Delete|Remove", re.I))
    ).last
    with page.expect_response(lambda r: "/api/v1/announcements/" in r.url and r.request.method == "DELETE") as del_resp:
        row.get_by_role("button", name=re.compile(r"Delete|Remove", re.I)).first.click()
    assert del_resp.value.status == 200
    expect(page.get_by_text(title)).not_to_be_visible()
    page.reload(wait_until="domcontentloaded")
    expect(page.get_by_text(title)).not_to_be_visible()


# ---------------------------------------------------------------------------
# F18: Teacher Student Doubt Resolution Hub
# ---------------------------------------------------------------------------

def test_T1_F18_01_teacher_sees_student_doubts_with_student_and_subject(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")

    expect(page.get_by_text("Alex Carter", exact=False).first).to_be_visible(timeout=10000)
    expect(page.get_by_text("practical assessment", exact=False).first).to_be_visible()


def test_T1_F18_02_teacher_filters_doubt_hub_by_pending_status(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")

    hub = page.locator("section, div").filter(has_text=re.compile(r"Doubt.*Hub|Student Doubts", re.I)).last
    status_sel = hub.locator("select").filter(has_text=re.compile(r"Pending", re.I)).first
    status_sel.select_option(label="Pending")
    expect(page.get_by_text("practical assessment", exact=False)).to_be_visible()
    expect(page.get_by_text("quadratic factorisation", exact=False)).not_to_be_visible()


def test_T1_F18_03_teacher_filters_doubt_hub_by_subject(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")

    hub = page.locator("section, div").filter(has_text=re.compile(r"Doubt.*Hub|Student Doubts", re.I)).last
    subj_sel = hub.locator("select").filter(has_text=re.compile(r"Science", re.I)).first
    subj_sel.select_option(label="Science")
    expect(page.get_by_text("practical assessment", exact=False)).to_be_visible()
    expect(page.get_by_text("quadratic factorisation", exact=False)).not_to_be_visible()

    subj_sel.select_option(index=0)
    expect(page.get_by_text("quadratic factorisation", exact=False)).to_be_visible()


def test_T1_F18_04_teacher_submits_answer_in_doubt_hub(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    student_1_headers: Dict[str, str],
) -> None:
    q = f"Teacher hub answer test [{unique_tag()}]"
    create_doubt(api_client, student_1_headers, subject_id=SUBJECT_MATH_ID, question=q)

    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    expect(page.get_by_text(q)).to_be_visible(timeout=10000)

    card = page.locator("div, li").filter(has_text=q).filter(
        has=page.get_by_role("button", name=re.compile(r"Answer|Reply|Resolve|Submit", re.I))
    ).last
    ans_text = "Force equals mass times acceleration."
    card.locator("input, textarea").first.fill(ans_text)
    with page.expect_response(lambda r: "/answer" in r.url and r.request.method == "POST") as resp_info:
        card.get_by_role("button", name=re.compile(r"Answer|Reply|Resolve|Submit", re.I)).first.click()
    assert resp_info.value.status == 200
    expect(page.get_by_text(ans_text)).to_be_visible(timeout=10000)


def test_T1_F18_05_answered_doubt_persists_after_teacher_reload(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    student_1_headers: Dict[str, str],
) -> None:
    q = f"Doubt reload persist [{unique_tag()}]"
    create_doubt(api_client, student_1_headers, subject_id=SUBJECT_MATH_ID, question=q)

    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    expect(page.get_by_text(q)).to_be_visible(timeout=10000)

    card = page.locator("div, li").filter(has_text=q).filter(
        has=page.get_by_role("button", name=re.compile(r"Answer|Reply|Resolve|Submit", re.I))
    ).last
    ans_text = f"Saved answer [{unique_tag()}]"
    card.locator("input, textarea").first.fill(ans_text)
    with page.expect_response(lambda r: "/answer" in r.url and r.request.method == "POST"):
        card.get_by_role("button", name=re.compile(r"Answer|Reply|Resolve|Submit", re.I)).first.click()

    page.reload(wait_until="domcontentloaded")
    expect(page.get_by_text(ans_text)).to_be_visible(timeout=10000)


# ---------------------------------------------------------------------------
# F19: Teacher Bulk Marks CSV Upload & Exam Datesheet Upload
# ---------------------------------------------------------------------------

def test_T1_F19_01_marks_entry_displays_bulk_csv_upload_panel(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    page.goto(f"{frontend_url}/teacher/marks", wait_until="domcontentloaded")

    expect(page.get_by_text(re.compile(r"Bulk.*CSV|CSV.*Upload", re.I)).first).to_be_visible(timeout=10000)
    expect(page.locator('input[type="file"][accept*="csv" i]').first).to_be_attached()


def test_T1_F19_02_teacher_uploads_valid_marks_csv_in_ui(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
    tmp_path: Path,
) -> None:
    stack, page, _ = fresh_isolated_stack
    sarah_h = auth_headers_for(stack.api_client, TEACHER_SARAH_CREDS)
    exam = create_exam(stack.api_client, sarah_h, name=f"UI CSV Exam {unique_tag()}", max_marks=50.0)

    csv_path = tmp_path / "marks_batch.csv"
    csv_path.write_text(f"Admission Number,Exam ID,Score\nSTU1001,{exam['id']},45\nSTU1002,{exam['id']},49\n", encoding="utf-8")

    ui_login(page, stack.frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    page.goto(f"{stack.frontend_url}/teacher/marks", wait_until="domcontentloaded")

    csv_panel = page.locator("section, div").filter(has_text=re.compile(r"Bulk.*CSV|CSV.*Upload", re.I)).last
    csv_panel.locator('input[type="file"]').first.set_input_files(str(csv_path))
    with page.expect_response(lambda r: "/api/v1/marks/upload-csv" in r.url and r.request.method == "POST") as resp_info:
        csv_panel.get_by_role("button", name=re.compile(r"Upload|Import", re.I)).first.click()
    assert resp_info.value.status == 200
    assert resp_info.value.json()["imported_count"] == 2
    expect(page.get_by_text(re.compile(r"2\s*(records?|marks?)?\s*(imported|uploaded|success)", re.I)).first).to_be_visible(timeout=10000)


def test_T1_F19_03_teacher_marks_provides_datesheet_upload_control(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    page.goto(f"{frontend_url}/teacher/marks", wait_until="domcontentloaded")

    expect(page.locator('input[type="file"][accept*="pdf" i]').first).to_be_attached(timeout=10000)


def test_T1_F19_04_teacher_uploads_exam_datesheet_pdf_in_ui(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
    tmp_path: Path,
) -> None:
    exam = create_exam(api_client, teacher_sarah_headers, name=f"UI Datesheet Exam {unique_tag()}")
    pdf_path = tmp_path / "exam_datesheet.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 teacher ui datesheet\n%%EOF")

    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    page.goto(f"{frontend_url}/teacher/marks", wait_until="domcontentloaded")

    exam_select = page.locator("select").filter(has_text=exam["name"]).first
    exam_select.select_option(value=str(exam["id"]))

    ds_input = page.locator('input[type="file"][accept*="pdf" i]').first
    with page.expect_response(lambda r: f"/api/v1/exams/{exam['id']}/datesheet" in r.url and r.request.method == "POST") as resp_info:
        ds_input.set_input_files(str(pdf_path))
        upload_btns = page.get_by_role("button", name=re.compile(r"Upload Datesheet|Attach Datesheet", re.I))
        if upload_btns.count() > 0:
            upload_btns.first.click()
    assert resp_info.value.status == 200
    expect(page.get_by_text(re.compile(r"exam_datesheet\.pdf|uploaded", re.I)).first).to_be_visible(timeout=10000)


def test_T1_F19_05_uploaded_datesheet_indicator_persists_on_reload(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
) -> None:
    exam = create_exam(api_client, teacher_sarah_headers, name=f"Persist DS Exam {unique_tag()}")
    upload_exam_datesheet(api_client, teacher_sarah_headers, exam["id"], filename="persisted_ds.pdf")

    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    page.goto(f"{frontend_url}/teacher/marks", wait_until="domcontentloaded")

    exam_select = page.locator("select").filter(has_text=exam["name"]).first
    exam_select.select_option(value=str(exam["id"]))
    page.reload(wait_until="domcontentloaded")
    page.locator("select").filter(has_text=exam["name"]).first.select_option(value=str(exam["id"]))
    expect(page.get_by_text("persisted_ds.pdf", exact=False).first).to_be_visible(timeout=10000)


# ---------------------------------------------------------------------------
# F20: Admin Model Switcher UI & Metrics Comparison
# ---------------------------------------------------------------------------

def test_T1_F20_01_admin_model_registry_displays_side_by_side_metrics(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *ADMIN_CREDS, expected_url_part="/admin")
    page.goto(f"{frontend_url}/admin/models", wait_until="domcontentloaded")

    for name in ("LinearRegression", "Random Forest", "XGBoost"):
        expect(page.get_by_text(name, exact=False).first).to_be_visible(timeout=10000)
    for metric in ("MAE", "RMSE", "R2"):
        expect(page.get_by_text(re.compile(rf"\b{metric}\b|R²", re.I)).first).to_be_visible()


def test_T1_F20_02_admin_model_registry_has_exactly_one_active_regression_model(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    ui_login(page, stack.frontend_url, *ADMIN_CREDS, expected_url_part="/admin")
    with page.expect_response(lambda r: "/api/v1/ml/models" in r.url and r.status == 200, timeout=15000) as resp_info:
        page.goto(f"{stack.frontend_url}/admin/models", wait_until="domcontentloaded")
    reg = [m for m in resp_info.value.json() if "regression" in m["task"].lower()]
    assert sum(1 for m in reg if m["is_active"]) == 1


def test_T1_F20_03_admin_switches_active_model_to_xgboost_in_ui(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    ui_login(page, stack.frontend_url, *ADMIN_CREDS, expected_url_part="/admin")
    page.goto(f"{stack.frontend_url}/admin/models", wait_until="domcontentloaded")

    xgb_card = page.locator("div").filter(has_text="XGBoost").filter(
        has=page.get_by_role("button", name=re.compile(r"Switch|Activate|Set Active", re.I))
    ).last
    with page.expect_response(lambda r: "/api/v1/ml/switch-model" in r.url and r.request.method == "POST") as resp_info:
        xgb_card.get_by_role("button", name=re.compile(r"Switch|Activate|Set Active", re.I)).first.click()
    assert resp_info.value.status == 200
    assert "xgboost" in resp_info.value.json()["active_model"].lower()


def test_T1_F20_04_admin_switches_active_model_to_linear_regression_in_ui(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    ui_login(page, stack.frontend_url, *ADMIN_CREDS, expected_url_part="/admin")
    page.goto(f"{stack.frontend_url}/admin/models", wait_until="domcontentloaded")

    lin_card = page.locator("div").filter(has_text=re.compile(r"LinearRegression|Linear Regression")).filter(
        has=page.get_by_role("button", name=re.compile(r"Switch|Activate|Set Active", re.I))
    ).last
    with page.expect_response(lambda r: "/api/v1/ml/switch-model" in r.url and r.request.method == "POST") as resp_info:
        lin_card.get_by_role("button", name=re.compile(r"Switch|Activate|Set Active", re.I)).first.click()
    assert resp_info.value.status == 200
    assert "linear" in resp_info.value.json()["active_model"].lower()


def test_T1_F20_05_model_switch_persists_across_reload(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    ui_login(page, stack.frontend_url, *ADMIN_CREDS, expected_url_part="/admin")
    page.goto(f"{stack.frontend_url}/admin/models", wait_until="domcontentloaded")

    xgb_card = page.locator("div").filter(has_text="XGBoost").filter(
        has=page.get_by_role("button", name=re.compile(r"Switch|Activate|Set Active", re.I))
    ).last
    with page.expect_response(lambda r: "/api/v1/ml/switch-model" in r.url and r.request.method == "POST"):
        xgb_card.get_by_role("button", name=re.compile(r"Switch|Activate|Set Active", re.I)).first.click()

    with page.expect_response(lambda r: "/api/v1/ml/models" in r.url and r.status == 200, timeout=15000) as reload_models:
        page.reload(wait_until="domcontentloaded")
    active_reg = [
        m for m in reload_models.value.json() if "regression" in m["task"].lower() and m["is_active"]
    ]
    assert len(active_reg) == 1 and "xgboost" in active_reg[0]["model_name"].lower()


# ---------------------------------------------------------------------------
# F21: App Routing, Sidebar & Navbar Wiring
# ---------------------------------------------------------------------------

def test_T1_F21_01_student_sidebar_links_navigate_cleanly(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    links = page.locator("aside nav a")
    count = links.count()
    assert count >= 2
    for idx in range(count):
        href = links.nth(idx).get_attribute("href")
        links.nth(idx).click()
        page.wait_for_url(f"**{href}**", wait_until="commit", timeout=10000)
        page.locator("main, form").first.wait_for(state="visible", timeout=15000)
        assert page.locator("main").inner_text().strip()


def test_T1_F21_02_teacher_sidebar_links_navigate_cleanly(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")

    links = page.locator("aside nav a")
    count = links.count()
    assert count >= 5
    for idx in range(count):
        href = links.nth(idx).get_attribute("href")
        links.nth(idx).click()
        page.wait_for_url(f"**{href}**", wait_until="commit", timeout=10000)
        page.locator("main, form").first.wait_for(state="visible", timeout=15000)
        assert page.locator("main").inner_text().strip()


def test_T1_F21_03_admin_sidebar_links_navigate_cleanly(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *ADMIN_CREDS, expected_url_part="/admin")

    links = page.locator("aside nav a")
    count = links.count()
    assert count >= 7
    for idx in range(count):
        href = links.nth(idx).get_attribute("href")
        links.nth(idx).click()
        page.wait_for_url(f"**{href}**", wait_until="commit", timeout=10000)
        page.locator("main, form").first.wait_for(state="visible", timeout=15000)
        assert page.locator("main").inner_text().strip()


def test_T1_F21_04_navbar_displays_brand_session_profile_and_logout(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    header = page.locator("header")
    expect(header.get_by_text("EDWISE")).to_be_visible()
    expect(header.locator("select")).to_be_visible()
    expect(header.get_by_text("Alex Carter")).to_be_visible()
    expect(header.get_by_text("STU1001")).to_be_visible()
    expect(header.get_by_text("STUDENT", exact=True)).to_be_visible()
    expect(header.locator('button[title="Sign Out"]')).to_be_visible()


def test_T1_F21_05_logout_clears_session_and_blocks_protected_routes(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    ui_logout(page)

    token = page.evaluate("() => localStorage.getItem('access_token') || sessionStorage.getItem('access_token')")
    assert token is None

    page.goto(f"{frontend_url}/teacher", wait_until="domcontentloaded")
    expect(page).to_have_url(re.compile(r"/login"), timeout=10000)
