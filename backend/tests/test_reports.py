import pytest
from backend.tests.conftest import make_token


def test_student_report_pdf_and_excel(client, test_data):
    """
    T-015: PDF and Excel reports generation with role scope.
    """
    t_token = make_token(test_data["user_teacher_1"], teacher_id=test_data["teacher_1"].id)
    headers = {"Authorization": f"Bearer {t_token}"}

    # 1. Download PDF
    pdf_resp = client.get(
        f"/api/v1/reports/student/{test_data['student_1'].id}/pdf?session_id={test_data['session'].id}",
        headers=headers
    )
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert len(pdf_resp.content) > 500  # non-trivial PDF bytes

    # 2. Download Excel
    excel_resp = client.get(
        f"/api/v1/reports/student/{test_data['student_1'].id}/excel?session_id={test_data['session'].id}",
        headers=headers
    )
    assert excel_resp.status_code == 200
    assert "spreadsheetml" in excel_resp.headers["content-type"]
    assert len(excel_resp.content) > 500


def test_student_forbidden_from_other_student_reports(client, test_data):
    """
    T-015 & T-004: Student 1 attempts to download Student 2's report -> returns 404.
    """
    s1_token = make_token(test_data["user_student_1"], student_id=test_data["student_1"].id)
    headers = {"Authorization": f"Bearer {s1_token}"}

    resp = client.get(
        f"/api/v1/reports/student/{test_data['student_2'].id}/pdf?session_id={test_data['session'].id}",
        headers=headers
    )
    assert resp.status_code == 404

