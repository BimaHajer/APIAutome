from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

def get_drive_service():
    credentials = service_account.Credentials.from_service_account_file(
        os.getenv('authentification'),
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    service = build('drive', 'v3', credentials=credentials)
    return service