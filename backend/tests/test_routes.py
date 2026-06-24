"""
Routing regression guard.

The literal /students/export.* and /students/template.* routes must not be
shadowed by the dynamic GET /students/{student_id} route. They were, until
{student_id} was constrained to :int — this locks that fix.
"""

from starlette.routing import Match

from agents.students_agent import router


def _match_names(method: str, path: str) -> list[str]:
    scope = {"type": "http", "method": method, "path": path,
             "headers": [], "query_string": b""}
    return [r.name for r in router.routes if r.matches(scope)[0] == Match.FULL]


def test_export_and_template_routes_not_shadowed():
    for path, name in [
        ("/students/export.csv", "export_csv"),
        ("/students/export.xlsx", "export_xlsx"),
        ("/students/template.csv", "csv_template"),
        ("/students/template.xlsx", "xlsx_template"),
    ]:
        names = _match_names("GET", path)
        assert name in names, f"{path} did not resolve to {name} (got {names})"
        assert "get_student" not in names, f"{path} is shadowed by get_student"


def test_numeric_student_id_still_resolves():
    names = _match_names("GET", "/students/42")
    assert "get_student" in names
