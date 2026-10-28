# Static Code Analysis Issues — Student Grade System

## Overview

The original `student_grade_system.py` was analyzed using Pylint, Bandit, and Flake8. The issues below are based on the original reports. Line numbers refer to the original version and may differ after edits.

| Issue | Type | Original line(s) | Description | Fix approach |
|---|---|---:|---|---|
| Shell command built with filename | Security (Bandit B605, High) | 60 | `os.system()` ran a shell command containing the filename, creating a potential command-injection risk. | Removed the shell call and used a normal `print()` statement after exporting the file. |
| Weak MD5 hash | Security (Bandit B324, High) | 49 | MD5 is a weak hash function for security-sensitive use. | Replaced MD5 with SHA-256. A hash of a student ID is not encryption and should not be treated as secret. |
| Dynamic `eval()` | Security (Bandit B307, Medium; Pylint W0123) | 44 | `eval(gpa_expr)` executes an arbitrary Python expression. | Removed the expression parameter and calculated the current GPA-like score directly from the average marks. |
| Hardcoded portal token | Security (Bandit B105, Low) | 64 | A token-like value was embedded in source code and printed. | Read the value from the `ADMIN_GRADE_PORTAL_TOKEN` environment variable and print only whether it is configured. |
| Non-cryptographic PIN generator | Security (Bandit B311, Low) | 53 | `random.randint()` is not suitable for security-sensitive PIN generation. | Replaced it with `secrets.randbelow()` to generate a four-digit PIN. |
| Bare exception swallowed | Robustness/security (Bandit B110; Pylint W0702; Flake8 E722) | 22–27 | A bare `except: pass` hid errors in attendance recording. | Replaced it with explicit input validation and a Boolean result. |
| Mutable default argument | Code quality (Pylint W0102) | 15 | `grade_list=[]` reused a mutable object across calls. | Changed the default to `None` and creates a new list when no list is supplied. |
| Function naming | Code style (Pylint C0103) | 15 | `addGrade` did not follow snake_case. | Renamed it to `add_grade` and updated the call site. |
| Unused imports and variables | Code quality/style (Pylint W0611/W0612; Flake8 F401/F841) | Various | Imports and local variables were unused, including `json`, `random` in the original code, and `grace_marks`. | Removed unused imports and variables. |
| Missing docstrings | Code quality (Pylint C0116) | Function definitions | Functions did not explain their purpose. | Added docstrings to functions. |
| Incorrect `None` comparison and redundant conditional | Code quality (Pylint C0121/R1703/R1705) | 32–38 | Used `== None` and an unnecessary `if/else` return structure. | Used `is None`, handled missing/empty marks, and returned the Boolean comparison directly. |
| File handling and encoding | Code quality (Pylint W1514/R1732) | 57–59 | File was opened without an explicit encoding and closed manually. | Used a `with open(..., encoding="utf-8")` context manager. |
| Formatting violations | Style (Flake8 E501/E302/W292) | Various | Long lines, insufficient blank lines, and missing final newline were reported. | Reformatted the affected lines, added required blank lines, and ensured a final newline. |
| Old-style string formatting | Code quality (Pylint C0209) | 19 | A regular `%`-formatted string could use an f-string. | Replaced it with an f-string. |

## Verification

After the fixes, the submitted reports showed:
- **Bandit:** “No issues identified.”
- **Pylint:** 10.00/10.
- **Flake8:** the after-report was empty, consistent with no reported violations.

Run the tools again on the final committed file if any further edits are made.
