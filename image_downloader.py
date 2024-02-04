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
async def download_images(query: str = Query(...), limit: int = Query(1)):
    image_urls = get_image_urls(query, count=limit)
    service = build_drive_service()

    # Download images and save them to a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, "images.zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for i, url in enumerate(image_urls):
                try:
                    img_content = download_image(url)
                    img_filename = os.path.join(temp_dir, f"image_{i}.jpg")
                    with open(img_filename, 'wb') as img_file:
                        img_file.write(img_content)
                    zipf.write(img_filename, arcname=f"image_{i}.jpg")
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Failed to download or zip image: {str(e)}")
        
        # Upload the zip file to Google Drive
        uploaded_url = upload_file_to_drive(service, zip_path)
        return {"message": "Zip file uploaded successfully.", "url": uploaded_url}
