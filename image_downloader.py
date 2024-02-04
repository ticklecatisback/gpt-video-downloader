from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from bing_image_downloader import downloader
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import requests
import os
import tempfile
import zipfile


app = FastAPI()

# Path to your service account key file
SERVICE_ACCOUNT_FILE = 'triple-water-379900-cd410b5aff31.json'
SCOPES = ['https://www.googleapis.com/auth/drive.file']
BING_API_KEY = 'd7325b31eb1845b7940decf84ba56e13'

def build_drive_service():
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=credentials)

def upload_file_to_drive(service, file_path, mime_type='application/zip'):
    file_name = os.path.basename(file_path)
    file_metadata = {'name': file_name}
    media = MediaFileUpload(file_path, mimetype=mime_type)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    file_id = file.get('id')
    
    # Change the file permission to make it viewable by anyone with the link
    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
        fields='id'
    ).execute()
    
    return f"https://drive.google.com/uc?id={file_id}"

@app.get("/")
async def root():
    return HTMLResponse(content="<h1>Image Uploader to Google Drive</h1>")

@app.post("/download-images/")
async def download_images(query: str = Query(..., description="The search query for downloading images"),
                          limit: int = Query(1, description="The number of images to download")):
    # Correct function name used here
    image_urls = get_image_urls_for_query(query, count=limit)
    service = build_drive_service()
    uploaded_urls = []

    for image_url in image_urls:
        file_content = download_image_in_memory(image_url)
        file_name = os.path.basename(image_url)  # Extract file name from URL
        try:
            uploaded_url = upload_file_to_drive(service, file_name, file_content)
            uploaded_urls.append(uploaded_url)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload {image_url}: {str(e)}")

    return {"message": "Images uploaded successfully.", "urls": uploaded_urls}

