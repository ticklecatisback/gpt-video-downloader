from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
# Assuming you might still want to use requests for other purposes, keeping it imported
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from io import BytesIO
import os
import tempfile
import base64
import zipfile

app = FastAPI()

SERVICE_ACCOUNT_FILE = 'triple-water-379900-cd410b5aff31.json'
SCOPES = ['https://www.googleapis.com/auth/drive']
BING_API_KEY = 'd7325b31eb1845b7940decf84ba56e13'  # If you plan to use Bing Image Search API directly


def build_drive_service():
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=credentials)

def get_image_urls_for_query(query, limit=5):
    search_url = "https://api.bing.microsoft.com/v7.0/images/search"
    headers = {"Ocp-Apim-Subscription-Key": BING_API_KEY}
    params = {"q": query, "count": limit}
    response = requests.get(search_url, headers=headers, params=params)
    response.raise_for_status()
    search_results = response.json()
    return [img["contentUrl"] for img in search_results["value"]]


def upload_file_to_drive(service, file_name, file_content, mime_type='image/jpeg'):
    file_metadata = {'name': file_name}
    media = MediaIoBaseUpload(file_content, mimetype=mime_type, resumable=True)
    try:
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        file_id = file.get('id')

        # Set the file to be publicly readable
        permission = {
            'type': 'anyone',
            'role': 'reader',
        }
        service.permissions().create(fileId=file_id, body=permission).execute()
        print("Permissions set successfully.")
        
        # Optional: Check if the permission is applied correctly
        permissions = service.permissions().list(fileId=file_id).execute()
        if not any(perm['type'] == 'anyone' and perm['role'] == 'reader' for perm in permissions.get('permissions', [])):
            raise Exception("Failed to set file as publicly readable")

        return f"https://drive.google.com/uc?id={file_id}"
    except HttpError as error:
        print(f'An error occurred: {error}')
        raise HTTPException(status_code=500, detail=f"Failed to upload {file_name}: {str(error)}")




@app.get("/")
async def root():
    return HTMLResponse(content="<h1>Image Uploader to Google Drive</h1>")

@app.post("/download-images/")
async def download_images(query: str = Query(..., description="The search query for downloading images"), 
                          limit: int = Query(1, description="The number of images to download")):
    image_urls = get_image_urls_for_query(query, limit)

    with tempfile.TemporaryDirectory() as temp_dir:
        zip_filename = os.path.join(temp_dir, "images.zip")
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for i, image_url in enumerate(image_urls, start=1):
                try:
                    image_content = requests.get(image_url).content
                    image_name = f"image_{i}.jpg"
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
        drive_url = f"https://drive.google.com/uc?id={file.get('id')}"
        return {"message": "Zip file uploaded successfully.", "url": drive_url}
