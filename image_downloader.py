from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from io import BytesIO
import requests  # Assuming you're using requests to download images into memory
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
    return f"https://drive.google.com/uc?id={file['id']}"

@app.get("/")
async def root():
    return HTMLResponse(content="<h1>Image Uploader to Google Drive</h1>")

@app.post("/download-images/")
async def download_images(query: str = Query(..., description="The search query for downloading images"),
                          limit: int = Query(1, description="The number of images to download")):
    # Placeholder for actual image URLs to download - you'll need a way to obtain these based on the query
    image_urls = ["URL_TO_IMAGE_BASED_ON_QUERY"]
    service = build_drive_service()
    uploaded_urls = []
    for image_url in image_urls[:limit]:  # Limit the number of images processed
        try:
            file_content = download_image_in_memory(image_url)
            uploaded_url = upload_file_to_drive(service, os.path.basename(image_url), file_content)
            uploaded_urls.append(uploaded_url)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload {image_url}: {str(e)}")
    return {"message": "Images uploaded successfully.", "urls": uploaded_urls}
