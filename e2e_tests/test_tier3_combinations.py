from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import re
from typing import Dict, Tuple

import httpx
from playwright.sync_api import Page, expect
import pytest

from helpers.auth import auth_headers_for, ui_login, ui_logout
from helpers.seed_helpers import (
    ADMIN_CREDS,
    CLASS_ID,
    SECTION_A_ID,
    SESSION_ID,
    STUDENT_1_CREDS,
    STUDENT_1_ID,
    STUDENT_3_ID,
    SUBJECT_MATH_ID,
    SUBJECT_SCI_ID,
    TEACHER_ALAN_CREDS,
    TEACHER_SARAH_CREDS,
    create_announcement,
    create_doubt,
    create_exam,
    create_fresh_student,
    record_attendance_days,
    save_student_marks,
    unique_tag,
)
from helpers.servers import IsolatedStack
from helpers.watchers import BrowserErrorWatcher

pytestmark = [pytest.mark.tier3]


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


@pytest.mark.browser
def test_T3_01_teacher_uploads_datesheet_student_downloads_with_countdown(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
    tmp_path: Path,
) -> None:
    exam = create_exam(
        api_client,
        teacher_sarah_headers,
        name=f"T301 Exam {unique_tag()}",
        exam_date=date.today() + timedelta(days=7),
    )
    pdf_bytes = b"%PDF-1.4 T3_01 cross feature datesheet\n%%EOF"
    pdf_path = tmp_path / "t301.pdf"
    pdf_path.write_bytes(pdf_bytes)

    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    page.goto(f"{frontend_url}/teacher/marks", wait_until="domcontentloaded")
    page.locator("select").filter(has_text=exam["name"]).first.select_option(value=str(exam["id"]))

    ds_input = page.locator('input[type="file"][accept*="pdf" i]').first
    with page.expect_response(lambda r: f"/api/v1/exams/{exam['id']}/datesheet" in r.url and r.status == 200):
        ds_input.set_input_files(str(pdf_path))
        btns = page.get_by_role("button", name=re.compile(r"Upload Datesheet|Attach Datesheet", re.I))
        if btns.count() > 0:
            btns.first.click()

    ui_logout(page)
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    expect(page.get_by_text(exam["name"])).to_be_visible(timeout=10000)
    expect(page.get_by_text("7 Days Left").first).to_be_visible()

    row = page.locator("tr, div, li").filter(has_text=exam["name"]).filter(
        has=page.get_by_role("button", name=re.compile(r"download|datesheet", re.I))
    ).last
    with page.expect_download() as dl_info:
        row.get_by_role("button", name=re.compile(r"download|datesheet", re.I)).first.click()
    dl_path = dl_info.value.path()
    assert dl_path is not None and Path(dl_path).read_bytes() == pdf_bytes


@pytest.mark.browser
def test_T3_02_teacher_creates_and_deletes_notice_reflected_on_student_board(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    high_title = f"T302 High Notice {unique_tag()}"
    norm_title = f"T302 Normal Notice {unique_tag()}"

    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    board = page.locator("section, div").filter(has_text=re.compile(r"Notice Board|Announcements", re.I)).last

    board.get_by_placeholder(re.compile(r"title", re.I)).first.fill(high_title)
    board.locator("textarea").first.fill("High priority body")
    board.locator("select").filter(has_text=re.compile(r"Normal|High", re.I)).first.select_option("High")
    board.locator("select").filter(has_text=re.compile(r"Grade 10", re.I)).first.select_option(label="Grade 10")
    with page.expect_response(lambda r: "/api/v1/announcements" in r.url and r.status == 200):
        board.get_by_role("button", name=re.compile(r"Post|Create|Publish|Add", re.I)).first.click()

    board.get_by_placeholder(re.compile(r"title", re.I)).first.fill(norm_title)
    board.locator("textarea").first.fill("Normal priority body")
    board.locator("select").filter(has_text=re.compile(r"Normal|High", re.I)).first.select_option("Normal")
    board.locator("select").filter(has_text=re.compile(r"All Classes", re.I)).first.select_option(label="All Classes")
    with page.expect_response(lambda r: "/api/v1/announcements" in r.url and r.status == 200):
        board.get_by_role("button", name=re.compile(r"Post|Create|Publish|Add", re.I)).first.click()

    ui_logout(page)
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    expect(page.get_by_text(high_title)).to_be_visible(timeout=10000)
    expect(page.get_by_text(norm_title)).to_be_visible()

    ui_logout(page)
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    row = page.locator("div, li, tr").filter(has_text=high_title).filter(
        has=page.get_by_role("button", name=re.compile(r"Delete|Remove", re.I))
    ).last
    with page.expect_response(lambda r: "/api/v1/announcements/" in r.url and r.request.method == "DELETE"):
        row.get_by_role("button", name=re.compile(r"Delete|Remove", re.I)).first.click()

    ui_logout(page)
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    expect(page.get_by_text(norm_title)).to_be_visible(timeout=10000)
    expect(page.get_by_text(high_title)).not_to_be_visible()


@pytest.mark.browser
def test_T3_03_student_submits_doubt_teacher_answers_student_sees_resolution(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    q = f"T303 cross doubt [{unique_tag()}]"
    ans = f"T303 resolved answer [{unique_tag()}]"

    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    doubt_card = page.locator("section, div").filter(has_text=re.compile(r"Doubt Clearing|Ask a Doubt", re.I)).last
    doubt_card.locator("textarea, input[type='text']").first.fill(q)
    with page.expect_response(lambda r: "/api/v1/doubts" in r.url and r.request.method == "POST"):
        doubt_card.get_by_role("button", name=re.compile(r"Submit|Ask|Send", re.I)).first.click()
    expect(page.get_by_text(q)).to_be_visible(timeout=10000)

    ui_logout(page)
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    hub = page.locator("section, div").filter(has_text=re.compile(r"Doubt.*Hub|Student Doubts", re.I)).last
    hub.locator("select").filter(has_text=re.compile(r"Pending", re.I)).first.select_option(label="Pending")
    card = page.locator("div, li").filter(has_text=q).filter(
        has=page.get_by_role("button", name=re.compile(r"Answer|Reply|Resolve|Submit", re.I))
    ).last
    card.locator("input, textarea").first.fill(ans)
    with page.expect_response(lambda r: "/answer" in r.url and r.request.method == "POST"):
        card.get_by_role("button", name=re.compile(r"Answer|Reply|Resolve|Submit", re.I)).first.click()

    ui_logout(page)
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    expect(page.get_by_text(ans)).to_be_visible(timeout=10000)


@pytest.mark.browser
def test_T3_04_bulk_csv_marks_updates_student_dashboard_and_badges(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
    tmp_path: Path,
) -> None:
    stack, page, _ = fresh_isolated_stack
    csv_path = tmp_path / "t304.csv"
    csv_path.write_text("Admission Number,Exam ID,Score\nSTU1001,1,50\nSTU1001,2,100\n", encoding="utf-8")

    ui_login(page, stack.frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    page.goto(f"{stack.frontend_url}/teacher/marks", wait_until="domcontentloaded")
    csv_panel = page.locator("section, div").filter(has_text=re.compile(r"Bulk.*CSV|CSV.*Upload", re.I)).last
    csv_panel.locator('input[type="file"]').first.set_input_files(str(csv_path))
    with page.expect_response(lambda r: "/api/v1/marks/upload-csv" in r.url and r.status == 200):
        csv_panel.get_by_role("button", name=re.compile(r"Upload|Import", re.I)).first.click()

    ui_logout(page)
    with page.expect_response(lambda r: f"/api/v1/analytics/student-badges/{STUDENT_1_ID}" in r.url and r.status == 200) as b_resp:
        ui_login(page, stack.frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    badges = {b["title"]: b["unlocked"] for b in b_resp.value.json()["badges"]}
    assert badges["Top Performer"] is True and badges["Subject Ace"] is True
    expect(page.get_by_text("100", exact=False).first).to_be_visible()


@pytest.mark.browser
def test_T3_05_admin_model_switch_changes_student_what_if_active_prediction(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    ui_login(page, stack.frontend_url, *ADMIN_CREDS, expected_url_part="/admin")
    page.goto(f"{stack.frontend_url}/admin/models", wait_until="domcontentloaded")
    expect(page.get_by_text("Random Forest", exact=False).first).to_be_visible(timeout=10000)

    xgb_card = page.locator("div").filter(has_text="XGBoost").filter(
        has=page.get_by_role("button", name=re.compile(r"Switch|Activate|Set Active", re.I))
    ).last
    with page.expect_response(lambda r: "/api/v1/ml/switch-model" in r.url and r.status == 200):
        xgb_card.get_by_role("button", name=re.compile(r"Switch|Activate|Set Active", re.I)).first.click()

    ui_logout(page)
    with page.expect_response(lambda r: "/api/v1/ml/predict-live" in r.url and r.status == 200) as p1:
        ui_login(page, stack.frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    d1 = p1.value.json()
    assert "xgboost" in d1["active_model"].lower()
    assert d1["active_prediction"] == d1["xgb_prediction"]

    ui_logout(page)
    ui_login(page, stack.frontend_url, *ADMIN_CREDS, expected_url_part="/admin")
    page.goto(f"{stack.frontend_url}/admin/models", wait_until="domcontentloaded")
    expect(page.get_by_text("Random Forest", exact=False).first).to_be_visible(timeout=10000)
    lin_card = page.locator("div").filter(has_text=re.compile(r"LinearRegression|Linear Regression")).filter(
        has=page.get_by_role("button", name=re.compile(r"Switch|Activate|Set Active", re.I))
    ).last
    with page.expect_response(lambda r: "/api/v1/ml/switch-model" in r.url and r.status == 200):
        lin_card.get_by_role("button", name=re.compile(r"Switch|Activate|Set Active", re.I)).first.click()

    ui_logout(page)
    ui_login(page, stack.frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    sliders = page.locator('input[type="range"]')
    with page.expect_response(lambda r: "/api/v1/ml/predict-live" in r.url and r.status == 200) as p2:
        _set_range_slider(sliders.nth(0), 85)
    d2 = p2.value.json()
    assert "linear" in d2["active_model"].lower()
    assert d2["active_prediction"] == d2["linear_prediction"]


@pytest.mark.browser
def test_T3_06_sequential_multi_role_navigation_pass(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    for creds, prefix in (
        (STUDENT_1_CREDS, "/student"),
        (TEACHER_SARAH_CREDS, "/teacher"),
        (ADMIN_CREDS, "/admin"),
    ):
        ui_login(page, frontend_url, *creds, expected_url_part=prefix)
        links = page.locator("aside nav a")
        for idx in range(links.count()):
            href = links.nth(idx).get_attribute("href")
            links.nth(idx).click()
            page.wait_for_url(f"**{href}**", wait_until="commit", timeout=10000)
            page.locator("main, form").first.wait_for(state="visible", timeout=15000)
            assert page.locator("main").inner_text().strip()
            if href == "/teacher/analytics":
                expect(
                    page.get_by_text("K-Means Engagement Pattern Exploration", exact=False).first
                ).to_be_visible(timeout=10000)
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
        ui_logout(page)


@pytest.mark.browser
def test_T3_07_admin_global_high_notice_visible_to_teacher_and_student(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    admin_headers: Dict[str, str],
) -> None:
    title = f"Admin Global T307 {unique_tag()}"
    ann = create_announcement(api_client, admin_headers, class_id=None, title=title, priority="High")
    try:
        page, watcher = page_with_watcher
        ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
        expect(page.get_by_text(title)).to_be_visible(timeout=10000)
        expect(page.get_by_text("Administration").first).to_be_visible()

        row = page.locator("div, li, tr").filter(has_text=title).last
        del_btn = row.get_by_role("button", name=re.compile(r"Delete|Remove", re.I))
        if del_btn.count() > 0 and del_btn.first.is_enabled():
            with watcher.allow_status(403, 422):
                del_btn.first.click()
                page.wait_for_timeout(300)

        ui_logout(page)
        ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
        expect(page.get_by_text(title)).to_be_visible(timeout=10000)
    finally:
        api_client.delete(f"/api/v1/announcements/{ann['id']}", headers=admin_headers)


@pytest.mark.browser
def test_T3_08_admin_answers_doubt_via_teacher_route_and_student_sees_it(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    student_1_headers: Dict[str, str],
) -> None:
    q = f"T308 Admin doubt [{unique_tag()}]"
    ans = f"T308 Admin reply [{unique_tag()}]"
    d = create_doubt(api_client, student_1_headers, question=q)

    page, _ = page_with_watcher
    ui_login(page, frontend_url, *ADMIN_CREDS, expected_url_part="/admin")
    page.goto(f"{frontend_url}/teacher", wait_until="domcontentloaded")
    expect(page.get_by_text(q)).to_be_visible(timeout=10000)

    card = page.locator("div, li").filter(has_text=q).filter(
        has=page.get_by_role("button", name=re.compile(r"Answer|Reply|Resolve|Submit", re.I))
    ).last
    card.locator("input, textarea").first.fill(ans)
    with page.expect_response(lambda r: f"/api/v1/doubts/{d['id']}/answer" in r.url and r.status == 200) as ans_resp:
        card.get_by_role("button", name=re.compile(r"Answer|Reply|Resolve|Submit", re.I)).first.click()
    assert ans_resp.value.json()["answered_by"] is None

    ui_logout(page)
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    expect(page.get_by_text(ans)).to_be_visible(timeout=10000)


@pytest.mark.browser
def test_T3_09_same_day_exam_png_datesheet_upload_and_student_download(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
    tmp_path: Path,
) -> None:
    exam = create_exam(api_client, teacher_sarah_headers, name=f"T309 Today PNG {unique_tag()}", exam_date=date.today())
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
    png_path = tmp_path / "today_sheet.png"
    png_path.write_bytes(png_bytes)

    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    page.goto(f"{frontend_url}/teacher/marks", wait_until="domcontentloaded")
    page.locator("select").filter(has_text=exam["name"]).first.select_option(value=str(exam["id"]))
    ds_input = page.locator('input[type="file"][accept*="pdf" i]').first
    with page.expect_response(lambda r: f"/api/v1/exams/{exam['id']}/datesheet" in r.url and r.status == 200):
        ds_input.set_input_files(str(png_path))
        btns = page.get_by_role("button", name=re.compile(r"Upload Datesheet|Attach Datesheet", re.I))
        if btns.count() > 0:
            btns.first.click()

    ui_logout(page)
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    expect(page.get_by_text(exam["name"])).to_be_visible(timeout=10000)
    expect(page.get_by_text("Today!").first).to_be_visible()
    row = page.locator("tr, div, li").filter(has_text=exam["name"]).filter(
        has=page.get_by_role("button", name=re.compile(r"download|datesheet", re.I))
    ).last
    with page.expect_download() as dl_info:
        row.get_by_role("button", name=re.compile(r"download|datesheet", re.I)).first.click()
    assert Path(dl_info.value.path()).read_bytes() == png_bytes


@pytest.mark.browser
def test_T3_10_low_attendance_goal_and_mirrored_what_if_high_risk(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    admin_h = auth_headers_for(stack.api_client, ADMIN_CREDS)
    sarah_h = auth_headers_for(stack.api_client, TEACHER_SARAH_CREDS)
    stu = create_fresh_student(stack.api_client, admin_h, claim=True)
    record_attendance_days(stack.api_client, sarah_h, student_id=stu["id"], present_count=5, absent_count=5)

    ui_login(page, stack.frontend_url, stu["admission_number"], stu["password"], expected_url_part="/student")
    expect(page.get_by_text(re.compile(r"50(\.0)?%", re.I)).first).to_be_visible(timeout=10000)
    sliders = page.locator('input[type="range"]')
    with page.expect_response(lambda r: "/api/v1/ml/predict-live" in r.url and r.status == 200) as r_info:
        _set_range_slider(sliders.nth(3), 50)
    assert r_info.value.json()["risk_level"] == "High Risk"
    expect(page.get_by_text("High Risk", exact=False).first).to_be_visible()


@pytest.mark.browser
def test_T3_11_csv_low_science_scores_drive_ai_lesson_plan_focus_subject(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
    tmp_path: Path,
) -> None:
    stack, page, _ = fresh_isolated_stack
    alan_h = auth_headers_for(stack.api_client, TEACHER_ALAN_CREDS)
    sci_exam = create_exam(stack.api_client, alan_h, subject_id=SUBJECT_SCI_ID, name=f"Sci Low {unique_tag()}", max_marks=100.0)
    csv_path = tmp_path / "sci_low.csv"
    csv_path.write_text(
        f"Admission Number,Exam ID,Score\nSTU1001,{sci_exam['id']},35\nSTU1002,{sci_exam['id']},35\n",
        encoding="utf-8",
    )

    ui_login(page, stack.frontend_url, *TEACHER_ALAN_CREDS, expected_url_part="/teacher")
    page.goto(f"{stack.frontend_url}/teacher/marks", wait_until="domcontentloaded")
    csv_panel = page.locator("section, div").filter(has_text=re.compile(r"Bulk.*CSV|CSV.*Upload", re.I)).last
    csv_panel.locator('input[type="file"]').first.set_input_files(str(csv_path))
    with page.expect_response(lambda r: "/api/v1/marks/upload-csv" in r.url and r.status == 200):
        csv_panel.get_by_role("button", name=re.compile(r"Upload|Import", re.I)).first.click()

    page.locator('aside nav a[href="/teacher"]').click()
    page.wait_for_url("**/teacher", wait_until="commit", timeout=10000)
    page.get_by_role("button", name=re.compile(r"AI.*Lesson Plan|Remedial.*Plan", re.I)).first.click()
    with page.expect_response(lambda r: "/api/v1/analytics/ai-lesson-plan/" in r.url and r.status == 200) as p_info:
        page.get_by_role("button", name=re.compile(r"Generate", re.I)).first.click()
    plan = p_info.value.json()
    assert plan["focus_subject"] == "Science"
    assert plan["performance_status"] == "Challenging"


@pytest.mark.browser
def test_T3_12_teacher_navigates_marks_csv_to_analytics_reflects_scores(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
    tmp_path: Path,
) -> None:
    stack, page, _ = fresh_isolated_stack
    sarah_h = auth_headers_for(stack.api_client, TEACHER_SARAH_CREDS)
    exam = create_exam(stack.api_client, sarah_h, name=f"Analytics CSV {unique_tag()}", max_marks=100.0)
    csv_path = tmp_path / "t312.csv"
    csv_path.write_text(f"Admission Number,Exam ID,Score\nSTU1001,{exam['id']},88\nSTU1002,{exam['id']},92\n", encoding="utf-8")

    ui_login(page, stack.frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    page.locator('aside nav a[href="/teacher/marks"]').click()
    page.wait_for_url("**/teacher/marks**", wait_until="commit", timeout=10000)
    csv_panel = page.locator("section, div").filter(has_text=re.compile(r"Bulk.*CSV|CSV.*Upload", re.I)).last
    csv_panel.locator('input[type="file"]').first.set_input_files(str(csv_path))
    with page.expect_response(lambda r: "/api/v1/marks/upload-csv" in r.url and r.status == 200):
        csv_panel.get_by_role("button", name=re.compile(r"Upload|Import", re.I)).first.click()

    page.locator('aside nav a[href="/teacher/analytics"]').click()
    page.wait_for_url("**/teacher/analytics**", wait_until="commit", timeout=10000)
    page.locator("main, form").first.wait_for(state="visible", timeout=15000)
    expect(page.get_by_text(exam["name"], exact=False).first).to_be_visible(timeout=10000)


@pytest.mark.api
def test_T3_13_marks_csv_elevation_promotes_student_rank_and_badges(
    fresh_backend_client: httpx.Client,
) -> None:
    admin_h = auth_headers_for(fresh_backend_client, ADMIN_CREDS)
    sarah_h = auth_headers_for(fresh_backend_client, TEACHER_SARAH_CREDS)
    csv_bytes = b"Admission Number,Exam ID,Score\nSTU1003,1,50\nSTU1003,2,100\n"
    up = fresh_backend_client.post(
        "/api/v1/marks/upload-csv",
        data={"session_id": str(SESSION_ID), "reason": "Retest boost"},
        files={"file": ("boost.csv", csv_bytes, "text/csv")},
        headers=sarah_h,
    )
    assert up.status_code == 200
    badges = fresh_backend_client.get(
        f"/api/v1/analytics/student-badges/{STUDENT_3_ID}",
        params={"session_id": SESSION_ID},
        headers=admin_h,
    ).json()
    by_title = {b["title"]: b["unlocked"] for b in badges["badges"]}
    assert by_title["Top Performer"] is True or badges["rank"] <= 3
    assert by_title["Subject Ace"] is True


@pytest.mark.browser
def test_T3_14_attendance_drop_below_95_keeps_goal_safe_but_locks_attendance_champ(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    admin_h = auth_headers_for(stack.api_client, ADMIN_CREDS)
    sarah_h = auth_headers_for(stack.api_client, TEACHER_SARAH_CREDS)
    stu = create_fresh_student(stack.api_client, admin_h, claim=True)
    record_attendance_days(stack.api_client, sarah_h, student_id=stu["id"], present_count=19, absent_count=1, start_date=date(2026, 2, 1))

    # 19/20 = 95.0% -> Attendance Champ unlocked
    b1 = {
        b["title"]: b["unlocked"]
        for b in stack.api_client.get(
            f"/api/v1/analytics/student-badges/{stu['id']}", params={"session_id": SESSION_ID}, headers=admin_h
        ).json()["badges"]
    }
    assert b1["Attendance Champ"] is True

    # 1 absent -> 19/21 = 90.5% (>=75% safe, <95% Attendance Champ locked)
    record_attendance_days(stack.api_client, sarah_h, student_id=stu["id"], present_count=0, absent_count=1, start_date=date(2026, 4, 1))
    ui_login(page, stack.frontend_url, stu["admission_number"], stu["password"], expected_url_part="/student")
    b2 = {
        b["title"]: b["unlocked"]
        for b in stack.api_client.get(
            f"/api/v1/analytics/student-badges/{stu['id']}", params={"session_id": SESSION_ID}, headers=admin_h
        ).json()["badges"]
    }
    assert b2["Attendance Champ"] is False
    goal = stack.api_client.get(
        f"/api/v1/attendance/goal/{stu['id']}", params={"session_id": SESSION_ID}, headers=admin_h
    ).json()
    assert goal["is_warning"] is False


@pytest.mark.browser
def test_T3_15_teacher_lesson_plan_and_student_detail_route_consistent(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    page.get_by_role("button", name=re.compile(r"AI.*Lesson Plan|Remedial.*Plan", re.I)).first.click()
    page.get_by_role("button", name=re.compile(r"Generate", re.I)).first.click()
    expect(page.get_by_text("Monday", exact=False).first).to_be_visible(timeout=10000)
    page.get_by_role("button", name=re.compile(r"Close|Cancel", re.I)).first.click()

    page.goto(f"{frontend_url}/teacher/students/{STUDENT_3_ID}", wait_until="domcontentloaded")
    expect(page.get_by_text("David Miller", exact=False).first).to_be_visible(timeout=10000)


@pytest.mark.browser
def test_T3_16_admin_model_switch_writes_audit_log_and_updates_simulator(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    ui_login(page, stack.frontend_url, *ADMIN_CREDS, expected_url_part="/admin")
    page.goto(f"{stack.frontend_url}/admin/models", wait_until="domcontentloaded")
    expect(page.get_by_text("Random Forest", exact=False).first).to_be_visible(timeout=10000)
    rf_card = page.locator("div").filter(has_text="Random Forest").filter(
        has=page.get_by_role("button", name=re.compile(r"Switch|Activate|Set Active", re.I))
    ).last
    if rf_card.count() > 0:
        btn = rf_card.get_by_role("button", name=re.compile(r"Switch|Activate|Set Active", re.I)).first
        if btn.is_enabled():
            with page.expect_response(lambda r: "/api/v1/ml/switch-model" in r.url and r.status == 200):
                btn.click()

    admin_h = auth_headers_for(stack.api_client, ADMIN_CREDS)
    logs = stack.api_client.get("/api/v1/audit/logs", params={"limit": 50}, headers=admin_h).json()
    assert any("model" in str(l).lower() for l in logs)

    ui_logout(page)
    with page.expect_response(lambda r: "/api/v1/ml/predict-live" in r.url and r.status == 200) as pred:
        ui_login(page, stack.frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    d = pred.value.json()
    assert d["active_prediction"] == d["rf_prediction"]


@pytest.mark.browser
def test_T3_17_student_sidebar_roundtrip_preserves_exams_and_notices(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    page.locator('aside nav a[href="/student/assignments"]').click()
    page.wait_for_url("**/student/assignments**", wait_until="commit", timeout=10000)
    page.locator('aside nav a[href="/student"]').click()
    page.wait_for_url("**/student", wait_until="commit", timeout=10000)
    expect(page.get_by_text("Mid-Term Examination Datesheet Released")).to_be_visible(timeout=10000)
    expect(page.get_by_text("Unit Test 1 - Algebra").first).to_be_visible()


@pytest.mark.browser
def test_T3_18_student_session_switch_updates_notice_board(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    admin_h = auth_headers_for(stack.api_client, ADMIN_CREDS)
    ses = stack.api_client.post(
        "/api/v1/institution/sessions",
        json={"name": "2027-2028", "start_date": "2027-06-01", "end_date": "2028-04-30", "is_active": False},
        headers=admin_h,
    ).json()
    create_announcement(stack.api_client, admin_h, session_id=ses["id"], class_id=None, title="Session 2027 Notice")

    ui_login(page, stack.frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    page.locator("header select").select_option(value=str(ses["id"]))
    expect(page.get_by_text("Session 2027 Notice")).to_be_visible(timeout=10000)


@pytest.mark.browser
def test_T3_19_student_roster_claim_ui_then_login_and_attendance_goal(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    page.goto(f"{stack.frontend_url}/login", wait_until="domcontentloaded")
    page.get_by_role("button", name="Claim Student Roster").click()
    page.get_by_placeholder("e.g. STU1003").fill("STU1003")
    page.get_by_placeholder("Minimum 8 characters").fill("ClaimPass@123")
    with page.expect_response(lambda r: "/api/v1/auth/register-student" in r.url and r.status == 202):
        page.get_by_role("button", name="Claim Student Record").click()

    page.get_by_role("button", name="Sign In", exact=True).click()
    ui_login(page, stack.frontend_url, "STU1003", "ClaimPass@123", expected_url_part="/student")
    expect(page.get_by_text("David Miller").first).to_be_visible(timeout=10000)
    expect(page.get_by_text(re.compile(r"consecutive|needed|must attend", re.I)).first).to_be_visible()


@pytest.mark.browser
def test_T3_20_student_submits_two_doubts_teacher_answers_one_filters_isolate(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
) -> None:
    q_math = f"T320 Math [{unique_tag()}]"
    q_sci = f"T320 Sci [{unique_tag()}]"
    ans_math = f"T320 Math Answer [{unique_tag()}]"

    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    doubt_card = page.locator("section, div").filter(has_text=re.compile(r"Doubt Clearing|Ask a Doubt", re.I)).last
    subj_sel = doubt_card.locator("select").filter(has_text="Mathematics").first

    subj_sel.select_option(label="Mathematics")
    doubt_card.locator("textarea, input[type='text']").first.fill(q_math)
    with page.expect_response(lambda r: "/api/v1/doubts" in r.url and r.request.method == "POST") as r_math:
        doubt_card.get_by_role("button", name=re.compile(r"Submit|Ask|Send", re.I)).first.click()
    math_id = r_math.value.json()["id"]

    subj_sel.select_option(label="Science")
    doubt_card.locator("textarea, input[type='text']").first.fill(q_sci)
    with page.expect_response(lambda r: "/api/v1/doubts" in r.url and r.request.method == "POST"):
        doubt_card.get_by_role("button", name=re.compile(r"Submit|Ask|Send", re.I)).first.click()

    api_client.post(f"/api/v1/doubts/{math_id}/answer", json={"answer": ans_math}, headers=teacher_sarah_headers)
    page.reload(wait_until="domcontentloaded")

    expect(page.get_by_text(ans_math)).to_be_visible(timeout=10000)
    expect(page.get_by_text(q_sci)).to_be_visible()


@pytest.mark.browser
def test_T3_21_what_if_simulator_survives_token_refresh_and_updates(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, watcher = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    sliders = page.locator('input[type="range"]')
    _set_range_slider(sliders.nth(0), 85)

    with watcher.allow_status(401):
        page.evaluate("() => localStorage.setItem('access_token', 'expired.token.value')")
        with page.expect_response(lambda r: "/api/v1/ml/predict-live" in r.url and r.status == 200, timeout=15000) as r_info:
            _set_range_slider(sliders.nth(1), 90)
    assert r_info.value.json()["active_prediction"] >= 0


@pytest.mark.browser
def test_T3_22_admin_switches_model_visits_audit_returns_active_persists(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    ui_login(page, stack.frontend_url, *ADMIN_CREDS, expected_url_part="/admin")
    page.locator('aside nav a[href="/admin/models"]').click()
    page.wait_for_url("**/admin/models**", wait_until="commit", timeout=10000)

    xgb_card = page.locator("div").filter(has_text="XGBoost").filter(
        has=page.get_by_role("button", name=re.compile(r"Switch|Activate|Set Active", re.I))
    ).last
    with page.expect_response(lambda r: "/api/v1/ml/switch-model" in r.url and r.status == 200):
        xgb_card.get_by_role("button", name=re.compile(r"Switch|Activate|Set Active", re.I)).first.click()

    page.locator('aside nav a[href="/admin/audit"]').click()
    page.wait_for_url("**/admin/audit**", wait_until="commit", timeout=10000)
    with page.expect_response(lambda r: "/api/v1/ml/models" in r.url and r.status == 200) as m_resp:
        page.locator('aside nav a[href="/admin/models"]').click()
    active = [m for m in m_resp.value.json() if "regression" in m["task"].lower() and m["is_active"]]
    assert len(active) == 1 and "xgboost" in active[0]["model_name"].lower()
