def _clean(value: str) -> str:
    return str(value or "").strip()


def resolve_project(text: str, explicit_project: str = "", project_repo=None) -> str:
    explicit = _clean(explicit_project)
    if explicit:
        return explicit

    if project_repo is None:
        from app.repositories.sheets_project_repository import SheetsProjectRepository

        project_repo = SheetsProjectRepository()

    haystack = _clean(text).lower()
    if not haystack:
        return ""

    for project in project_repo.search_projects(""):
        status = _clean(project.get("status")).lower()
        if status and status != "active":
            continue

        name = _clean(project.get("name"))
        if name and name.lower() in haystack:
            return name

    return ""
