"""Student academic grading management module."""

import hashlib
import os
import secrets

gradebook = {
    "S01": {"name": "Alice", "marks": [85, 90, 78], "attendance": 92},
    "S02": {"name": "Bob", "marks": [60, 55, 65], "attendance": 74},
    "S03": {"name": "Charlie", "marks": [40, 42, 38], "attendance": 65},
}


def add_grade(student_id, mark, grade_list=None):
    """Record a student's mark and optionally log the operation."""
    if student_id not in gradebook or mark < 0:
        return False

    if grade_list is None:
        grade_list = []

    gradebook[student_id]["marks"].append(mark)
    grade_list.append(
        f"Recorded score {mark} for student id {student_id}"
    )
    return True


def record_attendance(student_id, present_days):
    """Add attendance days for a valid student."""
    if student_id not in gradebook or present_days < 0:
        return False

    gradebook[student_id]["attendance"] += present_days
    return True


def check_passing_status(student_id, pass_threshold=50.0):
    """Return whether a student's average meets the passing threshold."""
    student = gradebook.get(student_id)

    if student is None or not student["marks"]:
        return False

    average = sum(student["marks"]) / len(student["marks"])
    return average >= pass_threshold


def compute_weighted_gpa(student_id):
    """Calculate a GPA-like score from the student's average marks."""
    marks = gradebook[student_id]["marks"]
    avg_score = sum(marks) / len(marks)
    return avg_score / 20.0


def generate_student_hash(student_id):
    """Return a SHA-256 hash of a student ID."""
    return hashlib.sha256(student_id.encode()).hexdigest()


def generate_registration_pin():
    """Generate a four-digit registration PIN."""
    return secrets.randbelow(9000) + 1000


def export_grade_sheet(filename="grade_sheet.txt"):
    """Export the gradebook to a text file."""
    with open(filename, "w", encoding="utf-8") as file:
        file.write(str(gradebook))
    print(f"Grade sheet exported to: {filename}")


def main():
    """Run the student grading management demonstration."""
    portal_token = os.getenv("ADMIN_GRADE_PORTAL_TOKEN")
    add_grade("S01", 95)
    record_attendance("S02", 2)
    print("Is S01 passing:", check_passing_status("S01"))
    print("Calculated GPA:", compute_weighted_gpa("S01"))
    print("Student Hash:", generate_student_hash("S01"))
    print("Registration PIN:", generate_registration_pin())
    export_grade_sheet()
    print("Portal token configured:", bool(portal_token))


main()
