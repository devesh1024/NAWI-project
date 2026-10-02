# backend/app/services/report_files.py
#
# Generated report files (.docx/.pdf) live on disk under generated_reports/
# (see api/reports/routes.py). When a report is deleted its files must go too,
# but only files that really are inside that folder: a path stored in the
# database must never be able to make us delete something elsewhere.

from pathlib import Path

REPORTS_DIR = Path("generated_reports")


def collect_report_paths(*reports) -> set[str]:
    """Paths referenced by the given Report / ReportVersion rows."""
    paths: set[str] = set()
    for report in reports:
        for attr in ("docx_path", "pdf_path"):
            value = getattr(report, attr, None)
            if value:
                paths.add(value)
    return paths


def remove_report_files(paths: set[str]) -> list[str]:
    """
    Best-effort delete, to be called AFTER the database commit succeeded.
    Returns the paths that were removed. Anything outside generated_reports/
    is ignored.
    """
    base = REPORTS_DIR.resolve()
    removed: list[str] = []

    for raw in paths:
        try:
            path = Path(raw).resolve()
            if base in path.parents and path.is_file():
                path.unlink()
                removed.append(str(path))
        except OSError:
            continue  # a locked/missing file must not fail the request

    return removed
