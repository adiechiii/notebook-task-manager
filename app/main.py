from fastapi import FastAPI
from app.api.routes import ingest, tasks_update, tasks_delete, tasks_list, tasks_command_center

app = FastAPI()

app.include_router(ingest.router)
app.include_router(tasks_update.router)
app.include_router(tasks_delete.router)
app.include_router(tasks_list.router)
app.include_router(tasks_command_center.router)


@app.get("/")
def root():
    return {"message": "API running"}