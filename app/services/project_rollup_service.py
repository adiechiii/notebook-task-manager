TASK_BUCKETS = ("today", "overdue", "upcoming", "no_date", "done")


def _display_text(value):
    return str(value or "").strip()


def _project_key(value):
    return _display_text(value).lower()


def _empty_counts(project):
    return {
        "project": project,
        "task_count": 0,
        "memory_count": 0,
        "today": 0,
        "overdue": 0,
        "upcoming": 0,
        "no_date": 0,
        "done": 0,
    }


def _project_metadata(project):
    return {
        "project": _display_text(project.get("name")),
        "status": _display_text(project.get("status")),
        "priority": _display_text(project.get("priority")),
        "category": _display_text(project.get("category")),
        "tags": _display_text(project.get("tags")),
    }


def _bucket_lookup(command_center):
    lookup = {}

    for bucket in TASK_BUCKETS:
        for task in (command_center or {}).get(bucket, []):
            lookup[id(task)] = bucket

    return lookup


def _task_bucket(task, lookup):
    bucket = lookup.get(id(task))
    if bucket:
        return bucket

    if _display_text(task.get("status")).lower() == "done":
        return "done"

    return "no_date"


def build_project_rollups(tasks, memories, projects, command_center=None):
    project_by_key = {}
    project_order = []

    for project in projects or []:
        name = _display_text(project.get("name"))
        key = _project_key(name)

        if not key:
            continue

        if key not in project_by_key:
            project_order.append(key)

        project_by_key[key] = project

    linked = {}
    unmatched = {}
    unlinked_tasks = 0
    unlinked_memories = 0
    unmatched_project_tasks = 0
    unmatched_project_memories = 0
    task_bucket_lookup = _bucket_lookup(command_center)

    for key in project_order:
        linked[key] = _empty_counts(_display_text(project_by_key[key].get("name")))

    for task in tasks or []:
        project_name = _display_text(task.get("project"))
        key = _project_key(project_name)

        if not key:
            unlinked_tasks += 1
            continue

        if key in linked:
            rollup = linked[key]
        else:
            unmatched_project_tasks += 1
            rollup = unmatched.setdefault(key, _empty_counts(project_name))

        rollup["task_count"] += 1
        rollup[_task_bucket(task, task_bucket_lookup)] += 1

    for memory in memories or []:
        project_name = _display_text(memory.get("project"))
        key = _project_key(project_name)

        if not key:
            unlinked_memories += 1
            continue

        if key in linked:
            rollup = linked[key]
        else:
            unmatched_project_memories += 1
            rollup = unmatched.setdefault(key, _empty_counts(project_name))

        rollup["memory_count"] += 1

    items = []
    active_projects_without_links = []

    for key in project_order:
        project = project_by_key[key]
        metadata = _project_metadata(project)
        rollup = linked[key]
        has_links = rollup["task_count"] > 0 or rollup["memory_count"] > 0

        if has_links:
            items.append({**metadata, **{k: rollup[k] for k in rollup if k != "project"}})
        elif metadata["status"].lower() == "active":
            active_projects_without_links.append(metadata)

    return {
        "total_projects": len(project_order),
        "active_projects": sum(
            1
            for key in project_order
            if _display_text(project_by_key[key].get("status")).lower() == "active"
        ),
        "projects_with_tasks": sum(1 for rollup in linked.values() if rollup["task_count"] > 0),
        "projects_with_memories": sum(1 for rollup in linked.values() if rollup["memory_count"] > 0),
        "unlinked_tasks": unlinked_tasks,
        "unlinked_memories": unlinked_memories,
        "unmatched_project_tasks": unmatched_project_tasks,
        "unmatched_project_memories": unmatched_project_memories,
        "items": items,
        "unmatched_projects": list(unmatched.values()),
        "active_projects_without_links": active_projects_without_links,
    }
