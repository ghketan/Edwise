from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import re
from typing import Tuple

from playwright.sync_api import Page, expect
import pytest

from helpers.auth import auth_headers_for, ui_login, ui_logout
from helpers.seed_helpers import (
    ADMIN_CREDS,
    CLASS_ID,
    SESSION_ID,
    STUDENT_1_CREDS,
    STUDENT_1_ID,
    STUDENT_2_ID,
    STUDENT_3_ID,
    SUBJECT_MATH_ID,
    SUBJECT_SCI_ID,
    TEACHER_ALAN_CREDS,
    TEACHER_SARAH_CREDS,
    claim_student_account,
    create_announcement,
    create_exam,
    create_fresh_student,
    record_attendance_days,
    unique_tag,
    upload_exam_datesheet,
)
from helpers.servers import IsolatedStack
from helpers.watchers import BrowserErrorWatcher

pytestmark = [pytest.mark.tier4]


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
def test_T4_01_exam_prep_and_student_self_service_day(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    sarah_h = auth_headers_for(stack.api_client, TEACHER_SARAH_CREDS)
    exam = create_exam(
        stack.api_client,
        sarah_h,
        name=f"Term Finals {unique_tag()}",
        exam_date=date.today() + timedelta(days=3),
    )
    pdf_bytes = b"%PDF-1.4 T4_01 Term Finals Schedule\n%%EOF"
    upload_exam_datesheet(stack.api_client, sarah_h, exam["id"], filename="finals_t4.pdf", content=pdf_bytes)
    notice = create_announcement(
        stack.api_client,
        sarah_h,
        class_id=CLASS_ID,
        title=f"Finals Prep Notice {unique_tag()}",
        priority="High",
    )

    ui_login(page, stack.frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    expect(page.get_by_text(exam["name"])).to_be_visible(timeout=10000)
    expect(page.get_by_text("3 Days Left").first).to_be_visible()
    expect(page.get_by_text(notice["title"])).to_be_visible()

    row = page.locator("tr, div, li").filter(has_text=exam["name"]).filter(
        has=page.get_by_role("button", name=re.compile(r"download|datesheet", re.I))
    ).last
    with page.expect_download() as dl_info:
        row.get_by_role("button", name=re.compile(r"download|datesheet", re.I)).first.click()
    assert Path(dl_info.value.path()).read_bytes() == pdf_bytes

    expect(page.get_by_text(re.compile(r"100(\.0)?%")).first).to_be_visible()
    expect(page.get_by_text("Top Performer", exact=False).first).to_be_visible()

    q = f"T401 Science practical doubt [{unique_tag()}]"
    doubt_card = page.locator("section, div").filter(has_text=re.compile(r"Doubt Clearing|Ask a Doubt", re.I)).last
    doubt_card.locator("select").filter(has_text="Science").first.select_option(label="Science")
    doubt_card.locator("textarea, input[type='text']").first.fill(q)
    with page.expect_response(lambda r: "/api/v1/doubts" in r.url and r.request.method == "POST"):
        doubt_card.get_by_role("button", name=re.compile(r"Submit|Ask|Send", re.I)).first.click()
    expect(page.get_by_text(q)).to_be_visible()

    sliders = page.locator('input[type="range"]')
    with page.expect_response(lambda r: "/api/v1/ml/predict-live" in r.url and r.status == 200):
        for i, v in enumerate((50, 50, 50, 65)):
            _set_range_slider(sliders.nth(i), v)
    expect(page.get_by_text("High Risk", exact=False).first).to_be_visible()

    with page.expect_response(lambda r: "/api/v1/ml/predict-live" in r.url and r.status == 200):
        for i, v in enumerate((90, 92, 94, 96)):
            _set_range_slider(sliders.nth(i), v)
    expect(page.get_by_text("Low Risk", exact=False).first).to_be_visible()

    page.locator('aside nav a[href="/student/assignments"]').click()
    page.wait_for_url("**/student/assignments**", wait_until="commit", timeout=10000)
    ui_logout(page)


@pytest.mark.browser
def test_T4_02_teacher_remediation_and_bulk_assessment_workflow(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
    tmp_path: Path,
) -> None:
    stack, page, _ = fresh_isolated_stack
    ui_login(page, stack.frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")

    # 1. AI Remedial Lesson Plan
    page.get_by_role("button", name=re.compile(r"AI.*Lesson Plan|Remedial.*Plan", re.I)).first.click()
    with page.expect_response(lambda r: "/api/v1/analytics/ai-lesson-plan/" in r.url and r.status == 200):
        page.get_by_role("button", name=re.compile(r"Generate", re.I)).first.click()
    expect(page.get_by_text("Monday", exact=False).first).to_be_visible(timeout=10000)
    page.get_by_role("button", name=re.compile(r"Close|Cancel", re.I)).first.click()

    # 2. Notice Board create + delete
    notice_title = f"T402 Notice {unique_tag()}"
    board = page.locator("section, div").filter(has_text=re.compile(r"Notice Board|Announcements", re.I)).last
    board.get_by_placeholder(re.compile(r"title", re.I)).first.fill(notice_title)
    board.locator("textarea").first.fill("T402 remediation notice")
    board.locator("select").filter(has_text=re.compile(r"Normal|High", re.I)).first.select_option("High")
    board.locator("select").filter(has_text=re.compile(r"Grade 10", re.I)).first.select_option(label="Grade 10")
    with page.expect_response(lambda r: "/api/v1/announcements" in r.url and r.status == 200):
        board.get_by_role("button", name=re.compile(r"Post|Create|Publish|Add", re.I)).first.click()
    expect(page.get_by_text(notice_title)).to_be_visible(timeout=10000)

    # 3. Doubt Resolution Hub
    ans_text = f"T402 practical explanation [{unique_tag()}]"
    d_card = page.locator("div, li").filter(has_text="practical assessment").filter(
        has=page.get_by_role("button", name=re.compile(r"Answer|Reply|Resolve|Submit", re.I))
    ).last
    d_card.locator("input, textarea").first.fill(ans_text)
    with page.expect_response(lambda r: "/answer" in r.url and r.status == 200):
        d_card.get_by_role("button", name=re.compile(r"Answer|Reply|Resolve|Submit", re.I)).first.click()

    # 4. Delete temp notice
    n_row = page.locator("div, li, tr").filter(has_text=notice_title).filter(
        has=page.get_by_role("button", name=re.compile(r"Delete|Remove", re.I))
    ).last
    with page.expect_response(lambda r: "/api/v1/announcements/" in r.url and r.request.method == "DELETE"):
        n_row.get_by_role("button", name=re.compile(r"Delete|Remove", re.I)).first.click()

    # 5. Navigate to Marks Entry: bulk CSV + datesheet upload
    page.locator('aside nav a[href="/teacher/marks"]').click()
    page.wait_for_url("**/teacher/marks**", wait_until="commit", timeout=10000)

    csv_path = tmp_path / "t402_marks.csv"
    csv_path.write_text("Admission Number,Exam ID,Score\nSTU1001,1,48\nSTU1002,1,50\n", encoding="utf-8")
    csv_panel = page.locator("section, div").filter(has_text=re.compile(r"Bulk.*CSV|CSV.*Upload", re.I)).last
    csv_panel.locator('input[type="file"]').first.set_input_files(str(csv_path))
    with page.expect_response(lambda r: "/api/v1/marks/upload-csv" in r.url and r.status == 200) as csv_resp:
        csv_panel.get_by_role("button", name=re.compile(r"Upload|Import", re.I)).first.click()
    assert csv_resp.value.json()["imported_count"] == 2

    pdf_path = tmp_path / "t402_ds.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 T4_02 datesheet")
    ds_input = page.locator('input[type="file"][accept*="pdf" i]').first
    with page.expect_response(lambda r: "/datesheet" in r.url and r.status == 200):
        ds_input.set_input_files(str(pdf_path))
        btns = page.get_by_role("button", name=re.compile(r"Upload Datesheet|Attach Datesheet", re.I))
        if btns.count() > 0:
            btns.first.click()

    page.reload(wait_until="domcontentloaded")
    expect(page.get_by_text("t402_ds.pdf", exact=False).first).to_be_visible(timeout=10000)
    ui_logout(page)


@pytest.mark.browser
def test_T4_03_admin_model_eval_and_live_switch_impact_on_student(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    ui_login(page, stack.frontend_url, *ADMIN_CREDS, expected_url_part="/admin")
    page.locator('aside nav a[href="/admin/models"]').click()
    page.wait_for_url("**/admin/models**", wait_until="commit", timeout=10000)

    for label in ("LinearRegression", "Random Forest", "XGBoost"):
        expect(page.get_by_text(label, exact=False).first).to_be_visible(timeout=10000)

    xgb_card = page.locator("div").filter(has_text="XGBoost").filter(
        has=page.get_by_role("button", name=re.compile(r"Switch|Activate|Set Active", re.I))
    ).last
    with page.expect_response(lambda r: "/api/v1/ml/switch-model" in r.url and r.status == 200):
        xgb_card.get_by_role("button", name=re.compile(r"Switch|Activate|Set Active", re.I)).first.click()
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass
    page.reload(wait_until="domcontentloaded")

    ui_logout(page)
    with page.expect_response(lambda r: "/api/v1/ml/predict-live" in r.url and r.status == 200) as p_xgb:
        ui_login(page, stack.frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    assert p_xgb.value.json()["active_prediction"] == p_xgb.value.json()["xgb_prediction"]

    ui_logout(page)
    ui_login(page, stack.frontend_url, *ADMIN_CREDS, expected_url_part="/admin")
    page.goto(f"{stack.frontend_url}/admin/models", wait_until="domcontentloaded")
    expect(page.get_by_text("XGBoost", exact=False).first).to_be_visible(timeout=10000)
    lin_card = page.locator("div").filter(has_text=re.compile(r"LinearRegression|Linear Regression")).filter(
        has=page.get_by_role("button", name=re.compile(r"Switch|Activate|Set Active", re.I))
    ).last
    with page.expect_response(lambda r: "/api/v1/ml/switch-model" in r.url and r.status == 200):
        lin_card.get_by_role("button", name=re.compile(r"Switch|Activate|Set Active", re.I)).first.click()
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass

    ui_logout(page)
    ui_login(page, stack.frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    sliders = page.locator('input[type="range"]')
    with page.expect_response(lambda r: "/api/v1/ml/predict-live" in r.url and r.status == 200) as p_lin:
        _set_range_slider(sliders.nth(0), 77)
    assert p_lin.value.json()["active_prediction"] == p_lin.value.json()["linear_prediction"]


@pytest.mark.api
@pytest.mark.browser
def test_T4_04_role_based_security_and_boundary_stress_journey(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    c = stack.api_client

    # 1. Unauthenticated API & UI
    assert c.get("/api/v1/doubts", params={"session_id": SESSION_ID}).status_code == 401
    assert c.get("/api/v1/ml/models").status_code == 401
    page.goto(f"{stack.frontend_url}/admin/models", wait_until="domcontentloaded")
    expect(page).to_have_url(re.compile(r"/login"), timeout=10000)
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass

    # 2. Student RBAC API & UI
    stu_h = auth_headers_for(c, STUDENT_1_CREDS)
    assert c.post("/api/v1/announcements", json={"session_id": 1, "title": "x", "content": "y"}, headers=stu_h).status_code == 403
    assert c.post("/api/v1/doubts/2/answer", json={"answer": "x"}, headers=stu_h).status_code == 403
    assert c.get("/api/v1/analytics/ai-lesson-plan/1", params={"session_id": 1}, headers=stu_h).status_code == 403
    assert c.get("/api/v1/ml/models", headers=stu_h).status_code == 403
    assert c.post("/api/v1/ml/switch-model", json={"model_name": "xgboost"}, headers=stu_h).status_code == 403

    # 3. Cross-student scoping
    assert c.get(f"/api/v1/attendance/goal/{STUDENT_2_ID}", params={"session_id": 1}, headers=stu_h).status_code == 404
    assert c.get(f"/api/v1/analytics/student-badges/{STUDENT_2_ID}", params={"session_id": 1}, headers=stu_h).status_code == 404

    # 4. Cross-teacher scoping
    alan_h = auth_headers_for(c, TEACHER_ALAN_CREDS)
    sarah_h = auth_headers_for(c, TEACHER_SARAH_CREDS)
    sarah_ann = create_announcement(c, sarah_h, title="T404 Sarah Notice")
    assert c.delete(f"/api/v1/announcements/{sarah_ann['id']}", headers=alan_h).status_code in (403, 422)
    assert c.post("/api/v1/exams/1/datesheet", files={"file": ("x.pdf", b"%PDF", "application/pdf")}, headers=alan_h).status_code in (403, 404)

    # 5. Boundary payloads
    admin_h = auth_headers_for(c, ADMIN_CREDS)
    assert c.get(f"/api/v1/attendance/goal/{STUDENT_3_ID}", params={"session_id": 1, "target_pct": 100.0}, headers=admin_h).status_code == 200
    assert c.post("/api/v1/ml/switch-model", json={"model_name": "gpt4"}, headers=admin_h).status_code in (404, 422)
    assert c.post(
        "/api/v1/marks/upload-csv",
        data={"session_id": "1"},
        files={"file": ("oob.csv", b"Admission Number,Exam ID,Score\nSTU1001,1,999\n", "text/csv")},
        headers=sarah_h,
    ).status_code in (400, 422)

    ui_login(page, stack.frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    page.goto(f"{stack.frontend_url}/teacher", wait_until="domcontentloaded")
    expect(page).to_have_url(re.compile(r"/student"), timeout=10000)
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass


@pytest.mark.browser
def test_T4_05_multi_student_badge_and_attendance_recovery_lifecycle(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    claim_student_account(stack.api_client, "STU1003", class_id=CLASS_ID, password="Student@123")
    ui_login(page, stack.frontend_url, "STU1003", "Student@123", expected_url_part="/student")
    expect(page.get_by_text(re.compile(r"consecutive|needed|must attend", re.I)).first).to_be_visible(timeout=10000)

    sarah_h = auth_headers_for(stack.api_client, TEACHER_SARAH_CREDS)
    # STU1003 starts 6/14 -> add 150 present days -> 156/164 = 95.1%
    record_attendance_days(
        stack.api_client, sarah_h, student_id=STUDENT_3_ID, present_count=150, absent_count=0, start_date=date(2026, 1, 1)
    )
    csv_bytes = b"Admission Number,Exam ID,Score\nSTU1003,1,50\nSTU1003,2,99\n"
    up = stack.api_client.post(
        "/api/v1/marks/upload-csv",
        data={"session_id": str(SESSION_ID), "reason": "Recovery"},
        files={"file": ("rec.csv", csv_bytes, "text/csv")},
        headers=sarah_h,
    )
    assert up.status_code == 200

    with page.expect_response(lambda r: f"/api/v1/analytics/student-badges/{STUDENT_3_ID}" in r.url and r.status == 200) as b_resp:
        page.reload(wait_until="domcontentloaded")
    badges = {b["title"]: b["unlocked"] for b in b_resp.value.json()["badges"]}
    assert badges["Attendance Champ"] is True
    assert badges["Subject Ace"] is True


@pytest.mark.browser
def test_T4_06_admin_model_switcher_resilience_and_governance_audit_journey(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    ui_login(page, stack.frontend_url, *ADMIN_CREDS, expected_url_part="/admin")
    page.goto(f"{stack.frontend_url}/admin/models", wait_until="domcontentloaded")
    expect(page.get_by_text("XGBoost", exact=False).first).to_be_visible(timeout=10000)

    for target in (r"LinearRegression|Linear Regression", r"Random Forest", r"XGBoost"):
        card = page.locator("div").filter(has_text=re.compile(target)).filter(
            has=page.get_by_role("button", name=re.compile(r"Switch|Activate|Set Active", re.I))
        ).last
        if card.count() > 0:
            btn = card.get_by_role("button", name=re.compile(r"Switch|Activate|Set Active", re.I)).first
            if btn.is_enabled():
                with page.expect_response(lambda r: "/api/v1/ml/switch-model" in r.url and r.status == 200):
                    btn.click()

    page.locator('aside nav a[href="/admin/audit"]').click()
    page.wait_for_url("**/admin/audit**", wait_until="commit", timeout=10000)
    page.locator('aside nav a[href="/admin/models"]').click()
    page.wait_for_url("**/admin/models**", wait_until="commit", timeout=10000)
    ui_logout(page)


@pytest.mark.browser
def test_T4_07_urgent_exam_reschedule_and_same_day_datesheet_broadcast(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
    tmp_path: Path,
) -> None:
    stack, page, _ = fresh_isolated_stack
    sarah_h = auth_headers_for(stack.api_client, TEACHER_SARAH_CREDS)
    exam = create_exam(stack.api_client, sarah_h, name="Pop Quiz - Algebra", exam_date=date.today())
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
    png_path = tmp_path / "pop_quiz.png"
    png_path.write_bytes(png_bytes)

    ui_login(page, stack.frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    board = page.locator("section, div").filter(has_text=re.compile(r"Notice Board|Announcements", re.I)).last
    board.get_by_placeholder(re.compile(r"title", re.I)).first.fill("Today's Exam Room Change")
    board.locator("textarea").first.fill("Room changed to Hall B.")
    board.locator("select").filter(has_text=re.compile(r"Normal|High", re.I)).first.select_option("High")
    board.locator("select").filter(has_text=re.compile(r"Grade 10", re.I)).first.select_option(label="Grade 10")
    with page.expect_response(lambda r: "/api/v1/announcements" in r.url and r.status == 200):
        board.get_by_role("button", name=re.compile(r"Post|Create|Publish|Add", re.I)).first.click()

    page.goto(f"{stack.frontend_url}/teacher/marks", wait_until="domcontentloaded")
    page.locator("select").filter(has_text=exam["name"]).first.select_option(value=str(exam["id"]))
    ds_input = page.locator('input[type="file"][accept*="pdf" i]').first
    with page.expect_response(lambda r: f"/api/v1/exams/{exam['id']}/datesheet" in r.url and r.status == 200):
        ds_input.set_input_files(str(png_path))
        btns = page.get_by_role("button", name=re.compile(r"Upload Datesheet|Attach Datesheet", re.I))
        if btns.count() > 0:
            btns.first.click()

    ui_logout(page)
    ui_login(page, stack.frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    expect(page.get_by_text("Pop Quiz - Algebra")).to_be_visible(timeout=10000)
    expect(page.get_by_text("Today!").first).to_be_visible()
    expect(page.get_by_text("Today's Exam Room Change")).to_be_visible()

    row = page.locator("tr, div, li").filter(has_text="Pop Quiz - Algebra").filter(
        has=page.get_by_role("button", name=re.compile(r"download|datesheet", re.I))
    ).last
    with page.expect_download() as dl_info:
        row.get_by_role("button", name=re.compile(r"download|datesheet", re.I)).first.click()
    assert Path(dl_info.value.path()).read_bytes() == png_bytes


@pytest.mark.browser
def test_T4_08_multi_subject_doubt_triage_and_announcement_cleanup(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    q_math = f"T408 Math doubt [{unique_tag()}]"
    q_sci = f"T408 Sci doubt [{unique_tag()}]"

    ui_login(page, stack.frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    doubt_card = page.locator("section, div").filter(has_text=re.compile(r"Doubt Clearing|Ask a Doubt", re.I)).last
    subj_sel = doubt_card.locator("select").filter(has_text="Mathematics").first
    subj_sel.select_option(label="Mathematics")
    doubt_card.locator("textarea, input[type='text']").first.fill(q_math)
    with page.expect_response(lambda r: "/api/v1/doubts" in r.url and r.request.method == "POST"):
        doubt_card.get_by_role("button", name=re.compile(r"Submit|Ask|Send", re.I)).first.click()

    subj_sel.select_option(label="Science")
    doubt_card.locator("textarea, input[type='text']").first.fill(q_sci)
    with page.expect_response(lambda r: "/api/v1/doubts" in r.url and r.request.method == "POST"):
        doubt_card.get_by_role("button", name=re.compile(r"Submit|Ask|Send", re.I)).first.click()

    ui_logout(page)
    ui_login(page, stack.frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    m_card = page.locator("div, li").filter(has_text=q_math).filter(
        has=page.get_by_role("button", name=re.compile(r"Answer|Reply|Resolve|Submit", re.I))
    ).last
    m_card.locator("input, textarea").first.fill("Sarah Math Reply")
    with page.expect_response(lambda r: "/answer" in r.url and r.status == 200):
        m_card.get_by_role("button", name=re.compile(r"Answer|Reply|Resolve|Submit", re.I)).first.click()

    board = page.locator("section, div").filter(has_text=re.compile(r"Notice Board|Announcements", re.I)).last
    temp_notice = f"T408 Temp Notice {unique_tag()}"
    board.get_by_placeholder(re.compile(r"title", re.I)).first.fill(temp_notice)
    board.locator("textarea").first.fill("Temporary")
    with page.expect_response(lambda r: "/api/v1/announcements" in r.url and r.status == 200):
        board.get_by_role("button", name=re.compile(r"Post|Create|Publish|Add", re.I)).first.click()
    n_row = page.locator("div, li, tr").filter(has_text=temp_notice).filter(
        has=page.get_by_role("button", name=re.compile(r"Delete|Remove", re.I))
    ).last
    with page.expect_response(lambda r: "/api/v1/announcements/" in r.url and r.request.method == "DELETE"):
        n_row.get_by_role("button", name=re.compile(r"Delete|Remove", re.I)).first.click()

    ui_logout(page)
    ui_login(page, stack.frontend_url, *TEACHER_ALAN_CREDS, expected_url_part="/teacher")
    s_card = page.locator("div, li").filter(has_text=q_sci).filter(
        has=page.get_by_role("button", name=re.compile(r"Answer|Reply|Resolve|Submit", re.I))
    ).last
    s_card.locator("input, textarea").first.fill("Alan Science Reply")
    with page.expect_response(lambda r: "/answer" in r.url and r.status == 200):
        s_card.get_by_role("button", name=re.compile(r"Answer|Reply|Resolve|Submit", re.I)).first.click()

    ui_logout(page)
    ui_login(page, stack.frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    expect(page.get_by_text("Sarah Math Reply")).to_be_visible(timeout=10000)
    expect(page.get_by_text("Alan Science Reply")).to_be_visible()
    expect(page.get_by_text(temp_notice)).not_to_be_visible()


@pytest.mark.browser
def test_T4_09_remediation_feedback_loop_csv_to_lesson_plan_to_retest(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
    tmp_path: Path,
) -> None:
    stack, page, _ = fresh_isolated_stack
    alan_h = auth_headers_for(stack.api_client, TEACHER_ALAN_CREDS)
    sci_exam = create_exam(stack.api_client, alan_h, subject_id=SUBJECT_SCI_ID, name="Sci Remediation Test", max_marks=100.0)

    low_csv = tmp_path / "low_sci.csv"
    low_csv.write_text(f"Admission Number,Exam ID,Score\nSTU1001,{sci_exam['id']},30\nSTU1002,{sci_exam['id']},30\n", encoding="utf-8")

    ui_login(page, stack.frontend_url, *TEACHER_ALAN_CREDS, expected_url_part="/teacher")
    page.goto(f"{stack.frontend_url}/teacher/marks", wait_until="domcontentloaded")
    csv_panel = page.locator("section, div").filter(has_text=re.compile(r"Bulk.*CSV|CSV.*Upload", re.I)).last
    csv_panel.locator('input[type="file"]').first.set_input_files(str(low_csv))
    with page.expect_response(lambda r: "/api/v1/marks/upload-csv" in r.url and r.status == 200):
        csv_panel.get_by_role("button", name=re.compile(r"Upload|Import", re.I)).first.click()

    page.goto(f"{stack.frontend_url}/teacher", wait_until="domcontentloaded")
    page.get_by_role("button", name=re.compile(r"AI.*Lesson Plan|Remedial.*Plan", re.I)).first.click()
    with page.expect_response(lambda r: "/api/v1/analytics/ai-lesson-plan/" in r.url and r.status == 200) as p1:
        page.get_by_role("button", name=re.compile(r"Generate", re.I)).first.click()
    p1_data = p1.value.json()
    assert p1_data["focus_subject"] == "Science"
    assert p1_data["performance_status"] == "Challenging"
    page.get_by_role("button", name=re.compile(r"Close|Cancel", re.I)).first.click()

    high_csv = tmp_path / "high_sci.csv"
    high_csv.write_text(f"Admission Number,Exam ID,Score\nSTU1001,{sci_exam['id']},92\nSTU1002,{sci_exam['id']},94\n", encoding="utf-8")
    page.goto(f"{stack.frontend_url}/teacher/marks", wait_until="domcontentloaded")
    csv_panel = page.locator("section, div").filter(has_text=re.compile(r"Bulk.*CSV|CSV.*Upload", re.I)).last
    csv_panel.locator('input[type="file"]').first.set_input_files(str(high_csv))
    with page.expect_response(lambda r: "/api/v1/marks/upload-csv" in r.url and r.status == 200):
        csv_panel.get_by_role("button", name=re.compile(r"Upload|Import", re.I)).first.click()

    page.goto(f"{stack.frontend_url}/teacher", wait_until="domcontentloaded")
    page.get_by_role("button", name=re.compile(r"AI.*Lesson Plan|Remedial.*Plan", re.I)).first.click()
    with page.expect_response(lambda r: "/api/v1/analytics/ai-lesson-plan/" in r.url and r.status == 200) as p2:
        page.get_by_role("button", name=re.compile(r"Generate", re.I)).first.click()
    assert p2.value.json()["avg_score"] > p1_data["avg_score"]


@pytest.mark.browser
def test_T4_10_token_refresh_and_session_continuity_across_study_session(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, watcher = fresh_isolated_stack
    ui_login(page, stack.frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    with watcher.allow_status(401):
        page.evaluate("() => localStorage.setItem('access_token', 'stale.expired.jwt')")
        page.locator('aside nav a[href="/student/assignments"]').click()
        page.wait_for_url("**/student/assignments**", wait_until="commit", timeout=10000)
        page.locator('aside nav a[href="/student"]').click()
        page.wait_for_url("**/student", wait_until="commit", timeout=10000)

    q = f"T410 post-refresh doubt [{unique_tag()}]"
    doubt_card = page.locator("section, div").filter(has_text=re.compile(r"Doubt Clearing|Ask a Doubt", re.I)).last
    doubt_card.locator("textarea, input[type='text']").first.fill(q)
    with page.expect_response(lambda r: "/api/v1/doubts" in r.url and r.request.method == "POST"):
        doubt_card.get_by_role("button", name=re.compile(r"Submit|Ask|Send", re.I)).first.click()
    expect(page.get_by_text(q)).to_be_visible(timeout=10000)


@pytest.mark.browser
def test_T4_11_newly_enrolled_zero_history_student_onboarding(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    admin_h = auth_headers_for(stack.api_client, ADMIN_CREDS)
    stu = create_fresh_student(stack.api_client, admin_h, claim=False)

    page.goto(f"{stack.frontend_url}/login", wait_until="domcontentloaded")
    page.get_by_role("button", name="Claim Student Roster").click()
    page.get_by_placeholder("e.g. STU1003").fill(stu["admission_number"])
    page.get_by_placeholder("Minimum 8 characters").fill("NewStudent@123")
    with page.expect_response(lambda r: "/api/v1/auth/register-student" in r.url and r.status == 202):
        page.get_by_role("button", name="Claim Student Record").click()

    page.get_by_role("button", name="Sign In", exact=True).click()
    ui_login(page, stack.frontend_url, stu["admission_number"], "NewStudent@123", expected_url_part="/student")

    assert "nan" not in page.locator("main").inner_text().lower()
    assert "infinity" not in page.locator("main").inner_text().lower()

    stu_h = auth_headers_for(stack.api_client, (stu["admission_number"], "NewStudent@123"))
    g75 = stack.api_client.get(f"/api/v1/attendance/goal/{stu['id']}", params={"session_id": SESSION_ID, "target_pct": 75.0}, headers=stu_h)
    g100 = stack.api_client.get(f"/api/v1/attendance/goal/{stu['id']}", params={"session_id": SESSION_ID, "target_pct": 100.0}, headers=stu_h)
    assert g75.status_code == 200 and g100.status_code == 200
    b = stack.api_client.get(f"/api/v1/analytics/student-badges/{stu['id']}", params={"session_id": SESSION_ID}, headers=stu_h).json()
    by_title = {x["title"]: x["unlocked"] for x in b["badges"]}
    assert by_title["Top Performer"] is False and by_title["All-Rounder"] is False
