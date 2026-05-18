import json
import os

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


def load_google_credentials(scopes=SCOPES):
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if credentials_path:
        return Credentials.from_service_account_file(credentials_path, scopes=scopes)

    credentials_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if credentials_json:
        credentials_info = json.loads(credentials_json)
        return Credentials.from_service_account_info(credentials_info, scopes=scopes)

    return Credentials.from_service_account_file("credentials.json", scopes=scopes)


def get_gspread_client():
    creds = load_google_credentials()
    return gspread.authorize(creds)


def get_workbook(name="NotebookTasksDB"):
    spreadsheet_id = (
        os.getenv("GOOGLE_SPREADSHEET_ID")
        or os.getenv("GOOGLE_SHEET_ID")
        or os.getenv("NOTEBOOK_TASKS_DB_ID")
    )
    if spreadsheet_id:
        return get_gspread_client().open_by_key(spreadsheet_id)

    return get_gspread_client().open(name)


def get_client():
    return get_gspread_client()
