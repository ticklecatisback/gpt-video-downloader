from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
# Assuming you might still want to use requests for other purposes, keeping it imported
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.http import MediaFileUpload
from io import BytesIO
import os
import tempfile
import base64
import zipfile

app = FastAPI()

SERVICE_ACCOUNT_FILE = 'triple-water-379900-cd410b5aff31.json'
SCOPES = ['https://www.googleapis.com/auth/drive']
BING_API_KEY = 'd7325b31eb1845b7940decf84ba56e13'  # If you plan to use Bing Image Search API directly

def download_image(image_url):
    response = requests.get(image_url)
    response.raise_for_status()
    return response.content
    
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
    # Placeholder: Replace with actual logic to get image URLs based on the query
    image_urls = ["https://example.com/image1.jpg", "https://example.com/image2.jpg"]

    with tempfile.TemporaryDirectory() as temp_dir:
        zip_filename = os.path.join(temp_dir, "images.zip")
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for i, image_url in enumerate(image_urls[:limit], start=1):
                try:
                    image_content = download_image(image_url)
                    image_name = f"image_{i}.jpg"  # Simple naming, adjust as needed
                    image_path = os.path.join(temp_dir, image_name)
                    with open(image_path, 'wb') as image_file:
                        image_file.write(image_content)
                    zipf.write(image_path, arcname=image_name)
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Failed to download {image_url}: {str(e)}")
        
        service = build_drive_service()
        file_metadata = {'name': 'images.zip'}
        media = MediaFileUpload(zip_filename, mimetype='application/zip')
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        file_id = file.get('id')
        drive_url = f"https://drive.google.com/uc?id={file_id}"
        return {"message": "Zip file uploaded successfully.", "url": drive_url}
