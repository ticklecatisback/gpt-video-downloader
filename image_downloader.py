from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from io import BytesIO
import requests
import os

app = FastAPI()

# Update these variables with your actual service account file path and scope
SERVICE_ACCOUNT_FILE = 'triple-water-379900-cd410b5aff31.json'
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def build_drive_service():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('drive', 'v3', credentials=credentials)
    return service

def download_image_in_memory(image_url):
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; YourBotName/1.0; +http://yourwebsite.com/bot.html)'}
    response = requests.get(image_url, headers=headers)
    response.raise_for_status()  # Ensure the download was successful
    return BytesIO(response.content)

def upload_file_to_drive(service, file_name, file_content, mime_type='image/jpeg'):
    file_metadata = {'name': file_name}
    media = MediaIoBaseUpload(file_content, mimetype=mime_type, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return f"https://drive.google.com/uc?id={file['id']}"

def get_image_urls_for_query(query):
    # Placeholder for a function that fetches image URLs for a given query
    # For demonstration purposes, let's return a list with a single image URL
    return [
        "https://cat-world.com/wp-content/uploads/2017/06/spotted-tabby-1.jpg",
    ]

@app.get("/")
async def root():
    return HTMLResponse(content="<h1>Image Uploader to Google Drive</h1>")

@app.post("/download-images/")
async def download_images(query: str = Query(..., description="The search query for downloading images"), limit: int = Query(1, description="The number of images to download")):
    image_urls = get_image_urls_for_query(query)
    service = build_drive_service()
    uploaded_urls = []

    for image_url in image_urls[:limit]:  # Process only up to `limit` images
        try:
            file_content = download_image_in_memory(image_url)
            uploaded_url = upload_file_to_drive(service, os.path.basename(image_url), file_content)
            uploaded_urls.append(uploaded_url)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload {image_url}: {str(e)}")

    return {"message": "Images uploaded successfully.", "urls": uploaded_urls}
