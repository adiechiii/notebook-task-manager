from fastapi import FastAPI
from app.api.routes import ingest, tasks_update, tasks_delete, tasks_list

app = FastAPI()

app.include_router(ingest.router)
app.include_router(tasks_update.router)
app.include_router(tasks_delete.router)
app.include_router(tasks_list.router)


@app.get("/")
def root():
    return {"message": "API running"}