from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from bing_image_downloader import downloader
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from io import BytesIO
import requests
import os
import tempfile
import base64

app = FastAPI()

# Path to your service account key file
SERVICE_ACCOUNT_FILE = 'triple-water-379900-cd410b5aff31.json'
SCOPES = ['https://www.googleapis.com/auth/drive']

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=SCOPES)

def build_drive_service():
    """Builds a service object for accessing the Google Drive API."""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('drive', 'v3', credentials=credentials)
    return service

def download_image_in_memory(image_url):
    """Downloads an image directly into memory."""
    response = requests.get(image_url)
    response.raise_for_status()
    return BytesIO(response.content)

def upload_file_to_drive(service, file_name, file_content, mime_type='image/jpeg'):
    """Uploads a file from memory to Google Drive."""
    file_metadata = {'name': file_name}
    media = MediaIoBaseUpload(file_content, mimetype=mime_type, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    # Make the file viewable by anyone with the link
    permission = {
        'type': 'anyone',
        'role': 'reader',
    }
    service.permissions().create(fileId=file.get('id'), body=permission).execute()
    return f"https://drive.google.com/uc?id={file.get('id')}"

@contextlib.contextmanager
def change_dir(destination):
    """Change the working directory temporarily."""
    try:
        cwd = os.getcwd()
        os.chdir(destination)
        yield
    finally:
        os.chdir(cwd)

@contextlib.contextmanager
def change_dir(destination):
    """Change the working directory temporarily."""
    try:
        cwd = os.getcwd()
        os.chdir(destination)
        yield
    finally:
        os.chdir(cwd)


@app.get("/")
async def root():
    return HTMLResponse(content="<h1>Image Uploader to Google Drive</h1>")

@app.post("/download-images/")
async def download_images(query: str = Query(..., description="The search query for downloading images"),
                          limit: int = Query(1, description="The number of images to download")):
    service = build_drive_service()
    uploaded_urls = []
    with tempfile.TemporaryDirectory() as temp_dir:
        with change_dir(temp_dir):
        downloader.download(query, limit=limit, output_dir=temp_dir, adult_filter_off=True, force_replace=False, timeout=60)
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            file_content = download_image_in_memory(file_path)
            try:
                uploaded_url = upload_file_to_drive(service, filename, file_content)
                uploaded_urls.append(uploaded_url)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    return {"message": "Images uploaded successfully.", "urls": uploaded_urls}
