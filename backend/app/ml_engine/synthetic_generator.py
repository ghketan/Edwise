import random
from typing import List, Tuple
import numpy as np
import pandas as pd


def generate_synthetic_academic_dataset(
    n_students: int = 300,
    random_seed: int = 42
) -> pd.DataFrame:
    """
    Generates synthetic academic data conforming to D-015:
    Features represent strictly academic behaviours (attendance rate,
    prior exam percentages, assignment submission rate).
    Every row is labeled is_synthetic=True (R-015).
    """
    np.random.seed(random_seed)
    random.seed(random_seed)

    student_ids = [f"STU_{1000 + i}" for i in range(n_students)]
    
    # Latent academic engagement factor
    engagement = np.random.beta(a=5, b=2, size=n_students)  # between 0 and 1, skewed towards diligence

    # Attendance rate (strongly correlated with engagement)
    attendance_rate = np.clip(engagement * 100 + np.random.normal(0, 5, n_students), 20, 100)

    # Assignment submission rate (strongly correlated with engagement)
    assignment_rate = np.clip(engagement * 100 + np.random.normal(0, 8, n_students), 10, 100)

    # Exam 1 (prior mark)
    exam1 = np.clip(engagement * 100 + np.random.normal(0, 10, n_students), 10, 100)

    # Exam 2 (midterm)
    exam2 = np.clip(0.4 * exam1 + 0.4 * (engagement * 100) + 0.2 * attendance_rate + np.random.normal(0, 8, n_students), 10, 100)

    # Final Exam (Target for regression)
    final_exam = np.clip(
        0.35 * exam2 + 0.35 * exam1 + 0.15 * (attendance_rate) + 0.15 * (assignment_rate) + np.random.normal(0, 7, n_students),
        5, 100
    )

    # At-risk label: True if final exam < 40 (standard academic passing cutoff)
    is_at_risk = (final_exam < 40).astype(int)

    df = pd.DataFrame({
        "student_id": student_ids,
        "attendance_rate": np.round(attendance_rate, 2),
        "assignment_rate": np.round(assignment_rate, 2),
        "exam1_pct": np.round(exam1, 2),
        "exam2_pct": np.round(exam2, 2),
        "prior_exam_avg": np.round((exam1 + exam2) / 2.0, 2),
        "final_exam_score": np.round(final_exam, 2),
        "is_at_risk": is_at_risk,
        "is_synthetic": True
    })

    return df

