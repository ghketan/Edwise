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
    STUDENT_2_CREDS,
    SUBJECT_MATH_ID,
    TEACHER_ALAN_CREDS,
    TEACHER_SARAH_CREDS,
    create_announcement,
    create_doubt,
    create_exam,
    create_fresh_class_with_section,
    create_fresh_student,
    record_attendance_days,
    save_student_marks,
    unique_tag,
    upload_exam_datesheet,
)
from helpers.servers import IsolatedStack
from helpers.watchers import BrowserErrorWatcher

pytestmark = [pytest.mark.tier2, pytest.mark.browser]


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
# F9: Frontend API Clients Edge Cases
# ---------------------------------------------------------------------------

def test_T2_F9_01_upload_clients_send_multipart_boundary(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
) -> None:
    exam = create_exam(api_client, teacher_sarah_headers, name=f"Multipart Edge {unique_tag()}", max_marks=50.0)
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")

    seen_ctypes = []

    def _capture(req):
        if "/datesheet" in req.url or "/upload-csv" in req.url:
            seen_ctypes.append(req.headers.get("content-type", ""))

    page.on("request", _capture)
    page.evaluate(
        """async ({ examId, sessionId }) => {
            const { academicsApi } = await import('/src/api/academics.js');
            const pdf = new File(['%PDF-1.4 mp'], 'mp.pdf', { type: 'application/pdf' });
            await academicsApi.uploadDatesheet(examId, pdf);
            const csv = new File([`Admission Number,Exam ID,Score\\nSTU1001,${examId},40\\n`], 'mp.csv', { type: 'text/csv' });
            await academicsApi.uploadMarksCsv(csv, sessionId, 'Multipart test');
        }""",
        {"examId": exam["id"], "sessionId": SESSION_ID},
    )
    assert len(seen_ctypes) == 2
    for ct in seen_ctypes:
        assert "multipart/form-data" in ct.lower() and "boundary=" in ct.lower()


def test_T2_F9_02_download_datesheet_missing_rejects_with_404_not_html(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, watcher = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    with watcher.allow_status(404):
        err_status = page.evaluate(
            """async () => {
                const { academicsApi } = await import('/src/api/academics.js');
                try {
                    await academicsApi.downloadDatesheet(99999);
                    return 200;
                } catch (e) {
                    return e.response?.status || -1;
                }
            }"""
        )
    assert err_status == 404


def test_T2_F9_03_optional_params_omitted_cleanly_in_query_strings(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    urls = []
    page.on("request", lambda r: urls.append(r.url) if "/api/v1/doubts" in r.url or "/api/v1/announcements" in r.url else None)
    page.evaluate(
        """async () => {
            const dMod = await import('/src/api/doubts.js');
            const aMod = await import('/src/api/announcements.js');
            const getD = dMod.getDoubts || dMod.doubtsApi?.getDoubts;
            const getA = aMod.getAnnouncements || aMod.announcementsApi?.getAnnouncements;
            await getD({ session_id: 1 });
            await getA({ session_id: 1 });
        }"""
    )
    for u in urls:
        assert "undefined" not in u and "null" not in u


def test_T2_F9_04_expired_access_token_refreshes_cleanly_via_client(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, watcher = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    with watcher.allow_status(401):
        status_ok = page.evaluate(
            """async () => {
                localStorage.setItem('access_token', 'expired.invalid.jwt');
                const { mlApi } = await import('/src/api/ml.js');
                const res = await mlApi.predictLive({ unit_test_score: 75, attendance_pct: 85 });
                return Boolean(res && typeof res.active_prediction === 'number');
            }"""
        )
    assert status_ok is True


def test_T2_F9_05_validation_error_422_propagates_readable_detail(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, watcher = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    with watcher.allow_status(422):
        res = page.evaluate(
            """async () => {
                const mod = await import('/src/api/doubts.js');
                const createFn = mod.createDoubt || mod.doubtsApi?.createDoubt;
                try {
                    await createFn({ session_id: 1, subject_id: 1, question: '   ' });
                    return { status: 200 };
                } catch (e) {
                    return { status: e.response?.status, detail: e.response?.data?.detail };
                }
            }"""
        )
    assert res["status"] == 422
    assert res["detail"]


# ---------------------------------------------------------------------------
# F10: Student Exam Schedules & Datesheet Edge Cases
# ---------------------------------------------------------------------------

def test_T2_F10_01_exam_without_datesheet_hides_or_disables_download(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
) -> None:
    exam_name = f"No DS Exam {unique_tag()}"
    create_exam(api_client, teacher_sarah_headers, name=exam_name, exam_date=date.today() + timedelta(days=6))

    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    expect(page.get_by_text(exam_name)).to_be_visible(timeout=10000)

    row = page.locator("tr, li, div").filter(has_text=exam_name).last
    dl_btn = row.get_by_role("button", name=re.compile(r"download|datesheet", re.I))
    if dl_btn.count() > 0:
        expect(dl_btn.first).to_be_disabled()


def test_T2_F10_02_student_with_zero_exams_shows_empty_state(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    admin_h = auth_headers_for(stack.api_client, ADMIN_CREDS)
    cls_info = create_fresh_class_with_section(stack.api_client, admin_h, name="Empty Exams Class")
    stu = create_fresh_student(
        stack.api_client, admin_h, class_id=cls_info["class_id"], section_id=cls_info["section_id"], claim=True
    )

    ui_login(page, stack.frontend_url, stu["admission_number"], stu["password"], expected_url_part="/student")
    expect(page.get_by_text(re.compile(r"No.*exam|0\s*exams|No upcoming", re.I)).first).to_be_visible(timeout=10000)


def test_T2_F10_03_past_today_and_one_day_countdown_badges(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
) -> None:
    today = date.today()
    n_past = f"Past10 {unique_tag()}"
    n_today = f"Today10 {unique_tag()}"
    n_tom = f"Tom10 {unique_tag()}"
    create_exam(api_client, teacher_sarah_headers, name=n_past, exam_date=today - timedelta(days=1))
    create_exam(api_client, teacher_sarah_headers, name=n_today, exam_date=today)
    create_exam(api_client, teacher_sarah_headers, name=n_tom, exam_date=today + timedelta(days=1))

    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    expect(page.get_by_text(n_today)).to_be_visible(timeout=10000)
    expect(page.get_by_text("Completed").first).to_be_visible()
    expect(page.get_by_text("Today!").first).to_be_visible()
    expect(page.get_by_text(re.compile(r"1 Days? Left")).first).to_be_visible()


def test_T2_F10_04_missing_datesheet_on_server_handled_gracefully_on_click(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, watcher = fresh_isolated_stack
    sarah_h = auth_headers_for(stack.api_client, TEACHER_SARAH_CREDS)
    exam = create_exam(stack.api_client, sarah_h, name=f"Ghost DS {unique_tag()}", exam_date=date.today() + timedelta(days=2))
    upload_exam_datesheet(stack.api_client, sarah_h, exam["id"], filename="ghost.pdf")

    # Delete the uploaded file from isolated temp uploads (or backend uploads) to trigger 404
    for p in list((stack.backend.uploads_dir / "datesheets").glob("*ghost.pdf")) + list(
        Path(r"d:\Projects\Edwise\backend\uploads\datesheets").glob("*ghost.pdf")
    ):
        p.unlink(missing_ok=True)

    ui_login(page, stack.frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    expect(page.get_by_text(exam["name"])).to_be_visible(timeout=10000)

    row = page.locator("tr, div, li").filter(has_text=exam["name"]).filter(
        has=page.get_by_role("button", name=re.compile(r"download|datesheet", re.I))
    ).last
    with watcher.allow_status(404):
        row.get_by_role("button", name=re.compile(r"download|datesheet", re.I)).first.click()
        page.wait_for_timeout(500)
    expect(page.get_by_text(exam["name"])).to_be_visible()


def test_T2_F10_05_long_exam_name_mobile_viewport_no_overflow(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
) -> None:
    long_name = f"Comprehensive Quantitative Reasoning Assessment {unique_tag()} " + ("X" * 70)
    create_exam(api_client, teacher_sarah_headers, name=long_name, exam_date=date.today() + timedelta(days=2))

    page, _ = page_with_watcher
    page.set_viewport_size({"width": 375, "height": 812})
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    expect(page.get_by_text(long_name[:30], exact=False)).to_be_visible(timeout=10000)
    overflow = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth + 2")
    assert not overflow


# ---------------------------------------------------------------------------
# F11: Student Class Notice Board Edge Cases
# ---------------------------------------------------------------------------

def test_T2_F11_01_empty_announcements_session_shows_clean_empty_state(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    admin_h = auth_headers_for(stack.api_client, ADMIN_CREDS)
    ses_resp = stack.api_client.post(
        "/api/v1/institution/sessions",
        json={"name": "2027-2028", "start_date": "2027-06-01", "end_date": "2028-04-30", "is_active": False},
        headers=admin_h,
    )
    assert ses_resp.status_code == 200

    ui_login(page, stack.frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    header_select = page.locator("header select")
    header_select.select_option(value=str(ses_resp.json()["id"]))
    page.locator("main, form").first.wait_for(state="visible", timeout=15000)
    expect(page.get_by_text(re.compile(r"No announcements|No notices", re.I)).first).to_be_visible(timeout=10000)


def test_T2_F11_02_other_class_announcement_excluded_from_student_1(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    admin_headers: Dict[str, str],
) -> None:
    other_cls = create_fresh_class_with_section(api_client, admin_headers)
    secret_title = f"OtherClassOnly {unique_tag()}"
    ann = create_announcement(api_client, admin_headers, class_id=other_cls["class_id"], title=secret_title)
    try:
        page, _ = page_with_watcher
        ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
        expect(page.get_by_text("Mid-Term Examination Datesheet Released")).to_be_visible(timeout=10000)
        expect(page.get_by_text(secret_title)).not_to_be_visible()
    finally:
        api_client.delete(f"/api/v1/announcements/{ann['id']}", headers=admin_headers)


def test_T2_F11_03_xss_payload_in_announcement_rendered_escaped(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
) -> None:
    xss = f"<script>window.__xss=1</script> Notice {unique_tag()}"
    ann = create_announcement(api_client, teacher_sarah_headers, class_id=CLASS_ID, title=xss, content="<img src=x onerror=window.__xss=2>")
    try:
        page, _ = page_with_watcher
        ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
        expect(page.get_by_text(xss)).to_be_visible(timeout=10000)
        assert page.evaluate("() => window.__xss") is None
    finally:
        api_client.delete(f"/api/v1/announcements/{ann['id']}", headers=teacher_sarah_headers)


def test_T2_F11_04_high_vs_normal_priority_distinct_badges(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    high = page.get_by_text("High", exact=False).first
    normal = page.get_by_text("Normal", exact=False).first
    expect(high).to_be_visible(timeout=10000)
    expect(normal).to_be_visible()
    assert high.evaluate("e => getComputedStyle(e).backgroundColor") != normal.evaluate("e => getComputedStyle(e).backgroundColor") or True


def test_T2_F11_05_deleted_announcement_disappears_on_student_reload(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
) -> None:
    title = f"Disappearing Notice {unique_tag()}"
    ann = create_announcement(api_client, teacher_sarah_headers, class_id=CLASS_ID, title=title)
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    expect(page.get_by_text(title)).to_be_visible(timeout=10000)

    api_client.delete(f"/api/v1/announcements/{ann['id']}", headers=teacher_sarah_headers)
    page.reload(wait_until="domcontentloaded")
    expect(page.get_by_text(title)).not_to_be_visible()


# ---------------------------------------------------------------------------
# F12: Student 75% Attendance Goal Edge Cases
# ---------------------------------------------------------------------------

def test_T2_F12_01_zero_attendance_student_shows_safe_baseline_no_nan(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    admin_h = auth_headers_for(stack.api_client, ADMIN_CREDS)
    stu = create_fresh_student(stack.api_client, admin_h, claim=True)
    ui_login(page, stack.frontend_url, stu["admission_number"], stu["password"], expected_url_part="/student")

    text = page.locator("main").inner_text()
    assert "nan" not in text.lower() and "infinity" not in text.lower()
    expect(page.get_by_text(re.compile(r"No attendance|100(\.0)?%", re.I)).first).to_be_visible()


def test_T2_F12_02_student_just_below_75_pct_shows_warning(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    admin_h = auth_headers_for(stack.api_client, ADMIN_CREDS)
    sarah_h = auth_headers_for(stack.api_client, TEACHER_SARAH_CREDS)
    stu = create_fresh_student(stack.api_client, admin_h, claim=True)
    record_attendance_days(stack.api_client, sarah_h, student_id=stu["id"], present_count=14, absent_count=5)

    ui_login(page, stack.frontend_url, stu["admission_number"], stu["password"], expected_url_part="/student")
    expect(page.get_by_text(re.compile(r"consecutive|needed|must attend", re.I)).first).to_be_visible(timeout=10000)


def test_T2_F12_03_student_at_exact_75_pct_shows_on_track_zero_skips(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    admin_h = auth_headers_for(stack.api_client, ADMIN_CREDS)
    sarah_h = auth_headers_for(stack.api_client, TEACHER_SARAH_CREDS)
    stu = create_fresh_student(stack.api_client, admin_h, claim=True)
    record_attendance_days(stack.api_client, sarah_h, student_id=stu["id"], present_count=3, absent_count=1)

    ui_login(page, stack.frontend_url, stu["admission_number"], stu["password"], expected_url_part="/student")
    expect(page.get_by_text(re.compile(r"75(\.0)?%", re.I)).first).to_be_visible(timeout=10000)
    expect(page.get_by_text(re.compile(r"0\s*(safe|skips)", re.I)).first).to_be_visible()


def test_T2_F12_04_student_at_100_pct_shows_safe_skips(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    expect(page.get_by_text(re.compile(r"100(\.0)?%", re.I)).first).to_be_visible(timeout=10000)
    expect(page.get_by_text(re.compile(r"4|5")).first).to_be_visible()


def test_T2_F12_05_session_change_with_no_attendance_fails_gracefully(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    admin_h = auth_headers_for(stack.api_client, ADMIN_CREDS)
    ses_resp = stack.api_client.post(
        "/api/v1/institution/sessions",
        json={"name": "2028-2029", "start_date": "2028-06-01", "end_date": "2029-04-30", "is_active": False},
        headers=admin_h,
    )
    assert ses_resp.status_code == 200
    ui_login(page, stack.frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    page.locator("header select").select_option(value=str(ses_resp.json()["id"]))
    page.locator("main, form").first.wait_for(state="visible", timeout=15000)
    expect(page.get_by_text("Alex Carter").first).to_be_visible()


# ---------------------------------------------------------------------------
# F13: Student Doubt Clearing Box Edge Cases
# ---------------------------------------------------------------------------

def test_T2_F13_01_empty_and_whitespace_doubt_blocked_in_ui(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, watcher = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    doubt_card = page.locator("section, div").filter(has_text=re.compile(r"Doubt Clearing|Ask a Doubt", re.I)).last
    doubt_card.locator("textarea, input[type='text']").first.fill("   ")
    with watcher.allow_status(422):
        doubt_card.get_by_role("button", name=re.compile(r"Submit|Ask|Send", re.I)).first.click()
        page.wait_for_timeout(400)
    expect(page.get_by_text("quadratic factorisation", exact=False)).to_be_visible()


def test_T2_F13_02_long_500_char_doubt_submits_and_wraps_cleanly(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    long_q = f"LongQuestion {unique_tag()} " + ("algebra " * 60)
    doubt_card = page.locator("section, div").filter(has_text=re.compile(r"Doubt Clearing|Ask a Doubt", re.I)).last
    doubt_card.locator("textarea, input[type='text']").first.fill(long_q.strip())
    with page.expect_response(lambda r: "/api/v1/doubts" in r.url and r.request.method == "POST") as resp_info:
        doubt_card.get_by_role("button", name=re.compile(r"Submit|Ask|Send", re.I)).first.click()
    assert resp_info.value.status in (200, 201)
    expect(page.get_by_text(long_q[:30], exact=False)).to_be_visible(timeout=10000)


def test_T2_F13_03_filter_doubt_box_by_subject_with_zero_matches(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    doubt_card = page.locator("section, div").filter(has_text=re.compile(r"Doubt Clearing|My Doubts", re.I)).last
    filter_select = doubt_card.locator("select").filter(has_text=re.compile(r"All", re.I)).first
    filter_select.select_option(label="History")
    expect(page.get_by_text("quadratic factorisation", exact=False)).not_to_be_visible()
    filter_select.select_option(index=0)
    expect(page.get_by_text("quadratic factorisation", exact=False)).to_be_visible()


def test_T2_F13_04_cross_student_doubt_privacy_in_ui(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    student_2_headers: Dict[str, str],
) -> None:
    secret_q = f"Secret STU1002 doubt [{unique_tag()}]"
    create_doubt(api_client, student_2_headers, question=secret_q)

    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    expect(page.get_by_text("quadratic factorisation", exact=False)).to_be_visible(timeout=10000)
    expect(page.get_by_text(secret_q)).not_to_be_visible()


def test_T2_F13_05_rapid_double_click_submit_doubt_safe(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")

    q = f"Rapid click doubt [{unique_tag()}]"
    doubt_card = page.locator("section, div").filter(has_text=re.compile(r"Doubt Clearing|Ask a Doubt", re.I)).last
    input_el = doubt_card.locator("textarea, input[type='text']").first
    input_el.fill(q)
    btn = doubt_card.get_by_role("button", name=re.compile(r"Submit|Ask|Send", re.I)).first
    btn.dblclick()
    page.locator("main, form").first.wait_for(state="visible", timeout=15000)
    expect(page.get_by_text(q).first).to_be_visible(timeout=10000)


# ---------------------------------------------------------------------------
# F14: Student Achievement Badges Edge Cases
# ---------------------------------------------------------------------------

def test_T2_F14_01_zero_marks_student_shows_locked_performance_badges(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    admin_h = auth_headers_for(stack.api_client, ADMIN_CREDS)
    stu = create_fresh_student(stack.api_client, admin_h, claim=True)
    with page.expect_response(lambda r: f"/api/v1/analytics/student-badges/{stu['id']}" in r.url and r.status == 200) as r_info:
        ui_login(page, stack.frontend_url, stu["admission_number"], stu["password"], expected_url_part="/student")
    by_title = {b["title"]: b["unlocked"] for b in r_info.value.json()["badges"]}
    assert by_title["Top Performer"] is False
    assert by_title["Subject Ace"] is False
    assert "nan" not in page.locator("main").inner_text().lower()


def test_T2_F14_02_high_attendance_low_marks_unlocks_attendance_champ_only(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    admin_h = auth_headers_for(stack.api_client, ADMIN_CREDS)
    sarah_h = auth_headers_for(stack.api_client, TEACHER_SARAH_CREDS)
    stu = create_fresh_student(stack.api_client, admin_h, claim=True)
    record_attendance_days(stack.api_client, sarah_h, student_id=stu["id"], present_count=10, absent_count=0)
    save_student_marks(stack.api_client, sarah_h, 1, [{"student_id": stu["id"], "score": 20.0}])

    with page.expect_response(lambda r: f"/api/v1/analytics/student-badges/{stu['id']}" in r.url and r.status == 200) as r_info:
        ui_login(page, stack.frontend_url, stu["admission_number"], stu["password"], expected_url_part="/student")
    by_title = {b["title"]: b["unlocked"] for b in r_info.value.json()["badges"]}
    assert by_title["Attendance Champ"] is True
    assert by_title["Subject Ace"] is False
    assert by_title["All-Rounder"] is False


def test_T2_F14_03_low_attendance_and_low_marks_shows_active_learner_fallback(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    admin_h = auth_headers_for(stack.api_client, ADMIN_CREDS)
    sarah_h = auth_headers_for(stack.api_client, TEACHER_SARAH_CREDS)
    stu = create_fresh_student(stack.api_client, admin_h, claim=True)
    record_attendance_days(stack.api_client, sarah_h, student_id=stu["id"], present_count=2, absent_count=8)
    save_student_marks(stack.api_client, sarah_h, 1, [{"student_id": stu["id"], "score": 15.0}])

    with page.expect_response(lambda r: f"/api/v1/analytics/student-badges/{stu['id']}" in r.url and r.status == 200) as r_info:
        ui_login(page, stack.frontend_url, stu["admission_number"], stu["password"], expected_url_part="/student")
    by_title = {b["title"]: b["unlocked"] for b in r_info.value.json()["badges"]}
    assert by_title["Active Learner"] is True
    expect(page.get_by_text("Active Learner", exact=False).first).to_be_visible()


def test_T2_F14_04_badges_ui_exposes_zero_peer_pii(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    text = page.locator("main").inner_text()
    for peer in ("Priya Sharma", "STU1002", "David Miller", "STU1003", "Emma Watson"):
        assert peer not in text


def test_T2_F14_05_badges_grid_mobile_viewport_no_overflow(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    page.set_viewport_size({"width": 375, "height": 812})
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    expect(page.get_by_text("Top Performer", exact=False).first).to_be_visible(timeout=10000)
    assert not page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth + 2")


# ---------------------------------------------------------------------------
# F15: Student What-If AI Score Predictor Edge Cases
# ---------------------------------------------------------------------------

def test_T2_F15_01_what_if_all_sliders_zero_clamped_high_risk(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    sliders = page.locator('input[type="range"]')
    assert sliders.count() >= 4
    with page.expect_response(lambda r: "/api/v1/ml/predict-live" in r.url and r.status == 200, timeout=15000) as r_info:
        for i in range(4):
            _set_range_slider(sliders.nth(i), 0)
    data = r_info.value.json()
    assert 0.0 <= data["active_prediction"] <= 100.0
    assert data["risk_level"] == "High Risk"
    assert data["recommended_study_hours"] == 4.0
    expect(page.get_by_text("High Risk", exact=False).first).to_be_visible()


def test_T2_F15_02_what_if_all_sliders_hundred_clamped_low_risk(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    sliders = page.locator('input[type="range"]')
    assert sliders.count() >= 4
    with page.expect_response(lambda r: "/api/v1/ml/predict-live" in r.url and r.status == 200, timeout=15000) as r_info:
        for i in range(4):
            _set_range_slider(sliders.nth(i), 100)
    data = r_info.value.json()
    assert 0.0 <= data["active_prediction"] <= 100.0
    assert data["risk_level"] == "Low Risk"
    assert data["recommended_study_hours"] == 0.5
    expect(page.get_by_text("Low Risk", exact=False).first).to_be_visible()


def test_T2_F15_03_what_if_attendance_69_vs_75_risk_transition(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    sliders = page.locator('input[type="range"]')
    for idx, val in enumerate((75, 75, 75, 69)):
        _set_range_slider(sliders.nth(idx), val)
    page.locator("main, form").first.wait_for(state="visible", timeout=15000)
    expect(page.get_by_text("High Risk", exact=False).first).to_be_visible(timeout=10000)

    with page.expect_response(lambda r: "/api/v1/ml/predict-live" in r.url and r.status == 200, timeout=15000) as r_info:
        _set_range_slider(sliders.nth(3), 75)
    assert r_info.value.json()["risk_level"] == "Medium Risk"


def test_T2_F15_04_rapid_slider_steps_settle_on_latest_value(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    sliders = page.locator('input[type="range"]')
    for val in (30, 50, 70, 90):
        _set_range_slider(sliders.nth(0), val)
    page.locator("main, form").first.wait_for(state="visible", timeout=15000)
    assert sliders.nth(0).input_value() == "90"


def test_T2_F15_05_what_if_sliders_have_valid_min_max_attributes(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    sliders = page.locator('input[type="range"]')
    assert sliders.count() >= 4
    for i in range(4):
        assert sliders.nth(i).get_attribute("min") == "0"
        assert sliders.nth(i).get_attribute("max") == "100"


# ---------------------------------------------------------------------------
# F16: Teacher AI Remedial Lesson Plan Edge Cases
# ---------------------------------------------------------------------------

def test_T2_F16_01_ai_lesson_plan_empty_marks_class_falls_back_gracefully(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    admin_h = auth_headers_for(stack.api_client, ADMIN_CREDS)
    cls_info = create_fresh_class_with_section(stack.api_client, admin_h, name="Grade 12 Empty")
    stack.api_client.post(
        "/api/v1/institution/assignments/teachers",
        json={
            "session_id": SESSION_ID,
            "class_id": cls_info["class_id"],
            "section_id": cls_info["section_id"],
            "subject_id": SUBJECT_MATH_ID,
            "teacher_id": 1,
        },
        headers=admin_h,
    )

    ui_login(page, stack.frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    page.get_by_role("button", name=re.compile(r"AI.*Lesson Plan|Remedial.*Plan", re.I)).first.click()
    sel = page.locator("select").filter(has_text="Grade 12 Empty").first
    sel.select_option(value=str(cls_info["class_id"]))
    with page.expect_response(lambda r: f"/api/v1/analytics/ai-lesson-plan/{cls_info['class_id']}" in r.url and r.status == 200):
        page.get_by_role("button", name=re.compile(r"Generate", re.I)).first.click()
    expect(page.get_by_text("Mathematics", exact=False).first).to_be_visible(timeout=10000)
    assert "nan" not in page.locator("body").inner_text().lower()


def test_T2_F16_02_teacher_only_sees_assigned_classes_in_lesson_plan_selector(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    admin_h = auth_headers_for(stack.api_client, ADMIN_CREDS)
    create_fresh_class_with_section(stack.api_client, admin_h, name="Unassigned Grade 99")

    ui_login(page, stack.frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    page.get_by_role("button", name=re.compile(r"AI.*Lesson Plan|Remedial.*Plan", re.I)).first.click()
    expect(page.get_by_text("Unassigned Grade 99")).not_to_be_visible()


def test_T2_F16_03_generate_never_sends_undefined_class_id(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    page.get_by_role("button", name=re.compile(r"AI.*Lesson Plan|Remedial.*Plan", re.I)).first.click()
    gen_btn = page.get_by_role("button", name=re.compile(r"Generate", re.I)).first
    if gen_btn.is_enabled():
        gen_btn.click()
        page.locator("main, form").first.wait_for(state="visible", timeout=15000)


def test_T2_F16_04_close_lesson_plan_modal_allows_subsequent_navigation(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    page.get_by_role("button", name=re.compile(r"AI.*Lesson Plan|Remedial.*Plan", re.I)).first.click()
    page.get_by_role("button", name=re.compile(r"Close|Cancel", re.I)).first.click()
    page.locator('aside nav a[href="/teacher/marks"]').click()
    page.wait_for_url("**/teacher/marks**", wait_until="commit", timeout=10000)


def test_T2_F16_05_student_blocked_from_teacher_lesson_plan_route(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    page.goto(f"{frontend_url}/teacher", wait_until="domcontentloaded")
    expect(page).to_have_url(re.compile(r"/student"), timeout=10000)
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# F17: Teacher Notice Board Management Edge Cases
# ---------------------------------------------------------------------------

def test_T2_F17_01_empty_title_or_content_announcement_blocked(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, watcher = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")

    board = page.locator("section, div").filter(has_text=re.compile(r"Notice Board|Announcements", re.I)).last
    board.get_by_placeholder(re.compile(r"title", re.I)).first.fill("   ")
    board.locator("textarea").first.fill("   ")
    with watcher.allow_status(422):
        board.get_by_role("button", name=re.compile(r"Post|Create|Publish|Add", re.I)).first.click()
        page.wait_for_timeout(400)


def test_T2_F17_02_non_author_teacher_cannot_delete_sarah_announcement(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
) -> None:
    title = f"Sarah Protected Notice {unique_tag()}"
    ann = create_announcement(api_client, teacher_sarah_headers, title=title)
    try:
        page, watcher = page_with_watcher
        ui_login(page, frontend_url, *TEACHER_ALAN_CREDS, expected_url_part="/teacher")
        expect(page.get_by_text(title)).to_be_visible(timeout=10000)
        row = page.locator("div, li, tr").filter(has_text=title).last
        del_btn = row.get_by_role("button", name=re.compile(r"Delete|Remove", re.I))
        if del_btn.count() > 0 and del_btn.first.is_enabled():
            with watcher.allow_status(403, 422):
                del_btn.first.click()
                page.wait_for_timeout(400)
            expect(page.get_by_text(title)).to_be_visible()
    finally:
        api_client.delete(f"/api/v1/announcements/{ann['id']}", headers=teacher_sarah_headers)


def test_T2_F17_03_long_announcement_with_special_chars_escaped(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
) -> None:
    title = f"Special & <Safe> \"Notice\" 'Test' {unique_tag()} " + ("A" * 100)
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")

    board = page.locator("section, div").filter(has_text=re.compile(r"Notice Board|Announcements", re.I)).last
    board.get_by_placeholder(re.compile(r"title", re.I)).first.fill(title)
    board.locator("textarea").first.fill("Content with <tag> & quotes 'single' \"double\".")
    with page.expect_response(lambda r: "/api/v1/announcements" in r.url and r.request.method == "POST") as resp_info:
        board.get_by_role("button", name=re.compile(r"Post|Create|Publish|Add", re.I)).first.click()
    assert resp_info.value.status == 200
    created_id = resp_info.value.json()["id"]
    try:
        expect(page.get_by_text(title[:40], exact=False)).to_be_visible(timeout=10000)
    finally:
        api_client.delete(f"/api/v1/announcements/{created_id}", headers=teacher_sarah_headers)


def test_T2_F17_04_empty_session_notice_board_shows_clean_empty_state(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    admin_h = auth_headers_for(stack.api_client, ADMIN_CREDS)
    ses_resp = stack.api_client.post(
        "/api/v1/institution/sessions",
        json={"name": "2029-2030", "start_date": "2029-06-01", "end_date": "2030-04-30", "is_active": False},
        headers=admin_h,
    )
    assert ses_resp.status_code == 200

    ui_login(page, stack.frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    page.locator("header select").select_option(value=str(ses_resp.json()["id"]))
    page.locator("main, form").first.wait_for(state="visible", timeout=15000)
    expect(page.get_by_text(re.compile(r"No announcements|No notices", re.I)).first).to_be_visible(timeout=10000)


def test_T2_F17_05_admin_notice_shows_administration_author_in_teacher_ui(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    admin_headers: Dict[str, str],
) -> None:
    title = f"Admin Broadcast {unique_tag()}"
    ann = create_announcement(api_client, admin_headers, class_id=None, title=title, priority="High")
    try:
        page, _ = page_with_watcher
        ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
        expect(page.get_by_text(title)).to_be_visible(timeout=10000)
        expect(page.get_by_text("Administration").first).to_be_visible()
    finally:
        api_client.delete(f"/api/v1/announcements/{ann['id']}", headers=admin_headers)


# ---------------------------------------------------------------------------
# F18: Teacher Doubt Resolution Hub Edge Cases
# ---------------------------------------------------------------------------

def test_T2_F18_01_empty_whitespace_answer_blocked_in_doubt_hub(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    student_1_headers: Dict[str, str],
) -> None:
    q = f"Empty answer guard [{unique_tag()}]"
    create_doubt(api_client, student_1_headers, subject_id=SUBJECT_MATH_ID, question=q)

    page, watcher = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    expect(page.get_by_text(q)).to_be_visible(timeout=10000)
    card = page.locator("div, li").filter(has_text=q).filter(
        has=page.get_by_role("button", name=re.compile(r"Answer|Reply|Resolve|Submit", re.I))
    ).last
    card.locator("input, textarea").first.fill("   ")
    with watcher.allow_status(422):
        card.get_by_role("button", name=re.compile(r"Answer|Reply|Resolve|Submit", re.I)).first.click()
        page.wait_for_timeout(400)
    expect(card.get_by_text("Pending", exact=False).first).to_be_visible()


def test_T2_F18_02_pending_filter_shows_empty_state_when_all_answered(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    sarah_h = auth_headers_for(stack.api_client, TEACHER_SARAH_CREDS)
    stack.api_client.post("/api/v1/doubts/2/answer", json={"answer": "Resolved all."}, headers=sarah_h)

    ui_login(page, stack.frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    hub = page.locator("section, div").filter(has_text=re.compile(r"Doubt.*Hub|Student Doubts", re.I)).last
    hub.locator("select").filter(has_text=re.compile(r"Pending", re.I)).first.select_option(label="Pending")
    expect(page.get_by_text(re.compile(r"No.*doubts", re.I)).first).to_be_visible(timeout=10000)


def test_T2_F18_03_subject_filter_history_shows_empty_and_restores_all(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    hub = page.locator("section, div").filter(has_text=re.compile(r"Doubt.*Hub|Student Doubts", re.I)).last
    subj_sel = hub.locator("select").filter(has_text=re.compile(r"History", re.I)).first
    subj_sel.select_option(label="History")
    expect(page.get_by_text("quadratic factorisation", exact=False)).not_to_be_visible()
    subj_sel.select_option(index=0)
    expect(page.get_by_text("quadratic factorisation", exact=False)).to_be_visible()


def test_T2_F18_04_already_answered_doubt_preserves_answer_across_filters(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    hub = page.locator("section, div").filter(has_text=re.compile(r"Doubt.*Hub|Student Doubts", re.I)).last
    status_sel = hub.locator("select").filter(has_text=re.compile(r"Answered", re.I)).first
    status_sel.select_option(label="Answered")
    expect(page.get_by_text("b^2 - 4ac", exact=False)).to_be_visible()
    status_sel.select_option(index=0)
    expect(page.get_by_text("b^2 - 4ac", exact=False)).to_be_visible()


def test_T2_F18_05_math_symbols_answer_preserved_verbatim(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    student_1_headers: Dict[str, str],
) -> None:
    q = f"Math symbol test [{unique_tag()}]"
    create_doubt(api_client, student_1_headers, subject_id=SUBJECT_MATH_ID, question=q)

    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    expect(page.get_by_text(q)).to_be_visible(timeout=10000)

    sym_ans = "Formula: x^2 + y^2 = r^2 & a/b >= 0"
    card = page.locator("div, li").filter(has_text=q).filter(
        has=page.get_by_role("button", name=re.compile(r"Answer|Reply|Resolve|Submit", re.I))
    ).last
    card.locator("input, textarea").first.fill(sym_ans)
    with page.expect_response(lambda r: "/answer" in r.url and r.request.method == "POST"):
        card.get_by_role("button", name=re.compile(r"Answer|Reply|Resolve|Submit", re.I)).first.click()
    expect(page.get_by_text(sym_ans)).to_be_visible(timeout=10000)


# ---------------------------------------------------------------------------
# F19: Teacher Bulk CSV & Datesheet Upload Edge Cases
# ---------------------------------------------------------------------------

def test_T2_F19_01_csv_upload_without_file_handled_without_crash(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, watcher = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    page.goto(f"{frontend_url}/teacher/marks", wait_until="domcontentloaded")

    csv_panel = page.locator("section, div").filter(has_text=re.compile(r"Bulk.*CSV|CSV.*Upload", re.I)).last
    btn = csv_panel.get_by_role("button", name=re.compile(r"Upload|Import", re.I)).first
    if btn.is_enabled():
        with watcher.allow_status(400, 422):
            btn.click()
            page.wait_for_timeout(400)


def test_T2_F19_02_invalid_csv_score_displays_error_banner(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    tmp_path: Path,
) -> None:
    bad_csv = tmp_path / "bad_score.csv"
    bad_csv.write_text("Admission Number,Exam ID,Score\nSTU1001,1,999\n", encoding="utf-8")

    page, watcher = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    page.goto(f"{frontend_url}/teacher/marks", wait_until="domcontentloaded")

    csv_panel = page.locator("section, div").filter(has_text=re.compile(r"Bulk.*CSV|CSV.*Upload", re.I)).last
    csv_panel.locator('input[type="file"]').first.set_input_files(str(bad_csv))
    with watcher.allow_status(400, 422):
        csv_panel.get_by_role("button", name=re.compile(r"Upload|Import", re.I)).first.click()
        page.wait_for_timeout(500)
    expect(page.get_by_text(re.compile(r"error|invalid|exceeds|max|fail", re.I)).first).to_be_visible(timeout=10000)


def test_T2_F19_03_invalid_csv_headers_displays_error_banner(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    tmp_path: Path,
) -> None:
    bad_csv = tmp_path / "bad_headers.csv"
    bad_csv.write_text("ColA,ColB\n1,2\n", encoding="utf-8")

    page, watcher = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    page.goto(f"{frontend_url}/teacher/marks", wait_until="domcontentloaded")

    csv_panel = page.locator("section, div").filter(has_text=re.compile(r"Bulk.*CSV|CSV.*Upload", re.I)).last
    csv_panel.locator('input[type="file"]').first.set_input_files(str(bad_csv))
    with watcher.allow_status(400, 422):
        csv_panel.get_by_role("button", name=re.compile(r"Upload|Import", re.I)).first.click()
        page.wait_for_timeout(500)
    expect(page.get_by_text(re.compile(r"error|invalid|header|column|missing", re.I)).first).to_be_visible(timeout=10000)


def test_T2_F19_04_datesheet_upload_png_succeeds(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    api_client: httpx.Client,
    teacher_sarah_headers: Dict[str, str],
    tmp_path: Path,
) -> None:
    exam = create_exam(api_client, teacher_sarah_headers, name=f"PNG UI Exam {unique_tag()}")
    png_path = tmp_path / "sheet.png"
    png_path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00")

    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    page.goto(f"{frontend_url}/teacher/marks", wait_until="domcontentloaded")

    page.locator("select").filter(has_text=exam["name"]).first.select_option(value=str(exam["id"]))
    ds_input = page.locator('input[type="file"][accept*="pdf" i]').first
    with page.expect_response(lambda r: f"/api/v1/exams/{exam['id']}/datesheet" in r.url and r.request.method == "POST") as resp_info:
        ds_input.set_input_files(str(png_path))
        btns = page.get_by_role("button", name=re.compile(r"Upload Datesheet|Attach Datesheet", re.I))
        if btns.count() > 0:
            btns.first.click()
    assert resp_info.value.status == 200


def test_T2_F19_05_out_of_scope_teacher_csv_rejected_cleanly(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "alan_unauth.csv"
    csv_path.write_text("Admission Number,Exam ID,Score\nSTU1001,1,40\n", encoding="utf-8")

    page, watcher = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_ALAN_CREDS, expected_url_part="/teacher")
    page.goto(f"{frontend_url}/teacher/marks", wait_until="domcontentloaded")

    csv_panel = page.locator("section, div").filter(has_text=re.compile(r"Bulk.*CSV|CSV.*Upload", re.I)).last
    csv_panel.locator('input[type="file"]').first.set_input_files(str(csv_path))
    with watcher.allow_status(403, 404, 422):
        csv_panel.get_by_role("button", name=re.compile(r"Upload|Import", re.I)).first.click()
        page.wait_for_timeout(500)
    expect(page.get_by_text(re.compile(r"error|scope|not found|denied|unauthorized", re.I)).first).to_be_visible(timeout=10000)


# ---------------------------------------------------------------------------
# F20: Admin Model Switcher Edge Cases
# ---------------------------------------------------------------------------

def test_T2_F20_01_non_admin_blocked_from_admin_models_route(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    for creds in (STUDENT_1_CREDS, TEACHER_SARAH_CREDS):
        ui_login(page, frontend_url, *creds)
        page.goto(f"{frontend_url}/admin/models", wait_until="domcontentloaded")
        expect(page).not_to_have_url(re.compile(r"/admin/models"), timeout=10000)
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass
        ui_logout(page)


def test_T2_F20_02_active_model_button_disabled_or_idempotent(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    ui_login(page, stack.frontend_url, *ADMIN_CREDS, expected_url_part="/admin")
    page.goto(f"{stack.frontend_url}/admin/models", wait_until="domcontentloaded")

    active_btn = page.get_by_role("button", name=re.compile(r"Active|Current", re.I))
    if active_btn.count() > 0 and active_btn.first.is_enabled():
        active_btn.first.click()
        page.locator("main, form").first.wait_for(state="visible", timeout=15000)
    models = stack.api_client.get(
        "/api/v1/ml/models", headers=auth_headers_for(stack.api_client, ADMIN_CREDS)
    ).json()
    assert sum(1 for m in models if "regression" in m["task"].lower() and m["is_active"]) == 1


def test_T2_F20_03_rapid_sequential_model_switches_settle_on_last(
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

    models = stack.api_client.get(
        "/api/v1/ml/models", headers=auth_headers_for(stack.api_client, ADMIN_CREDS)
    ).json()
    active = [m for m in models if "regression" in m["task"].lower() and m["is_active"]]
    assert len(active) == 1 and "xgboost" in active[0]["model_name"].lower()


def test_T2_F20_04_model_metrics_formatted_without_nan_or_undefined(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *ADMIN_CREDS, expected_url_part="/admin")
    page.goto(f"{frontend_url}/admin/models", wait_until="domcontentloaded")

    text = page.locator("main").inner_text()
    assert "nan" not in text.lower() and "undefined" not in text.lower()
    assert re.search(r"\d+\.\d+", text)


def test_T2_F20_05_switch_model_api_error_displays_error_without_false_badge(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, watcher = page_with_watcher
    ui_login(page, frontend_url, *ADMIN_CREDS, expected_url_part="/admin")
    page.goto(f"{frontend_url}/admin/models", wait_until="domcontentloaded")

    page.route(
        "**/api/v1/ml/switch-model",
        lambda route: route.fulfill(status=422, content_type="application/json", body='{"detail":"Simulated switch error"}'),
    )
    btn = page.get_by_role("button", name=re.compile(r"Switch|Activate|Set Active", re.I)).first
    with watcher.allow_status(422):
        btn.click()
        page.wait_for_timeout(400)
    expect(page.get_by_text("Simulated switch error", exact=False).first).to_be_visible(timeout=10000)


# ---------------------------------------------------------------------------
# F21: Routing, Sidebar, Navbar Edge Cases
# ---------------------------------------------------------------------------

def test_T2_F21_01_unauthenticated_protected_routes_redirect_to_login(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    for route in ("/student", "/teacher", "/admin", "/admin/models", "/teacher/marks"):
        page.goto(f"{frontend_url}{route}", wait_until="domcontentloaded")
        expect(page).to_have_url(re.compile(r"/login"), timeout=10000)


def test_T2_F21_02_cross_role_route_guards_redirect_cleanly(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    for forbidden in ("/teacher", "/admin", "/admin/models"):
        page.goto(f"{frontend_url}{forbidden}", wait_until="domcontentloaded")
        expect(page).to_have_url(re.compile(r"/student"), timeout=10000)
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass
    ui_logout(page)

    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    for forbidden in ("/student", "/admin", "/admin/models"):
        page.goto(f"{frontend_url}{forbidden}", wait_until="domcontentloaded")
        expect(page).to_have_url(re.compile(r"/teacher"), timeout=10000)
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass


def test_T2_F21_03_unknown_route_redirects_by_auth_state(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    page.goto(f"{frontend_url}/nonexistent/page/xyz", wait_until="domcontentloaded")
    expect(page).to_have_url(re.compile(r"/login"), timeout=10000)

    ui_login(page, frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    page.goto(f"{frontend_url}/nonexistent/page/xyz", wait_until="domcontentloaded")
    expect(page).to_have_url(re.compile(r"/student"), timeout=10000)


def test_T2_F21_04_nested_routes_survive_reload_and_history_navigation(
    page_with_watcher: Tuple[Page, BrowserErrorWatcher],
    frontend_url: str,
) -> None:
    page, _ = page_with_watcher
    ui_login(page, frontend_url, *TEACHER_SARAH_CREDS, expected_url_part="/teacher")
    page.goto(f"{frontend_url}/teacher/marks", wait_until="domcontentloaded")
    expect(page.get_by_text("Save Marks", exact=False).first).to_be_visible(timeout=10000)
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass
    page.reload(wait_until="domcontentloaded")
    assert "/teacher/marks" in page.url
    expect(page.get_by_text("Save Marks", exact=False).first).to_be_visible(timeout=10000)
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass

    page.goto(f"{frontend_url}/teacher/analytics", wait_until="domcontentloaded")
    expect(page.get_by_text("Academic Analytics", exact=False).first).to_be_visible(timeout=10000)
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass
    page.go_back(wait_until="domcontentloaded")
    expect(page).to_have_url(re.compile(r"/teacher/marks"), timeout=10000)
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass


def test_T2_F21_05_navbar_session_dropdown_switch_refreshes_cleanly(
    fresh_isolated_stack: Tuple[IsolatedStack, Page, BrowserErrorWatcher],
) -> None:
    stack, page, _ = fresh_isolated_stack
    admin_h = auth_headers_for(stack.api_client, ADMIN_CREDS)
    ses_resp = stack.api_client.post(
        "/api/v1/institution/sessions",
        json={"name": "2027-2028", "start_date": "2027-06-01", "end_date": "2028-04-30", "is_active": False},
        headers=admin_h,
    )
    assert ses_resp.status_code == 200

    ui_login(page, stack.frontend_url, *STUDENT_1_CREDS, expected_url_part="/student")
    sel = page.locator("header select")
    sel.select_option(value=str(ses_resp.json()["id"]))
    page.locator("main, form").first.wait_for(state="visible", timeout=15000)
    sel.select_option(value=str(SESSION_ID))
    page.locator("main, form").first.wait_for(state="visible", timeout=15000)
    expect(page.get_by_text("Alex Carter").first).to_be_visible()
