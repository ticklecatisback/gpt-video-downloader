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
import contextlib

app = FastAPI()

# Path to your service account key file
SERVICE_ACCOUNT_FILE = 'triple-water-379900-cd410b5aff31.json'
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def build_drive_service():
    """Builds a service object for accessing the Google Drive API."""
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('drive', 'v3', credentials=credentials)
    return service

def download_image_in_memory(image_url):
    """Downloads an image directly into memory."""
    response = requests.get(image_url)
    response.raise_for_status()  # Ensure the request was successful
    return BytesIO(response.content)

def upload_file_to_drive(service, file_name, file_content, mime_type='image/jpeg'):
    """Uploads a file from memory to Google Drive and makes it public."""
    file_metadata = {'name': file_name}
    media = MediaIoBaseUpload(file_content, mimetype=mime_type)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    # Make the file viewable by anyone with the link
    permission = {'type': 'anyone', 'role': 'reader'}
    service.permissions().create(fileId=file.get('id'), body=permission).execute()

    return f"https://drive.google.com/uc?id={file.get('id')}"

@app.get("/")
async def root():
    """Root GET endpoint"""
    return HTMLResponse(content="<h1>Image Uploader to Google Drive</h1>")

@app.post("/download-images/")
async def download_images(query: str = Query(..., description="The search query for downloading images"),
                          limit: int = Query(1, description="The number of images to download")):
    """Downloads images based on a query and uploads them to Google Drive."""
    # Implement your logic here to obtain image URLs based on `query`
    # For this example, let's use a placeholder list of image URLs
    image_urls = ["list_of_image_urls_based_on_query"]

    service = build_drive_service()
    uploaded_urls = []

    for image_url in image_urls[:limit]:
        try:
            file_content = download_image_in_memory(image_url)
            file_name = image_url.split("/")[-1]  # Extract file name from URL
            uploaded_url = upload_file_to_drive(service, file_name, file_content)
            uploaded_urls.append(uploaded_url)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload {image_url}: {str(e)}")

    return {"message": "Images uploaded successfully.", "urls": uploaded_urls}
