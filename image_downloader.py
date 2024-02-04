from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
# Assuming you might still want to use requests for other purposes, keeping it imported
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from io import BytesIO
import os
import tempfile
import base64

app = FastAPI()

SERVICE_ACCOUNT_FILE = 'triple-water-379900-cd410b5aff31.json'
SCOPES = ['https://www.googleapis.com/auth/drive']
BING_API_KEY = 'd7325b31eb1845b7940decf84ba56e13'  # If you plan to use Bing Image Search API directly

def build_drive_service():
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=credentials)

def download_image_in_memory(image_url):
    headers = {'User-Agent': 'Mozilla/5.0'}  # Some sites may require a user-agent header
    response = requests.get(image_url, headers=headers)
    response.raise_for_status()
    return BytesIO(response.content)

def upload_file_to_drive(service, file_name, file_content, mime_type='image/jpeg'):
    file_metadata = {'name': file_name}
    media = MediaIoBaseUpload(file_content, mimetype=mime_type, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    # Set file permission if needed
    return f"https://drive.google.com/uc?id={file.get('id')}"

@app.get("/")
async def root():
    return HTMLResponse(content="<h1>Image Uploader to Google Drive</h1>")

@app.post("/download-images/")
async def download_images(query: str = Query(..., description="The search query for downloading images"), 
                          limit: int = Query(1, description="The number of images to download")):
    # This part needs to be adjusted based on how you decide to fetch image URLs
    # For now, it's a placeholder to demonstrate the rest of the flow
    image_urls = ["list_of_image_urls_based_on_query"]
    service = build_drive_service()
    uploaded_urls = []
    for image_url in image_urls:
        try:
            file_content = download_image_in_memory(image_url)
            file_name = os.path.basename(image_url)  # Extract file name from URL
            uploaded_url = upload_file_to_drive(service, file_name, file_content)
            uploaded_urls.append(uploaded_url)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload {image_url}: {str(e)}")
    return {"message": "Images uploaded successfully.", "urls": uploaded_urls}
