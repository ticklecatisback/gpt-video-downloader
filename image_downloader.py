from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from bing_image_downloader import downloader
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import tempfile
import os

app = FastAPI()

# Update with the path to your Google service account credentials
SERVICE_ACCOUNT_FILE = 'triple-water-379900-cd410b5aff31.json'
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def build_drive_service():
    """Builds a service object for accessing the Google Drive API."""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('drive', 'v3', credentials=credentials)
    return service

def upload_file_to_drive(service, file_name, file_path, mime_type='image/jpeg'):
    """Uploads a file to Google Drive."""
    file_metadata = {'name': file_name}
    media = MediaFileUpload(file_path, mimetype=mime_type)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return f"https://drive.google.com/uc?id={file['id']}"

@app.get("/")
async def root():
    return HTMLResponse(content="<h1>Image Uploader to Google Drive</h1>")

@app.post("/download-images/")
async def download_images(query: str = Query(..., description="The search query for downloading images"),
                          limit: int = Query(1, description="The number of images to download")):
    service = build_drive_service()
    uploaded_urls = []
    with tempfile.TemporaryDirectory() as temp_dir:
        downloader.download(query, limit=limit, output_dir=temp_dir, adult_filter_off=True, force_replace=False, timeout=60)
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            try:
                uploaded_url = upload_file_to_drive(service, filename, file_path)
                uploaded_urls.append(uploaded_url)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    return {"message": "Images uploaded successfully.", "urls": uploaded_urls}
