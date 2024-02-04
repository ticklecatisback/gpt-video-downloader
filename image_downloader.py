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
BING_API_KEY = 'd7325b31eb1845b7940decf84ba56e13'

def build_drive_service():
    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('drive', 'v3', credentials=credentials)
    return service

def download_image_in_memory(image_url):
    headers = {'User-Agent': 'Your Custom User Agent'}
    response = requests.get(image_url, headers=headers)
    response.raise_for_status()  # Ensure the request was successful
    return BytesIO(response.content)


def upload_file_to_drive(service, file_name, file_content, mime_type='image/jpeg'):
    file_metadata = {'name': file_name}
    media = MediaIoBaseUpload(file_content, mimetype=mime_type)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    permission = {'type': 'anyone', 'role': 'reader'}
    service.permissions().create(fileId=file.get('id'), body=permission).execute()
    return f"https://drive.google.com/uc?id={file.get('id')}"

def get_image_urls_for_query(query, count=5):
    search_url = "https://api.bing.microsoft.com/v7.0/images/search"
    headers = {"Ocp-Apim-Subscription-Key": BING_API_KEY}
    params = {"q": query, "count": count}
    response = requests.get(search_url, headers=headers, params=params)
    response.raise_for_status()
    search_results = response.json()
    return [img["contentUrl"] for img in search_results["value"]]

@app.get("/")
async def root():
    return HTMLResponse(content="<h1>Image Uploader to Google Drive</h1>")

@app.post("/download-images/")
async def download_images(query: str = Query(..., description="The search query for downloading images"),
                          limit: int = Query(4, description="The number of images to download")):
    image_urls = get_image_urls_for_query(query, count=limit)
    if len(image_urls) < limit:
        print(f"Warning: Only {len(image_urls)} images found for '{query}'.")
    # Proceed with downloading and uploading as before

    image_urls = get_image_urls_for_query(query, count=limit)
    service = build_drive_service()
    uploaded_urls = []

    for image_url in image_urls:
        try:
            file_content = download_image_in_memory(image_url)
            file_name = os.path.basename(image_url)  # Extract file name from URL
            uploaded_url = upload_file_to_drive(service, file_name, file_content)
            uploaded_urls.append(uploaded_url)
        except requests.exceptions.HTTPError as e:
            print(f"Failed to download {image_url}: {e}")
            continue  # Skip this image and continue with the next
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload {image_url}: {str(e)}")

    return {"message": "Images uploaded successfully.", "urls": uploaded_urls}
