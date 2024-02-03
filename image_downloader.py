from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from io import BytesIO
import requests
import os

app = FastAPI()

# Assume this is the path to your service account JSON file
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

def get_image_urls_for_query(query):
    """Fetch image URLs for a given query. This function needs to be implemented."""
    # Implement logic to fetch image URLs based on `query`
    # This could involve calling an external API, web scraping, etc.
    # For demonstration, return a list of hypothetical URLs
    return [
        "https://cat-world.com/wp-content/uploads/2017/06/spotted-tabby-1.jpg",
        # Add more URLs as needed
    ]

@app.get("/")
async def root():
    return HTMLResponse(content="<h1>Image Uploader to Google Drive</h1>")

@app.post("/download-images/")
async def download_images(query: str = Query(..., description="The search query for downloading images"),
                          limit: int = Query(1, description="The number of images to download")):
        headers = {
        'User-Agent': 'Mozilla/5.0 ... Safari/537.3'
    }
    response = requests.get(image_url, headers=headers)
    response.raise_for_status()  # Ensure download was successful

    with open(save_path, 'wb') as image_file:
        image_file.write(response.content)
    image_urls = get_image_urls_for_query(query)
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
