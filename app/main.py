from fastapi import FastAPI
from app.api.routes import ingest, tasks_update, tasks_delete, tasks_list, tasks_command_center, tasks_archive, tasks_duplicates, tasks_duplicates_plan, tasks_duplicates_archive, recurring_tasks_preview, memory, projects, review, search, summary, health, brief, night_review, focus, decisions, capture, dashboard

app = FastAPI()

app.include_router(ingest.router)
app.include_router(tasks_update.router)
app.include_router(tasks_delete.router)
app.include_router(tasks_list.router)
app.include_router(tasks_command_center.router)
app.include_router(tasks_archive.router)
app.include_router(tasks_duplicates.router)
app.include_router(tasks_duplicates_plan.router)
app.include_router(tasks_duplicates_archive.router)
app.include_router(recurring_tasks_preview.router)
app.include_router(memory.router)
app.include_router(projects.router)
app.include_router(review.router)
app.include_router(search.router)
app.include_router(summary.router)
app.include_router(health.router)
app.include_router(brief.router)
app.include_router(night_review.router)
app.include_router(focus.router)
app.include_router(decisions.router)
app.include_router(capture.router)
app.include_router(dashboard.router)


@app.get("/")
def root():
    return {"message": "API running"}
