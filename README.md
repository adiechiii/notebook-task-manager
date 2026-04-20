# 🧠 Notebook Task Manager

AI-powered task manager using FastAPI + Google Sheets + Custom GPT.

---

## 🚀 Overview

Notebook Task Manager allows you to manage tasks using natural language through a custom GPT connected to a FastAPI backend.

You can:

* ✅ Create tasks from plain text
* ✅ Update tasks (mark as Done)
* ✅ Delete tasks
* ✅ Fetch tasks (All / Pending / Done)

All tasks are stored in Google Sheets as a lightweight database.

---

## 🏗️ Architecture

User (GPT)
↓
FastAPI Backend
↓
Google Sheets (Database)

---

## 🔄 Request Flow

### 1. Create Tasks

User:
"Buy milk and call John"

GPT sends:

```json
POST /ingest/confirm
{
  "text": "Buy milk\\nCall John"
}
```

Backend:

* Splits text into multiple tasks
* Runs extraction service
* Stores tasks in Google Sheets
* Default status = Pending

---

### 2. Update Task

User:
"Mark Buy milk as done"

```json
POST /tasks/update
{
  "text": "Buy milk",
  "status": "Done"
}
```

Backend:

* Finds task by text
* Updates status
* Sets completion date

---

### 3. Delete Task

User:
"Delete Call John"

```json
POST /tasks/delete
{
  "text": "Call John"
}
```

Backend:

* Finds task by text
* Deletes it from sheet

---

### 4. Get Tasks

```bash
GET /tasks
GET /tasks?status=Pending
GET /tasks?status=Done
```

---

## 📊 Google Sheets Structure

Spreadsheet: **NotebookTasksDB**

### 📄 Sheet: `Tasks`

| Column | Name             | Description                        |
| ------ | ---------------- | ---------------------------------- |
| A      | Task ID          | Unique UUID for each task          |
| B      | Raw Text         | Original user input                |
| C      | Normalized Title | Cleaned task text                  |
| D      | Category         | Task category (default: "Unclear") |
| E      | Status           | `Pending` or `Done`                |
| F      | Page Date        | (Optional / unused)                |
| G      | Capture Date     | Task creation timestamp            |
| H      | Source Type      | e.g. `text`                        |
| I      | Source Reference | e.g. `manual`                      |
| J      | Duplicate Flag   | `TRUE` / `FALSE`                   |
| K      | Review Required  | `TRUE` / `FALSE`                   |
| L      | Created At       | Creation timestamp                 |
| M      | Updated At       | Last update timestamp              |
| N      | Completion Date  | When task marked `Done`            |

---

### 📄 Sheet: `StatusLog` (Optional / Not Used)

| Column | Name          | Description     |
| ------ | ------------- | --------------- |
| A      | Log ID        | Unique log ID   |
| B      | Task ID       | Related task    |
| C      | Old Status    | Previous status |
| D      | New Status    | Updated status  |
| E      | Changed At    | Timestamp       |
| F      | Change Source | API / Manual    |

⚠️ Currently **not used in the system**

---

## 📁 Project Structure

```
app/
├── main.py
├── api/routes/
│   ├── ingest.py
│   ├── tasks.py
│   └── health.py
├── schemas/
│   ├── ingest_schema.py
│   ├── update_schema.py
│   ├── delete_schema.py
│   ├── query_schema.py
├── services/
│   ├── task_extraction_service.py
│   ├── duplicate_detection_service.py
│   ├── date_parser_service.py
│   ├── category_service.py
├── repositories/
│   ├── sheets_task_repository.py
│   ├── sheets_status_log_repository.py
├── integrations/
│   └── google_sheets_client.py
├── config/
│   └── env.py
```

---

## ⚙️ Setup

### 1. Clone repository

```bash
git clone <your-repo>
cd notebook-task-manager
```

---

### 2. Create virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### 3. Install dependencies

```bash
pip install fastapi uvicorn gspread google-auth
```

---

### 4. Add credentials

Place your Google service account file:

```bash
credentials.json
```

---

### 5. Share Google Sheet

Share your sheet with:

```
your-service-account-email@project.iam.gserviceaccount.com
```

---

### ▶️ Running the Server

You can run the backend locally (VS Code) or on a VPS.

---

### 💻 Run from VS Code (Local Development)

1. Open project in VS Code
2. Open terminal inside VS Code

Activate virtual environment:

```bash
source .venv/bin/activate
```

Run server:

```bash
uvicorn app.main:app --reload
```

Open in browser:

```
http://127.0.0.1:8000/docs
```

---

### 🌐 Run from VPS (Production / Remote Server)

SSH into your server:

```bash
ssh root@your-server-ip
```

Navigate to project:

```bash
cd /root/notebook-todo-memory
```

Activate environment:

```bash
source .venv/bin/activate
```

Run server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

### 🔗 Expose API with ngrok (for GPT)

Start ngrok:

```bash
ngrok http 8000
```

You will get:

```
https://xxxx.ngrok-free.app
```

Use this URL in your GPT Actions.

---

### ⚠️ Notes

* Always activate `.venv` before running
* Use `--reload` only in development (VS Code)
* Do NOT use `--reload` in VPS production
* Keep ngrok running while using GPT

---

```

Open API docs:

```
http://localhost:8000/docs
```

---

## 🤖 GPT Integration

This project is designed for Custom GPT Actions.

### Key Rules:

* Tasks are identified by **text**
* GPT does NOT use task_id
* Backend resolves everything internally

### Example Output:

1. Buy milk
2. Call John
3. Finish report

---

## 🔐 Security

Never commit:

* credentials.json
* .env
* .venv/

Use `.gitignore` to protect secrets.

---

## ✅ Current Status

* Create → ✔ Working
* Update → ✔ Working
* Delete → ✔ Working
* List → ✔ Working
* GPT Integration → ✔ Working

---

## 🚀 Next Features

* Smart AI task parsing (dates, time)
* Priority system
* Due dates
* Frontend dashboard
* Notifications

---

## 🧠 Design Principles

* Clean layered architecture
* Separation of concerns
* Google Sheets as lightweight DB
* GPT-friendly API design

---

## 📌 Notes

* Requires Google Sheets API enabled
* Requires service account credentials
* Backend must be running for GPT integration

---

## 👨‍💻 Author

Built by you 🚀

---

## 📄 License

MIT (or your choice)
