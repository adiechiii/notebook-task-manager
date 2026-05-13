from app.repositories.sheets_status_log_repository import SheetsStatusLogRepository
from app.repositories.sheets_task_repository import SheetsTaskRepository
from app.services.duplicate_cleanup_plan_service import build_duplicate_cleanup_plan


DUPLICATE_ARCHIVE_CONFIRMATION = "ARCHIVE DUPLICATE TASKS"


def _display_value(value):
    return str(value or "").strip()


def _normalize_requested_task_ids(task_ids):
    normalized = []
    seen = set()
    skipped = []

    for task_id in task_ids or []:
        cleaned = _display_value(task_id)
        if not cleaned:
            skipped.append({
                "task_id": cleaned,
                "reason": "blank_task_id",
            })
            continue

        if cleaned in seen:
            skipped.append({
                "task_id": cleaned,
                "reason": "duplicate_requested_task_id",
            })
            continue

        seen.add(cleaned)
        normalized.append(cleaned)

    return normalized, skipped


def _suggested_archive_by_task_id(cleanup_plan):
    eligible = {}

    for group in cleanup_plan.get("cleanup_plan", []):
        group_key = group.get("group_key")
        confidence = group.get("confidence")
        reason = group.get("reason")

        for task in group.get("suggested_archive", []):
            task_id = _display_value(task.get("task_id"))
            if not task_id:
                continue

            enriched_task = dict(task)
            enriched_task["group_key"] = group_key
            enriched_task["confidence"] = confidence
            enriched_task["eligibility_reason"] = reason
            eligible[task_id] = enriched_task

    return eligible


def archive_duplicate_cleanup_candidates(
    task_ids,
    dry_run=True,
    confirmation="",
    task_repo=None,
    status_log_repo=None,
):
    if not dry_run and confirmation != DUPLICATE_ARCHIVE_CONFIRMATION:
        return {
            "dry_run": False,
            "requested_count": len(task_ids or []),
            "eligible_count": 0,
            "archived_count": 0,
            "logged_count": 0,
            "eligible": [],
            "archived": [],
            "skipped": [],
            "warnings": ["Exact confirmation phrase is required. No tasks were archived."],
        }

    task_repo = task_repo or SheetsTaskRepository()
    requested_ids, skipped = _normalize_requested_task_ids(task_ids)
    cleanup_plan = build_duplicate_cleanup_plan(task_repo=task_repo)
    plan_eligible_by_id = _suggested_archive_by_task_id(cleanup_plan)

    eligible = []
    eligible_ids = []

    for task_id in requested_ids:
        task = plan_eligible_by_id.get(task_id)
        if task:
            eligible.append(task)
            eligible_ids.append(task_id)
            continue

        skipped.append({
            "task_id": task_id,
            "reason": "not_currently_suggested_for_duplicate_archive",
        })

    warnings = []
    if dry_run:
        warnings.append("Dry-run only. No tasks were changed.")

    archived = []
    logged_count = 0

    if not dry_run and confirmation == DUPLICATE_ARCHIVE_CONFIRMATION and eligible_ids:
        status_log_repo = status_log_repo or SheetsStatusLogRepository()
        archived, archive_warnings = task_repo.archive_duplicate_task_ids(eligible_ids)
        warnings.extend(archive_warnings)

        for task in archived:
            status_log_repo.create_log(
                task.get("task_id"),
                task.get("previous_status"),
                "Archived",
                change_source="duplicate_cleanup",
            )
            logged_count += 1

    if not eligible:
        warnings.append("No requested task IDs are currently eligible for duplicate archive.")

    return {
        "dry_run": bool(dry_run),
        "requested_count": len(task_ids or []),
        "eligible_count": len(eligible),
        "archived_count": len(archived),
        "logged_count": logged_count,
        "eligible": eligible,
        "archived": archived,
        "skipped": skipped,
        "warnings": warnings,
    }
