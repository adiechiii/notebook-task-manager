# Internal Cognition Layer Architecture

## Goal

Add backend intelligence to Notebook Task Manager / Mind OS without adding new OpenAI Actions or public API endpoints.

This layer improves existing systems through internal services only:

- Smart Project Linking
- Priority Scoring
- Related Memory Suggestions

It plugs into existing endpoints:

- POST /capture/preview
- POST /capture/confirm
- GET /dashboard/unified
- GET /priorities/smart
- GET /insights
- GET /planning/weekly

No new public routes or Custom GPT actions are required.

## Architecture Principles

1. Keep existing API actions stable.
2. Put intelligence in internal services under app/services/.
3. Keep read-only endpoints returning dry_run: true and writes: false.
4. Keep write endpoints explicit and safe.
5. Keep confirmCapture protected by exact confirmation: CONFIRM CAPTURE.
6. Return explainable metadata: suggested_project, confidence, score, reason, and signals.
7. Prefer deterministic scoring from existing text fields before adding external AI dependencies.

## Internal Services

### app/services/context_linking_service.py

Purpose: Smart Project Linking.

Main responsibility:
- Detect the best project for tasks, memories, decisions, notes, ideas, and reflections.

Inputs:
- capture text
- explicit project, when provided
- active projects
- related memories
- related decisions
- recent tasks

Returns:
- suggested_project
- confidence
- score
- linking_reason
- candidate_projects
- signals

Scoring signals:
- explicit project
- project name match
- project description and goal overlap
- project tag overlap
- memory overlap
- decision overlap
- recent task or project activity
- active project status

Confidence bands:
- 80+ high
- 50-79 medium
- 20-49 low
- below 20 none

### app/services/priority_scoring_service.py

Purpose: Automatic Priority Scoring and Decision-Aware Ranking.

Main responsibility:
- Calculate dynamic task or decision priority from urgency, due date, project importance, decisions, blockers, and related context.

Inputs:
- text
- manual priority
- due date
- project
- project metadata
- related decisions
- related memories
- task context

Returns:
- priority
- priority_band
- score
- scoring_reason
- score_breakdown
- signals

Scoring signals:
- due date
- overdue status
- urgency wording
- manual priority
- project priority
- high-importance decisions
- blocker or dependency language
- repeated mentions
- memory relevance

### app/services/related_memory_service.py

Purpose: Related Memory Suggestions.

Main responsibility:
- Surface useful memories during capture preview, dashboard, review, priorities, insights, and weekly planning.

Inputs:
- text
- project
- memories
- limit

Returns:
- text
- summary
- project
- importance
- relevance_score
- relevance_reason

Matching signals:
- same project
- keyword overlap
- tag overlap
- entity overlap
- memory importance
- active status
- strategic memory type

## Endpoint Integration

### POST /capture/preview

Enhancement:
1. Load projects, memories, decisions, and recent tasks.
2. Run Smart Project Linking.
3. Use the suggested project only when no explicit project was provided and confidence is medium or high.
4. Run Related Memory Suggestions.
5. Run Priority Scoring for tasks and decisions.
6. Add cognition metadata inside the existing preview object.

No schema change is required because preview is already a flexible dictionary.

Expected added preview fields:
- suggested_project
- project_linking
- priority_scoring
- related_memories

### POST /capture/confirm

Enhancement:
1. Re-run deterministic project linking.
2. Preserve explicit project if supplied.
3. Use suggested project only when confidence is medium or high.
4. Re-run priority scoring for tasks and decisions.
5. Do not create extra records.
6. Do not save related memory suggestions as hidden writes.

Safety:
- No write happens without CONFIRM CAPTURE.
- No destructive action is introduced.

### GET /dashboard/unified

Enhancement:
- Use scoring to improve focus ranking.
- Show project health summaries.
- Surface blockers and risks.
- Surface next best action.
- Attach related memories to focus tasks where useful.

### GET /priorities/smart

Enhancement:
- Reuse priority_scoring_service.py.
- Keep current response contract.
- Add decision-aware boosts.
- Add related memory influence.
- Keep dry_run: true and writes: false.

### GET /insights

Enhancement:
- Use the cognition layer to detect stalled projects, inactive strategic work, unresolved blockers, overdue chains, and missing next actions.

### GET /planning/weekly

Enhancement:
- Use priority scoring for weekly selection.
- Use memories for recommendations.
- Rebalance overloaded weeks.
- Prioritize strategic projects.
- Keep dry_run: true and writes: false.

## Data Sources

Projects:
- name
- description
- goal
- status
- priority
- category
- tags

Memories:
- text
- summary
- type
- entity
- project
- tags
- importance
- status

Decisions:
- decision
- context
- rationale
- outcome
- tradeoffs
- project
- tags
- status
- importance
- created_at
- updated_at

Tasks:
- task_id
- text
- title
- status
- page_date
- category
- priority
- project
- updated_at
- completion_date

## Implementation Order

Phase 1:
1. Add context_linking_service.py.
2. Add related_memory_service.py.
3. Add priority_scoring_service.py.
4. Enhance capture_preview_service.py.
5. Validate response shape and safety.

Phase 2:
1. Refactor smart_priority_service.py to reuse priority_scoring_service.py.
2. Preserve existing response fields.
3. Add related memory context to ranked tasks.

Phase 3:
1. Enhance unified_dashboard_service.py.
2. Add project health summaries.
3. Add next best action logic.
4. Add blocker and risk explanations.

Phase 4:
1. Enhance insight_service.py.
2. Enhance weekly_planning_service.py.
3. Add blocker, pattern, and cognitive timeline services only as internal modules.

## Validation Requirements

Before commit:
- python -m compileall app
- pytest -q

For Custom GPT schema:
- keep 30 actions or fewer
- no dangling refs
- no /thoughts/*
- no new exposed internal cognition endpoints

Production verification after deploy:
- curl -s https://notebook-task-manager.onrender.com/openapi.json
- curl -s https://notebook-task-manager.onrender.com/capture/preview

## Non-Goals

Do not add:
- /graph/context
- POST /insights/query
- separate expense endpoints
- separate recurring task endpoints
- separate notes/ideas/reflections endpoints
- /thoughts/*
- new public project intelligence endpoints

The cognition layer remains internal unless there is a clear future reason to expose it.
